#!/usr/bin/env python3

from glob import glob
from os import path
from typing import Callable

import os
import sys
import argparse

TARGET_VID_PIDS = {
    (0x088D, 0x062E): "usb",       # llTECH Wireless-Receiver
    (0x089D, 0x062F): "usb_dongle" # ll TECH USB Gaming Mouse
}

POLLING_RATE_MAP = {
    125: 0x08,
    250: 0x04,
    500: 0x02,
    1000: 0x01
}

REPORT_DESCRIPTOR = bytes.fromhex("0602ff0900a10119002aff00150026ff00750895208101750895209101c0")

def interfaces() -> list[tuple[str, str]]:
    ifs: list[tuple[str, str]] = []
    for hidraw in glob("/sys/class/hidraw/hidraw*"):
        uevent = path.join(hidraw, "device/uevent")
        if not path.exists(uevent): continue

        try:
            ue_data = open(uevent, "r").read()
            hid_id = ue_data[(_ := ue_data.find("HID_ID=") + 7):ue_data.find("\n", _)]
            if not hid_id: continue

            vid, pid = map(lambda x: int(x, 16), hid_id.split(":")[1:])
            if (vid, pid) in TARGET_VID_PIDS and open(path.join(hidraw, "device/report_descriptor"), "rb").read() == REPORT_DESCRIPTOR:
                ifs.append((f"/dev/{path.basename(hidraw)}", TARGET_VID_PIDS[(vid, pid)]))
        except:
            pass

    return ifs

def __write(dev: str, packet: bytes) -> None:
    assert len(packet) == 32, "Packet must be exactly 32 bytes long"

    fd = os.open(dev, os.O_RDWR | os.O_NONBLOCK)
    try: os.write(fd, packet)
    finally: os.close(fd)

def set_polling_rate(dev: str, rate: int) -> None:
    assert rate in POLLING_RATE_MAP, f"Unsupported polling rate: {rate} Hz"

    packet = bytearray(32)
    packet[0] = 0x02
    packet[1] = 0x00
    packet[2] = 0x01
    packet[3] = 0x01
    packet[31] = packet[4] = POLLING_RATE_MAP[rate]

    return __write(dev, packet)

def __return_exception(func: Callable):
    def __wrapper(*args, **kwargs):
        try: result = func(*args, **kwargs)
        except Exception as e: return e
        else: return result

    return __wrapper

def main() -> int:
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
            for d in ifs: print(f"  - {d[0]} {d[1]}")

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

        dev = ifs[0][0]

    print(f"Using device: {dev}")

    if args.command == "set":
        if args.property == "polling-rate":
            if err := __return_exception(set_polling_rate)(dev, args.value):
                print(f"ERROR: Failed to set polling rate: {err}", file=sys.stderr)

                return 1
            else:
                print(f"Polling rate set to {args.value} Hz successfully.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
