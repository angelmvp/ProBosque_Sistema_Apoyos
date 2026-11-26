import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import cdse_piloto as cdse


def feature(item_id, date):
    return {'id': item_id, 'collection': 'sentinel-2-l2a',
            'properties': {'datetime': date},
            'geometry': {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}


class CatalogTests(unittest.TestCase):
    def test_real_transport_requests_geojson_for_catalog_and_json_for_stats(self):
        class Opener:
            def open(self, request, timeout):
                requested.append((request.full_url, request.get_header('Accept')))
                return io.BytesIO(b'{}')
        requested = []
        with patch.object(cdse, 'build_opener', return_value=Opener()):
            cdse.request_json(cdse.CATALOG, {})
            cdse.request_json(cdse.STATS, {})
        self.assertEqual(requested, [(cdse.CATALOG, 'application/geo+json'),
                                     (cdse.STATS, 'application/json')])

    def test_pagination_deduplication_and_exclusive_final_date(self):
        next_url = cdse.PUBLIC + '?token=next-page'
        responses = iter([
            {'type': 'FeatureCollection', 'features': [feature('a', '2025-12-31T10:00:00Z')],
             'links': [{'rel': 'next', 'href': next_url}]},
            {'type': 'FeatureCollection', 'features': [feature('a', '2025-12-31T10:00:00Z'),
              feature('b', '2026-01-01T00:00:00Z')], 'links': []}])
        with contextlib.redirect_stdout(io.StringIO()):
            rows, pages = cdse.fetch_public([0, 0, 1, 1], lambda url: next(responses))
        self.assertEqual(pages, 2)
        self.assertEqual([r['id'] for r in rows], ['a'])

    def test_external_pagination_is_rejected(self):
        response = {'type': 'FeatureCollection', 'features': [],
                    'links': [{'rel': 'next', 'href': 'https://example.com/search'}]}
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(cdse.CDSEError):
            cdse.fetch_public([0, 0, 1, 1], lambda url: response)

    def test_missing_metadata_does_not_publish_partial_success(self):
        response = {'type': 'FeatureCollection', 'features': [{'id': 'incomplete'}]}
        with self.assertRaises(cdse.CDSEError):
            cdse.fetch_public([0, 0, 1, 1], lambda url: response)

    def test_reprocessing_keeps_latest_version_but_distinct_tiles(self):
        common = {'fecha': '2025-01-01T10:00:00Z', 'plataforma': 's2a',
                  'tesela': '14QLG', 'fecha_procesamiento': '2025-01-01'}
        rows = [dict(common, id='old', version_procesamiento='04.00'),
                dict(common, id='new', version_procesamiento='05.11'),
                dict(common, id='neighbor', tesela='14QMG', version_procesamiento='05.11')]
        self.assertEqual({r['id'] for r in cdse.deduplicate(rows)}, {'new', 'neighbor'})

    def test_bimonth_boundaries_and_missing_period_not_zero_forest(self):
        days = [{'fecha': d, 'productos': 2, 'cobertura_geometrica_pct': 100}
                for d in ('2024-12-31', '2025-01-01', '2025-02-28', '2025-03-01')]
        rows = {r['periodo']: r for r in cdse.period_rows(days)}
        self.assertEqual(rows['2024-B6']['dias_con_productos'], 1)
        self.assertEqual(rows['2025-B1']['dias_con_productos'], 2)
        self.assertEqual(rows['2025-B2']['dias_con_productos'], 1)
        self.assertEqual(rows['2025-B3']['dias_con_productos'], 0)
        self.assertIsNone(rows['2025-B3']['superficie_forestal_ha'])
        self.assertFalse(rows['2025-B1']['calidad_pixeles_verificada'])


class AuthTests(unittest.TestCase):
    def test_credentials_preserve_literal_symbols_and_env_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / '.env'
            file.write_text('CDSE_CLIENT_ID=file-id\nCDSE_CLIENT_SECRET="a#b=c$literal"\n', encoding='utf-8')
            values = cdse.load_credentials(file, {'CDSE_CLIENT_ID': 'env-id'})
            self.assertEqual(values, {'CDSE_CLIENT_ID': 'env-id', 'CDSE_CLIENT_SECRET': 'a#b=c$literal'})

    def test_missing_credentials_message_has_no_values(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(cdse.CDSEError) as ctx:
                cdse.load_credentials(Path(folder) / 'absent', {'CDSE_CLIENT_ID': 'not-for-output'})
            self.assertNotIn('not-for-output', str(ctx.exception))

    def test_reuse_token_then_renew_expired_token(self):
        calls = []
        def transport(url, payload=None, **kwargs):
            calls.append(url)
            if url == cdse.TOKEN:
                return {'access_token': 'fake-token', 'expires_in': 300}
            return {'type': 'FeatureCollection', 'features': []}
        client = cdse.SentinelHubClient({'CDSE_CLIENT_ID': 'fake-id', 'CDSE_CLIENT_SECRET': 'fake-secret'}, transport)
        client.request(cdse.CATALOG, {})
        client.request(cdse.CATALOG, {})
        self.assertEqual(calls.count(cdse.TOKEN), 1)
        client._expires = 0
        client.request(cdse.CATALOG, {})
        self.assertEqual(calls.count(cdse.TOKEN), 2)

    def test_token_not_sent_to_public_or_unknown_endpoint(self):
        calls = []
        client = cdse.SentinelHubClient({}, lambda *args, **kwargs: calls.append(args))
        with self.assertRaises(cdse.CDSEError):
            client.request(cdse.PUBLIC, {})
        self.assertEqual(calls, [])

    def test_401_renews_once_then_returns_result(self):
        tokens, requests = [], []
        def transport(url, payload=None, **kwargs):
            if url == cdse.TOKEN:
                tokens.append(1)
                return {'access_token': 'fake', 'expires_in': 300}
            requests.append(1)
            if len(requests) == 1:
                raise cdse.CDSEHTTPError(401, 'HTTP 401')
            return {'ok': True}
        client = cdse.SentinelHubClient({'CDSE_CLIENT_ID': 'fake', 'CDSE_CLIENT_SECRET': 'fake'}, transport)
        self.assertEqual(client.request(cdse.CATALOG, {}), {'ok': True})
        self.assertEqual(len(tokens), 2)


class QualityTests(unittest.TestCase):
    def test_daily_window_handles_year_boundary(self):
        payload = cdse.quality_request('2025-12-31', {'type': 'Polygon', 'coordinates': []})
        self.assertEqual(payload['aggregation']['timeRange']['to'], '2026-01-01T00:00:00Z')
        self.assertEqual(payload['aggregation']['resx'], 100)
        self.assertIn('dataMask: [s.dataMask]', payload['aggregation']['evalscript'])

    def test_quality_denominator_is_observed_pixels(self):
        response = {'data': [{'outputs': {'utilizable': {'bands': {'B0': {'stats': {
            'sampleCount': 100, 'noDataCount': 20, 'mean': 0.75}}}}}}]}
        result = cdse.summarize_quality(response)[0]
        self.assertEqual(result['pixeles_observados_muestra'], 80)
        self.assertEqual(result['pct_scl_utilizable_entre_pixeles_observados'], 75)

    def test_no_data_does_not_become_zero_quality(self):
        response = {'data': [{'outputs': {'utilizable': {'bands': {'B0': {'stats': {
            'sampleCount': 100, 'noDataCount': 100, 'mean': 'NaN'}}}}}}]}
        self.assertIsNone(cdse.summarize_quality(response)[0]['pct_scl_utilizable_entre_pixeles_observados'])


if __name__ == '__main__':
    unittest.main()
