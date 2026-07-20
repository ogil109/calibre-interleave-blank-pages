# Interleave Blank Pages

A [Calibre](https://calibre-ebook.com/) plugin that, whenever you import a PDF,
writes a copy of it with **one blank page after every original page** into a
folder you choose.

The point is note-taking space. A blank page bound after each page of the
document gives you room for handwritten notes, sketches or annotations —
whether you read on a tablet, an e-ink device, or on paper.

Your Calibre library is never touched. The imported file and its database
record stay exactly as they were; the interleaved version is a separate copy.

```
source.pdf          ->   Deep Work (42)-interleaved.pdf
  page 1                   page 1
  page 2                   (blank, same size as page 1)
  page 3                   page 2
                           (blank, same size as page 2)
                           page 3
                           (blank, same size as page 3)
```

Blank pages match the dimensions of the page they follow, so documents with
mixed page sizes — scanned books especially — interleave correctly.

## Requirements

Calibre 6.0 or newer. That is all — there is **nothing else to install**.

The plugin bundles the PDF library it needs (PyMuPDF) inside its own zip and
loads it itself, so there is no `pip` step, no separate Python, and nothing to
configure beyond an output folder.

## Installation

Download the zip for your platform from the
[releases page](https://github.com/ogil109/calibre-interleave-blank-pages/releases)
— they are named `interleave_blank_pages-linux.zip`, `-macos.zip`,
`-macos-intel.zip` and `-windows.zip`.

Then in Calibre: **Preferences → Plugins → Load plugin from file**, pick the
zip, and restart Calibre. Or from a terminal:

```sh
calibre-customize -a interleave_blank_pages-linux.zip
```

The zips are around 20–25 MB because each carries the PDF library for its
platform. Everything else about the plugin is a few kilobytes.

### Building it yourself

```sh
git clone https://github.com/ogil109/calibre-interleave-blank-pages
cd calibre-interleave-blank-pages
python scripts/build_plugin.py --platform linux   # or: all
calibre-customize -a dist/interleave_blank_pages-linux.zip
```

## Configuration

Preferences → Plugins → File type → **Interleave Blank Pages** → Customize
plugin.

| Setting | Meaning |
| --- | --- |
| Enabled | Master on/off switch. |
| Output folder | Where interleaved copies are written. Created if missing. **If empty, the plugin does nothing.** |

Pick a folder and you are done.

## Behaviour

- Runs only on PDF import, via Calibre's `postimport` hook.
- Output is named from the Calibre record, not the source filename — Calibre
  stores most PDFs as `book.pdf`, so names come from the book's title plus its
  database id: `Deep Work (42)-interleaved.pdf`. The id keeps two books with
  the same title from colliding.
- Idempotent: if the output already exists and is no older than the source, it
  is left alone. Re-importing does not redo the work.
- Never breaks an import. Any failure — a corrupt PDF, an unwritable folder —
  is logged and swallowed; the import completes.
- Never follows or creates symlinks, and never writes over the source file.

Plugin messages appear in Calibre's log. To watch them, run `calibre-debug -g`
from a terminal.

## Command line

The interleaving logic is a standalone script with no Calibre dependency. With
PyMuPDF available (`uv sync` sets that up):

```sh
python interleave_blank_pages/interleave.py source.pdf -o interleaved.pdf
```

## Development

The project uses [uv](https://docs.astral.sh/uv/) for tooling:

```sh
uv sync                                # create the venv
uv run pytest                          # interleaving, naming, idempotency
uv run ruff check .                    # lint

# Needs the plugin installed from a built zip:
calibre-debug tests/calibre_checks.py  # bundled wheel + the import hook
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project layout, why the tests
are split, and why the PDF library is bundled rather than depended on.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project layout and how the
pieces fit together.

## Non-goals

This plugin does one thing. It deliberately does not extract annotations, sync
to devices, generate notes or markdown, touch version control, draw ruled or
dot-grid pages, or handle EPUB/MOBI.

## Licence

[GPL-3.0-or-later](LICENSE), matching Calibre's own licence.
