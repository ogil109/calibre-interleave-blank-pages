# Interleave Blank Pages

A pair of [Calibre](https://calibre-ebook.com/) plugins that write a copy of a
PDF with **one blank page after every original page** into a folder you choose.

The point is note-taking space. A blank page bound after each page of the
document gives you room for handwritten notes, sketches or annotations —
whether you read on a tablet, an e-ink device, or on paper.

Your Calibre library is never touched. The source file and its database record
stay exactly as they were; the interleaved version is a separate copy.

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

## Two plugins, two ways to trigger it

Calibre only lets a plugin zip register one plugin, so this ships as two:

| Plugin | What it does |
| --- | --- |
| **Interleave Blank Pages** | Automatic. Every PDF you import is interleaved into the output folder, with no further action. |
| **Interleave Blank Pages (manual)** | On demand. Adds a button to interleave the **selected** books — for PDFs already in your library, where re-importing would be a hack. |

Install whichever you want, or both. They share the same output-folder setting,
so configuring one configures the other.

## Requirements

Calibre 6.0 or newer. That is all — there is **nothing else to install**.

The plugins bundle the PDF library they need (PyMuPDF) inside their own zips and
load it themselves, so there is no `pip` step, no separate Python, and nothing
to configure beyond an output folder.

## Installation

Download the zip(s) for your platform from the
[releases page](https://github.com/ogil109/calibre-interleave-blank-pages/releases):

- `interleave_blank_pages-<platform>.zip` — the automatic plugin
- `interleave_blank_pages_manual-<platform>.zip` — the manual action

where `<platform>` is `linux`, `macos`, `macos-intel` or `windows`.

Then in Calibre: **Preferences → Plugins → Load plugin from file**, pick the
zip, and restart Calibre. Or from a terminal:

```sh
calibre-customize -a interleave_blank_pages-linux.zip
calibre-customize -a interleave_blank_pages_manual-linux.zip   # if you want the manual action too
```

Each zip is around 20–25 MB because it carries the PDF library for its
platform. Everything else is a few kilobytes.

### Building it yourself

```sh
git clone https://github.com/ogil109/calibre-interleave-blank-pages
cd calibre-interleave-blank-pages
python scripts/build_plugin.py --platform linux        # both plugins, linux
calibre-customize -a dist/interleave_blank_pages-linux.zip
calibre-customize -a dist/interleave_blank_pages_manual-linux.zip
```

`--kind auto` or `--kind manual` builds just one; `--platform all` builds every
platform.

## Configuration

Preferences → Plugins → open either plugin → **Customize plugin**.

| Setting | Meaning |
| --- | --- |
| Enabled | Master on/off switch for the automatic plugin. |
| Output folder | Where interleaved copies are written. Created if missing. **If empty, nothing is written.** |

Pick a folder and you are done. Both plugins read the same setting.

## Using it

**Automatic plugin** — just import a PDF. The interleaved copy appears in the
output folder. It runs at import time, so books already in your library are not
touched; use the manual action for those.

**Manual action** — after installing, the action lands on the main toolbar as
**Interleave blank pages**. Select one or more books and click it; it writes an
interleaved copy of each selected book's PDF and reports a summary. Books
without a PDF format are skipped. To add the action to the right-click menu,
go to Preferences → Toolbars & menus → *The context menu for the books in the
calibre library* and add it there.

## Behaviour

- Output is named from the Calibre record, not the source filename — Calibre
  stores most PDFs as `book.pdf`, so names come from the book's title plus its
  database id: `Deep Work (42)-interleaved.pdf`. The id keeps two books with
  the same title from colliding.
- Idempotent: if the output already exists and is no older than the source, it
  is left alone. Re-importing or re-running the manual action does not redo the
  work.
- The automatic plugin never breaks an import: any failure — a corrupt PDF, an
  unwritable folder — is logged and swallowed; the import completes. The manual
  action reports failures per book without stopping the rest.
- Never follows or creates symlinks, and never writes over the source file.
- The manual action runs in the background, so interleaving a large book does
  not freeze Calibre.

Plugin messages appear in Calibre's log. To watch them, run `calibre-debug -g`
from a terminal.

## Command line

The interleaving logic is a standalone script with no Calibre dependency. With
PyMuPDF available (`uv sync` sets that up):

```sh
python shared/interleave.py source.pdf -o interleaved.pdf
```

## Development

The project uses [uv](https://docs.astral.sh/uv/) for tooling:

```sh
uv sync                                # create the venv
uv run pytest                          # interleaving, naming, idempotency
uv run ruff check .                    # lint

# Needs both plugin zips built and installed:
calibre-debug tests/calibre_checks.py  # bundled wheel, import hook, manual worker
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project layout, why the tests
are split, and why the PDF library is bundled rather than depended on.

## Non-goals

These plugins do one thing. They deliberately do not extract annotations, sync
to devices, generate notes or markdown, touch version control, draw ruled or
dot-grid pages, or handle EPUB/MOBI.

## Licence

[GPL-3.0-or-later](LICENSE), matching Calibre's own licence.
