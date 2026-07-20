"""Calibre plugin: write an interleaved copy of every imported PDF.

For each imported PDF the plugin emits a side copy with one blank page after
every original page, into a user-configured folder. The imported file and its
database record are never touched.
"""

import os
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
    author = 'ogil109 <hello@oscargilbalaguer.com>'
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
        from calibre_plugins.interleave_blank_pages.interleave import interleave
        from calibre_plugins.interleave_blank_pages.naming import needs_rewrite, output_name
        from calibre_plugins.interleave_blank_pages.vendor import ensure_pymupdf

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

        # Put the bundled PyMuPDF on sys.path before interleave() imports it.
        ensure_pymupdf(self.plugin_path, log=lambda msg: default_log.info(f'{PLUGIN_NAME}: {msg}'))

        os.makedirs(output_dir, exist_ok=True)
        interleave(src_path, dst_path)
        default_log.info(f'{PLUGIN_NAME}: wrote {dst_path}')
