#!/usr/bin/env python3

from glob import glob
from os import path

import os
import sys
import argparse

TARGET_VID_PIDS = [
    (0x088D, 0x062E),  # llTECH Wireless-Receiver (Wire)
    (0x089D, 0x062F)   # ll TECH USB Gaming Mouse (Wireless)
]

POLLING_RATE_MAP = {
    125: 0x08,
    250: 0x04,
    500: 0x02,
    1000: 0x01
}

REPORT_DESCRIPTOR = bytes.fromhex("0602ff0900a10119002aff00150026ff00750895208101750895209101c0")

def interfaces() -> list[str]:
    ifs: list[str] = []
    for hidraw in glob("/sys/class/hidraw/hidraw*"):
        uevent = path.join(hidraw, "device/uevent")
        if not path.exists(uevent): continue
        try:
            for line in filter(lambda x: x.startswith("HID_ID="), open(uevent, "r").readlines()):
                parts = line.split("=")[1].split(":")
                vid, pid = [int(parts[i], 16) for i in (1, 2)]
                if (vid, pid) in TARGET_VID_PIDS: break
            else:
                continue

            if open(path.join(hidraw, "device/report_descriptor"), "rb").read() == REPORT_DESCRIPTOR:
                ifs.append(f"/dev/{path.basename(hidraw)}")
        except:
            pass
    return ifs

def write(dev: str, payload: bytes) -> None | Exception:
    try:
        fd = os.open(dev, os.O_RDWR | os.O_NONBLOCK)
        os.write(fd, payload)
        os.close(fd)
    except Exception as e:
        return e
    else:
        return None

def set_polling_rate(dev: str, rate: int):
    packet = bytearray(32)
    packet[0] = 0x02
    packet[1] = 0x00
    packet[2] = 0x01
    packet[3] = 0x01
    packet[31] = packet[4] = POLLING_RATE_MAP[rate]

    if err := write(dev, packet):
        print(f"Failed to communicate with device: {err}", file=sys.stderr)
    else:
        print(f"Successfully set polling rate to {rate}Hz on {dev}")

def main():
    parser = argparse.ArgumentParser(prog="sc580", description="AULA SC580 Mouse Configuration CLI")

    parser.add_argument("--dev", type=str, help="Path to hidraw device (e.g. /dev/hidraw7)")
    parser.add_argument("--list", action="store_true", help="List available SC580 hidraw devices and exit")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    parser_set = subparsers.add_parser("set", help="Set mouse properties")
    set_subparsers = parser_set.add_subparsers(dest="property", required=True, help="Property to set")

    parser_rate = set_subparsers.add_parser("polling-rate", help="Set the mouse polling rate")
    parser_rate.add_argument("value", type=int, choices=POLLING_RATE_MAP.keys(), help="Target polling rate in Hz")

    args = parser.parse_args()

    if args.list:
        ifs = interfaces()
        if not ifs:
            print("No SC580 devices found.")
        else:
            print("Found SC580 devices:")
            for d in ifs: print(f"  - {d}")
        return 0

    if not args.command:
        parser.print_help()
        return 1

    dev = args.dev
    if not dev:
        ifs = interfaces()
        if not ifs:
            print("ERROR: No SC580 device found! Please connect the mouse or specify --dev.", file=sys.stderr)
            return 1
        dev = ifs[0]

    if args.command == "set":
        if args.property == "polling-rate":
            set_polling_rate(dev, args.value)

if __name__ == "__main__":
    sys.exit(main())
