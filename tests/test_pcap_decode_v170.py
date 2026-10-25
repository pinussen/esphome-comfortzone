"""Capture-backed checks for offline reconstruction, without live equipment."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pcap_decode_v170 import Frame, decode_fields, event_snapshot, valid_frame

FIXTURES = json.loads(Path(__file__).with_name('v170_capture_fixtures.json').read_text())['frames']


def frame(reg, time=100):
    return Frame(time, bytes.fromhex(FIXTURES[reg]))


class DecodeTest(unittest.TestCase):
    def test_frequency_through_hot_water_and_stop(self):
        cases = json.loads(Path(__file__).with_name('v170_frequency_fixtures.json').read_text())['frames']
        for case in cases:
            f = Frame(0, bytes.fromhex(case['raw']))
            self.assertTrue(valid_frame(f.raw))
            values = decode_fields(f)
            self.assertEqual(values['compressor_frequency_raw'], case['actual_frequency_raw'])
            self.assertEqual(values['compressor_output_w'], case['output_w'])
        self.assertEqual(cases[-1]['actual_frequency_raw'], 0)
        self.assertNotEqual(cases[-1]['legacy_frequency_raw'], 0)

    def test_panel_confirmed_heating_samples(self):
        samples = json.loads(Path(__file__).with_name('v170_panel_heating_fixtures.json').read_text())
        for sample in samples['observations']:
            power = Frame(0, bytes.fromhex(sample['power_reply']['raw']))
            status = Frame(0, bytes.fromhex(sample['preceding_status_reply']['raw']))
            self.assertTrue(valid_frame(power.raw))
            self.assertTrue(valid_frame(status.raw))
            self.assertEqual(power.device, status.device)
            decoded = decode_fields(power)
            self.assertAlmostEqual(decoded['compressor_frequency_raw'] / 10,
                                   sample['panel_frequency_hz'])
            self.assertEqual(decoded['compressor_output_w'], sample['panel_power_w'])
            self.assertEqual(decoded['additional_power_w'], sample['panel_additional_power_w'])
            self.assertEqual(status.read(0x18, 1), b'\x2a')
            # Evidence for this observed heating state, not all enum/bit meanings.

    def test_crc_rejects_corruption_and_truncation(self):
        for raw in FIXTURES.values():
            p = bytes.fromhex(raw)
            self.assertTrue(valid_frame(p))
            self.assertFalse(valid_frame(p[:-1]))
            self.assertFalse(valid_frame(p[:21]+bytes([p[21] ^ 1])+p[22:]))

    def test_short_sensor_reply_has_same_addresses(self):
        full = decode_fields(frame('010000'))
        short = decode_fields(frame('010400'))
        # These slow-changing sensors agree despite different sample times.
        for k in ('te0_c','te1_c','te2_c','te3_c','te10_c','te24_c'):
            self.assertEqual(full[k], short[k])
        self.assertEqual(short['pump_datetime'], '2026-10-24T23:30:31')
        self.assertEqual(short['te24_c'], 51.7)
        self.assertIsNone(frame('010400').read(0x63, 2))

    def test_short_counter_suffix(self):
        a = decode_fields(frame('050000'))
        b = decode_fields(frame('052c00'))
        self.assertEqual(a, b)
        self.assertEqual(b['total_runtime_minutes'], 4747708)

    def test_float_candidates(self):
        values = decode_fields(frame('01b200'))
        for key in ('candidate_float_temperatures_00e1', 'candidate_float_temperatures_0111'):
            self.assertEqual(len(values[key]), 12)
            self.assertAlmostEqual(values[key][0], 10.3, places=3)
            self.assertAlmostEqual(values[key][7], 51.7, places=3)

    def test_settings_capture(self):
        settings = json.loads(Path(__file__).with_name('v170_settings_fixtures.json').read_text())['frames']
        decoded = {}
        for raw in settings.values():
            packet = bytes.fromhex(raw)
            self.assertTrue(valid_frame(packet))
            decoded.update(decode_fields(Frame(0, packet)))
        self.assertEqual(decoded['hot_water_setting_c'], 53.1)
        self.assertEqual(decoded['heating_curve'], 5)
        self.assertEqual(decoded['fan_mode'], 1)
        self.assertEqual(decoded['hot_water_max_runtime_minutes'], 30)
        self.assertEqual(decoded['hot_water_pause_minutes'], 20)
        self.assertEqual(decoded['hot_water_min_frequency_hz'], 30)
        self.assertEqual(decoded['hot_water_max_frequency_hz'], 55)
        self.assertEqual(decoded['extra_hot_water_target_c'], 70)
        self.assertEqual(decoded['extra_hot_water_minutes'], 180)
        self.assertEqual(decoded['normal_fan_percent'], 87)

    def test_six_byte_clock(self):
        raw = frame('010400').raw[:27] + b'\x00'
        decoded = decode_fields(Frame(0, raw))
        self.assertEqual(decoded['pump_datetime'], '2026-10-24T23:30:31')
        self.assertNotIn('weekday_raw', decoded)

    def test_event_records_cross_frame_boundaries(self):
        parts = [frame(r, 100+i) for i,r in enumerate(('03150d','03c70d','03790e'))]
        latest = {(p.device,p.bank,p.address): p for p in parts}
        result = event_snapshot(latest, parts[-1])
        self.assertEqual(len(result['records']), 30)
        self.assertTrue(all(r['datetime'] is not None for r in result['records']))
        self.assertEqual(result['header_raw'], 26)
        self.assertEqual(result['records'][12]['datetime'], '2026-06-19T22:25:31')
        self.assertEqual(result['records'][25]['datetime'], '2026-10-16T07:50:45')
        self.assertIsNone(event_snapshot(latest, frame('03790e', 120)))
        del latest[parts[0].device,3,0xd15]
        self.assertIsNone(event_snapshot(latest, parts[-1]))
        # Another pump's blocks cannot complete this pump's history.
        latest['different',3,0xd15] = parts[0]
        self.assertIsNone(event_snapshot(latest, parts[-1]))


if __name__ == '__main__':
    unittest.main()
