import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import calidad_temporal as temporal
from shapely.geometry import box, shape


class TemporalTests(unittest.TestCase):
    def test_blocks_are_aligned_disjoint_and_preserve_area(self):
        municipality=box(367060,2109880,399140,2133460)
        parts=temporal.blocks(municipality)
        self.assertEqual(len(parts),4)
        self.assertAlmostEqual(sum(shape(p[2]).area for p in parts),municipality.area)
        for i,part in enumerate(parts):
            self.assertTrue(all(value%20==0 for value in part[1]))
            for other in parts[i+1:]:
                self.assertEqual(shape(part[2]).intersection(shape(other[2])).area,0)

    def test_request_uses_calendar_bimonth_and_orbit_dates(self):
        req=temporal.request_for(('2024-B6','2024-11-01','2025-01-01',2),[0,0,20,20],{})
        self.assertEqual(req['aggregation']['aggregationInterval']['of'],'P2M')
        self.assertEqual(req['aggregation']['resx'],20)
        self.assertIn('mosaicking:"ORBIT"',req['aggregation']['evalscript'])
        self.assertIn('dateFrom < TO',req['aggregation']['evalscript'])

    def test_summary_uses_observed_denominator_and_binary_count(self):
        result={'data':[{'outputs':{'temporal':{'bands':{
            'eligible':{'stats':{'sampleCount':100,'noDataCount':20,'mean':0.75}},
            'validMonths':{'stats':{'mean':1.8}}}}}}]}
        summary=temporal.summarize(result)
        self.assertEqual(summary['observados'],80)
        self.assertEqual(summary['elegibles'],60)

    def test_partial_or_empty_response_rejected(self):
        with self.assertRaises(temporal.CDSEError): temporal.summarize({'data':[]})


if __name__=='__main__': unittest.main()
