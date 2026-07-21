"""Make the bundled PyMuPDF wheel importable inside Calibre.

Calibre's embedded Python cannot see packages installed into the system
Python, and asking a reader to install one is a barrier most will not clear.
So the plugin ships a PyMuPDF wheel and puts it on ``sys.path`` itself.

The wheel contains a compiled extension module, which cannot be imported from
inside the plugin zip, so it is unpacked into Calibre's cache directory once
and reused from there afterwards.

The wheels are built for the CPython **stable ABI** (``cp310-abi3``), so a
single wheel per platform works across every Python that Calibre 6, 7 and 8
ship, with no version matching.
"""

import io
import os
import shutil
import sys
import zipfile

#: Directory inside the plugin zip holding the wheel for this platform.
VENDOR_DIR = 'vendor'

#: Written once an unpack has fully succeeded, so a half-extracted directory
#: from an interrupted run is never mistaken for a usable one.
MARKER = '.unpacked'


class MissingWheel(Exception):
    """No bundled wheel is available for this platform."""


def ensure_pymupdf(plugin_path, log=None):
    """Import and return PyMuPDF, unpacking the bundled wheel if needed.

    ``plugin_path`` is the path to the installed plugin zip, or None when the
    plugin is being run from a source checkout.
    """
    try:
        import pymupdf

        return pymupdf
    except ImportError:
        pass

    target = _unpack_wheel(plugin_path, log=log)
    if target not in sys.path:
        # Appended, not inserted: a PyMuPDF the user has already installed
        # should win over ours.
        sys.path.append(target)

    import pymupdf

    return pymupdf


def _unpack_wheel(plugin_path, log=None):
    """Unpack the bundled wheel into the cache directory and return its path."""
    from calibre.constants import cache_dir

    if not plugin_path or not os.path.exists(plugin_path):
        raise MissingWheel(
            'The plugin is not running from an installed zip, so its bundled '
            'PyMuPDF cannot be found. Install PyMuPDF for Calibre, or install '
            'the plugin from a release zip.'
        )

    with zipfile.ZipFile(plugin_path) as archive:
        wheels = [
            name for name in archive.namelist() if name.startswith(VENDOR_DIR + '/') and name.endswith('.whl')
        ]
        if not wheels:
            raise MissingWheel(
                'This plugin zip contains no PyMuPDF wheel. Download the zip '
                'built for your platform from the project releases page.'
            )
        wheel_name = wheels[0]

        target = os.path.join(cache_dir(), 'interleave_blank_pages', _stem(wheel_name))
        if os.path.exists(os.path.join(target, MARKER)):
            return target

        if log:
            log(f'unpacking bundled {os.path.basename(wheel_name)}')

        # Unpack beside the target and move into place, so a failure part way
        # through never leaves something importable but incomplete.
        staging = target + '.partial'
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging, exist_ok=True)

        # Read the wheel into memory rather than streaming it: nested
        # ZipFile needs a seekable handle, and the wheel is ~25 MB.
        payload = io.BytesIO(archive.read(wheel_name))

    with zipfile.ZipFile(payload) as wheel:
        wheel.extractall(staging)

    open(os.path.join(staging, MARKER), 'wb').close()
    shutil.rmtree(target, ignore_errors=True)
    os.replace(staging, target)
    return target


def _stem(wheel_path):
    return os.path.splitext(os.path.basename(wheel_path))[0]
