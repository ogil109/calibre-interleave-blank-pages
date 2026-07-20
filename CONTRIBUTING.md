# Contributing

Thanks for taking a look. This is a deliberately small, single-purpose plugin;
the bar for new features is high, but fixes and platform reports are very
welcome.

## Getting set up

```sh
uv sync
uv run pytest                          # naming and idempotency rules
calibre-debug tests/calibre_checks.py  # interleaving and the import hook
uv run ruff check .
```

You need Calibre installed for the second command — the interleaving uses
Calibre's bundled podofo, so it cannot run in a plain virtualenv.

## Project layout

```
interleave_blank_pages/     the plugin; zipped flat into what Calibre installs
  __init__.py               FileTypePlugin subclass: the postimport hook,
                            path resolution, naming, idempotency, error handling
  config.py                 JSONConfig settings + the Preferences widget
  interleave.py             the PDF work, via Calibre's bundled podofo
  naming.py                 output filename rules and the idempotency check
  plugin-import-name-*.txt  empty marker Calibre requires so the plugin can
                            import its own submodules
scripts/build_plugin.py     packages the above into dist/*.zip
tests/test_naming.py        plain pytest over the Calibre-free rules
tests/calibre_checks.py     runs under calibre-debug; interleaving + the hook
```

### Why PyMuPDF is bundled

The plugin must work on a stock Calibre install with nothing else set up. A
reader who wants blank pages for notes will not install Python and pip a
package first. But Calibre's embedded Python cannot see system packages, so
the library has to come from somewhere.

**Calibre's own podofo bindings were tried and rejected.** They are already
present, which would have been ideal, but `insert_existing_page` **segfaults**
on complex documents — it died on 3 of 60 real-world PDFs, and the three were
all full-length books, exactly this plugin's use case. A segfault is not
catchable, so it takes Calibre down mid-import. That is worse than any install
step, so the idea was dropped.

So the plugin ships a PyMuPDF wheel per platform and puts it on `sys.path`
itself (`vendor.py`). This is workable because PyMuPDF publishes **`cp310-abi3`**
wheels: the stable ABI means one wheel per platform covers every Python that
Calibre 6, 7 and 8 ship, with no version matching. The wheel is unpacked once
into Calibre's cache directory, since a compiled extension cannot be imported
from inside the plugin zip.

Please do not add a runtime dependency the user has to install. If PyMuPDF
ever needs replacing, the replacement has to be bundled the same way.

### Why the tests are split

- **`tests/` under pytest** covers `interleave.py` and `naming.py`, which
  import nothing from Calibre. `tests/conftest.py` puts the plugin directory on
  `sys.path` and imports them as top-level modules, because importing the
  *package* would execute `__init__.py`, which needs Calibre.
- **`tests/calibre_checks.py` under `calibre-debug`** covers what only Calibre
  can show: that the bundled wheel really is importable inside Calibre's
  Python, and that the `postimport` hook behaves against a real library. It is
  a self-contained runner because Calibre's Python has no pytest.

`calibre_checks.py` needs the plugin installed from a built zip, since it
exercises the bundled wheel:

```sh
python scripts/build_plugin.py --platform linux
calibre-customize -a dist/interleave_blank_pages-linux.zip
calibre-debug tests/calibre_checks.py
```

Set `IBP_REAL_PDFS` to a colon-separated list of real PDFs to exercise them as
a regression guard — long, structurally complex books are the interesting case:

```sh
IBP_REAL_PDFS="/path/one.pdf:/path/two.pdf" calibre-debug tests/calibre_checks.py
```

## Testing changes in Calibre

```sh
uv run python scripts/build_plugin.py
calibre-customize -a dist/interleave_blank_pages.zip
calibre-debug -g          # run Calibre with plugin log output visible
```

To remove it again: `calibre-customize -r "Interleave Blank Pages"`.

Please verify by hand that an import still succeeds when things go wrong — a
corrupt PDF, an unset output folder, an unwritable target. Never breaking the
user's import is the plugin's most important property.

## Style

- `ruff` settings live in `pyproject.toml`; run it before opening a PR.
- Comments should explain *why*, not restate the code. Most of the non-obvious
  parts of this codebase are Calibre API quirks — those are worth a comment.
- Keep it single-purpose. See the non-goals in the README before proposing a
  feature.

## Pull requests

Describe what you changed and how you verified it, including which Calibre
version and OS you tested on. Add tests for anything in `interleave.py` or
`naming.py` — `tests/calibre_checks.py` for the former, `tests/test_naming.py`
for the latter.
