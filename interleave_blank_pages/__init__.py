"""Calibre plugin: write an interleaved copy of every imported PDF.

For each imported PDF the plugin emits a side copy with one blank page after
every original page, into a user-configured folder. The imported file and its
database record are never touched.
"""

import os
import subprocess
import sys
import traceback

from calibre.customize import FileTypePlugin
from calibre.utils.logging import default_log

__version__ = (1, 0, 0)

PLUGIN_NAME = 'Interleave Blank Pages'


class InterleaveBlankPages(FileTypePlugin):
    name = PLUGIN_NAME
    description = (
        'After a PDF is imported, write a copy with a blank page after every '
        'page into a folder of your choice, for handwritten notes.'
    )
    supported_platforms = ['linux', 'osx', 'windows']
    author = 'ogil'
    version = __version__
    minimum_calibre_version = (6, 0, 0)

    file_types = {'pdf'}
    on_postimport = True

    # -- Calibre configuration plumbing ------------------------------------

    def is_customizable(self):
        # The base class infers this from customization_help(), which we do
        # not implement because we supply a real config widget instead.
        return True

    def config_widget(self):
        from calibre_plugins.interleave_blank_pages.config import ConfigWidget

        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()

    # -- The hook ----------------------------------------------------------

    def postimport(self, book_id, book_format, db):
        """Called by Calibre once a PDF has been added to a book record.

        Wrapped whole: a failure here must never break the user's import.
        """
        try:
            self._run(book_id, book_format, db)
        except Exception:
            default_log.error(f'{PLUGIN_NAME}: failed for book {book_id}')
            default_log.error(traceback.format_exc())

    def _run(self, book_id, book_format, db):
        from calibre_plugins.interleave_blank_pages.config import prefs
        from calibre_plugins.interleave_blank_pages.naming import needs_rewrite, output_name

        if not prefs['enabled']:
            return

        output_dir = (prefs['output_dir'] or '').strip()
        if not output_dir:
            default_log.info(
                f'{PLUGIN_NAME}: no output folder configured, skipping. Set one in Preferences -> Plugins.'
            )
            return

        # Calibre lowercases the format before calling us; format_abspath
        # uppercases again internally, so either case resolves correctly.
        api = getattr(db, 'new_api', db)
        src_path = api.format_abspath(book_id, book_format)
        if not src_path:
            # Books added from a stream have no file on disk to read.
            default_log.info(f'{PLUGIN_NAME}: no file on disk for book {book_id}, skipping.')
            return

        title = api.field_for('title', book_id)
        dst_path = os.path.join(output_dir, output_name(title, book_id))

        if os.path.abspath(dst_path) == os.path.abspath(src_path):
            default_log.warn(f'{PLUGIN_NAME}: output path equals source path, skipping.')
            return

        if os.path.islink(output_dir) or os.path.islink(dst_path):
            default_log.warn(f'{PLUGIN_NAME}: refusing to write through a symlink: {dst_path}')
            return

        if not needs_rewrite(src_path, dst_path):
            default_log.info(f'{PLUGIN_NAME}: {dst_path} is up to date, skipping.')
            return

        os.makedirs(output_dir, exist_ok=True)
        self._interleave(src_path, dst_path, prefs['python_path'] or 'python3')
        default_log.info(f'{PLUGIN_NAME}: wrote {dst_path}')

    # -- Running the interleaver -------------------------------------------

    def _interleave(self, src_path, dst_path, python_path):
        """Run interleave.py under an external Python that has PyMuPDF.

        Calibre bundles its own Python, which cannot see packages installed
        into the system Python, so the actual PDF work happens out of process.
        """
        script = self._script_path()
        cmd = [python_path, script, src_path, '-o', dst_path]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0,
        )
        if result.returncode != 0:
            output = result.stdout.decode('utf-8', 'replace').strip()
            raise RuntimeError(
                f'{python_path} exited {result.returncode} while interleaving {src_path}. '
                'The output below says why; a ModuleNotFoundError means PyMuPDF is not '
                f'installed for that interpreter.\n{output}'
            )

    def _script_path(self):
        """Materialize interleave.py somewhere a subprocess can run it.

        Installed plugins live inside a zip, so the script has to be unpacked
        before it can be handed to another interpreter.
        """
        from calibre.constants import cache_dir

        sibling = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'interleave.py')
        if os.path.exists(sibling):
            return sibling

        source = self.load_resources(['interleave.py'])['interleave.py']
        target_dir = os.path.join(cache_dir(), 'interleave_blank_pages')
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, 'interleave.py')
        with open(target, 'wb') as handle:
            handle.write(source)
        return target
