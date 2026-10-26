#!/usr/bin/env python3
"""Inventory observed register bytes without guessing their physical meaning.

Coverage means addresses documented in the scalar schema, not verified semantics
or successful decoding. Clock, status, floats and history are outside that schema.
Devices and banks are kept separate; no values are synthesized across frames.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from pcap_decode_v170 import Frame, PREFIX, REGISTER_SCHEMA, REGISTER_TYPES, packets, valid_frame


def coverage(stream):
    known = {(f['bank'], a)
             for f in REGISTER_SCHEMA['fields']
             for a in range(int(f['address'], 16), int(f['address'], 16)+REGISTER_TYPES[f['type']][0])}
    observed = defaultdict(dict)
    counts = defaultdict(int)
    for timestamp, raw in stream:
        if not valid_frame(raw) or raw[11:12] != b'r' or raw[12:18] != PREFIX:
            continue
        f = Frame(timestamp, raw)
        if f.address+len(f.data) > 65536:
            continue
        key = (f.device, f.bank)
        counts[key] += 1
        for address, value in enumerate(f.data, f.address):
            item = observed[key].setdefault(address, {'values': set(), 'last': value, 'changes': 0})
            item['changes'] += item['last'] != value
            item['last'] = value
            item['values'].add(value)
    result = []
    for (device, bank), memory in sorted(observed.items()):
        missing = sorted(a for a in memory if (bank, a) not in known)
        runs = []
        for a in missing:
            if not runs or a != runs[-1][-1]+1:
                runs.append([])
            runs[-1].append(a)
        spans = []
        for run in runs:
            spans.append({'start': f'{run[0]:04x}', 'end_exclusive': f'{run[-1]+1:04x}',
                          'bytes': len(run),
                          'changing_bytes': sum(len(memory[a]['values']) > 1 for a in run),
                          'ever_nonzero_bytes': sum(any(memory[a]['values']) for a in run),
                          'max_distinct_byte_values': max(len(memory[a]['values']) for a in run),
                          'last_observed_hex': bytes(memory[a]['last'] for a in run).hex()})
        result.append({'device': device, 'bank': bank, 'read_replies': counts[device, bank],
                       'observed_bytes': len(memory), 'schema_defined_bytes': len(memory)-len(missing),
                       'outside_scalar_schema_bytes': len(missing), 'outside_scalar_schema_ranges': spans})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pcap', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    report = {'capture': str(args.pcap.resolve()), 'coverage': coverage(packets(args.pcap)),
              'caveats': ['Outside scalar schema does not mean wholly unknown: clock/status/history have separate decoders.',
                          'Last observed bytes in a span can come from different timestamps; this is not an atomic snapshot.',
                          'Zero bytes are observed data, not proof of padding or idle traffic.',
                          'Repeated unchanged replies do not prove duplicated messages or fields.']}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    for item in report['coverage']:
        print(item['device'], 'bank', item['bank'], 'observed', item['observed_bytes'],
              'schema', item['schema_defined_bytes'], 'outside', item['outside_scalar_schema_bytes'])


if __name__ == '__main__':
    main()
