"""Tests for the interleaving itself, mirroring the acceptance criteria."""

import hashlib

import fitz
import pytest
from interleave import interleave, main


def sizes_of(doc):
    return [(round(p.rect.width, 2), round(p.rect.height, 2)) for p in doc]


def test_doubles_page_count_with_blanks_at_odd_indices(a4_pdf, tmp_path):
    dst = tmp_path / 'out.pdf'

    assert interleave(str(a4_pdf), str(dst)) == 6

    with fitz.open(dst) as doc:
        assert doc.page_count == 6
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if i % 2:
                assert text == '', f'page {i} should be blank'
            else:
                assert text == f'page {i // 2}'


def test_blank_matches_size_of_preceding_page(make_pdf, tmp_path):
    # A scanned book: page sizes vary from page to page.
    src = make_pdf('scanned.pdf', [(595, 842), (612, 792), (400, 1000)])
    dst = tmp_path / 'out.pdf'

    interleave(str(src), str(dst))

    with fitz.open(dst) as doc:
        pages = sizes_of(doc)
    assert pages == [(595, 842), (595, 842), (612, 792), (612, 792), (400, 1000), (400, 1000)]


def test_source_is_left_byte_identical(a4_pdf, tmp_path):
    before = hashlib.sha256(a4_pdf.read_bytes()).hexdigest()

    interleave(str(a4_pdf), str(tmp_path / 'out.pdf'))

    assert hashlib.sha256(a4_pdf.read_bytes()).hexdigest() == before


def test_single_page_document(make_pdf, tmp_path):
    src = make_pdf('one.pdf', [(595, 842)])
    dst = tmp_path / 'out.pdf'

    assert interleave(str(src), str(dst)) == 2


ZERO_PAGE_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj
trailer<</Root 1 0 R>>
%%EOF
"""


def test_zero_page_document_raises_a_clear_error(tmp_path):
    src = tmp_path / 'empty.pdf'
    src.write_bytes(ZERO_PAGE_PDF)

    with pytest.raises(ValueError, match='has no pages'):
        interleave(str(src), str(tmp_path / 'out.pdf'))


def test_zero_byte_file_raises(tmp_path):
    # The plugin catches this and logs it; the import must not be broken.
    src = tmp_path / 'broken.pdf'
    src.write_bytes(b'')

    with pytest.raises(fitz.EmptyFileError):
        interleave(str(src), str(tmp_path / 'out.pdf'))


def test_corrupt_file_raises(tmp_path):
    src = tmp_path / 'corrupt.pdf'
    src.write_bytes(b'%PDF-1.4\nnot really a pdf at all\n')

    with pytest.raises(fitz.FileDataError):
        interleave(str(src), str(tmp_path / 'out.pdf'))


def test_cli_writes_output(a4_pdf, tmp_path, capsys):
    dst = tmp_path / 'cli.pdf'

    assert main([str(a4_pdf), '-o', str(dst)]) == 0

    assert 'wrote 6 pages' in capsys.readouterr().out
    with fitz.open(dst) as doc:
        assert doc.page_count == 6
