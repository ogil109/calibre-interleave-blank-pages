# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- The manual action's toolbar button is now greyed out when no output folder
  is configured, with a tooltip explaining why, instead of failing on click.
  It re-enables the moment you set the folder in the plugin preferences.
- The automatic plugin now logs a warning (rather than an easily-missed info
  line) when it is triggered with no output folder configured.

## [0.1.0] - 2026-07-24

First release. The functionality below is verified against Calibre 8.0, but the
plugins have not yet been used widely, so the API stays at 0.x until real-world
use has had a chance to shake out surprises.

### Added

- Calibre `FileTypePlugin` that hooks `postimport` for PDFs and writes an
  interleaved copy — one blank page after every original page — to a
  configured output folder.
- A second plugin, **Interleave Blank Pages (manual)**: an `InterfaceAction`
  that interleaves the PDFs of the books you select, for documents already in
  the library. It runs in a background job so large books do not freeze the
  GUI, and reports a per-book summary. Calibre allows only one plugin class per
  zip, so it ships as its own zip; both share the same output-folder setting.
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
- Standalone CLI: `python shared/interleave.py SRC -o DST`.
- `scripts/build_plugin.py` to package the installable zips (`--kind`,
  `--platform`).

### Known limitations

- If no output folder is configured, the automatic plugin does nothing and says
  so only in Calibre's log. It runs at import time and has no window of its own,
  so it cannot prompt; set the folder after installing. (The manual action's
  button is greyed out in this state instead — see Unreleased.)
- The manual action is added to the main toolbar, not the book right-click
  menu. Calibre builds that menu from a user-configured list, so a plugin
  cannot put itself there; add it via Preferences → Toolbars & menus.

[0.1.0]: https://github.com/ogil109/calibre-interleave-blank-pages/releases/tag/v0.1.0
