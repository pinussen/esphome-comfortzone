import json
from pathlib import Path
import unittest
from pcap_decode_v170 import Frame, valid_frame
from status_timeline_v170 import observations


class WeekCaptureTest(unittest.TestCase):
    def test_heater_register_in_original_frames(self):
        samples = json.loads((Path(__file__).parent / 'v170_week_fixtures.json').read_text())['samples']
        nonzero = 0
        for sample in samples:
            status = bytes.fromhex(sample['status_frame'])
            power = bytes.fromhex(sample['power_frame'])
            self.assertTrue(valid_frame(status) and valid_frame(power))
            frame = Frame(0, power)
            heater = int.from_bytes(frame.read(0x315, 2), 'little')
            row = list(observations([(0, status), (sample['status_age_s'], power)]))[0]
            self.assertTrue(row['paired'])
            self.assertEqual(row['additional_w'], heater)
            self.assertEqual(row['total_w'], row['output_w'] + heater)
            nonzero += heater > 0
        self.assertGreater(nonzero, 0)
