<!-- Thanks for contributing. Keep it focused: one change per PR. -->

## What this changes

<!-- A sentence or two on the change and why. Link an issue if there is one. -->

## How it was verified

<!-- Tick what you ran; note the Calibre version and OS for anything GUI-related. -->

- [ ] `uv run pytest`
- [ ] `uv run ruff check .` and `uv run ruff format --check .`
- [ ] `calibre-debug tests/calibre_checks.py` (built and installed both zips first)
- [ ] Checked by hand in `calibre-debug -g` (for changes to the GUI action)

Calibre version / OS tested on:

## Notes

<!-- Anything reviewers should know: trade-offs, follow-ups, things left out.
     New runtime dependencies are out of scope — see CONTRIBUTING.md. -->
