# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for MusicAnalysis — PySide6 + QtWebEngine desktop app
with heavy scientific-computing dependencies.

Build with:  pyinstaller music_analysis.spec
Output:      dist/MusicAnalysis/  (one-folder bundle)
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    collect_data_files,
)

block_cipher = None
ROOT = Path(SPECPATH)


def _strip_tests(modules):
    """Remove test / example / benchmark submodules to cut size and build time."""
    return [
        m for m in modules
        if not any(part in m for part in (
            '.tests', '.test_', '.testing.', '.benchmarks',
            '.conftest', '.examples', '_pytest',
        ))
    ]


# ── hidden imports ──────────────────────────────────────────────────
hidden = []

# Scientific stack — collect submodules but drop tests
hidden += _strip_tests(collect_submodules('sklearn'))
hidden += _strip_tests(collect_submodules('scipy'))
hidden += _strip_tests(collect_submodules('librosa'))
hidden += _strip_tests(collect_submodules('soundfile'))
hidden += _strip_tests(collect_submodules('stumpy'))
hidden += _strip_tests(collect_submodules('tslearn'))
hidden += _strip_tests(collect_submodules('plotly'))
hidden += _strip_tests(collect_submodules('numpy'))

# music21 — grab submodules but corpus data excluded below
hidden += _strip_tests(collect_submodules('music21'))

# Qt / PySide6
hidden += [
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebChannel',
    'PySide6.QtNetwork',
    'PySide6.QtPositioning',
    'PySide6.QtPrintSupport',
    'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets',
]

# Our own packages
hidden += collect_submodules('ui')
hidden += collect_submodules('stages')
hidden += collect_submodules('viz')

# ── data files ──────────────────────────────────────────────────────
datas = []

# PySide6 — collect everything (plugins, translations, WebEngine resources)
pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all('PySide6')
datas += pyside6_datas
hidden += pyside6_hidden

# stumpy needs its source files on disk (stumpy.cache.get_njit_funcs
# enumerates the package directory at runtime via pathlib.iterdir)
import importlib
_stumpy_spec = importlib.util.find_spec('stumpy')
if _stumpy_spec and _stumpy_spec.origin:
    datas += [(str(Path(_stumpy_spec.origin).parent), 'stumpy')]

# librosa needs its example / util data
datas += collect_data_files('librosa')

# music21 — include instrument definitions etc, but NOT the corpus
m21_datas = collect_data_files('music21')
m21_datas = [
    (src, dst) for src, dst in m21_datas
    if 'corpus' not in src.replace('\\', '/').lower()
]
datas += m21_datas

# plotly needs its bundled JS templates
datas += collect_data_files('plotly')

# ── excluded modules ────────────────────────────────────────────────
excludes = [
    'tkinter', '_tkinter',
    'IPython', 'jupyter', 'jupyter_client', 'jupyter_core',
    'notebook', 'nbconvert', 'nbformat',
    'pytest', '_pytest',
    'sphinx',
    # music21.corpus code is kept (tiny); only corpus DATA is filtered below
    # Deep-learning frameworks — optional, unused, multi-GB each
    'torch', 'torchvision', 'torchaudio', 'torchtext',
    'tensorflow', 'keras', 'jax', 'jaxlib',
    # Other heavy optional deps
    'dask', 'distributed',
    'sympy',
    'h5py', 'tables',
    'bokeh', 'panel', 'holoviews',
    # Additional bloat
    'pyarrow', 'pandas.tests',
]

# ── Analysis object ─────────────────────────────────────────────────
a = Analysis(
    [str(ROOT / 'run_gui.py')],
    pathex=[str(ROOT)],
    binaries=pyside6_binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # one-folder mode
    name='MusicAnalysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                  # windowed app — no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MusicAnalysis',
)

# macOS .app bundle (ignored on Windows/Linux)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='MusicAnalysis.app',
        bundle_identifier='com.musicanalysis.app',
    )
