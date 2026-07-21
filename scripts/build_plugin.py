#!/usr/bin/env python3
"""Package the plugins into zips Calibre can install.

This repository ships two plugins that share a common library:

- ``auto``   -- the FileTypePlugin that interleaves every imported PDF.
- ``manual`` -- the InterfaceAction that interleaves the selected books.

Calibre only lets a zip register one plugin class, so each is built into its
own zip: the shared modules in ``shared/`` are flattened to the zip root
alongside the chosen plugin's entry files, with the marker file Calibre needs
and a PyMuPDF wheel for one platform. The wheels target the CPython stable ABI,
so one per platform covers every Calibre version.

    python scripts/build_plugin.py --platform linux            # both plugins, linux
    python scripts/build_plugin.py --platform all              # both, every platform
    python scripts/build_plugin.py --kind auto --platform all  # just the auto plugin
    python scripts/build_plugin.py --no-wheel                  # sources only, both
"""

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED_DIR = ROOT / 'shared'
DIST_DIR = ROOT / 'dist'

#: Shipped alongside the code so each plugin carries its licence.
EXTRA_FILES = ['README.md', 'LICENSE']

#: The two plugins, each keyed by the short name used on the command line.
#: ``import_name`` is the Calibre plugin import name (the marker file and the
#: calibre_plugins.<name> package); it must be unique per installed plugin.
KINDS = {
    'auto': {'dir': ROOT / 'auto', 'import_name': 'interleave_blank_pages'},
    'manual': {'dir': ROOT / 'manual', 'import_name': 'interleave_blank_pages_manual'},
}

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


def build(kind, output_path, platform=None):
    """Assemble one plugin zip: shared modules + the plugin's entry files."""
    spec = KINDS[kind]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for source_dir in (SHARED_DIR, spec['dir']):
            for path in sorted(source_dir.rglob('*.py')):
                if '__pycache__' in path.parts:
                    continue
                archive.write(path, path.relative_to(source_dir))

        # The marker file Calibre requires so the zip can import its submodules.
        archive.writestr(f'plugin-import-name-{spec["import_name"]}.txt', '')

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


def zip_name(kind, platform):
    base = KINDS[kind]['import_name']
    return f'{base}-{platform}.zip' if platform else f'{base}.zip'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--kind',
        choices=[*KINDS, 'both'],
        default='both',
        help='which plugin(s) to build (default: both)',
    )
    parser.add_argument(
        '--platform',
        choices=[*PLATFORMS, 'all'],
        default='all',
        help='which platform to bundle a wheel for (default: all)',
    )
    parser.add_argument('--no-wheel', action='store_true', help='omit the bundled wheel')
    args = parser.parse_args(argv)

    kinds = list(KINDS) if args.kind == 'both' else [args.kind]
    if args.no_wheel:
        platforms = [None]
    elif args.platform == 'all':
        platforms = list(PLATFORMS)
    else:
        platforms = [args.platform]

    for kind in kinds:
        for platform in platforms:
            path = DIST_DIR / zip_name(kind, platform)
            report(build(kind, path, platform))
    return 0


def report(path):
    print(f'{path}  ({path.stat().st_size / 1048576:.1f} MB)')


if __name__ == '__main__':
    sys.exit(main())
