# Contributing

Thanks for taking a look. This is a deliberately small, single-purpose plugin;
the bar for new features is high, but fixes and platform reports are very
welcome.

## Getting set up

```sh
uv sync
uv run pytest
uv run ruff check .
```

You need Calibre installed to test the plugin end to end, but not to run the
test suite — the logic under test is Calibre-free by design.

## Project layout

```
interleave_blank_pages/     the plugin; zipped flat into what Calibre installs
  __init__.py               FileTypePlugin subclass: the postimport hook,
                            path resolution, naming, idempotency, error handling
  config.py                 JSONConfig settings + the Preferences widget
  interleave.py             the actual PDF work; standalone, also a CLI
  naming.py                 output filename rules and the idempotency check
  plugin-import-name-*.txt  empty marker Calibre requires so the plugin can
                            import its own submodules
scripts/build_plugin.py     packages the above into dist/*.zip
tests/                      pytest suite over the Calibre-free modules
```

### Why the split

Calibre runs plugins inside its own embedded Python, which has neither PyMuPDF
nor any of your system packages. So:

- `interleave.py` and `naming.py` import nothing from Calibre. They are plain
  Python, unit-testable in a normal virtualenv, and `interleave.py` is executed
  as a **subprocess** under an interpreter that does have PyMuPDF.
- `__init__.py` and `config.py` import Calibre and can only run inside it.

That is why `tests/conftest.py` puts the plugin directory on `sys.path` and
imports `interleave` and `naming` as top-level modules rather than importing
the package: importing the package would execute `__init__.py`, which needs
Calibre.

## Testing changes in Calibre

```sh
uv run python scripts/build_plugin.py
calibre-customize -a dist/interleave_blank_pages.zip
calibre-debug -g          # run Calibre with plugin log output visible
```

To remove it again: `calibre-customize -r "Interleave Blank Pages"`.

Please verify by hand that an import still succeeds when things go wrong — a
corrupt PDF, an unset output folder, a bad interpreter path. Never breaking the
user's import is the plugin's most important property, and it is the one the
unit tests can't fully cover.

## Style

- `ruff` settings live in `pyproject.toml`; run it before opening a PR.
- Comments should explain *why*, not restate the code. Most of the non-obvious
  parts of this codebase are Calibre API quirks — those are worth a comment.
- Keep it single-purpose. See the non-goals in the README before proposing a
  feature.

## Pull requests

Describe what you changed and how you verified it, including which Calibre
version and OS you tested on. Add tests for anything in `interleave.py` or
`naming.py`.
