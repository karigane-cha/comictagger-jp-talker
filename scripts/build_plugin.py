"""Copy the built pure-Python wheel as a ComicTagger local-plugin ZIP.

The loader reads distribution metadata directly from ZIP roots. Dependencies are
provided by the host; never bundle ComicTagger or a second copy of comicapi.
"""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path


def build_plugin(wheel: Path) -> Path:
    with zipfile.ZipFile(wheel) as archive:
        wheel_metadata = next(n for n in archive.namelist() if n.endswith(".dist-info/WHEEL"))
        if "Root-Is-Purelib: true" not in archive.read(wheel_metadata).decode():
            raise ValueError("Local ZIP must contain a pure-Python wheel")
        metadata_file = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_file).decode()
        version = next(
            line.removeprefix("Version: ") for line in metadata.splitlines() if line.startswith("Version: ")
        )
        entry_file = next(n for n in archive.namelist() if n.endswith(".dist-info/entry_points.txt"))
        if (
            "jpbooks = comictagger_jp_talker.talker:JapaneseBooksTalker"
            not in archive.read(entry_file).decode()
        ):
            raise ValueError("Missing jpbooks entry point")
    target = wheel.parent / f"jpbooks_talker-plugin-{version}.zip"
    shutil.copyfile(wheel, target)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    print(build_plugin(parser.parse_args().wheel))
