#!/usr/bin/env python3
"""Insert one blank page after every page of a PDF.

Uses PyMuPDF, which the plugin ships as a bundled wheel so that nothing has to
be installed by hand -- see ``vendor.py``. Calibre's own podofo bindings were
tried first and rejected: they segfault while inserting pages into complex
documents, and a native crash cannot be caught, so it would take Calibre down
mid-import.

This module imports nothing from Calibre, so it can be unit tested in a plain
virtualenv and run from the command line.

Usage:
    interleave.py SRC -o DST
"""

import argparse
import sys

__all__ = ['interleave', 'main']


def interleave(src_path, dst_path):
    """Write a copy of ``src_path`` with a blank page after each original page.

    Each blank page matches the dimensions of the page it follows, because page
    sizes vary within a document -- scanned books especially.

    Returns the page count of the written document (twice the source's).
    """
    import pymupdf  # imported lazily so --help works without it

    with pymupdf.open(src_path) as src:
        if src.page_count == 0:
            # PyMuPDF cannot save a zero-page document; fail with a message
            # that says why rather than one about saving.
            raise ValueError(f'{src_path} has no pages')

        # Record each page's size before touching the output, since the blanks
        # match the page they follow.
        rects = [src[i].rect for i in range(src.page_count)]

        with pymupdf.open() as out:
            # Copy the whole document in one call, then splice blanks in.
            # Copying page by page instead is quadratic: on a 2000-page PDF it
            # is the difference between ~10 seconds and several minutes.
            out.insert_pdf(src)

            # Insert blanks back to front, so each insertion leaves the indices
            # of the originals still to be processed unchanged.
            for i in range(len(rects) - 1, -1, -1):
                out.insert_page(i + 1, width=rects[i].width, height=rects[i].height)

            out.save(dst_path, garbage=4, deflate=True)
            return out.page_count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('src', help='path to the source PDF')
    parser.add_argument('-o', '--output', required=True, help='path to write')
    args = parser.parse_args(argv)

    pages = interleave(args.src, args.output)
    print(f'{args.output}: wrote {pages} pages')
    return 0


if __name__ == '__main__':
    sys.exit(main())
