"""Persistent settings and the Preferences dialog for the plugin."""

from calibre.utils.config import JSONConfig

#: Stored under Calibre's config directory as plugins/interleave_blank_pages.json
prefs = JSONConfig('plugins/interleave_blank_pages')

prefs.defaults['output_dir'] = ''
prefs.defaults['enabled'] = True


class ConfigWidget:
    """Lazily built so importing this module never requires Qt.

    Calibre only calls :meth:`config_widget` from the GUI, but the plugin
    module itself is imported in headless contexts too (``calibredb``), where
    importing Qt would be wasteful at best.
    """

    def __new__(cls):
        return _build_widget()


def _build_widget():
    from qt.core import (
        QCheckBox,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    class _ConfigWidget(QWidget):
        def __init__(self):
            QWidget.__init__(self)
            layout = QVBoxLayout(self)
            self.setLayout(layout)

            self.enabled_box = QCheckBox('Interleave blank pages on PDF import')
            self.enabled_box.setChecked(bool(prefs['enabled']))
            layout.addWidget(self.enabled_box)

            layout.addWidget(QLabel('Output folder:'))
            row = QHBoxLayout()
            self.dir_edit = QLineEdit(prefs['output_dir'] or '')
            self.dir_edit.setPlaceholderText('Leave empty to disable output')
            row.addWidget(self.dir_edit)
            browse = QPushButton('Browse...')
            browse.clicked.connect(self._pick_dir)
            row.addWidget(browse)
            layout.addLayout(row)

            note = QLabel(
                'Interleaved copies are written to the output folder. Your Calibre library is never modified.'
            )
            note.setWordWrap(True)
            layout.addWidget(note)
            layout.addStretch()

        def _pick_dir(self):
            chosen = QFileDialog.getExistingDirectory(
                self, 'Select output folder', self.dir_edit.text() or ''
            )
            if chosen:
                self.dir_edit.setText(chosen)

        def save_settings(self):
            prefs['enabled'] = self.enabled_box.isChecked()
            prefs['output_dir'] = self.dir_edit.text().strip()

    return _ConfigWidget()
