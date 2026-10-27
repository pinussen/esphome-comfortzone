import unittest
from status_profiles_v170 import summarize


def sample(**changes):
    return dict(dict(device='pump', status='202a000010', paired=True,
                     frequency_hz=30, output_w=2400, additional_w=0,
                     total_w=2400, input_w=800), **changes)


class ProfileTest(unittest.TestCase):
    def test_stale_and_invalid_values_do_not_pollute_ranges(self):
        p=summarize([sample(),sample(paired=False,input_w=10000),sample(input_w=65535)])['profiles'][0]
        self.assertEqual(p['ranges']['input_w'],{'min':800,'max':800})
        self.assertEqual((p['paired'],p['unpaired'],p['invalid']),(2,1,1))

    def test_sources_and_profiles_separate_zero_from_missing(self):
        zero=sample(frequency_hz=0,output_w=0,total_w=0,input_w=0)
        rows=summarize([zero,sample(),sample(device='other'),sample(status='2008000010')])['profiles']
        self.assertEqual(len(rows),3)
        p=next(x for x in rows if x['device']=='pump' and x['status']=='202a000010')
        self.assertEqual(p['zero_snapshots'],1)
        self.assertEqual(p['positive_frequency'],1)
        self.assertEqual(set(p['examples']),{'zero','nonzero'})

    def test_additional_and_inconsistent_totals_are_observations(self):
        p=summarize([sample(additional_w=500,total_w=2900),sample(total_w=2500)])['profiles'][0]
        self.assertEqual(p['positive_additional'],1)
        self.assertEqual(p['inconsistent_total'],1)
