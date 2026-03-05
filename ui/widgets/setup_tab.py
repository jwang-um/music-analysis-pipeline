"""Setup tab: full pipeline configuration with Load Config support."""

import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QGroupBox, QSpinBox,
    QFileDialog, QScrollArea, QAbstractItemView, QDialog, QTextBrowser,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
)
from ui.theme import (
    PRIMARY, PRIMARY_HOVER, PRIMARY_LIGHT, BACKGROUND, SURFACE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER,
)


HELP_HTML = f"""\
<style>
    body {{
        font-family: "Segoe UI", "Roboto", sans-serif;
        font-size: 13px;
        color: {TEXT_PRIMARY};
        line-height: 1.6;
        margin: 0;
        padding: 16px 20px;
    }}
    h1 {{
        font-size: 20px;
        font-weight: 700;
        color: {PRIMARY};
        margin: 0 0 6px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid {PRIMARY_LIGHT};
    }}
    h2 {{
        font-size: 14px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
        margin: 20px 0 6px 0;
        padding: 6px 10px;
        background-color: {PRIMARY_LIGHT};
        border-left: 3px solid {PRIMARY};
        border-radius: 0 4px 4px 0;
    }}
    h3 {{
        font-size: 13px;
        font-weight: 600;
        color: {TEXT_SECONDARY};
        margin: 14px 0 4px 0;
    }}
    p, li {{
        margin: 4px 0;
    }}
    ul {{
        margin: 4px 0 4px 20px;
        padding: 0;
    }}
    code {{
        font-family: "Cascadia Code", "Consolas", monospace;
        font-size: 12px;
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 3px;
        padding: 1px 5px;
    }}
    .note {{
        background: {PRIMARY_LIGHT};
        border: 1px solid {PRIMARY};
        border-radius: 6px;
        padding: 10px 14px;
        margin: 10px 0;
        font-size: 12px;
    }}
    .note b {{
        color: {PRIMARY};
    }}
    table {{
        border-collapse: collapse;
        width: 100%;
        margin: 8px 0;
        font-size: 12px;
    }}
    th {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        padding: 6px 10px;
        text-align: left;
        font-weight: 600;
        color: {TEXT_SECONDARY};
    }}
    td {{
        border: 1px solid {BORDER};
        padding: 6px 10px;
    }}
    .step-num {{
        display: inline-block;
        width: 22px;
        height: 22px;
        line-height: 22px;
        text-align: center;
        background: {PRIMARY};
        color: white;
        border-radius: 50%;
        font-size: 12px;
        font-weight: 700;
        margin-right: 6px;
    }}
</style>

<body>

<h1>Configuration Guide</h1>
<p>
This guide documents every field in the Setup tab. You may configure the
pipeline manually using the controls below, or load a pre-written Python
configuration file to populate all fields at once.
</p>

<h2><span class="step-num">1</span> Quick Start &mdash; Loading a Config File</h2>
<p>
Click <b>Load Config File&hellip;</b> to import a Python
<code>.py</code> file that defines the required variables. All recognised
variables are read and applied to the corresponding form fields.
Relative file paths in the config are resolved from the directory
containing the config file.
</p>
<div class="note">
<b>Tip:</b> See <code>config_shostakovich.py</code> in the project root for
a fully-worked example. You can duplicate and modify it for any new piece.
</div>
<p>
The following variable names are recognised:
</p>
<table>
  <tr><th>Variable</th><th>Type</th><th>Description</th></tr>
  <tr><td><code>PIECE_TITLE</code></td><td>str</td>
      <td>Display title used in reports and plot headings</td></tr>
  <tr><td><code>MIDI_PATHS</code></td><td>list[str]</td>
      <td>Ordered list of MIDI file paths (one per movement)</td></tr>
  <tr><td><code>AUDIO_PATHS</code></td><td>list[str]</td>
      <td>Ordered list of audio file paths (same order as MIDI)</td></tr>
  <tr><td><code>MOVEMENT_NAMES</code></td><td>list[str]</td>
      <td>Human-readable names for each movement</td></tr>
  <tr><td><code>PART_NAME_MAP</code></td><td>dict</td>
      <td>Variant &rarr; canonical instrument name mappings</td></tr>
  <tr><td><code>SR</code></td><td>int</td>
      <td>Audio sample rate in Hz</td></tr>
  <tr><td><code>HOP_LENGTH</code></td><td>int</td>
      <td>CQT hop length in samples</td></tr>
  <tr><td><code>N_BINS</code></td><td>int</td>
      <td>Number of CQT frequency bins</td></tr>
  <tr><td><code>BINS_PER_OCT</code></td><td>int</td>
      <td>Frequency resolution per octave</td></tr>
  <tr><td><code>MP_WINDOW_SIZES</code></td><td>list[int]</td>
      <td>Window sizes for Matrix Profile motif discovery</td></tr>
  <tr><td><code>NMF_COMPONENTS</code></td><td>int</td>
      <td>Number of NMF textural components to extract</td></tr>
  <tr><td><code>SEG_K</code></td><td>int</td>
      <td>Number of Laplacian eigenvectors for structural segmentation</td></tr>
</table>

<h2><span class="step-num">2</span> Input Files</h2>
<p>
Provide one MIDI file and one audio file per movement. Files are paired
by their position in each list: the first MIDI file corresponds to the
first audio file, the second to the second, and so on.
</p>
<ul>
  <li>Use <b>Browse&hellip;</b> to add files. They are sorted alphabetically
      on import; reorder by dragging if needed.</li>
  <li>The MIDI and audio file counts must match. The <b>Run Analysis</b>
      button is disabled until they do.</li>
  <li>Supported audio formats: WAV, FLAC, MP3.</li>
</ul>
<p>
For a single-movement piece, add exactly one MIDI file and one audio file.
</p>

<h2><span class="step-num">3</span> Piece Metadata</h2>
<h3>Title</h3>
<p>
A descriptive title for the piece (e.g.&nbsp;<code>Shostakovich &mdash;
Symphony No.&thinsp;5</code>). This appears in all generated plots and
report headers.
</p>
<h3>Movement names</h3>
<p>
Editable labels that appear in axes, tables, and narrative reports.
They are auto-populated when files are added (as "Movement 1",
"Movement 2", etc.) and can be renamed by double-clicking.
</p>

<h2><span class="step-num">4</span> Part Name Normalisation</h2>
<p>
MIDI files authored independently often label the same instrument
differently across movements (e.g.&nbsp;"Grand Piano" vs.&nbsp;"Piano",
or "Violins" vs.&nbsp;"Violins 1"). The stitching stage must merge
these into continuous cross-movement streams.
</p>
<p>
Add rows to the mapping table to specify how variant names should be
normalised:
</p>
<ul>
  <li><b>From (variant)</b> &mdash; the name as it appears in the MIDI file.</li>
  <li><b>To (canonical)</b> &mdash; the standardised name to use internally.</li>
</ul>
<p>
Leave the table empty if all movements already use consistent part
names.
</p>

<h2><span class="step-num">5</span> Audio Parameters</h2>
<table>
  <tr><th>Parameter</th><th>Default</th><th>Description</th></tr>
  <tr>
    <td><b>Sample rate</b></td><td>22 050 Hz</td>
    <td>Target sample rate for audio loading. Higher values preserve more
    high-frequency detail at the cost of memory and compute time. 22 050 Hz
    is standard for music analysis.</td>
  </tr>
  <tr>
    <td><b>CQT hop length</b></td><td>512</td>
    <td>Number of samples between successive CQT frames. At 22 050 Hz this
    yields ~23 ms per frame. Smaller values increase time resolution but
    produce larger spectrograms.</td>
  </tr>
  <tr>
    <td><b>CQT frequency bins</b></td><td>84</td>
    <td>Total number of frequency bins in the Constant-Q Transform.
    84 bins at 12 bins/octave spans 7 octaves. Increase for wider
    frequency coverage.</td>
  </tr>
  <tr>
    <td><b>Bins per octave</b></td><td>12</td>
    <td>Frequency resolution. 12 gives semitone resolution (one bin per
    semitone). 24 gives quarter-tone resolution for microtonal works.</td>
  </tr>
</table>
<div class="note">
<b>Note:</b> The defaults are well-suited to most Western tonal music.
Adjust only if you have specific requirements for frequency range or
time resolution.
</div>

<h2><span class="step-num">6</span> Analysis Parameters</h2>
<table>
  <tr><th>Parameter</th><th>Default</th><th>Description</th></tr>
  <tr>
    <td><b>MP window sizes</b></td><td>8, 10</td>
    <td>Comma-separated list of note-count window sizes for Matrix Profile
    motif discovery. Each window size runs a separate search; results are
    merged. Shorter windows find brief melodic cells, longer windows
    capture phrase-level patterns.</td>
  </tr>
  <tr>
    <td><b>NMF components</b></td><td>8</td>
    <td>Number of components for Non-Negative Matrix Factorisation.
    Each component captures a distinct textural or timbral layer.
    Too few may conflate unlike textures; too many may over-partition
    and produce highly correlated components.</td>
  </tr>
  <tr>
    <td><b>Seg eigenvectors (SEG_K)</b></td><td>8</td>
    <td>Number of Laplacian eigenvectors used by the structural
    segmentation algorithm. Higher values permit finer-grained section
    boundaries. For short pieces or single movements, 4&ndash;6 is
    usually sufficient; for multi-movement symphonies, 8&ndash;12
    is recommended.</td>
  </tr>
</table>

<h2><span class="step-num">7</span> Running the Analysis</h2>
<p>
Once all required fields are configured, the <b>Run Analysis</b> button
in the toolbar becomes active. Click it to start the pipeline.
</p>
<p>
Progress is reported in the toolbar in real time. The pipeline runs in a
background thread; the interface remains responsive throughout. When
complete, the results tabs (Overview, Arc Plot, SSM, NMF, Validation)
are populated automatically and the view switches to the Overview tab.
</p>
<p>
If the pipeline encounters a non-fatal error in a particular stage,
it will skip that stage and continue. Skipped stages are reported in
the Overview tab's error list. A fatal error halts the pipeline and
displays the error message in the toolbar.
</p>

</body>
"""


