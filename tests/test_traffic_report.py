import unittest
from traffic_report_v170 import report
from test_register_coverage import reply


class TrafficReportTest(unittest.TestCase):
    def test_repeats_are_scoped_to_source_range_and_length(self):
        r = report([(0,reply(4,0,b'\0')), (1,reply(4,0,b'\0')),
                    (2,reply(4,0,b'\0\0')), (3,reply(4,0,b'\0',source=b'ABCD')),
                    (4,reply(4,0,b'\1'))])
        self.assertEqual(len(r['ranges']),3)
        row = next(x for x in r['ranges'] if x['source']=='656fde02' and x['payload_bytes']==1)
        self.assertEqual(row['unchanged_from_previous'],1)
        self.assertEqual(row['all_zero_payloads'],2)
        self.assertEqual(row['mean_interval_s'],2)
        self.assertEqual(r['minimum_serial_seconds_19200_8n1'],r['valid_frame_bytes']*10/19200)

    def test_status_changes_preserve_gaps_and_devices(self):
        a=reply(1,0x17,bytes.fromhex('282a000010'))
        b=reply(1,0x17,bytes.fromhex('282e000010'))
        r=report([(0,a),(1,a),(20,b),(21,a)])
        self.assertEqual(r['gap_count'],1)
        self.assertEqual(r['longest_gap_s'],19)
        self.assertEqual(len(r['status_transitions']),2)
        self.assertEqual(sum(x['within_gap_threshold'] for x in r['status_transitions']),1)
        self.assertEqual(r['status_profiles'][0]['count'],3)

    def test_bad_frames_other_versions_and_clock_jump(self):
        r=report([(3,b'bad'),(1,reply(1,0,b'\0',prefix=9)),
                  (2,reply(1,65535,b'\0\0'))])
        self.assertEqual(r['backwards_timestamps'],1)
        self.assertEqual(r['counts']['other_protocol'],1)
        self.assertEqual(r['counts']['overflow_reply'],1)
        self.assertEqual(r['ranges'],[])
        self.assertEqual(report([])['duration_s'],0)
        self.assertIsNone(report([])['serial_time_to_capture_duration'])
