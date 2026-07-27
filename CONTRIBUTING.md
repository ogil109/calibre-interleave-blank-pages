# Contributing

Thanks for taking a look. This is a deliberately small, single-purpose tool;
the bar for new features is high, but fixes and platform reports are very
welcome.

## Getting set up

```sh
uv sync
uv run pytest                          # interleaving, naming, idempotency
uv run ruff check .

# Needs both plugin zips built and installed (see below):
calibre-debug tests/calibre_checks.py  # bundled wheel, import hook, manual worker
```

## Project layout

Two plugins share one library. Calibre only lets a zip register one plugin
class, so each is built into its own zip from the shared modules plus one
plugin's entry files (see `scripts/build_plugin.py`).

```
shared/               modules copied into BOTH zips
  interleave.py       the PDF work, via the bundled PyMuPDF; standalone + a CLI
  naming.py           output filename rules and the idempotency check
  vendor.py           unpacks the bundled PyMuPDF wheel onto sys.path
  config.py           JSONConfig settings + the Preferences widget
  processing.py       the shared core: resolve() reads the DB, process_resolved()
                      does the file work; both plugins call these
auto/
  __init__.py         FileTypePlugin: the postimport hook (automatic on import)
manual/
  __init__.py         InterfaceActionBase (points at the action below)
  action.py           InterfaceAction: the toolbar/menu action + its worker
scripts/build_plugin.py   assembles shared/ + auto|manual into dist/*.zip
tests/test_*.py       plain pytest over the Calibre-free modules
tests/calibre_checks.py   runs under calibre-debug; wheel, hook, manual worker
```

Both plugins use the same `JSONConfig` path (`plugins/interleave_blank_pages`),
so their output-folder setting is shared. Both unpack the wheel into the same
cache subdirectory, so installing both unpacks it once.

Shared modules use **relative imports** (`from .naming import ...`) so the same
code works under either zip's package name (`calibre_plugins.interleave_blank_pages`
or `..._manual`). `interleave.py` and `naming.py` import no siblings, so they
stay importable standalone for the pytest suite.

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
  import nothing from Calibre. `tests/conftest.py` puts `shared/` on `sys.path`
  and imports them as top-level modules.
- **`tests/calibre_checks.py` under `calibre-debug`** covers what only Calibre
  can show: that the bundled wheel is importable inside Calibre's Python, that
  the shared processing rules behave, that the `postimport` hook works against a
  real library, and that the manual action's background worker produces output.
  It is a self-contained runner because Calibre's Python has no pytest.

The manual action's GUI glue (button → selection → job) is intentionally thin
and is exercised at the worker level; its `_worker` takes book data already
resolved on the GUI thread, so it runs headless. The pure GUI wiring is not
unit-tested — verify it by hand in `calibre-debug -g`.

`calibre_checks.py` needs both plugins installed from built zips:

```sh
python scripts/build_plugin.py --platform linux
calibre-customize -a dist/interleave_blank_pages-linux.zip
calibre-customize -a dist/interleave_blank_pages_manual-linux.zip
calibre-debug tests/calibre_checks.py
```

Set `IBP_REAL_PDFS` to a colon-separated list of real PDFs to exercise them as
a regression guard — long, structurally complex books are the interesting case:

```sh
IBP_REAL_PDFS="/path/one.pdf:/path/two.pdf" calibre-debug tests/calibre_checks.py
```

## Testing changes in Calibre

```sh
python scripts/build_plugin.py --platform linux
calibre-customize -a dist/interleave_blank_pages-linux.zip
calibre-customize -a dist/interleave_blank_pages_manual-linux.zip
calibre-debug -g          # run Calibre with plugin log output visible
```

To remove them again: `calibre-customize -r "Interleave Blank Pages"` and
`calibre-customize -r "Interleave Blank Pages (manual)"`.

Please verify by hand that an import still succeeds when things go wrong — a
corrupt PDF, an unset output folder, an unwritable target. Never breaking the
user's import is the automatic plugin's most important property.

## Style

- `ruff` settings live in `pyproject.toml`; run it before opening a PR.
- Comments should explain *why*, not restate the code. Most of the non-obvious
  parts of this codebase are Calibre API quirks — those are worth a comment.
- Keep it single-purpose. See the non-goals in the README before proposing a
  feature.

## Commits and releases

Commit messages must follow
[Conventional Commits](https://www.conventionalcommits.org/) — CI rejects a PR
whose commits do not, because releases are cut from them. In short:

- `feat: …` — a user-facing addition (bumps the minor version)
- `fix:`, `refactor:`, `perf:` — a bug fix or code change (bumps the patch
  version)
- a `!` after the type or a `BREAKING CHANGE:` footer marks a breaking change
  (while the project is 0.x this bumps the minor, not the major)
- `docs:`, `test:`, `ci:`, `build:`, `chore:`, `style:` — no release

These are commitizen's standard conventional-commit rules; use the type that
honestly describes the change and let the tooling decide the version.

`uv run cz commit` walks you through a valid message if you'd rather not
memorise the format.

**Releases are fully automated — do not bump versions or edit the changelog by
hand.** On every push to `main`, the Release workflow runs `commitizen`, which
works out the next version from the commits since the last tag, updates
`shared/version.py`, `pyproject.toml` and `CHANGELOG.md`, tags, and publishes
the plugin zips. If nothing since the last tag warrants a release, it does
nothing. The version lives in exactly one place: `shared/version.py`.

## Pull requests

Describe what you changed and how you verified it, including which Calibre
version and OS you tested on. Add tests: `tests/test_*.py` for anything in
`shared/interleave.py` or `shared/naming.py`, and `tests/calibre_checks.py` for
anything touching Calibre, the bundled wheel, or the manual worker.
