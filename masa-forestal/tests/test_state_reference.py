"""Comprobaciones de identidad, cobertura y publicación de los 125 municipios."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from server.cartography import reference_change
from server.service import ForestService
from server.state_reference import load_state_reference

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'data/mapbiomas-edomex'
CATALOG = ROOT / 'data/municipios/catalogo.json'


class StateReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_state_reference(DIRECTORY, CATALOG, strict=True)

    def test_every_municipality_has_its_own_ten_conserved_annual_maps(self):
        municipalities = self.bundle['municipalities']
        expected = {r['cvegeo'] for r in json.loads(CATALOG.read_text(encoding='utf-8'))['municipios']}
        self.assertEqual(set(municipalities), expected)
        self.assertEqual(len(municipalities), 125)
        self.assertEqual(len({m['sourceFingerprint'] for m in municipalities.values()}), 125)
        self.assertEqual(self.bundle['errors'], {})
        for code, data in municipalities.items():
            with self.subTest(municipality=code):
                self.assertLess(data['maxConservationErrorHa'], 1e-6)
                self.assertEqual({r['period'] for r in data['records']}, {str(y) for y in range(2016, 2026)})
                for row in data['records']:
                    self.assertEqual(row['municipality'], code)
                    self.assertFalse(row['forestValidated'])
                    self.assertEqual(row['status'], 'cartografia_publica')
                    self.assertGreaterEqual(row['forestHa'], 0)
                    self.assertLessEqual(row['forestHa'], row['referenceAreaHa'])
                    self.assertAlmostEqual(row['forestHa'], sum(c['ha'] for c in row['forestClasses']))

    def test_zero_forest_is_a_real_cartographic_value_and_not_missing_data(self):
        rows = self.bundle['municipalities']['15030']['records']
        self.assertTrue(all(r['forestHa'] == 0 for r in rows))
        self.assertEqual(reference_change(rows[-1], rows[-2]), {'ha': 0, 'pct': None})

    def test_changes_cannot_mix_municipalities_even_if_other_metadata_matches(self):
        before, after = self.bundle['municipalities']['15110']['records'][-2:]
        self.assertIsNone(reference_change(after, before | {'municipality': '15106'})['ha'])

    def test_tampering_quarantines_one_municipality_and_strict_export_rejects_it(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'reference'
            shutil.copytree(DIRECTORY, folder)
            with (folder / 'estadisticas/15106.json').open('a', encoding='utf-8') as handle:
                handle.write(' ')
            loaded = load_state_reference(folder, CATALOG)
            self.assertEqual(set(loaded['errors']), {'15106'})
            self.assertEqual(len(loaded['municipalities']), 124)
            self.assertIn('15110', loaded['municipalities'])
            with self.assertRaises(ValueError):
                load_state_reference(folder, CATALOG, strict=True)
            service = ForestService(database=Path(temp) / 'history.sqlite3', reference_data=loaded, credentials_ready=False)
            try:
                self.assertEqual(service.record('15106', '2025')['status'], 'referencia_invalida')
                self.assertIsNone(service.record('15106', '2025')['forestHa'])
                self.assertGreater(service.record('15110', '2025')['forestHa'], 0)
                self.assertEqual(service.status()['referenceErrors'], ['15106'])
            finally:
                service.close()

    def test_a_changed_catalog_invalidates_the_reference_mapping(self):
        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp) / 'catalog.json'
            catalog.write_bytes(CATALOG.read_bytes() + b' ')
            with self.assertRaises(ValueError):
                load_state_reference(DIRECTORY, catalog)

    def test_api_returns_each_municipality_history_without_cdse_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            service = ForestService(database=Path(temp) / 'history.sqlite3', cutoff=lambda: '2026-11-26', credentials_ready=False)
            try:
                self.assertEqual(len(service.status()['referenceMunicipalities']), 125)
                for code in self.bundle['municipalities']:
                    result = service.history({'municipality': code, 'frequency': 'anual', 'from': '2017', 'to': '2025'})
                    self.assertEqual(len(result['rows']), 9)
                    expected = self.bundle['municipalities'][code]['records']
                    for row, previous, actual in zip(result['rows'], expected, expected[1:]):
                        self.assertEqual(row['municipality'], code)
                        self.assertEqual(row['forestHa'], actual['forestHa'])
                        self.assertEqual(row['referenceHa'], previous['forestHa'])
                        self.assertAlmostEqual(row['change']['ha'], actual['forestHa'] - previous['forestHa'])
                    bim = service.history({'municipality': code, 'frequency': 'bimestral', 'from': '2025-B1', 'to': '2025-B6'})
                    self.assertTrue(all(r['forestHa'] is None and r['change']['ha'] is None for r in bim['rows']))
                    self.assertIsNone(service.record(code, '2026')['forestHa'])
                self.assertAlmostEqual(service.record('15106', '2025')['forestHa'], 9428.05491685701)
                self.assertAlmostEqual(service.record('15058', '2025')['forestHa'], 42.298848724365236)
            finally:
                service.close()


if __name__ == '__main__':
    unittest.main()
