"""Checks that need Calibre. Run against an installed plugin zip:

    python scripts/build_plugin.py --platform linux
    calibre-customize -a dist/interleave_blank_pages-linux.zip
    calibre-debug tests/calibre_checks.py

These cover what a plain virtualenv cannot: that the bundled PyMuPDF wheel
really is importable inside Calibre's own Python, and that the postimport hook
behaves against a real library. The interleaving itself is covered by
tests/test_interleave.py.

Written as a self-contained runner rather than a pytest module, because
Calibre's Python has no pytest. Exits non-zero if any check fails.
"""

import hashlib
import io
import os
import shutil
import sys
import tempfile
import traceback

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


def make_pdf(pymupdf, path, sizes):
    """Write a PDF with one page per (width, height), stamped with its index."""
    with pymupdf.open() as doc:
        for i, (width, height) in enumerate(sizes):
            page = doc.new_page(width=width, height=height)
            page.insert_text((72, 72), f'page {i}', fontsize=24)
        doc.save(str(path))
    return path


def load_pymupdf():
    """Import PyMuPDF the way the plugin does: from the bundled wheel."""
    from calibre.customize.ui import find_plugin
    from calibre_plugins.interleave_blank_pages.vendor import ensure_pymupdf

    plugin = find_plugin('Interleave Blank Pages')
    assert plugin is not None, 'the plugin is not installed; run calibre-customize -a first'
    return ensure_pymupdf(plugin.plugin_path)


@check
def bundled_wheel_is_importable_inside_calibre(tmp):
    pymupdf = load_pymupdf()

    # The whole point of bundling: this must work with nothing installed.
    assert hasattr(pymupdf, 'open'), 'PyMuPDF imported but looks wrong'
    print(f'       {pymupdf.__doc__.splitlines()[0]}')


@check
def interleaving_works_inside_calibre(tmp):
    pymupdf = load_pymupdf()
    from calibre_plugins.interleave_blank_pages.interleave import interleave

    src = make_pdf(pymupdf, os.path.join(tmp, 'src.pdf'), [(595, 842), (612, 792), (400, 1000)])
    dst = os.path.join(tmp, 'out.pdf')

    assert interleave(src, dst) == 6

    with pymupdf.open(dst) as doc:
        sizes = [(round(p.rect.width), round(p.rect.height)) for p in doc]
        text = [p.get_text().strip() for p in doc]
    assert sizes == [(595, 842), (595, 842), (612, 792), (612, 792), (400, 1000), (400, 1000)], sizes
    assert text == ['page 0', '', 'page 1', '', 'page 2', ''], text


@check
def postimport_hook_end_to_end(tmp):
    pymupdf = load_pymupdf()

    from calibre.customize.ui import run_plugins_on_postimport
    from calibre.db.legacy import LibraryDatabase
    from calibre.ebooks.metadata.book.base import Metadata
    from calibre_plugins.interleave_blank_pages.config import prefs

    sample = make_pdf(pymupdf, os.path.join(tmp, 'sample.pdf'), [(595, 842), (612, 792), (400, 1000)])
    outdir = os.path.join(tmp, 'out')
    libdir = os.path.join(tmp, 'lib')

    saved = dict(prefs)
    prefs['output_dir'] = outdir
    prefs['enabled'] = True
    try:
        db = LibraryDatabase(libdir)
        api = db.new_api

        def add(title):
            book_id = api.create_book_entry(Metadata(title))
            with open(sample, 'rb') as handle:
                api.add_format(book_id, 'PDF', handle, run_hooks=False)
            return book_id

        # Calibre stores both books under the same filename, and they share a
        # title, so only the book id can keep the outputs apart.
        first, second = add('Deep Work'), add('Deep Work')
        source = api.format_abspath(first, 'PDF')
        with open(source, 'rb') as handle:
            before = hashlib.sha256(handle.read()).hexdigest()

        for book_id in (first, second):
            run_plugins_on_postimport(db, book_id, 'PDF')

        produced = sorted(os.listdir(outdir))
        assert len(produced) == 2, produced

        output = os.path.join(outdir, f'Deep Work ({first})-interleaved.pdf')
        assert os.path.exists(output), produced
        with pymupdf.open(output) as doc:
            assert doc.page_count == 6, doc.page_count

        with open(source, 'rb') as handle:
            assert hashlib.sha256(handle.read()).hexdigest() == before, 'library file was modified'

        # Idempotency: re-running must not rewrite an up-to-date output.
        mtime = os.path.getmtime(output)
        run_plugins_on_postimport(db, first, 'PDF')
        assert os.path.getmtime(output) == mtime, 'output was rewritten'

        # No output folder configured: the import must still complete.
        prefs['output_dir'] = ''
        run_plugins_on_postimport(db, first, 'PDF')
        assert len(os.listdir(outdir)) == 2

        # A corrupt PDF must be logged, not raised.
        prefs['output_dir'] = outdir
        broken = api.create_book_entry(Metadata('Corrupt Book'))
        api.add_format(broken, 'PDF', io.BytesIO(b''), run_hooks=False)
        run_plugins_on_postimport(db, broken, 'PDF')
        assert len(os.listdir(outdir)) == 2, 'corrupt book produced output'

        db.close()
    finally:
        for key, value in saved.items():
            prefs[key] = value


@check
def real_world_books_survive(tmp):
    """Regression guard for the documents that made podofo segfault.

    Set IBP_REAL_PDFS to a colon-separated list of PDFs to exercise them.
    """
    paths = [p for p in os.environ.get('IBP_REAL_PDFS', '').split(':') if p]
    if not paths:
        print('       skipped (set IBP_REAL_PDFS to run)')
        return

    pymupdf = load_pymupdf()
    from calibre_plugins.interleave_blank_pages.interleave import interleave

    for path in paths:
        with pymupdf.open(path) as doc:
            expected = doc.page_count * 2
        out = os.path.join(tmp, 'real.pdf')
        assert interleave(path, out) == expected, os.path.basename(path)
        print(f'       {os.path.basename(path)[:40]:42} -> {expected} pages')


def main():
    failures = 0
    for fn in CHECKS:
        tmp = tempfile.mkdtemp(prefix='ibp-check-')
        try:
            fn(tmp)
            print(f'  ok   {fn.__name__}')
        except Exception:
            failures += 1
            print(f'  FAIL {fn.__name__}')
            traceback.print_exc()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print(f'\n{len(CHECKS) - failures}/{len(CHECKS)} checks passed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
