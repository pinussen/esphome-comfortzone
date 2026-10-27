import unittest
import json
from pathlib import Path
from status_profiles_v170 import summarize
from status_timeline_v170 import observations
from pcap_decode_v170 import Frame, valid_frame


def sample(**changes):
    return dict(dict(device='pump', status='202a000010', paired=True,
                     frequency_hz=30, output_w=2400, additional_w=0,
                     total_w=2400, input_w=800), **changes)


class ProfileTest(unittest.TestCase):
    def test_flag_mirror_hypothesis_has_captured_counterexamples(self):
        data=json.loads((Path(__file__).parent/'v170_flag_counterexamples.json').read_text())
        values=set()
        for example in data['examples'].values():
            self.assertTrue(0 <= example['status_age'] <= 2)
            a,b=[bytes.fromhex(example[k]) for k in ('status_frame','candidate_frame')]
            self.assertTrue(valid_frame(a) and valid_frame(b))
            fa,fb=Frame(0,a),Frame(0,b)
            self.assertEqual(fa.device,fb.device)
            values.add((fa.read(0x17,1)[0],fb.read(0xc3,1)[0]))
        self.assertEqual(values,{(0x20,0),(0x20,1),(0x28,0),(0x28,1)})

    def test_captured_heating_request_channels(self):
        frames=json.loads((Path(__file__).parent/'v170_status_fixtures.json').read_text())['frames']
        pair=[r for r in frames if r['label'].startswith('202a000010')]
        stream=[(i*.35,bytes.fromhex(r['raw'])) for i,r in enumerate(pair)]
        p=summarize(observations(stream))['profiles'][0]
        self.assertEqual(p['candidate_request_patterns'],{'heating_only':1})

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