class ConfigHelpDialog(QDialog):
    """Scrollable reference dialog documenting every Setup field."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Configuration Guide')
        self.setMinimumSize(620, 520)
        self.resize(660, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(HELP_HTML)
        layout.addWidget(browser)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(12, 8, 12, 12)
        btn_row.addStretch()
        close_btn = QPushButton('Close')
        close_btn.setObjectName('primaryBtn')
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName('sectionTitle')
    return lbl


class FileListWidget(QWidget):
    """File list with Browse / Remove / Clear."""

    files_changed = Signal()

    def __init__(self, label: str, extensions: str, parent=None):
        super().__init__(parent)
        self._extensions = extensions
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(_section_label(label))

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setMaximumHeight(110)
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for text, slot in [('Browse…', self._browse),
                           ('Remove', self._remove_selected),
                           ('Clear', self._clear)]:
            btn = QPushButton(text)
            btn.setObjectName('flatBtn')
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

    def _browse(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Select files', '', self._extensions)
        if paths:
            for p in sorted(paths):
                self.list_widget.addItem(os.path.basename(p))
                self.list_widget.item(
                    self.list_widget.count() - 1).setData(Qt.ItemDataRole.UserRole, p)
            self.files_changed.emit()

    def _remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self.files_changed.emit()

    def _clear(self):
        self.list_widget.clear()
        self.files_changed.emit()

    def paths(self):
        return [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.list_widget.count())]

    def set_paths(self, paths):
        self.list_widget.clear()
        for p in paths:
            self.list_widget.addItem(os.path.basename(p))
            self.list_widget.item(
                self.list_widget.count() - 1).setData(Qt.ItemDataRole.UserRole, p)
        self.files_changed.emit()


class PartNameMapEditor(QWidget):
    """Key-value table for part name normalisation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.addWidget(_section_label('Part name map'))
        header.addStretch()
        add_btn = QPushButton('+')
        add_btn.setObjectName('flatBtn')
        add_btn.setFixedWidth(30)
        add_btn.setToolTip('Add mapping row')
        add_btn.clicked.connect(self._add_row)
        header.addWidget(add_btn)
        del_btn = QPushButton('−')
        del_btn.setObjectName('flatBtn')
        del_btn.setFixedWidth(30)
        del_btn.setToolTip('Remove selected row')
        del_btn.clicked.connect(self._remove_row)
        header.addWidget(del_btn)
        layout.addLayout(header)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['From (variant)', 'To (canonical)'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setMaximumHeight(120)
        layout.addWidget(self.table)

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(''))
        self.table.setItem(r, 1, QTableWidgetItem(''))

    def _remove_row(self):
        rows = set(idx.row() for idx in self.table.selectedIndexes())
        for r in sorted(rows, reverse=True):
            self.table.removeRow(r)

    def get_map(self):
        result = {}
        for r in range(self.table.rowCount()):
            key_item = self.table.item(r, 0)
            val_item = self.table.item(r, 1)
            if key_item and val_item:
                k = key_item.text().strip()
                v = val_item.text().strip()
                if k and v:
                    result[k] = v
        return result

    def set_map(self, mapping: dict):
        self.table.setRowCount(0)
        for k, v in mapping.items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(k))
            self.table.setItem(r, 1, QTableWidgetItem(v))


