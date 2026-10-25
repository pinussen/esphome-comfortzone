#!/usr/bin/env python3
"""Print complete status/power observations for protocol 170, without assigning modes.

CSV preserves source frame bytes and status age. A status older than two seconds
is shown but not marked paired. Replies from different devices never mix.
"""
import argparse
import csv
from datetime import datetime, timezone
import sys
from pcap_decode_v170 import Frame, PREFIX, packets, valid_frame


def observations(stream):
    statuses = {}
    for time, raw in stream:
        if not valid_frame(raw) or raw[11:12] != b'r' or raw[12:18] != PREFIX:
            continue
        f = Frame(time, raw)
        if f.bank != 1 or f.address + len(f.data) > 65536:
            continue
        status = f.read(0x17, 5)
        if status is not None:
            statuses[f.device] = (time, status, raw)
        power = f.read(0x2e9, 0x323-0x2e9)
        if power is None:
            continue
        previous = statuses.get(f.device)
        age = time-previous[0] if previous else None
        values = [int.from_bytes(f.read(a,2),'little') for a in (0x2e9,0x313,0x317,0x319,0x321)]
        yield dict(time_utc=datetime.fromtimestamp(time, timezone.utc).isoformat(), device=f.device,
                   status=previous[1].hex() if previous else '', status_age_s=round(age,3) if age is not None else '',
                   paired=age is not None and 0 <= age <= 2,
                   frequency_hz=values[0]/10, output_w=values[1], additional_w=values[2],
                   total_w=values[3], input_w=values[4],
                   status_frame=previous[2].hex() if previous else '', power_frame=raw.hex())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pcap')
    args = parser.parse_args()
    writer = None
    for row in observations(packets(args.pcap)):
        if writer is None:
            writer = csv.DictWriter(sys.stdout, fieldnames=row.keys())
            writer.writeheader()
        writer.writerow(row)


if __name__ == '__main__':
    main()
