"""Checks that need Calibre. Build and install both plugin zips first:

    python scripts/build_plugin.py --platform linux
    calibre-customize -a dist/interleave_blank_pages-linux.zip
    calibre-customize -a dist/interleave_blank_pages_manual-linux.zip
    calibre-debug tests/calibre_checks.py

These cover what a plain virtualenv cannot: that the bundled PyMuPDF wheel is
importable inside Calibre's own Python, that the shared processing rules behave,
that the automatic import hook works against a real library, and that the
manual action's background worker produces output. The pure interleaving is
covered by tests/test_interleave.py.

Written as a self-contained runner rather than a pytest module, because
Calibre's Python has no pytest. Exits non-zero if any check fails.
"""

import hashlib
import io
import os
import shutil
import sys
import tempfile
import traceback

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


def auto_plugin():
    from calibre.customize.ui import find_plugin

    plugin = find_plugin('Interleave Blank Pages')
    assert plugin is not None, 'the auto plugin is not installed; run calibre-customize -a first'
    return plugin


def manual_plugin():
    from calibre.customize.ui import find_plugin

    plugin = find_plugin('Interleave Blank Pages (manual)')
    assert plugin is not None, 'the manual plugin is not installed; run calibre-customize -a first'
    return plugin


def load_pymupdf(plugin=None):
    """Import PyMuPDF the way the plugins do: from the bundled wheel."""
    from calibre_plugins.interleave_blank_pages.vendor import ensure_pymupdf

    plugin = plugin or auto_plugin()
    return ensure_pymupdf(plugin.plugin_path)


def make_pdf(pymupdf, path, sizes):
    """Write a PDF with one page per (width, height), stamped with its index."""
    with pymupdf.open() as doc:
        for i, (width, height) in enumerate(sizes):
            page = doc.new_page(width=width, height=height)
            page.insert_text((72, 72), f'page {i}', fontsize=24)
        doc.save(str(path))
    return path


@check
def bundled_wheel_is_importable_inside_calibre(tmp):
    pymupdf = load_pymupdf()
    assert hasattr(pymupdf, 'open'), 'PyMuPDF imported but looks wrong'
    print(f'       {pymupdf.__doc__.splitlines()[0]}')


@check
def interleaving_works_inside_calibre(tmp):
    pymupdf = load_pymupdf()
    from calibre_plugins.interleave_blank_pages.interleave import interleave

    src = make_pdf(pymupdf, os.path.join(tmp, 'src.pdf'), [(595, 842), (612, 792), (400, 1000)])
    dst = os.path.join(tmp, 'out.pdf')

    assert interleave(src, dst) == 6

    with pymupdf.open(dst) as doc:
        sizes = [(round(p.rect.width), round(p.rect.height)) for p in doc]
        text = [p.get_text().strip() for p in doc]
    assert sizes == [(595, 842), (595, 842), (612, 792), (612, 792), (400, 1000), (400, 1000)], sizes
    assert text == ['page 0', '', 'page 1', '', 'page 2', ''], text


@check
def shared_processing_reports_outcomes(tmp):
    pymupdf = load_pymupdf()
    from calibre_plugins.interleave_blank_pages.processing import (
        SAME_PATH,
        UP_TO_DATE,
        WROTE,
        process_resolved,
    )

    src = make_pdf(pymupdf, os.path.join(tmp, 'book.pdf'), [(595, 842)] * 2)
    out = os.path.join(tmp, 'out')
    path = auto_plugin().plugin_path

    assert process_resolved(1, 'Title', src, out, path) == WROTE
    # Second run with the output already present and newer.
    assert process_resolved(1, 'Title', src, out, path) == UP_TO_DATE
    # force ignores the mtime check.
    assert process_resolved(1, 'Title', src, out, path, force=True) == WROTE
    # Writing on top of the source itself is refused: this happens only when the
    # source is already named like the output, so construct exactly that.
    collision_dir = os.path.join(tmp, 'collide')
    os.makedirs(collision_dir)
    collision = make_pdf(pymupdf, os.path.join(collision_dir, 'Title (1)-interleaved.pdf'), [(595, 842)])
    assert process_resolved(1, 'Title', collision, collision_dir, path, force=True) == SAME_PATH


