#!/usr/bin/env python3
"""Bounded offline evidence for upstream-inspired 170 candidates, never writes a pump."""
import argparse
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
from pcap_decode_v170 import Frame, PREFIX, packets, valid_frame

# Keep full words/blocks: a plausible low-bit mapping is not proof of semantics.
WINDOWS = {'priority_word': (0x000e, 2),
           'extra_target_and_duration': (0x03ec, 4),
           'post_extra_before_fan': (0x03f0, 11)}


def analyze(stream):
    counts, examples = {}, {}
    checked = lru_cache(maxsize=8192)(valid_frame)
    scanned = rejected = 0
    for timestamp, raw in stream:
        scanned += 1
        if len(raw) < 22 or raw[11:12] != b'r' or raw[12:18] != PREFIX or raw[18] != 0:
            continue
        f = Frame(timestamp, raw)
        covered = {name: f.read(address, size) for name, (address, size) in WINDOWS.items()}
        if not any(value is not None for value in covered.values()):
            continue
        if not checked(raw):
            rejected += 1
            continue
        for name, value in covered.items():
            if value is None:
                continue
            key = (f.device, name)
            counts.setdefault(key, Counter())[value.hex()] += 1
            sample = examples.setdefault((key, value.hex()), {'first': timestamp, 'last': timestamp, 'raw': raw.hex()})
            sample['last'] = timestamp
    return {'packets_scanned': scanned, 'invalid_candidate_frames': rejected,
            'interpretation': 'Candidate evidence only; counts include repeated/overlapping replies.',
            'windows': [{'device': device, 'name': name, 'address': f'00:{WINDOWS[name][0]:04x}',
                         'variants': [{'hex': value, 'count': count, **examples[((device, name), value)]}
                                      for value, count in histogram.most_common()]}
                        for (device, name), histogram in sorted(counts.items())]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pcap', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(packets(args.pcap))
    result['source'] = str(args.pcap.resolve())
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(f"Scanned {result['packets_scanned']} packets; {len(result['windows'])} device/windows; saved {args.output}")
