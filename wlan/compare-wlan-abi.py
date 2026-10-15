#!/usr/bin/env python3
"""Compare original OnePlus 13 WLAN module import CRCs with a freshly built module.

Static symbol-version comparison only; equal CRCs do not guarantee load safety.
"""
import pathlib
import re
import subprocess
import sys

def load(s):
    result = {}
    for line in s.splitlines():
        if not line.strip():
            continue
        m = re.fullmatch(r"(0x[0-9a-fA-F]{8})\s+(\S+)", line.strip())
        if not m or m.group(2) in result:
            raise ValueError("Invalid or duplicate symbol-version record: " + line)
        result[m.group(2)] = m.group(1).lower()
    if not result:
        raise ValueError("No symbol versions found")
    return result

def main():
    original = load(pathlib.Path(sys.argv[1]).read_text())
    new_text = subprocess.check_output(["modprobe", "--show-modversions",sys.argv[2]],text=True)
    fresh = load(new_text)
    common = original.keys() & fresh.keys()
    bad = [(name,original[name],fresh[name]) for name in sorted(common) if original[name] != fresh[name]]
    added = sorted(fresh.keys()-original.keys())
    removed = sorted(original.keys()-fresh.keys())
    print("original=%d new=%d shared=%d mismatched=%d new_imports=%d removed=%d" % (len(original),len(fresh),len(common),len(bad),len(added),len(removed)))
    print("new module vermagic:",subprocess.check_output(["modinfo","-F","vermagic",sys.argv[2]],text=True).strip())
    for name,old,new in bad:
        print("CRC CONFLICT",name,old,new)
    for name in added:
        print("ADDED IMPORT (validate provider)",name, fresh[name])
    for name in removed:
        print("REMOVED IMPORT",name)
    if bad:
        print("FAIL: cannot safely swap this module into the existing kernel")
        return 2
    if added:
        print("REVIEW: new symbol imports need independent provider validation")
        return 3
    print("STATIC CHECK PASS ONLY: runtime ABI and original kernel still need verification")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError,ValueError,subprocess.CalledProcessError,IndexError) as e:
        print("ERROR:",e,file=sys.stderr)
        sys.exit(1)