@check
def auto_postimport_hook_end_to_end(tmp):
    pymupdf = load_pymupdf()

    from calibre.customize.ui import run_plugins_on_postimport
    from calibre.db.legacy import LibraryDatabase
    from calibre.ebooks.metadata.book.base import Metadata
    from calibre_plugins.interleave_blank_pages.config import prefs

    sample = make_pdf(pymupdf, os.path.join(tmp, 'sample.pdf'), [(595, 842), (612, 792), (400, 1000)])
    outdir = os.path.join(tmp, 'out')
    libdir = os.path.join(tmp, 'lib')

    saved = dict(prefs)
    prefs['output_dir'] = outdir
    prefs['enabled'] = True
    try:
        db = LibraryDatabase(libdir)
        api = db.new_api

        def add(title):
            book_id = api.create_book_entry(Metadata(title))
            with open(sample, 'rb') as handle:
                api.add_format(book_id, 'PDF', handle, run_hooks=False)
            return book_id

        # Calibre stores both books under the same filename, and they share a
        # title, so only the book id can keep the outputs apart.
        first, second = add('Deep Work'), add('Deep Work')
        source = api.format_abspath(first, 'PDF')
        with open(source, 'rb') as handle:
            before = hashlib.sha256(handle.read()).hexdigest()

        for book_id in (first, second):
            run_plugins_on_postimport(db, book_id, 'PDF')

        produced = sorted(os.listdir(outdir))
        assert len(produced) == 2, produced

        output = os.path.join(outdir, f'Deep Work ({first})-interleaved.pdf')
        assert os.path.exists(output), produced
        with pymupdf.open(output) as doc:
            assert doc.page_count == 6, doc.page_count

        with open(source, 'rb') as handle:
            assert hashlib.sha256(handle.read()).hexdigest() == before, 'library file was modified'

        # Idempotency: re-running must not rewrite an up-to-date output.
        mtime = os.path.getmtime(output)
        run_plugins_on_postimport(db, first, 'PDF')
        assert os.path.getmtime(output) == mtime, 'output was rewritten'

        # No output folder configured: the import must still complete.
        prefs['output_dir'] = ''
        run_plugins_on_postimport(db, first, 'PDF')
        assert len(os.listdir(outdir)) == 2

        # A corrupt PDF must be logged, not raised.
        prefs['output_dir'] = outdir
        broken = api.create_book_entry(Metadata('Corrupt Book'))
        api.add_format(broken, 'PDF', io.BytesIO(b''), run_hooks=False)
        run_plugins_on_postimport(db, broken, 'PDF')
        assert len(os.listdir(outdir)) == 2, 'corrupt book produced output'

        db.close()
    finally:
        for key, value in saved.items():
            prefs[key] = value


@check
def manual_action_target_resolves(tmp):
    """The InterfaceActionBase must point at a real InterfaceAction subclass."""
    from calibre.gui2.actions import InterfaceAction
    from calibre_plugins.interleave_blank_pages_manual.action import InterleaveManualAction

    assert issubclass(InterleaveManualAction, InterfaceAction)
    # The actual_plugin string on the base must name that class.
    assert manual_plugin().actual_plugin.endswith(':InterleaveManualAction')


