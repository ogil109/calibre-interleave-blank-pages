#!/usr/bin/env python3
"""Package the plugin into a zip Calibre can install.

Calibre expects __init__.py at the *root* of the zip, while this repository
keeps the plugin sources in a subdirectory, so the contents are flattened here.

Each zip also carries a PyMuPDF wheel for one platform, so that installing the
plugin is the only thing a user has to do. The wheels are built for the
CPython stable ABI, so one per platform covers every Calibre version.

    python scripts/build_plugin.py --platform linux
    python scripts/build_plugin.py --platform all      # one zip per platform
    python scripts/build_plugin.py --no-wheel          # sources only
"""

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / 'interleave_blank_pages'
DIST_DIR = ROOT / 'dist'

#: Shipped alongside the code so the plugin carries its licence.
EXTRA_FILES = ['README.md', 'LICENSE']

#: pip's platform tag for each name we expose. Kept explicit rather than
#: detected, so a release build produces the same artifacts anywhere.
PLATFORMS = {
    'linux': 'manylinux_2_28_x86_64',
    'macos': 'macosx_11_0_arm64',
    'macos-intel': 'macosx_10_9_x86_64',
    'windows': 'win_amd64',
}

#: Minimum Python the wheel must support. PyMuPDF publishes cp310-abi3 wheels,
#: which then work on every later Python, including the 3.13 in Calibre 8.
ABI_PYTHON = '3.10'


def download_wheel(platform_tag, into):
    """Download the PyMuPDF wheel for one platform into ``into``."""
    subprocess.run(
        [
            sys.executable,
            '-m',
            'pip',
            'download',
            'pymupdf',
            '--no-deps',
            '--only-binary=:all:',
            '--platform',
            platform_tag,
            '--python-version',
            ABI_PYTHON,
            '--dest',
            str(into),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    wheels = list(into.glob('*.whl'))
    if len(wheels) != 1:
        raise RuntimeError(f'expected one wheel for {platform_tag}, got {wheels}')
    return wheels[0]


def build(output_path, platform=None):
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

        if platform:
            with tempfile.TemporaryDirectory() as tmp:
                wheel = download_wheel(PLATFORMS[platform], Path(tmp))
                # Stored, not deflated: a wheel is already compressed, and
                # deflating it again only slows the unpack down.
                archive.write(wheel, f'vendor/{wheel.name}', compress_type=zipfile.ZIP_STORED)

    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--platform',
        choices=[*PLATFORMS, 'all'],
        default='all',
        help='which platform to bundle a wheel for (default: all)',
    )
    parser.add_argument('--no-wheel', action='store_true', help='omit the bundled wheel')
    parser.add_argument('-o', '--output', type=Path, help='output path (single platform only)')
    args = parser.parse_args(argv)

    if args.no_wheel:
        written = build(args.output or DIST_DIR / 'interleave_blank_pages.zip')
        report(written)
        return 0

    targets = list(PLATFORMS) if args.platform == 'all' else [args.platform]
    if args.output and len(targets) > 1:
        parser.error('--output needs a single --platform')

    for platform in targets:
        path = args.output or DIST_DIR / f'interleave_blank_pages-{platform}.zip'
        report(build(path, platform))
    return 0


def report(path):
    print(f'{path}  ({path.stat().st_size / 1048576:.1f} MB)')


if __name__ == '__main__':
    sys.exit(main())
