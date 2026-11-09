import argparse
import struct
import sys

FIELDS = [
    ("magic", 0, "<I"), ("size", 4, "<I"), ("flags", 8, "<I"),
    ("height", 12, "<I"), ("width", 16, "<I"), ("pitch", 20, "<I"),
    ("mipcount", 28, "<I"), ("pf_size", 76, "<I"), ("pf_flags", 80, "<I"),
    ("fourcc", 84, "<I"), ("bits", 88, "<I"), ("caps", 108, "<I"), ("caps2", 112, "<I"),
]


def read_header(path):
    raw = open(path, "rb").read()
    values = {}
    for name, offset, layout in FIELDS:
        values[name] = struct.unpack_from(layout, raw, offset)[0]
    if values["magic"] != 0x20534444:
        print("DDS 头部非法：magic=%#x" % values["magic"], file=sys.stderr)
        sys.exit(1)
    values["bytes"] = len(raw)
    values["fourcc_text"] = values["fourcc"].to_bytes(4, "little").decode("latin1").rstrip("\x00")
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--set-pf-flags", type=lambda v: int(v, 0))
    parser.add_argument("--set-caps", type=lambda v: int(v, 0))
    parser.add_argument("--expect-pf-flags", type=lambda v: int(v, 0))
    parser.add_argument("--expect-caps", type=lambda v: int(v, 0))
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        head = read_header(path)
        if args.set_pf_flags is not None or args.set_caps is not None:
            payload = bytearray(open(path, "rb").read())
            if args.set_pf_flags is not None:
                struct.pack_into("<I", payload, 80, args.set_pf_flags)
            if args.set_caps is not None:
                struct.pack_into("<I", payload, 108, args.set_caps)
            open(path, "wb").write(payload)
            head = read_header(path)
        print("%s bytes=%d %dx%d mips=%d fourcc=%r bits=%d pf_flags=%#x caps=%#x caps2=%#x" % (
            path, head["bytes"], head["width"], head["height"], head["mipcount"],
            head["fourcc_text"], head["bits"], head["pf_flags"], head["caps"], head["caps2"]))
        if args.expect_pf_flags is not None and head["pf_flags"] != args.expect_pf_flags:
            print("  MISMATCH pf_flags %#x != %#x" % (head["pf_flags"], args.expect_pf_flags))
            failed = True
        if args.expect_caps is not None and head["caps"] != args.expect_caps:
            print("  MISMATCH caps %#x != %#x" % (head["caps"], args.expect_caps))
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
