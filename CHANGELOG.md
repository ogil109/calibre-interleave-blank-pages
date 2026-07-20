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
- Preferences widget for the output folder and a master enable switch.
- Nothing to install beyond the plugin: each release zip bundles a PyMuPDF
  wheel for its platform, which the plugin unpacks and puts on `sys.path`
  itself. The wheels target the CPython stable ABI, so one per platform covers
  every Python that Calibre 6, 7 and 8 ship.
- Per-platform release zips built by CI (`linux`, `macos`, `macos-intel`,
  `windows`).
- Output names derived from the Calibre record (`<Title> (<id>)-interleaved.pdf`)
  rather than the source filename, which is usually `book.pdf`.
- Idempotency: existing output that is no older than its source is left alone.
- Standalone CLI: `python interleave_blank_pages/interleave.py SRC -o DST`.
- `scripts/build_plugin.py` to package the installable zip.

[1.0.0]: https://github.com/ogil109/calibre-interleave-blank-pages/releases/tag/v1.0.0
