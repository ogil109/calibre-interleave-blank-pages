# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-07-19

### Added

- Calibre `FileTypePlugin` that hooks `postimport` for PDFs and writes an
  interleaved copy — one blank page after every original page — to a
  configured output folder.
- Blank pages match the dimensions of the page they follow, so documents with
  mixed page sizes interleave correctly.
- Preferences widget for the output folder, the master enable switch, and the
  path to a Python interpreter with PyMuPDF installed.
- Output names derived from the Calibre record (`<Title> (<id>)-interleaved.pdf`)
  rather than the source filename, which is usually `book.pdf`.
- Idempotency: existing output that is no older than its source is left alone.
- Standalone CLI: `python interleave_blank_pages/interleave.py SRC -o DST`.
- `scripts/build_plugin.py` to package the installable zip.

[1.0.0]: https://github.com/ogil109/calibre-interleave-blank-pages/releases/tag/v1.0.0
