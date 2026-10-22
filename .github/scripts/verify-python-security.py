"""Check CI packaging tools without adding a dependency to the build job."""

from __future__ import annotations

import argparse
from importlib.metadata import version

from pip._vendor import certifi
from pip._vendor.packaging.version import Version


def require_version(name: str, installed: str, minimum: str) -> None:
    print(f"{name}: {installed} (minimum {minimum})", flush=True)
    if Version(installed) < Version(minimum):
        raise SystemExit(f"Unsafe {name}: {installed}; need >= {minimum}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-certifi", action="store_true")
    args = parser.parse_args()
    require_version("pip", version("pip"), "26.2.2")
    require_version("pip bundled certifi", certifi.__version__, "2026.10.19")
    if args.require_certifi:
        require_version("standalone certifi", version("certifi"), "2026.10.19")


if __name__ == "__main__":
    main()
