from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.cartography import load_reference, read, validate_statistics, reference_change, FILES
from server.service import ForestService

DIRECTORY = ROOT / 'data/piloto/mapbiomas'


class CartographyTests(unittest.TestCase):
    def setUp(self):
        self.raw = read(DIRECTORY / 'estadisticas-15110-2016-2025.json')
        self.labels = read(DIRECTORY / 'leyenda.json')['legend']['items']
        self.territory = read(DIRECTORY / 'municipio.json')['territory']
        self.asset = read(DIRECTORY / 'coleccion.json')['subtheme']['asset']

    def check(self):
        return validate_statistics(self.raw, self.labels, self.territory, self.asset)

    def test_real_data_has_verified_units_classes_years_and_provenance(self):
        bundle = load_reference(DIRECTORY)
        self.assertEqual(len(bundle['records']), 10)
        self.assertLess(bundle['maxConservationErrorHa'], 1e-6)
        self.assertFalse(bundle['forestValidated'])
        self.assertFalse(bundle['bimonthlyValidated'])
        row = bundle['records'][-1]
        self.assertAlmostEqual(row['forestHa'], 32280.54728552795, places=6)
        self.assertEqual({c['code'] for c in row['forestClasses']}, {88, 89, 3, 5})

    def test_municipality_and_collection_cannot_be_substituted(self):
        for target, key, bad in [(self.territory, 'geocode', '15106'), (self.asset, 'scale', 10),
                                  (self.asset, 'assetId', 'another-source')]:
            old = target[key]
            target[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError): self.check()
            target[key] = old

    def test_rejects_mixed_units_missing_or_duplicate_years(self):
        original = deepcopy(self.raw)
        for mutate in [lambda x: x.update(unit='km2'), lambda x: x['statistic'].pop(),
                       lambda x: x['statistic'].append(deepcopy(x['statistic'][0])),
                       lambda x: x['statistic'][0].update(year=[2016, 2017])]:
            self.raw = deepcopy(original)
            mutate(self.raw)
            with self.assertRaises(ValueError): self.check()

    def test_rejects_duplicate_aggregate_or_missing_classes(self):
        original = deepcopy(self.raw)
        for mutate in [lambda x: x.pop(), lambda x: x.append(deepcopy(x[0])),
                       lambda x: x[0].update(pixelValue=1)]:
            self.raw = deepcopy(original)
            mutate(self.raw['statistic'][0]['items'])
            with self.assertRaises(ValueError): self.check()

    def test_invalid_areas_and_failed_conservation_reject_publication(self):
        for value in [-1, float('nan'), float('inf'), True, '5', 1e8]:
            self.raw['statistic'][0]['items'][0]['value'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): self.check()

    def test_unobserved_area_is_not_zero_forest_or_extrapolated(self):
        items = self.raw['statistic'][-1]['items']
        next(x for x in items if x['pixelValue'] == 88)['value'] -= 1
        next(x for x in items if x['pixelValue'] == 27)['value'] = 1
        records, _ = self.check()
        self.assertIsNone(records[-1]['forestHa'])
        self.assertEqual(records[-1]['status'], 'cartografia_parcial')
        self.assertIsNone(reference_change(records[-1], records[-2])['ha'])

    def test_changed_reference_files_fail_integrity_check(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for name in FILES | {'procedencia.json'}:
                shutil.copyfile(DIRECTORY / name, folder / name)
            with (folder / 'leyenda.json').open('a', encoding='utf-8') as handle: handle.write(' ')
            with self.assertRaises(ValueError): load_reference(folder)

    def test_changes_require_same_source_boundary_and_immediate_year(self):
        rows = load_reference(DIRECTORY)['records']
        before, after = rows[-2:]
        self.assertAlmostEqual(reference_change(after, before)['ha'], 347.6207806382777)
        for modified in [before | {'source': 'cdse'}, before | {'geometryVersion': 'INEGI'},
                         before | {'sourceFingerprint': 'different'}, before | {'period': '2022'},
                         before | {'period': '2024-B6'}, before | {'forestHa': None}]:
            self.assertIsNone(reference_change(after, modified)['ha'])
        self.assertIsNone(reference_change(after, before, True)['ha'])
        self.assertIsNone(reference_change(after, before | {'forestHa': 0})['pct'])

    def test_api_publishes_reference_only_for_matching_annual_pilot(self):
        with tempfile.TemporaryDirectory() as temp:
            service = ForestService(database=Path(temp) / 'history.sqlite3', cutoff=lambda: '2026-11-26', credentials_ready=False, reference_data=load_reference(DIRECTORY))
            try:
                self.assertTrue(service.status()['annualReferenceAvailable'])
                annual = service.history({'municipality': '15110', 'frequency': 'anual', 'from': '2024', 'to': '2025'})
                self.assertFalse(annual['forestValidated'])
                self.assertAlmostEqual(annual['rows'][1]['forestHa'], 32280.54728552795)
                self.assertAlmostEqual(annual['rows'][0]['referenceHa'], 31872.550151087235)
                self.assertEqual(annual['rows'][1]['status'], 'cartografia_publica')
                bim = service.history({'municipality': '15110', 'frequency': 'bimestral', 'from': '2025-B1', 'to': '2025-B2'})
                self.assertTrue(all(r['forestHa'] is None for r in bim['rows']))
                self.assertIsNone(service.record('15106', '2025')['forestHa'])
                self.assertIsNone(service.record('15110', '2026')['forestHa'])
            finally:
                service.close()

    def test_bad_reference_disables_numbers_without_disabling_cdse_history(self):
        with tempfile.TemporaryDirectory() as temp, patch('server.service.load_state_reference', side_effect=ValueError('bad hash')):
            service = ForestService(database=Path(temp) / 'history.sqlite3', credentials_ready=False)
            try:
                self.assertTrue(service.status()['referenceError'])
                self.assertFalse(service.status()['annualReferenceAvailable'])
                row = service.record('15110', '2025')
                self.assertIsNone(row['forestHa'])
                self.assertIsNotNone(row['observationPct'])
            finally:
                service.close()


if __name__ == '__main__':
    unittest.main()
