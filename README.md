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

- Calibre 6.0 or newer (developed and tested against Calibre 8.0)
- A Python 3 interpreter with [PyMuPDF](https://pymupdf.readthedocs.io/)
  installed

### Why a separate Python?

Calibre ships its own embedded Python, which cannot see packages you install
with `pip` into your system Python. Rather than bundling platform-specific
PyMuPDF wheels into the plugin, this plugin keeps itself thin and shells out to
an interpreter you point it at. That interpreter is configurable, so any of
these work:

```sh
pip install --user pymupdf          # then use: python3
uv tool install pymupdf             # or a uv-managed interpreter
python3 -m venv ~/.venvs/interleave && ~/.venvs/interleave/bin/pip install pymupdf
```

For the last one, set the interpreter path to `~/.venvs/interleave/bin/python`.

## Installation

Build the plugin zip and hand it to Calibre:

```sh
git clone https://github.com/ogil109/calibre-interleave-blank-pages
cd calibre-interleave-blank-pages
python scripts/build_plugin.py
calibre-customize -a dist/interleave_blank_pages.zip
```

Restart Calibre if it is running.

During development you can install the working tree directly:

```sh
calibre-customize -b interleave_blank_pages
```

## Configuration

Preferences → Plugins → File type → **Interleave Blank Pages** → Customize
plugin.

| Setting | Meaning |
| --- | --- |
| Enabled | Master on/off switch. |
| Output folder | Where interleaved copies are written. Created if missing. **If empty, the plugin does nothing.** |
| Python interpreter | Path to a Python 3 with PyMuPDF installed. Defaults to `python3`. |

## Behaviour

- Runs only on PDF import, via Calibre's `postimport` hook.
- Output is named from the Calibre record, not the source filename — Calibre
  stores most PDFs as `book.pdf`, so names come from the book's title plus its
  database id: `Deep Work (42)-interleaved.pdf`. The id keeps two books with
  the same title from colliding.
- Idempotent: if the output already exists and is no older than the source, it
  is left alone. Re-importing does not redo the work.
- Never breaks an import. Any failure — a corrupt PDF, a missing interpreter,
  an unwritable folder — is logged and swallowed; the import completes.
- Never follows or creates symlinks, and never writes over the source file.

Plugin messages appear in Calibre's log. To watch them, run `calibre-debug -g`
from a terminal.

## Command line

The interleaving logic is a standalone script with no Calibre dependency:

```sh
python interleave_blank_pages/interleave.py source.pdf -o interleaved.pdf
```

## Development

The project uses [uv](https://docs.astral.sh/uv/):

```sh
uv sync              # create the venv and install dependencies
uv run pytest        # run the test suite
uv run ruff check .  # lint
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project layout and how the
pieces fit together.

## Non-goals

This plugin does one thing. It deliberately does not extract annotations, sync
to devices, generate notes or markdown, touch version control, draw ruled or
dot-grid pages, or handle EPUB/MOBI.

## Licence

[GPL-3.0-or-later](LICENSE), matching Calibre's own licence.
