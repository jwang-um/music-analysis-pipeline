"""Interactive score visualization tab using Verovio WebAssembly."""

import json
import base64
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, Slot, QObject, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QCheckBox,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from ui.theme import PRIMARY, TEXT_SECONDARY, TAB10_HEX
from pipeline import AnalysisResults


SCORE_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body { margin:0; padding:0; overflow-y:auto; background:#fff;
       font-family:'Segoe UI','Roboto',sans-serif; }
#score-container { padding:10px 20px; min-height:200px; }
#loading { text-align:center; padding:60px 20px; color:#5F6368; font-size:14px; }
#loading .spinner { display:inline-block; width:28px; height:28px;
    border:3px solid #DADCE0; border-top-color:#1A73E8;
    border-radius:50%; animation:spin .8s linear infinite; margin-bottom:12px; }
@keyframes spin { to { transform:rotate(360deg); } }

.note-flash { animation: flash-anim 0.8s ease-out; }
@keyframes flash-anim {
    0%   { filter: drop-shadow(0 0 6px #FBBC04); }
    100% { filter: none; }
}
</style>
</head>
<body>
<div id="loading"><div class="spinner"></div><br>Loading Verovio engraver&hellip;</div>
<div id="score-container"></div>

<script src="https://www.verovio.org/javascript/latest/verovio-toolkit-wasm.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
var vrvToolkit = null;
var timemap = [];
var currentPage = 1;
var pageCount = 0;
var musicXmlData = '';
var bridge = null;
var scale = 35;

new QWebChannel(qt.webChannelTransport, function(channel) {
    bridge = channel.objects.bridge;
});

function loadScoreBase64(b64) {
    try { musicXmlData = atob(b64); } catch(e) { musicXmlData = ''; }
    if (vrvToolkit && musicXmlData) renderScore();
}

function renderScore() {
    var container = document.getElementById('score-container');
    document.getElementById('loading').style.display = 'none';
    container.style.display = '';

    var pw = Math.max(800, container.clientWidth - 40);
    vrvToolkit.setOptions({
        pageWidth:  Math.round(pw * 100 / scale),
        pageHeight: 30000,
        scale: scale,
        adjustPageHeight: false,
        breaks: 'auto',
        spacingStaff: 4,
        spacingSystem: 4
    });
    vrvToolkit.loadData(musicXmlData);
    pageCount = vrvToolkit.getPageCount();

    try { timemap = JSON.parse(vrvToolkit.renderToTimemap()); }
    catch(e) { timemap = []; }

    renderPage(1);
    if (bridge) bridge.onScoreLoaded(pageCount, JSON.stringify(timemap));
}

function renderPage(n) {
    if (n < 1 || n > pageCount) return;
    currentPage = n;
    var svg = vrvToolkit.renderToSVG(n);
    document.getElementById('score-container').innerHTML = svg;
    if (bridge) bridge.onPageChanged(currentPage, pageCount);
}

function setScale(s) {
    scale = s;
    if (vrvToolkit && musicXmlData) renderScore();
}

function goToPage(n) { renderPage(n); }

function _qs(entry) {
    return entry.qstamp !== undefined ? entry.qstamp : (entry.tstamp || 0);
}

function findNoteIdsAtBeat(beat, tolerance) {
    tolerance = tolerance || 0.5;
    var ids = [];
    for (var i = 0; i < timemap.length; i++) {
        var entry = timemap[i];
        if (entry.on && Math.abs(_qs(entry) - beat) <= tolerance) {
            ids = ids.concat(entry.on);
        }
    }
    return ids;
}

function findNoteIdsInRange(beatStart, beatEnd) {
    var ids = [];
    for (var i = 0; i < timemap.length; i++) {
        var entry = timemap[i];
        var q = _qs(entry);
        if (entry.on && q >= beatStart && q <= beatEnd) {
            ids = ids.concat(entry.on);
        }
    }
    return ids;
}

function highlightNotes(noteIds, color, className) {
    for (var i = 0; i < noteIds.length; i++) {
        var el = document.getElementById(noteIds[i]);
        if (!el) continue;
        el.classList.add(className);
        var children = el.querySelectorAll('path, use, ellipse, rect, polygon');
        for (var j = 0; j < children.length; j++) {
            children[j].style.fill = color;
        }
    }
}

function clearHighlights(className) {
    var els = document.querySelectorAll('.' + className);
    for (var i = 0; i < els.length; i++) {
        els[i].classList.remove(className);
        var children = els[i].querySelectorAll('path, use, ellipse, rect, polygon');
        for (var j = 0; j < children.length; j++) {
            children[j].style.fill = '';
        }
    }
}

function goToBeat(beat) {
    var ids = findNoteIdsAtBeat(beat, 4.0);
    if (ids.length === 0) {
        ids = findNearestNoteIds(beat);
    }
    if (ids.length === 0) return;
    var noteId = ids[0];
    var page = vrvToolkit.getPageWithElement(noteId);
    if (page > 0 && page !== currentPage) renderPage(page);
    setTimeout(function() {
        var el = document.getElementById(noteId);
        if (el) {
            el.scrollIntoView({ behavior:'smooth', block:'center' });
            el.classList.add('note-flash');
            setTimeout(function(){ el.classList.remove('note-flash'); }, 800);
        }
    }, 150);
}

function findNearestNoteIds(beat) {
    var bestDist = Infinity, bestIds = [];
    for (var i = 0; i < timemap.length; i++) {
        var entry = timemap[i];
        if (!entry.on) continue;
        var qs = entry.qstamp !== undefined ? entry.qstamp : 0;
        var dist = Math.abs(qs - beat);
        if (dist < bestDist) {
            bestDist = dist;
            bestIds = entry.on;
        }
    }
    return bestIds;
}

function getPageCount() { return pageCount; }
function getCurrentPage() { return currentPage; }

verovio.module.onRuntimeInitialized = function() {
    vrvToolkit = new verovio.toolkit();
    document.getElementById('loading').innerHTML =
        'Verovio ready. Run analysis to load a score.';
    if (bridge) bridge.onVerovioReady();
    if (musicXmlData) renderScore();
};
</script>
</body>
</html>"""


def _seconds_to_beats(times_sec: List[float],
                      tempo_marks: List) -> List[float]:
    """Inverse of beats_to_seconds: convert seconds back to beat positions."""
    if not tempo_marks:
        return list(times_sec)

    cum_sec = [0.0]
    cum_beats = [tempo_marks[0][0]]
    for i in range(1, len(tempo_marks)):
        prev_beat, prev_bpm = tempo_marks[i - 1]
        curr_beat, _ = tempo_marks[i]
        delta_sec = (curr_beat - prev_beat) * 60.0 / prev_bpm
        cum_sec.append(cum_sec[-1] + delta_sec)
        cum_beats.append(curr_beat)

    result = []
    for t in times_sec:
        idx = 0
        for i in range(1, len(cum_sec)):
            if t >= cum_sec[i]:
                idx = i
            else:
                break
        remaining = t - cum_sec[idx]
        bpm = tempo_marks[idx][1]
        beat = cum_beats[idx] + remaining * bpm / 60.0
        result.append(beat)
    return result


class ScoreBridge(QObject):
    """Python-side receiver for callbacks from the Verovio JavaScript."""

    verovio_ready = Signal()
    score_loaded = Signal(int, str)
    page_changed = Signal(int, int)

    @Slot()
    def onVerovioReady(self):
        self.verovio_ready.emit()

    @Slot(int, str)
    def onScoreLoaded(self, page_count: int, timemap_json: str):
        self.score_loaded.emit(page_count, timemap_json)

    @Slot(int, int)
    def onPageChanged(self, current: int, total: int):
        self.page_changed.emit(current, total)


class ScoreTab(QWidget):
    """Interactive score rendering tab with analysis overlays."""

    navigate_to_time = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._results: Optional[AnalysisResults] = None
        self._timemap: list = []
        self._page_count = 0
        self._current_page = 1
        self._verovio_ready = False
        self._pending_musicxml: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- toolbar --
        tb = QHBoxLayout()
        tb.setContentsMargins(8, 6, 8, 6)
        tb.setSpacing(8)

        self._btn_prev = QPushButton('\u25C0')
        self._btn_prev.setFixedSize(28, 28)
        self._btn_prev.setObjectName('flatBtn')
        self._btn_prev.clicked.connect(self._prev_page)
        tb.addWidget(self._btn_prev)

        self._page_label = QLabel('Page 0 / 0')
        self._page_label.setStyleSheet('font-size: 12px;')
        tb.addWidget(self._page_label)

        self._btn_next = QPushButton('\u25B6')
        self._btn_next.setFixedSize(28, 28)
        self._btn_next.setObjectName('flatBtn')
        self._btn_next.clicked.connect(self._next_page)
        tb.addWidget(self._btn_next)

        tb.addSpacing(16)

        zoom_lbl = QLabel('Zoom:')
        zoom_lbl.setStyleSheet('font-size: 12px;')
        tb.addWidget(zoom_lbl)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(15, 80)
        self._zoom_slider.setValue(35)
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.valueChanged.connect(self._on_zoom)
        tb.addWidget(self._zoom_slider)

        self._zoom_val = QLabel('35%')
        self._zoom_val.setFixedWidth(36)
        self._zoom_val.setStyleSheet('font-size: 12px;')
        tb.addWidget(self._zoom_val)

        tb.addSpacing(16)

        mov_lbl = QLabel('Jump to:')
        mov_lbl.setStyleSheet('font-size: 12px;')
        tb.addWidget(mov_lbl)

        self._mov_combo = QComboBox()
        self._mov_combo.setMinimumWidth(150)
        self._mov_combo.activated.connect(self._on_movement_jump)
        tb.addWidget(self._mov_combo)

        tb.addSpacing(16)

        self._chk_motifs = QCheckBox('Motif families')
        self._chk_motifs.setStyleSheet('font-size: 12px;')
        self._chk_motifs.setChecked(True)
        self._chk_motifs.toggled.connect(self._refresh_overlays)
        tb.addWidget(self._chk_motifs)

        self._chk_crosspart = QCheckBox('Cross-part')
        self._chk_crosspart.setStyleSheet('font-size: 12px;')
        self._chk_crosspart.setChecked(True)
        self._chk_crosspart.toggled.connect(self._refresh_overlays)
        tb.addWidget(self._chk_crosspart)

        self._chk_sections = QCheckBox('Sections')
        self._chk_sections.setStyleSheet('font-size: 12px;')
        self._chk_sections.setChecked(True)
        self._chk_sections.toggled.connect(self._refresh_overlays)
        tb.addWidget(self._chk_sections)

        self._chk_nmf = QCheckBox('NMF peaks')
        self._chk_nmf.setStyleSheet('font-size: 12px;')
        self._chk_nmf.setChecked(True)
        self._chk_nmf.toggled.connect(self._refresh_overlays)
        tb.addWidget(self._chk_nmf)

        tb.addStretch()

        tb_widget = QWidget()
        tb_widget.setLayout(tb)
        tb_widget.setObjectName('toolbar')
        layout.addWidget(tb_widget)

        # -- web view --
        self._web_view = QWebEngineView()

        self._bridge = ScoreBridge()
        self._channel = QWebChannel()
        self._channel.registerObject('bridge', self._bridge)
        self._web_view.page().setWebChannel(self._channel)

        self._bridge.verovio_ready.connect(self._on_verovio_ready)
        self._bridge.score_loaded.connect(self._on_score_loaded)
        self._bridge.page_changed.connect(self._on_page_changed)

        layout.addWidget(self._web_view, stretch=1)

        self._web_view.setHtml(SCORE_HTML, QUrl('https://www.verovio.org/'))

    # ------------------------------------------------------------------ public

    def update_results(self, results: AnalysisResults):
        self._results = results

        self._mov_combo.clear()
        self._mov_combo.addItem('(select movement)')
        for name in results.movement_names:
            self._mov_combo.addItem(name)

        if results.musicxml_data:
            if self._verovio_ready:
                self._load_score(results.musicxml_data)
            else:
                self._pending_musicxml = results.musicxml_data

    def navigate_to_beat(self, beat: float):
        self._web_view.page().runJavaScript(f'goToBeat({beat});')

    def navigate_to_seconds(self, seconds: float):
        if not self._results or not self._results.tempo_marks:
            return
        beats = _seconds_to_beats([seconds], self._results.tempo_marks)
        self.navigate_to_beat(beats[0])

    # --------------------------------------------------------------- internal

    def _load_score(self, musicxml: str):
        encoded = base64.b64encode(musicxml.encode('utf-8')).decode('ascii')
        self._web_view.page().runJavaScript(
            f"loadScoreBase64('{encoded}');")

    def _on_verovio_ready(self):
        self._verovio_ready = True
        if self._pending_musicxml:
            self._load_score(self._pending_musicxml)
            self._pending_musicxml = None

    def _on_score_loaded(self, page_count: int, timemap_json: str):
        self._page_count = page_count
        try:
            self._timemap = json.loads(timemap_json)
        except (json.JSONDecodeError, TypeError):
            self._timemap = []
        self._page_label.setText(f'Page 1 / {page_count}')
        self._refresh_overlays()

    def _on_page_changed(self, current: int, total: int):
        self._current_page = current
        self._page_count = total
        self._page_label.setText(f'Page {current} / {total}')
        self._apply_current_overlays()

    # ------------------------------------------------------------- navigation

    def _prev_page(self):
        if self._current_page > 1:
            self._web_view.page().runJavaScript(
                f'goToPage({self._current_page - 1});')

    def _next_page(self):
        if self._current_page < self._page_count:
            self._web_view.page().runJavaScript(
                f'goToPage({self._current_page + 1});')

    def _on_zoom(self, value: int):
        self._zoom_val.setText(f'{value}%')
        self._web_view.page().runJavaScript(f'setScale({value});')

    def _on_movement_jump(self, index: int):
        if index <= 0 or not self._results:
            return
        mov_idx = index - 1
        offsets = self._results.movement_offsets_beats
        if mov_idx < len(offsets):
            self.navigate_to_beat(offsets[mov_idx])

    # -------------------------------------------------------------- overlays

    def _refresh_overlays(self):
        self._apply_current_overlays()

    def _apply_current_overlays(self):
        if not self._results or not self._timemap:
            return

        for cls in ('hl-motif', 'hl-crosspart', 'hl-section', 'hl-nmf'):
            self._web_view.page().runJavaScript(
                f"clearHighlights('{cls}');")

        if self._chk_motifs.isChecked():
            self._apply_motif_highlights()
        if self._chk_crosspart.isChecked():
            self._apply_crosspart_highlights()
        if self._chk_sections.isChecked():
            self._apply_section_highlights()
        if self._chk_nmf.isChecked():
            self._apply_nmf_highlights()

    def _apply_motif_highlights(self):
        r = self._results
        if not r or not r.motif_pairs or not r.cluster_labels:
            return

        all_secs = []
        for t1, t2 in r.motif_pairs:
            all_secs.extend([t1, t2])
        beats = _seconds_to_beats(all_secs, r.tempo_marks)

        cmds = []
        for i, ((t1, t2), label) in enumerate(
                zip(r.motif_pairs, r.cluster_labels)):
            b1 = beats[i * 2]
            b2 = beats[i * 2 + 1]
            color = TAB10_HEX[label % 10]
            cmds.append(
                f"(function(){{"
                f"var a=findNoteIdsAtBeat({b1},4.0);"
                f"var b=findNoteIdsAtBeat({b2},4.0);"
                f"highlightNotes(a.concat(b),'{color}','hl-motif');"
                f"}})()")
        if cmds:
            self._web_view.page().runJavaScript('\n'.join(cmds))

    def _apply_crosspart_highlights(self):
        r = self._results
        if not r or not r.cross_part_pairs:
            return

        all_secs = []
        for t1, t2 in r.cross_part_pairs:
            all_secs.extend([t1, t2])
        beats = _seconds_to_beats(all_secs, r.tempo_marks)

        cmds = []
        for i in range(len(r.cross_part_pairs)):
            b1 = beats[i * 2]
            b2 = beats[i * 2 + 1]
            cmds.append(
                f"(function(){{"
                f"var a=findNoteIdsAtBeat({b1},4.0);"
                f"var b=findNoteIdsAtBeat({b2},4.0);"
                f"highlightNotes(a,'#FF6D00','hl-crosspart');"
                f"highlightNotes(b,'#AA00FF','hl-crosspart');"
                f"}})()")
        if cmds:
            self._web_view.page().runJavaScript('\n'.join(cmds))

    def _apply_section_highlights(self):
        r = self._results
        if not r or not r.sections:
            return

        section_colors = [
            '#1A73E8', '#34A853', '#FBBC04', '#EA4335', '#9467bd',
            '#8c564b', '#e377c2', '#17becf', '#bcbd22', '#ff7f0e',
        ]

        all_secs = []
        for s in r.sections:
            all_secs.extend([s.get('start_sec', 0), s.get('end_sec', 0)])
        beats = _seconds_to_beats(all_secs, r.tempo_marks)

        cmds = []
        for i, s in enumerate(r.sections):
            b_start = beats[i * 2]
            b_end = beats[i * 2 + 1]
            letter = s.get('letter', 'A')
            label_idx = ord(letter[0]) - ord('A')
            color = section_colors[label_idx % len(section_colors)]
            cmds.append(
                f"(function(){{"
                f"var ids=findNoteIdsInRange({b_start},{b_end});"
                f"highlightNotes(ids,'{color}','hl-section');"
                f"}})()")
        if cmds:
            self._web_view.page().runJavaScript('\n'.join(cmds))

    def _apply_nmf_highlights(self):
        r = self._results
        if not r or not r.nmf_profiles:
            return

        all_peak_secs = []
        peak_comp_indices = []
        for profile in r.nmf_profiles:
            for t in profile.get('top_peaks_sec', [])[:5]:
                all_peak_secs.append(t)
                peak_comp_indices.append(profile['index'])

        if not all_peak_secs:
            return

        beats = _seconds_to_beats(all_peak_secs, r.tempo_marks)

        cmds = []
        for beat, comp_idx in zip(beats, peak_comp_indices):
            color = TAB10_HEX[comp_idx % 10]
            cmds.append(
                f"(function(){{"
                f"var ids=findNoteIdsAtBeat({beat},2.0);"
                f"highlightNotes(ids,'{color}','hl-nmf');"
                f"}})()")
        if cmds:
            self._web_view.page().runJavaScript('\n'.join(cmds))
