"""The toolbar/menu action for interleaving selected books."""

import traceback

from calibre.gui2 import Dispatcher, error_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction

PLUGIN_NAME = 'Interleave Blank Pages (manual)'


def _worker(jobs, output_dir, plugin_path, abort=None, log=None, notifications=None):
    """Interleave each resolved book. Runs in a ThreadedJob worker thread.

    ``jobs`` is a list of ``(book_id, title, src_path)`` resolved on the GUI
    thread, so this function never touches the database. Returns a list of
    ``(title, code_or_error, detail)`` for the completion summary.
    """
    from .processing import LABELS, WROTE, process_resolved

    results = []
    total = len(jobs)
    for index, (book_id, title, src_path) in enumerate(jobs):
        if abort is not None and abort.is_set():
            break
        try:
            code = process_resolved(book_id, title, src_path, output_dir, plugin_path, log=None)
            results.append((title, code, None))
        except Exception:
            results.append((title, 'error', traceback.format_exc()))

        if notifications is not None:
            notifications.put(((index + 1) / total, f'Interleaved {title or book_id}'))
        if log is not None:
            last = results[-1][1]
            log(f'{title}: {LABELS.get(last, last)}' if last != WROTE else f'{title}: written')

    return results


class InterleaveManualAction(InterfaceAction):
    name = PLUGIN_NAME
    # (text, icon, tooltip, keyboard shortcut). No icon name -> Calibre uses a
    # default; the plugin ships no image resources.
    action_spec = (
        'Interleave blank pages',
        None,
        'Write an interleaved copy of each selected book’s PDF',
        None,
    )
    action_type = 'current'

    def genesis(self):
        self.qaction.triggered.connect(self.start)

    def start(self):
        from .config import prefs
        from .processing import resolve

        output_dir = (prefs['output_dir'] or '').strip()
        if not output_dir:
            return error_dialog(
                self.gui,
                'No output folder set',
                f'Set an output folder first: Preferences → Plugins → {PLUGIN_NAME} → Customize plugin.',
                show=True,
            )

        book_ids = self.gui.library_view.get_selected_ids()
        if not book_ids:
            return error_dialog(self.gui, 'No books selected', 'Select one or more books first.', show=True)

        # Resolve titles and paths here, on the database-owning thread, then
        # hand only plain data to the worker.
        api = self.gui.current_db.new_api
        jobs = []
        for book_id in book_ids:
            title, src_path = resolve(api, book_id)
            if src_path:
                jobs.append((book_id, title, src_path))

        if not jobs:
            return error_dialog(
                self.gui,
                'No PDFs to process',
                'None of the selected books have a PDF format.',
                show=True,
            )

        self._start_job(jobs, output_dir)

    def _start_job(self, jobs, output_dir):
        from calibre.gui2.threaded_jobs import ThreadedJob

        job = ThreadedJob(
            'interleave_blank_pages',
            f'Interleaving {len(jobs)} book(s)',
            _worker,
            (jobs, output_dir, self.plugin_path),
            {},
            Dispatcher(self._finished),
        )
        self.gui.job_manager.run_threaded_job(job)
        self.gui.status_bar.show_message(f'Interleaving {len(jobs)} book(s)…', 3000)

    def _finished(self, job):
        from .processing import LABELS, WROTE

        if job.failed:
            return self.gui.job_exception(job, dialog_title='Interleave failed')

        results = job.result or []
        wrote = sum(1 for _, code, _ in results if code == WROTE)
        errors = [(title, detail) for title, code, detail in results if code == 'error']

        # Group the non-error, non-written outcomes (up to date, no PDF, ...).
        skipped = {}
        for title, code, _ in results:
            if code not in (WROTE, 'error'):
                skipped.setdefault(code, []).append(title)

        lines = [f'Wrote {wrote} interleaved {"copy" if wrote == 1 else "copies"}.']
        for code, titles in skipped.items():
            lines.append(f'{len(titles)} skipped ({LABELS.get(code, code)}).')
        if errors:
            lines.append(f'{len(errors)} failed.')

        detail = None
        if errors:
            detail = '\n\n'.join(f'{title}:\n{tb}' for title, tb in errors)

        info_dialog(
            self.gui,
            'Interleave complete',
            '\n'.join(lines),
            det_msg=detail or '',
            show=True,
        )
