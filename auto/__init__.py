"""Automatic plugin: interleave every imported PDF.

A FileTypePlugin that fires on PDF import and writes a side copy with one blank
page after every original page, into a user-configured folder. The imported
file and its database record are never touched.

The actual work lives in the shared ``processing`` module, which this plugin
and the manual action both call.
"""

import traceback

from calibre.customize import FileTypePlugin
from calibre.utils.logging import default_log

__version__ = (0, 1, 0)

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
        from .config import ConfigWidget

        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()

    # -- The hook ----------------------------------------------------------

    def postimport(self, book_id, book_format, db):
        """Called by Calibre once a PDF has been added to a book record.

        Wrapped whole: a failure here must never break the user's import.
        """
        try:
            self._run(book_id, db)
        except Exception:
            default_log.error(f'{PLUGIN_NAME}: failed for book {book_id}')
            default_log.error(traceback.format_exc())

    def _run(self, book_id, db):
        from .config import prefs
        from .processing import LABELS, NO_PDF, WROTE, process_resolved, resolve

        if not prefs['enabled']:
            return

        output_dir = (prefs['output_dir'] or '').strip()
        if not output_dir:
            # A warning, not info: this is the commonest reason the plugin
            # appears to do nothing, and it should stand out in the log.
            default_log.warn(
                f'{PLUGIN_NAME}: no output folder configured, so nothing was written. '
                'Set one in Preferences -> Plugins -> Interleave Blank Pages -> Customize plugin.'
            )
            return

        api = getattr(db, 'new_api', db)
        title, src_path = resolve(api, book_id)
        if src_path is None:
            # Books added from a stream have no file on disk to read.
            default_log.info(f'{PLUGIN_NAME}: no file on disk for book {book_id}, skipping.')
            return

        code = process_resolved(
            book_id,
            title,
            src_path,
            output_dir,
            self.plugin_path,
            log=lambda msg: default_log.info(f'{PLUGIN_NAME}: {msg}'),
        )

        if code == WROTE:
            default_log.info(f'{PLUGIN_NAME}: wrote interleaved copy of "{title}"')
        elif code == NO_PDF:
            default_log.info(f'{PLUGIN_NAME}: no file on disk for book {book_id}, skipping.')
        else:
            default_log.info(f'{PLUGIN_NAME}: skipped "{title}" ({LABELS.get(code, code)})')
