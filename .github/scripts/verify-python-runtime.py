"""Fail closed on an unexpected or unpatched CI interpreter, before pip runs."""

from __future__ import annotations

import argparse
import sys
from typing import NamedTuple

MINIMUM_PATCH = {(3, 12): 16, (3, 13): 18, (3, 14): 10, (3, 15): 2}


class RuntimeVersion(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


def verify_runtime(actual: RuntimeVersion, expected: tuple[int, int]) -> None:
    minimum = MINIMUM_PATCH.get(expected)
    if minimum is None:
        raise ValueError(f"Unsupported expected Python series: {expected}")
    if actual[:2] != expected or actual.micro < minimum or actual.releaselevel != "final":
        raise ValueError(
            f"A final Python {expected[0]}.{expected[1]}.{minimum} or later in that series is required"
        )


def main() -> None:
    print(sys.version, flush=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("series", choices=[f"{major}.{minor}" for major, minor in MINIMUM_PATCH])
    args = parser.parse_args()
    expected = tuple(map(int, args.series.split(".")))
    try:
        verify_runtime(sys.version_info, expected)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
