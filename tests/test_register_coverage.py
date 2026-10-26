import unittest
from register_coverage_v170 import coverage
from pcap_decode_v170 import crc8


def reply(bank, address, payload, source=b'\x65\x6f\xde\x02', command=b'r', prefix=8):
    dest=b'ADDR'
    raw=bytearray(dest+bytes([crc8(dest),crc8(bytes(x^255 for x in dest))])+source+
                  bytes([22+len(payload)])+command+b'\x01\x02\x03\x04\x0b'+bytes([prefix,bank])+
                  address.to_bytes(2,'little')+payload)
    raw.append(crc8(raw))
    return bytes(raw)


class CoverageTest(unittest.TestCase):
    def test_overlaps_and_repeated_zeros_are_not_double_counted(self):
        r=coverage([(1,reply(4,0,b'\0\x01\x02')), (2,reply(4,1,b'\x01\x03'))])[0]
        self.assertEqual(r['observed_bytes'],3)
        self.assertEqual(r['read_replies'],2)
        span=r['outside_scalar_schema_ranges'][0]
        self.assertEqual(span['last_observed_hex'],'000103')
        self.assertEqual(span['changing_bytes'],1)
        self.assertEqual(span['ever_nonzero_bytes'],2)

    def test_schema_addresses_not_field_validity(self):
        r=coverage([(1,reply(0,0x2a5,b'\xff'))])[0]
        self.assertEqual(r['schema_defined_bytes'],1) # invalid value still has a documented address
        self.assertEqual(r['outside_scalar_schema_bytes'],0)

    def test_sources_banks_and_disjoint_ranges(self):
        rows=coverage([(1,reply(4,0,b'\1')), (2,reply(4,2,b'\2')),
                       (3,reply(5,0,b'\3')), (4,reply(4,0,b'\4',source=b'ABCD'))])
        self.assertEqual(len(rows),3)
        source=next(x for x in rows if x['device']=='656fde02' and x['bank']==4)
        self.assertEqual(len(source['outside_scalar_schema_ranges']),2)

    def test_wrong_command_protocol_crc_and_overflow(self):
        good=reply(4,0,b'\1')
        bad=good[:-1]+bytes([good[-1]^1])
        rows=coverage([(1,bad),(2,reply(4,0,b'\1',command=b'R')),
                       (3,reply(4,0,b'\1',prefix=9)),(4,reply(4,65535,b'\1\2'))])
        self.assertEqual(rows,[])
