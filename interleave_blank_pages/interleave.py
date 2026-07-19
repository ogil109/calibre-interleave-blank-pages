#!/usr/bin/env python3
"""Insert one blank page after every page of a PDF.

This module is deliberately standalone: it imports nothing from Calibre, so
the plugin can run it as a subprocess under a system Python that has PyMuPDF
installed (Calibre's embedded Python does not).

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
    import fitz  # PyMuPDF, imported lazily so --help works without it

    with fitz.open(src_path) as src:
        if src.page_count == 0:
            # PyMuPDF cannot save a zero-page document; fail with a message
            # that says why rather than one about saving.
            raise ValueError(f'{src_path} has no pages')
        with fitz.open() as out:
            for i in range(src.page_count):
                out.insert_pdf(src, from_page=i, to_page=i)
                rect = src[i].rect
                out.new_page(width=rect.width, height=rect.height)
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
