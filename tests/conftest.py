"""Shared fixtures for the plain-pytest suite.

The plugin entry points import Calibre, which only exists inside Calibre's
embedded Python. The Calibre-free shared modules (``interleave``, ``naming``)
are therefore imported as top-level modules from the ``shared`` directory.

The plugin hook itself is covered by ``tests/calibre_checks.py``, which runs
under ``calibre-debug``.
"""

import sys
from pathlib import Path

import pytest

SHARED_DIR = Path(__file__).resolve().parent.parent / 'shared'
sys.path.insert(0, str(SHARED_DIR))


@pytest.fixture
def make_pdf(tmp_path):
    """Return a factory building a PDF with the given page sizes.

    ``sizes`` is a list of (width, height) points, one per page. Each page is
    stamped with its index so tests can tell originals from blanks.
    """
    import pymupdf

    def _make(name, sizes):
        path = tmp_path / name
        with pymupdf.open() as doc:
            for i, (width, height) in enumerate(sizes):
                page = doc.new_page(width=width, height=height)
                page.insert_text((72, 72), f'page {i}', fontsize=24)
            doc.save(str(path))
        return path

    return _make


@pytest.fixture
def a4_pdf(make_pdf):
    """A three-page, uniformly sized, born-digital PDF."""
    return make_pdf('source.pdf', [(595, 842)] * 3)