class SetupTab(QScrollArea):
    """Full pipeline configuration UI with Load Config support."""

    config_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)

        # Load config + help
        config_row = QHBoxLayout()
        config_row.setSpacing(8)
        load_btn = QPushButton('Load Config File\u2026')
        load_btn.setObjectName('flatBtn')
        load_btn.setToolTip('Import a Python config file (e.g. config_shostakovich.py)')
        load_btn.clicked.connect(self._load_config)
        config_row.addWidget(load_btn)

        help_btn = QPushButton('?')
        help_btn.setObjectName('helpBtn')
        help_btn.setFixedSize(28, 28)
        help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        help_btn.setToolTip('Open configuration guide')
        help_btn.clicked.connect(self._show_help)
        config_row.addWidget(help_btn)

        config_row.addStretch()
        self._config_path_label = QLabel('')
        self._config_path_label.setStyleSheet(f'font-size: 11px; color: {TEXT_SECONDARY};')
        config_row.addWidget(self._config_path_label)
        layout.addLayout(config_row)

        # ---- Files section ----
        files_box = QGroupBox('Input Files')
        files_layout = QVBoxLayout(files_box)
        files_layout.setSpacing(8)

        self.midi_files = FileListWidget('MIDI files (one per movement, in order)',
                                         'MIDI Files (*.mid *.midi)')
        self.midi_files.files_changed.connect(self._on_files_changed)
        files_layout.addWidget(self.midi_files)

        self.wav_files = FileListWidget('WAV files (matching order)',
                                        'Audio Files (*.wav *.flac *.mp3)')
        self.wav_files.files_changed.connect(self._on_files_changed)
        files_layout.addWidget(self.wav_files)
        layout.addWidget(files_box)

        # ---- Metadata section ----
        meta_box = QGroupBox('Piece Metadata')
        meta_layout = QVBoxLayout(meta_box)
        meta_layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel('Title'))
        self.title_edit = QLineEdit('Untitled')
        title_row.addWidget(self.title_edit)
        meta_layout.addLayout(title_row)

        meta_layout.addWidget(_section_label('Movement names'))
        self.movement_list = QListWidget()
        self.movement_list.setMaximumHeight(110)
        self.movement_list.setAlternatingRowColors(True)
        meta_layout.addWidget(self.movement_list)
        layout.addWidget(meta_box)

        # ---- Part Name Map ----
        pnm_box = QGroupBox('Part Name Normalisation')
        pnm_layout = QVBoxLayout(pnm_box)
        self.part_name_editor = PartNameMapEditor()
        pnm_layout.addWidget(self.part_name_editor)
        pnm_hint = QLabel(
            'Maps variant instrument names across movements to a single canonical name. '
            'Leave empty if MIDI files use consistent names.')
        pnm_hint.setWordWrap(True)
        pnm_hint.setStyleSheet(f'font-size: 10px; color: {TEXT_SECONDARY};')
        pnm_layout.addWidget(pnm_hint)
        layout.addWidget(pnm_box)

        # ---- Audio Parameters ----
        audio_box = QGroupBox('Audio Parameters')
        audio_grid = QGridLayout(audio_box)
        audio_grid.setSpacing(8)

        self.sr_spin = QSpinBox()
        self.sr_spin.setRange(8000, 96000)
        self.sr_spin.setValue(22050)
        self.sr_spin.setSingleStep(1000)
        audio_grid.addWidget(QLabel('Sample rate (Hz)'), 0, 0)
        audio_grid.addWidget(self.sr_spin, 0, 1)

        self.hop_spin = QSpinBox()
        self.hop_spin.setRange(64, 4096)
        self.hop_spin.setValue(512)
        self.hop_spin.setSingleStep(64)
        audio_grid.addWidget(QLabel('CQT hop length'), 1, 0)
        audio_grid.addWidget(self.hop_spin, 1, 1)

        self.nbins_spin = QSpinBox()
        self.nbins_spin.setRange(12, 168)
        self.nbins_spin.setValue(84)
        self.nbins_spin.setSingleStep(12)
        audio_grid.addWidget(QLabel('CQT frequency bins'), 2, 0)
        audio_grid.addWidget(self.nbins_spin, 2, 1)

        self.bpo_spin = QSpinBox()
        self.bpo_spin.setRange(1, 48)
        self.bpo_spin.setValue(12)
        audio_grid.addWidget(QLabel('Bins per octave'), 3, 0)
        audio_grid.addWidget(self.bpo_spin, 3, 1)

        layout.addWidget(audio_box)

        # ---- Analysis Parameters ----
        analysis_box = QGroupBox('Analysis Parameters')
        analysis_grid = QGridLayout(analysis_box)
        analysis_grid.setSpacing(8)

        self.mp_edit = QLineEdit('8, 10')
        self.mp_edit.setToolTip('Comma-separated window sizes for Matrix Profile')
        analysis_grid.addWidget(QLabel('MP window sizes'), 0, 0)
        analysis_grid.addWidget(self.mp_edit, 0, 1)

        self.nmf_spin = QSpinBox()
        self.nmf_spin.setRange(2, 32)
        self.nmf_spin.setValue(8)
        analysis_grid.addWidget(QLabel('NMF components'), 1, 0)
        analysis_grid.addWidget(self.nmf_spin, 1, 1)

        self.seg_spin = QSpinBox()
        self.seg_spin.setRange(2, 32)
        self.seg_spin.setValue(8)
        analysis_grid.addWidget(QLabel('Seg eigenvectors (SEG_K)'), 2, 0)
        analysis_grid.addWidget(self.seg_spin, 2, 1)

        layout.addWidget(analysis_box)
        layout.addStretch()

        self.setWidget(inner)

    # ---- File count sync ----

    def _on_files_changed(self):
        midi_count = len(self.midi_files.paths())
        wav_count = len(self.wav_files.paths())
        n = max(midi_count, wav_count)
        self._set_movement_count(n)
        self.config_changed.emit()

    def _set_movement_count(self, n):
        current = [self.movement_list.item(i).text()
                    for i in range(self.movement_list.count())]
        self.movement_list.clear()
        for i in range(n):
            name = current[i] if i < len(current) else f'Movement {i + 1}'
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.movement_list.addItem(item)

    # ---- Load Config ----

    def _load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select config file', '', 'Python Files (*.py)')
        if not path:
            return

        ns = {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                exec(compile(f.read(), path, 'exec'), ns)
        except Exception as e:
            self._config_path_label.setText(f'Error: {e}')
            return

        config_dir = os.path.dirname(os.path.abspath(path))

        def _resolve(p):
            if os.path.isabs(p):
                return p
            return os.path.normpath(os.path.join(config_dir, p))

        if 'MIDI_PATHS' in ns:
            self.midi_files.set_paths([_resolve(p) for p in ns['MIDI_PATHS']])
        if 'AUDIO_PATHS' in ns:
            self.wav_files.set_paths([_resolve(p) for p in ns['AUDIO_PATHS']])
        if 'MOVEMENT_NAMES' in ns:
            self.movement_list.clear()
            for name in ns['MOVEMENT_NAMES']:
                item = QListWidgetItem(name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.movement_list.addItem(item)
        if 'PIECE_TITLE' in ns:
            self.title_edit.setText(ns['PIECE_TITLE'])
        if 'PART_NAME_MAP' in ns:
            self.part_name_editor.set_map(ns['PART_NAME_MAP'])
        if 'SR' in ns:
            self.sr_spin.setValue(int(ns['SR']))
        if 'HOP_LENGTH' in ns:
            self.hop_spin.setValue(int(ns['HOP_LENGTH']))
        if 'N_BINS' in ns:
            self.nbins_spin.setValue(int(ns['N_BINS']))
        if 'BINS_PER_OCT' in ns:
            self.bpo_spin.setValue(int(ns['BINS_PER_OCT']))
        if 'MP_WINDOW_SIZES' in ns:
            self.mp_edit.setText(', '.join(str(x) for x in ns['MP_WINDOW_SIZES']))
        if 'NMF_COMPONENTS' in ns:
            self.nmf_spin.setValue(int(ns['NMF_COMPONENTS']))
        if 'SEG_K' in ns:
            self.seg_spin.setValue(int(ns['SEG_K']))

        self._config_path_label.setText(os.path.basename(path))
        self.config_changed.emit()

    def _show_help(self):
        dlg = ConfigHelpDialog(self)
        dlg.exec()

    # ---- Collect all params ----

    def is_ready(self):
        midi_count = len(self.midi_files.paths())
        wav_count = len(self.wav_files.paths())
        return midi_count > 0 and wav_count > 0 and midi_count == wav_count

    def get_params(self):
        mp_sizes = []
        for token in self.mp_edit.text().replace(' ', '').split(','):
            try:
                mp_sizes.append(int(token))
            except ValueError:
                pass

        movement_names = [self.movement_list.item(i).text()
                          for i in range(self.movement_list.count())]

        return {
            'midi_paths': self.midi_files.paths(),
            'audio_paths': self.wav_files.paths(),
            'movement_names': movement_names,
            'piece_title': self.title_edit.text().strip() or 'Untitled',
            'part_name_map': self.part_name_editor.get_map(),
            'sr': self.sr_spin.value(),
            'hop_length': self.hop_spin.value(),
            'n_bins': self.nbins_spin.value(),
            'bins_per_oct': self.bpo_spin.value(),
            'mp_window_sizes': mp_sizes or [8, 10],
            'nmf_components': self.nmf_spin.value(),
            'seg_k': self.seg_spin.value(),
        }
