#!/usr/bin/env python3
"""Summarize ComfortZone register traffic inside a PCAP dump."""

from __future__ import annotations

import argparse
import struct
import sys
from collections import Counter, defaultdict
from typing import Iterable, Tuple


def iter_udp_payloads(pcap_path: str) -> Iterable[bytes]:
    """Yield every UDP payload (including the ComfortZone frame) from the PCAP."""

    with open(pcap_path, "rb") as fh:
        global_header = fh.read(24)
        if len(global_header) < 24:
            raise SystemExit("PCAP is too short.")

        while True:
            header = fh.read(16)
            if len(header) < 16:
                break
            ts_sec, ts_usec, incl_len, orig_len = struct.unpack("<IIII", header)

            packet = fh.read(incl_len)
            if len(packet) < 34:
                continue

            eth_type = struct.unpack("!H", packet[12:14])[0]
            if eth_type != 0x0800:
                continue

            ihl = (packet[14] & 0x0F) * 4
            proto = packet[23]
            if proto != 17:  # UDP
                continue

            ip_payload_offset = 14 + ihl
            udp_header = packet[ip_payload_offset : ip_payload_offset + 8]
            if len(udp_header) < 8:
                continue
            _, _, udp_len, _ = struct.unpack("!HHHH", udp_header)

            payload = packet[ip_payload_offset + 8 : ip_payload_offset + udp_len]
            if payload:
                yield payload


def parse_register(payload: bytes) -> Tuple[bytes, int, bytes, int]:
    """Return (reg_num, cmd, data_without_crc, crc)."""
    if len(payload) < 22:
        raise ValueError("ComfortZone frame too short.")

    reg_num = payload[12:21]
    cmd = payload[11]
    data = payload[21:]
    crc = data[-1]
    data_without_crc = data[:-1]
    return reg_num, cmd, data_without_crc, crc


def summarize(pcap_path: str, limit_samples: int) -> None:
    seen = Counter()
    cmd_counts: defaultdict[bytes, Counter[int]] = defaultdict(Counter)
    payload_samples: defaultdict[bytes, list[Tuple[bytes, int]]] = defaultdict(list)

    for payload in iter_udp_payloads(pcap_path):
        try:
            reg_num, cmd, data, crc = parse_register(payload)
        except ValueError:
            continue

        seen[reg_num] += 1
        cmd_counts[reg_num][cmd] += 1

        samples = payload_samples[reg_num]
        entry = (data, crc)
        if entry not in samples and len(samples) < limit_samples:
            samples.append(entry)

    if not seen:
        print("No packets parsed.", file=sys.stderr)
        return

    print(f"Total unique registers: {len(seen)}")
    for rank, (reg, count) in enumerate(seen.most_common(), 1):
        cmd_summary = ", ".join(
            f"{chr(cmd)}:{cnt}"
            for cmd, cnt in sorted(cmd_counts[reg].items(), key=lambda item: (-item[1], item[0]))
        )
        reg_str = " ".join(f"{b:02X}" for b in reg)
        print(f"{rank:02d}. {reg_str}  count={count}  cmds={cmd_summary}")

        for idx, (data, crc) in enumerate(payload_samples[reg], 1):
            data_hex = " ".join(f"{b:02X}" for b in data)
            suffix = f" (crc {crc:02X})" if crc is not None else ""
            print(f"    sample {idx:02d}: len={len(data)}{suffix} {data_hex}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pcap",
        nargs="?",
        default="../comfortzone-debug-1.pcap",
        help="Path to the PCAP file that contains the ComfortZone UDP traffic.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=2,
        help="Maximum number of payload samples to keep per register.",
    )
    args = parser.parse_args()

    summarize(args.pcap, args.samples)


if __name__ == "__main__":
    main()
