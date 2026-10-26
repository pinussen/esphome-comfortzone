#!/usr/bin/env python3
"""Streaming capture report: repeated replies, polling, gaps and raw status.

Equal payloads are unchanged observations, not evidence of redundant protocol
messages. Capture gaps can be UDP/network loss, forwarding expiry or a quiet
bus; they are not proof of a pump restart. No guessed operating modes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from pcap_decode_v170 import Frame, PREFIX, packets, valid_frame


def report(stream, gap_seconds=15):
    counts = Counter()
    ranges = {}
    statuses = {}
    previous_status = {}
    transitions = Counter()
    first = last = previous_time = None
    gaps = []
    gap_count = backwards = valid_bytes = 0
    longest_gap = 0
    # Keep only the most recent 100 gaps, not a day-long list of frame objects.
    for timestamp, raw in stream:
        counts['datagrams'] += 1
        if first is None:
            first = timestamp
        last = timestamp
        if previous_time is not None:
            delta = timestamp-previous_time
            backwards += delta < 0
            if delta > gap_seconds:
                gap_count += 1
                longest_gap = max(longest_gap, delta)
                gaps.append(dict(start=previous_time, end=timestamp, seconds=delta))
                gaps = gaps[-100:]
        previous_time = timestamp
        if not valid_frame(raw):
            counts['invalid_or_non_frame'] += 1
            continue
        counts['valid_frames'] += 1
        valid_bytes += len(raw)
        counts[chr(raw[11])] += 1
        if raw[12:18] != PREFIX:
            counts['other_protocol'] += 1
            continue
        if raw[11:12] != b'r':
            continue
        f = Frame(timestamp, raw)
        if f.address+len(f.data) > 65536:
            counts['overflow_reply'] += 1
            continue
        key = (f.device, raw[:4].hex(), f.bank, f.address, len(f.data))
        item = ranges.setdefault(key, dict(count=0, unchanged=0, all_zero=0,
            first=timestamp, last=timestamp, interval_count=0, interval_sum=0.,
            min_interval=None, max_interval=None, previous=None))
        if item['count']:
            delta = timestamp-item['last']
            if delta >= 0:
                item['interval_count'] += 1
                item['interval_sum'] += delta
                item['min_interval'] = delta if item['min_interval'] is None else min(item['min_interval'], delta)
                item['max_interval'] = delta if item['max_interval'] is None else max(item['max_interval'], delta)
            item['unchanged'] += item['previous'] == f.data
        item['count'] += 1
        item['all_zero'] += bool(f.data) and not any(f.data)
        item['last'] = timestamp
        item['previous'] = f.data
        if f.bank == 1 and (status := f.read(0x17, 5)) is not None:
            code = status.hex()
            # A status transition is between observations, not necessarily an
            # uninterrupted physical transition. Preserve the time gap.
            skey = (f.device, code)
            s = statuses.setdefault(skey, dict(count=0, first=timestamp, last=timestamp))
            s['count'] += 1
            s['last'] = timestamp
            old = previous_status.get(f.device)
            if old and old[0] != code:
                transitions[(f.device, old[0], code, 0 <= timestamp-old[1] <= gap_seconds)] += 1
            previous_status[f.device] = (code, timestamp)
    rows = []
    for (source, destination, bank, address, size), item in sorted(ranges.items()):
        rows.append(dict(source=source, destination=destination, bank=bank,
            address=f'{address:04x}', payload_bytes=size, replies=item['count'],
            unchanged_from_previous=item['unchanged'], all_zero_payloads=item['all_zero'],
            first=item['first'], last=item['last'],
            mean_interval_s=item['interval_sum']/item['interval_count'] if item['interval_count'] else None,
            min_interval_s=item['min_interval'], max_interval_s=item['max_interval']))
    return dict(counts=dict(counts), first=first, last=last,
        duration_s=last-first if first is not None else 0,
        valid_frame_bytes=valid_bytes,
        minimum_serial_seconds_19200_8n1=valid_bytes*10/19200,
        serial_time_to_capture_duration=(valid_bytes*10/19200/(last-first)
                                        if first is not None and last>first else None),
        backwards_timestamps=backwards, gap_threshold_s=gap_seconds,
        gap_count=gap_count, longest_gap_s=longest_gap, last_gaps=gaps,
        ranges=rows,
        status_profiles=[dict(device=d, raw=s, **v) for (d,s),v in sorted(statuses.items())],
        status_transitions=[dict(device=d, before=a, after=b, within_gap_threshold=continuous, observations=n)
                            for (d,a,b,continuous),n in sorted(transitions.items())],
        caveats=[__doc__.strip(), 'Status counts are observations, not elapsed time in a mode.',
                 'Intervals are UDP receipt intervals, not measured serial polling intervals.',
                 'Serial-time ratio assumes one 19200 baud 8N1 bus, one copy per frame and faithful capture timing. A ratio over one contradicts those assumptions; it does not identify the cause.',
                 'No packets before the first or after the last timestamp can be assessed from PCAP alone.',
                 'Overlapping blocks are inventoried separately; no assembled values or inferred names.'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pcap', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = report(packets(args.pcap))
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('counts','duration_s','gap_count','status_profiles','status_transitions')}, indent=2))
