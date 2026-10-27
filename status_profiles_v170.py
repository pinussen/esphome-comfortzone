#!/usr/bin/env python3
"""Summarize raw status/power pairs without assigning unverified mode names.

Only complete power frames paired with same-device status within two seconds
contribute to ranges. Counts are samples, not time spent in a mode.
"""
import argparse
import json
from pathlib import Path
from pcap_decode_v170 import packets
from status_timeline_v170 import observations

FIELDS = ('frequency_hz', 'output_w', 'additional_w', 'total_w', 'input_w')


def summarize(rows):
    profiles = {}
    for row in rows:
        key = (row['device'], row['status'])
        p = profiles.setdefault(key, dict(device=key[0], status=key[1], samples=0,
            paired=0, unpaired=0, invalid=0, zero_snapshots=0, positive_frequency=0,
            positive_additional=0, inconsistent_total=0, ranges={}, examples={}))
        p['samples'] += 1
        if not row['paired']:
            p['unpaired'] += 1
            continue
        p['paired'] += 1
        if not (0 <= row['frequency_hz'] <= 3276.7 and
                all(0 <= row[f] <= 32767 for f in FIELDS[1:])):
            p['invalid'] += 1
            p['examples'].setdefault('invalid', row)
            continue
        zero = all(row[f] == 0 for f in FIELDS)
        p['zero_snapshots'] += zero
        p['positive_frequency'] += row['frequency_hz'] > 0
        p['positive_additional'] += row['additional_w'] > 0
        p['inconsistent_total'] += row['total_w'] != row['output_w']+row['additional_w']
        p['examples'].setdefault('zero' if zero else 'nonzero', row)
        for f in FIELDS:
            bounds = p['ranges'].setdefault(f, dict(min=row[f], max=row[f]))
            bounds['min'] = min(bounds['min'], row[f])
            bounds['max'] = max(bounds['max'], row[f])
    return dict(profiles=[profiles[k] for k in sorted(profiles)],
                caveats=[__doc__.strip(),
                    'Positive frequency is an observation, not a verified operating-mode label.',
                    'Raw values outside the current signed-16-bit domain are excluded, not interpreted as zero.',
                    'Examples preserve complete original frames; values are never assembled from old fragments.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pcap', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(summarize(observations(packets(args.pcap))), indent=2)+'\n')
