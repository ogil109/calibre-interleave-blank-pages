"""Manual plugin: interleave the PDFs of the books you select.

An InterfaceAction that adds a toolbar button (and, once you add it there, a
right-click menu entry) to interleave blank pages into the selected books on
demand -- for PDFs already in the library, where re-importing to trigger the
automatic plugin would be a hack.

Calibre only lets a plugin zip register one plugin class, so this ships as its
own zip, separate from the automatic import-hook plugin. Both share the same
output-folder setting, so configuring either configures both.
"""

from calibre.customize import InterfaceActionBase

__version__ = (0, 1, 0)

PLUGIN_NAME = 'Interleave Blank Pages (manual)'


class InterleaveBlankPagesManual(InterfaceActionBase):
    name = PLUGIN_NAME
    description = (
        'Adds a toolbar/menu action to interleave blank pages into the PDFs of '
        'the selected books, for handwritten notes.'
    )
    supported_platforms = ['linux', 'osx', 'windows']
    author = 'ogil109 <hello@oscargilbalaguer.com>'
    version = __version__
    minimum_calibre_version = (6, 0, 0)

    # Points Calibre at the InterfaceAction implementation. Must be an absolute
    # module path; this zip's import name is interleave_blank_pages_manual.
    actual_plugin = 'calibre_plugins.interleave_blank_pages_manual.action:InterleaveManualAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.interleave_blank_pages_manual.config import ConfigWidget

        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