@check
def manual_worker_produces_output(tmp):
    """Run the manual action's background worker directly.

    The worker takes book data already resolved on the GUI thread, so it can be
    exercised without a running GUI -- which is the point of keeping database
    access out of it.
    """
    pymupdf = load_pymupdf(manual_plugin())
    from calibre_plugins.interleave_blank_pages_manual.action import _worker
    from calibre_plugins.interleave_blank_pages_manual.processing import UP_TO_DATE, WROTE

    src_a = make_pdf(pymupdf, os.path.join(tmp, 'a.pdf'), [(595, 842)] * 3)
    src_b = make_pdf(pymupdf, os.path.join(tmp, 'b.pdf'), [(400, 600)] * 2)
    outdir = os.path.join(tmp, 'out')
    path = manual_plugin().plugin_path

    jobs = [(1, 'Alpha', src_a), (2, 'Beta', src_b), (3, 'No PDF', None)]
    results = _worker(jobs, outdir, path)

    codes = {title: code for title, code, _ in results}
    assert codes['Alpha'] == WROTE, codes
    assert codes['Beta'] == WROTE, codes
    assert codes['No PDF'] == 'no_pdf', codes

    produced = sorted(os.listdir(outdir))
    assert produced == ['Alpha (1)-interleaved.pdf', 'Beta (2)-interleaved.pdf'], produced
    with pymupdf.open(os.path.join(outdir, 'Alpha (1)-interleaved.pdf')) as doc:
        assert doc.page_count == 6, doc.page_count

    # Re-running the same selection is idempotent.
    again = {title: code for title, code, _ in _worker(jobs, outdir, path)}
    assert again['Alpha'] == UP_TO_DATE, again


