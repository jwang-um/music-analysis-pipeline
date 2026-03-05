"""Shared UI utilities."""

import os
import tempfile

from PySide6.QtCore import QUrl


def load_html_in_webview(web_view, html: str, old_path: str = None) -> str:
    """Write HTML to a temp file and load in QWebEngineView.

    Bypasses the ~2 MB setHtml() / setContent() IPC limit by loading
    from a local file URL instead.  Returns the temp-file path so the
    caller can pass it back on the next call for cleanup.
    """
    if old_path:
        try:
            os.unlink(old_path)
        except OSError:
            pass

    fd, path = tempfile.mkstemp(suffix='.html', prefix='plot_')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(html)

    web_view.setUrl(QUrl.fromLocalFile(path))
    return path
