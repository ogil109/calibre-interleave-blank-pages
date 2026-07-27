"""Single source of truth for the version of both plugins.

Bumped automatically by commitizen (see ``[tool.commitizen]`` in
``pyproject.toml``); do not edit by hand. The plugins turn this string into the
``(major, minor, patch)`` tuple Calibre expects for a plugin's ``version``.
"""

__version__ = '0.2.1'

#: Calibre wants the plugin version as a tuple of ints.
version_tuple = tuple(int(part) for part in __version__.split('.'))
