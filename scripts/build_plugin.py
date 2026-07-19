#!/usr/bin/env python3
"""Package the plugin into a zip Calibre can install.

Calibre expects __init__.py at the *root* of the zip, while this repository
keeps the plugin sources in a subdirectory, so the contents are flattened here.

    python scripts/build_plugin.py [-o dist/interleave_blank_pages.zip]
"""

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / 'interleave_blank_pages'
DEFAULT_OUTPUT = ROOT / 'dist' / 'interleave_blank_pages.zip'

#: Shipped alongside the code so the plugin's About box carries its licence.
EXTRA_FILES = ['README.md', 'LICENSE']


def build(output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(SOURCE_DIR.rglob('*')):
            if path.is_dir() or '__pycache__' in path.parts:
                continue
            archive.write(path, path.relative_to(SOURCE_DIR))
        for name in EXTRA_FILES:
            source = ROOT / name
            if source.exists():
                archive.write(source, name)

    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('-o', '--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    written = build(args.output)
    print(f'{written} ({written.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
