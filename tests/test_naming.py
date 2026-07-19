"""Tests for output naming and the idempotency rule."""

import os

from naming import needs_rewrite, output_name, sanitize


def test_keeps_safe_characters():
    assert sanitize('Notes (2nd ed) - draft_1') == 'Notes (2nd ed) - draft_1'


def test_replaces_path_separators_and_specials():
    assert sanitize('a/b\\c:d*e?f') == 'a_b_c_d_e_f'


def test_strips_leading_and_trailing_dots_and_spaces():
    # A leading dot hides the file; a trailing dot is invalid on Windows.
    assert sanitize('  .hidden name.  ') == 'hidden name'


def test_name_includes_title_and_book_id():
    assert output_name('Deep Work', 42) == 'Deep Work (42)-interleaved.pdf'


def test_same_title_different_ids_do_not_collide():
    # Calibre stores most PDFs as book.pdf, so names must come from the record.
    assert output_name('Untitled', 1) != output_name('Untitled', 2)


def test_missing_title_falls_back():
    assert output_name('', 7) == 'Untitled (7)-interleaved.pdf'
    assert output_name(None, 7) == 'Untitled (7)-interleaved.pdf'


def test_title_of_only_unsafe_characters_still_yields_a_name():
    assert output_name('///', 3) == '___ (3)-interleaved.pdf'


def test_long_title_is_truncated():
    name = output_name('x' * 400, 5)

    assert len(name.encode()) < 255
    assert name.endswith('(5)-interleaved.pdf')


def test_rewrite_needed_when_output_missing(tmp_path):
    src = tmp_path / 'src.pdf'
    src.write_bytes(b'x')

    assert needs_rewrite(str(src), str(tmp_path / 'absent.pdf'))


def test_no_rewrite_when_output_is_newer(tmp_path):
    src = tmp_path / 'src.pdf'
    src.write_bytes(b'x')
    dst = tmp_path / 'dst.pdf'
    dst.write_bytes(b'y')
    os.utime(dst, (os.path.getmtime(src) + 10,) * 2)

    assert not needs_rewrite(str(src), str(dst))


def test_rewrite_when_source_is_newer(tmp_path):
    src = tmp_path / 'src.pdf'
    src.write_bytes(b'x')
    dst = tmp_path / 'dst.pdf'
    dst.write_bytes(b'y')
    os.utime(src, (os.path.getmtime(dst) + 10,) * 2)

    assert needs_rewrite(str(src), str(dst))
