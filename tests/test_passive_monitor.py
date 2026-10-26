from pathlib import Path
import struct
import tempfile
import unittest
from scripts.passive_monitor import udp_record, DiskBudget
from unittest.mock import patch
from types import SimpleNamespace
from pcap_decode_v170 import packets


class MonitorTest(unittest.TestCase):
    def test_size_and_free_space_limits_stop_further_writes(self):
        with patch('scripts.passive_monitor.shutil.disk_usage', return_value=SimpleNamespace(free=10000)):
            b=DiskBudget('.',65536+124,1000)
            self.assertTrue(b.allow(100))
            self.assertFalse(b.allow(1))
            self.assertEqual(b.reason,'capture_size_limit')
            self.assertFalse(b.allow(0))
        with patch('scripts.passive_monitor.shutil.disk_usage', return_value=SimpleNamespace(free=999)):
            b=DiskBudget('.',1024**2,1000)
            self.assertFalse(b.allow(1))
            self.assertEqual(b.reason,'free_disk_space_limit')

    def test_record_roundtrip_and_ip_checksum(self):
        record=udp_record(b'frame', '192.168.3.179','192.168.2.22',9502,19502,123.25)
        words=struct.unpack('!10H',record[30:50])
        total=sum(words)
        while total>>16:
            total=(total&65535)+(total>>16)
        self.assertEqual(total,65535)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'capture.pcap'
            path.write_bytes(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)+record)
            self.assertEqual(list(packets(path)),[(123.25,b'frame')])
