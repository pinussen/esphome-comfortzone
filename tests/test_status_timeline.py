import json
from pathlib import Path
import unittest
from status_timeline_v170 import observations
from pcap_decode_v170 import crc8


class StatusTimelineTest(unittest.TestCase):
    def setUp(self):
        rows = json.loads((Path(__file__).parent/'v170_status_fixtures.json').read_text())['frames']
        self.status, self.power = [bytes.fromhex(r['raw']) for r in rows[:2]]

    def test_complete_pair(self):
        result = list(observations([(0,self.status),(.35,self.power)]))[0]
        self.assertEqual(result['status'],'282a000010')
        self.assertTrue(result['paired'])
        self.assertEqual(result['input_w'],769)
        self.assertEqual(result['frequency_hz'],29.2)

    def test_stale_and_wrong_device(self):
        self.assertFalse(list(observations([(0,self.status),(3,self.power)]))[0]['paired'])
        power = bytearray(self.power); power[6] ^= 1; power[-1] = crc8(power[:-1])
        self.assertFalse(list(observations([(0,self.status),(.3,bytes(power))]))[0]['paired'])

    def test_corruption_and_partial(self):
        corrupt = bytearray(self.power); corrupt[-1] ^= 1
        self.assertEqual(list(observations([(0,self.status),(.3,bytes(corrupt))])),[])
        partial = bytearray(self.power[:40]); partial[10]=40; partial[-1]=crc8(partial[:-1])
        self.assertEqual(list(observations([(0,self.status),(.3,bytes(partial))])),[])
