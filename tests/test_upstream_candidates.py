import json
from pathlib import Path
import unittest
from upstream_candidates_v170 import analyze
from pcap_decode_v170 import crc8

ROOT = Path(__file__).resolve().parents[1]

class UpstreamCandidatesTest(unittest.TestCase):
    def test_real_frames_crc_and_complete_windows(self):
        settings=json.loads((ROOT/'tests/v170_settings_fixtures.json').read_text())
        raw=bytes.fromhex(settings['frames']['00d203'])
        corrupt=raw[:-1]+bytes([raw[-1]^1])
        result=analyze([(1,raw),(2,corrupt),(3,raw)])
        self.assertEqual(result['invalid_candidate_frames'],1)
        windows={w['name']:w for w in result['windows']}
        self.assertEqual(set(windows),{'extra_target_and_duration','post_extra_before_fan'})
        self.assertEqual(windows['extra_target_and_duration']['variants'][0]['hex'],'bc02b400')
        self.assertEqual(windows['post_extra_before_fan']['variants'][0]['hex'],'32000a0a26023300580201')
        self.assertEqual(windows['post_extra_before_fan']['variants'][0]['count'],2)

    def test_source_isolation_and_other_protocol(self):
        fixture=json.loads((ROOT/'tests/v170_priority_candidates.json').read_text())
        raw=bytes.fromhex(fixture['frames'][0]['raw'])
        other=bytearray(raw); other[6]^=1; other[-1]=crc8(other[:-1])
        result=analyze([(1,raw),(2,bytes(other)),(3,bytes.fromhex(fixture['frames'][1]['raw']))])
        self.assertEqual(len(result['windows']),2)
        for window in result['windows']:
            self.assertEqual(window['variants'][0]['hex'],'5241')
            self.assertEqual(window['variants'][0]['count'],1)
