"""Output naming and idempotency rules.

Calibre-free by design so it can be unit tested outside Calibre, and so the
rules that decide *where* output goes stay readable in one place.
"""

import os

__all__ = ['SUFFIX', 'sanitize', 'output_name', 'needs_rewrite']

#: Appended to every generated file, before the extension.
SUFFIX = '-interleaved.pdf'

#: Characters kept verbatim in a generated filename; everything else becomes
#: an underscore. Deliberately conservative so names are portable across
#: Windows, macOS and Linux filesystems.
_SAFE = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_()')

#: Leave room for the suffix and a filesystem's typical 255-byte name limit.
_MAX_TITLE = 150


def sanitize(text):
    """Reduce ``text`` to filesystem-safe characters.

    Unsafe characters become ``_``; leading/trailing whitespace and dots are
    stripped, since a leading dot hides the file and a trailing dot is invalid
    on Windows.
    """
    # Strip before substituting: a stray dot would otherwise become an
    # underscore and survive the strip.
    return ''.join(c if c in _SAFE else '_' for c in text.strip(' .'))


def output_name(title, book_id):
    """Build the output filename for a book.

    The name comes from the Calibre record rather than the source filename,
    because Calibre commonly stores every PDF as ``book.pdf``. Including
    ``book_id`` keeps names unique even when two books share a title.
    """
    safe_title = sanitize(title or '')[:_MAX_TITLE].strip() or 'Untitled'
    return f'{safe_title} ({book_id}){SUFFIX}'


def needs_rewrite(src_path, dst_path):
    """Return True if the output is missing or older than its source.

    This is the idempotency check: re-importing or re-triggering a book that
    has already been processed should not redo the work.
    """
    if not os.path.exists(dst_path):
        return True
    return os.path.getmtime(dst_path) < os.path.getmtime(src_path)