@check
def manual_action_gui_path(tmp):
    """Drive the real InterfaceAction the way Calibre's GUI drives it.

    Covers what the worker check cannot: building the QAction from action_spec,
    the triggered connection, reading the selection, resolving it against a real
    library, launching the job and rendering the completion summary.

    A stub GUI stands in for the main window, wired exactly as
    calibre/gui2/ui.py does (plugin_path + interface_action_base_plugin), and
    the job runs synchronously so the check stays deterministic. The dialogs are
    recorded rather than shown, since they are modal and nothing would dismiss
    them.
    """
    import types

    # Must be set before the first QApplication; there is no display in CI.
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from qt.core import QApplication, QWidget

    pymupdf = load_pymupdf(manual_plugin())

    from calibre.db.legacy import LibraryDatabase
    from calibre.ebooks.metadata.book.base import Metadata
    from calibre_plugins.interleave_blank_pages_manual import action as action_mod
    from calibre_plugins.interleave_blank_pages_manual.config import prefs

    app = QApplication.instance() or QApplication(sys.argv[:1])
    assert app is not None

    sample = make_pdf(pymupdf, os.path.join(tmp, 'sample.pdf'), [(595, 842)] * 3)
    outdir = os.path.join(tmp, 'out')
    libdir = os.path.join(tmp, 'lib')

    shown = []
    real_error, real_info = action_mod.error_dialog, action_mod.info_dialog
    action_mod.error_dialog = lambda parent, title, msg, **kw: shown.append(('error', title, msg))
    action_mod.info_dialog = lambda parent, title, msg, **kw: shown.append(('info', title, msg))

    saved = dict(prefs)
    try:
        db = LibraryDatabase(libdir)
        api = db.new_api

        with_pdf = api.create_book_entry(Metadata('Selected Book'))
        with open(sample, 'rb') as handle:
            api.add_format(with_pdf, 'PDF', handle, run_hooks=False)
        without_pdf = api.create_book_entry(Metadata('No Format Book'))

        selection = []

        def run_synchronously(job):
            job.result = job.func(*job.args, **job.kwargs)
            job.failed = False
            job.callback(job)

        gui = QWidget()
        gui.library_view = types.SimpleNamespace(get_selected_ids=lambda: list(selection))
        gui.current_db = db
        gui.job_manager = types.SimpleNamespace(run_threaded_job=run_synchronously)
        gui.status_bar = types.SimpleNamespace(show_message=lambda *a, **k: None)

        base = manual_plugin()
        action = action_mod.InterleaveManualAction(gui, '')
        # Exactly what calibre/gui2/ui.py does after load_actual_plugin.
        action.plugin_path = base.plugin_path
        action.interface_action_base_plugin = base
        action.do_genesis()

        assert action.qaction is not None, 'no QAction was built from action_spec'
        assert action.qaction.text() == 'Interleave blank pages', action.qaction.text()

        def fire():
            """Trigger the action and let queued callbacks run.

            The job's completion callback goes through a Dispatcher, which
            marshals it as a *queued* Qt signal -- it only runs once an event
            loop turns. The real GUI has one; here it has to be pumped.
            """
            action.qaction.trigger()
            for _ in range(3):
                app.processEvents()

        # 1. No output folder configured -> the button is greyed out, and its
        #    tooltip says why, rather than letting a click fail.
        prefs['output_dir'] = ''
        action.refresh_enabled()
        assert not action.qaction.isEnabled(), 'button should be disabled with no output folder'
        assert 'output folder' in action.qaction.toolTip().lower(), action.qaction.toolTip()
        selection[:] = [with_pdf]
        fire()  # trigger() is a no-op on a disabled action
        assert not shown, f'disabled button still acted: {shown}'
        assert not os.path.exists(outdir), 'output folder created while button disabled'

        # 2. Setting the folder via the config dialog re-enables the button
        #    immediately, without waiting for a library switch.
        base.actual_plugin_ = action  # what load_actual_plugin records

        class _Widget:
            def save_settings(self):
                prefs['output_dir'] = outdir

        base.save_settings(_Widget())
        assert action.qaction.isEnabled(), 'button not re-enabled after folder was set'
        assert action.qaction.toolTip() == action._enabled_tip, action.qaction.toolTip()

        # 3. The disabled-button guard: the keyboard-shortcut path can still
        #    call start() directly, so it must refuse cleanly on its own.
        prefs['output_dir'] = ''
        action.start()
        assert shown[-1][0] == 'error' and 'output folder' in shown[-1][1].lower(), shown[-1]
        prefs['output_dir'] = outdir
        action.refresh_enabled()

        # 4. Nothing selected -> complains.
        selection[:] = []
        fire()
        assert shown[-1][0] == 'error' and 'selected' in shown[-1][1].lower(), shown[-1]

        # 5. Selection has no PDF -> complains, writes nothing.
        selection[:] = [without_pdf]
        fire()
        assert shown[-1][0] == 'error' and 'PDF' in shown[-1][1], shown[-1]
        assert not os.path.exists(outdir), 'output folder created for a book with no PDF'

        # 6. The real path: a selected PDF is interleaved and reported.
        selection[:] = [with_pdf, without_pdf]
        fire()
        assert shown[-1][0] == 'info', shown[-1]
        assert 'Wrote 1' in shown[-1][2], shown[-1][2]

        produced = sorted(os.listdir(outdir))
        assert produced == [f'Selected Book ({with_pdf})-interleaved.pdf'], produced
        with pymupdf.open(os.path.join(outdir, produced[0])) as doc:
            assert doc.page_count == 6, doc.page_count

        # 7. Running it again reports the skip rather than redoing the work.
        fire()
        assert 'Wrote 0' in shown[-1][2], shown[-1][2]
        assert 'up to date' in shown[-1][2], shown[-1][2]

        db.close()
    finally:
        action_mod.error_dialog, action_mod.info_dialog = real_error, real_info
        for key, value in saved.items():
            prefs[key] = value


@check
def real_world_books_survive(tmp):
    """Regression guard for the documents that made podofo segfault.

    Set IBP_REAL_PDFS to a colon-separated list of PDFs to exercise them.
    """
    paths = [p for p in os.environ.get('IBP_REAL_PDFS', '').split(':') if p]
    if not paths:
        print('       skipped (set IBP_REAL_PDFS to run)')
        return

    pymupdf = load_pymupdf()
    from calibre_plugins.interleave_blank_pages.interleave import interleave

    for path in paths:
        with pymupdf.open(path) as doc:
            expected = doc.page_count * 2
        out = os.path.join(tmp, 'real.pdf')
        assert interleave(path, out) == expected, os.path.basename(path)
        print(f'       {os.path.basename(path)[:40]:42} -> {expected} pages')


def main():
    failures = 0
    for fn in CHECKS:
        tmp = tempfile.mkdtemp(prefix='ibp-check-')
        try:
            fn(tmp)
            print(f'  ok   {fn.__name__}')
        except Exception:
            failures += 1
            print(f'  FAIL {fn.__name__}')
            traceback.print_exc()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print(f'\n{len(CHECKS) - failures}/{len(CHECKS)} checks passed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
