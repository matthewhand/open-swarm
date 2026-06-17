#!/usr/bin/env python3
"""Print the number of non-blank lines in the file given as argv[1]."""
import sys


def count_non_blank(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 count.py <path>", file=sys.stderr)
        raise SystemExit(2)
    print(count_non_blank(sys.argv[1]))
