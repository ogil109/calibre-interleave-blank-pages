"""The shared core: turn one book into an interleaved copy.

Both plugins call this -- the import hook (``auto``) and the manual action
(``manual``) -- so the naming, idempotency, symlink and output rules live in
exactly one place.

Database access is deliberately separated from the file work. ``resolve`` reads
the library (title, on-disk path) and must run on the thread that owns the
database; ``process_resolved`` touches only the filesystem and is safe to run
in a background worker, which is how the manual action keeps the GUI
responsive on large books.
"""

import os

from .interleave import interleave
from .naming import needs_rewrite, output_name
from .vendor import ensure_pymupdf

#: Outcome codes returned by ``process_resolved``.
WROTE = 'wrote'
UP_TO_DATE = 'up_to_date'
NO_PDF = 'no_pdf'
SAME_PATH = 'same_path'
SYMLINK = 'symlink'

#: Human-readable summaries, keyed by outcome code.
LABELS = {
    WROTE: 'written',
    UP_TO_DATE: 'already up to date',
    NO_PDF: 'no PDF format',
    SAME_PATH: 'output path equals source',
    SYMLINK: 'refused (symlink in path)',
}


def resolve(api, book_id):
    """Return ``(title, pdf_path)`` for a book. Reads the database.

    ``pdf_path`` is None when the book has no PDF on disk (for example a book
    added from a stream). Must run on the database-owning thread.
    """
    title = api.field_for('title', book_id)
    src_path = api.format_abspath(book_id, 'PDF')
    return title, src_path


def process_resolved(book_id, title, src_path, output_dir, plugin_path, log=None, force=False):
    """Write the interleaved copy for one already-resolved book.

    Touches only the filesystem, so it is safe off the GUI thread. Returns an
    outcome code from the constants above; ``interleave`` may still raise on a
    corrupt PDF, which the caller is expected to catch per book.
    """
    if not src_path:
        return NO_PDF

    dst_path = os.path.join(output_dir, output_name(title, book_id))

    if os.path.abspath(dst_path) == os.path.abspath(src_path):
        return SAME_PATH

    if os.path.islink(output_dir) or os.path.islink(dst_path):
        return SYMLINK

    if not force and not needs_rewrite(src_path, dst_path):
        return UP_TO_DATE

    os.makedirs(output_dir, exist_ok=True)
    # Put the bundled PyMuPDF on sys.path before interleave() imports it.
    ensure_pymupdf(plugin_path, log=log)
    interleave(src_path, dst_path)
    return WROTE
