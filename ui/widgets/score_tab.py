"""Interactive score visualization tab using Verovio WebAssembly."""

import json
import base64
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, Slot, QObject, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QCheckBox, QFrame, QScrollArea,
)
from PySide6.QtWebEngineCore import QWebEnginePage
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
#score-container { padding:10px 20px; min-height:200px; overflow-x:auto; }
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
#tooltip {
    position: fixed; display: none; z-index: 9999;
    max-width: 320px; padding: 8px 12px;
    background: rgba(32, 33, 36, 0.95); color: #fff;
    font-size: 12px; line-height: 1.4;
    border-radius: 6px; pointer-events: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
#click-overlay {
    position: fixed; display: none; z-index: 9998;
    bottom: 16px; left: 50%; transform: translateX(-50%);
    max-width: 400px; padding: 10px 14px;
    background: rgba(32, 33, 36, 0.95); color: #fff;
    font-size: 12px; line-height: 1.4;
    border-radius: 6px; pointer-events: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.hl-motif-bg { stroke-width: 1.2; }
.hl-motif-bg.hl-emphasized, .hl-crosspart-bg.hl-emphasized,
.hl-section-bg.hl-emphasized, .hl-nmf-bg.hl-emphasized {
    opacity: 0.7;
}
.hl-crosspart-bg { stroke-dasharray: 5 3; }
.hl-section-bg { stroke-dasharray: 10 5; }
.hl-nmf-bg { stroke-dasharray: 2 2; }
</style>
</head>
<body>
<div id="loading"><div class="spinner"></div><br>Loading Verovio engraver&hellip;</div>
<div id="score-container"></div>
<div id="tooltip"></div>
<div id="click-overlay"></div>

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
var overlayData = {motifs:[], crosspart:[], sections:[], nmf:[]};

var tooltipEl = null;
function initTooltip() {
    if (!tooltipEl) tooltipEl = document.getElementById('tooltip');
    return tooltipEl;
}
function showTooltip(text, clientX, clientY) {
    var el = initTooltip();
    if (!el) return;
    el.textContent = text;
    el.style.display = 'block';
    moveTooltip(clientX, clientY);
}
function hideTooltip() {
    var el = initTooltip();
    if (el) el.style.display = 'none';
}
function moveTooltip(clientX, clientY) {
    var el = initTooltip();
    if (!el || el.style.display !== 'block') return;
    var offset = 14;
    var x = clientX + offset;
    var y = clientY + offset;
    var r = el.getBoundingClientRect();
    if (x + r.width > window.innerWidth) x = clientX - r.width - offset;
    if (y + r.height > window.innerHeight) y = clientY - r.height - offset;
    if (x < 0) x = offset;
    if (y < 0) y = offset;
    el.style.left = x + 'px';
    el.style.top = y + 'px';
}

var clickOverlayEl = null;
function initClickOverlay() {
    if (!clickOverlayEl) clickOverlayEl = document.getElementById('click-overlay');
    return clickOverlayEl;
}
function showClickOverlay(text) {
    var el = initClickOverlay();
    if (!el) return;
    el.textContent = text || '';
    el.style.display = 'block';
}
function hideClickOverlay() {
    var el = initClickOverlay();
    if (el) el.style.display = 'none';
}

var overlayDataKey = { motif: 'motifs', crosspart: 'crosspart', section: 'sections', nmf: 'nmf' };
function onOverlayRectClick(ev) {
    ev.preventDefault();
    ev.stopPropagation();
    var rect = ev.currentTarget;
    var type = rect.getAttribute('data-overlay-type');
    var index = rect.getAttribute('data-overlay-index');
    if (type == null || index == null) return;
    var idx = parseInt(index, 10);
    if (isNaN(idx)) return;
    var allBg = document.querySelectorAll('.hl-motif-bg, .hl-crosspart-bg, .hl-section-bg, .hl-nmf-bg');
    for (var i = 0; i < allBg.length; i++) allBg[i].classList.remove('hl-emphasized');
    var same = document.querySelectorAll('[data-overlay-type="' + type + '"][data-overlay-index="' + index + '"]');
    for (var j = 0; j < same.length; j++) same[j].classList.add('hl-emphasized');
    var label = '';
    var dataKey = overlayDataKey[type] || type;
    var arr = overlayData[dataKey];
    if (arr && arr[idx] && arr[idx].label != null)
        label = arr[idx].label;
    showClickOverlay(label);
    if (type === 'motif' && bridge) bridge.onMotifOverlayClicked(idx);
}

new QWebChannel(qt.webChannelTransport, function(channel) {
    bridge = channel.objects.bridge;
    console.log('[score] QWebChannel bridge established:', !!bridge);
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
        pageWidth:  Math.round(pw * 250 / scale),
        pageHeight: 30000,
        scale: scale,
        adjustPageHeight: false,
        breaks: 'auto',
        condense: 'none',
        spacingStaff: 4,
        spacingSystem: 4,
        spacingLinear: 0.15,
        spacingNonLinear: 0.4
    });
    vrvToolkit.loadData(musicXmlData);
    pageCount = vrvToolkit.getPageCount();

    try {
        var tmResult = vrvToolkit.renderToTimemap();
        timemap = (typeof tmResult === 'string') ? JSON.parse(tmResult) : tmResult;
    } catch(e) { console.warn('[score] renderToTimemap failed:', e); timemap = []; }

    console.log('[score] renderScore: pages=' + pageCount +
                ', timemap entries=' + timemap.length +
                ', first entry:', timemap.length > 0 ? JSON.stringify(timemap[0]) : 'N/A');

    renderPage(1);
    if (bridge) bridge.onScoreLoaded(pageCount, JSON.stringify(timemap));
}

function renderPage(n) {
    if (n < 1 || n > pageCount) return;
    currentPage = n;
    var svg = vrvToolkit.renderToSVG(n);
    document.getElementById('score-container').innerHTML = svg;
    applyStoredOverlays();
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

function highlightNotes(noteIds, color, className, label, motifIndex, overlayType, overlayIndex) {
    var found = 0;
    var tipText = (label != null && label !== '') ? String(label) : null;
    var oType = overlayType;
    var oIndex = overlayIndex;
    if (motifIndex !== undefined && motifIndex !== null && motifIndex >= 0) {
        oType = 'motif';
        oIndex = motifIndex;
    }
    var hasOverlayId = (oType != null && oType !== '' && oIndex !== undefined && oIndex !== null);
    for (var i = 0; i < noteIds.length; i++) {
        var el = document.getElementById(noteIds[i]);
        if (!el) continue;
        found++;
        el.classList.add(className);
        try {
            var bbox = el.getBBox();
            var rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', bbox.x - 2);
            rect.setAttribute('y', bbox.y - 2);
            rect.setAttribute('width', bbox.width + 4);
            rect.setAttribute('height', bbox.height + 4);
            rect.setAttribute('fill', color);
            rect.setAttribute('stroke', color);
            rect.setAttribute('stroke-width', '1.2');
            rect.setAttribute('opacity', '0.35');
            rect.setAttribute('rx', '3');
            rect.classList.add(className + '-bg');
            if (oType === 'motif') rect.setAttribute('data-motif-index', oIndex);
            if (hasOverlayId) {
                rect.setAttribute('data-overlay-type', oType);
                rect.setAttribute('data-overlay-index', String(oIndex));
                rect.style.cursor = 'pointer';
                rect.addEventListener('click', onOverlayRectClick);
            }
            if (tipText) {
                rect.addEventListener('mouseenter', function(e) {
                    showTooltip(tipText, e.clientX, e.clientY);
                });
                rect.addEventListener('mousemove', function(e) {
                    moveTooltip(e.clientX, e.clientY);
                });
                rect.addEventListener('mouseleave', function() { hideTooltip(); });
            }
            el.parentNode.insertBefore(rect, el);
        } catch(e) {}
    }
    return found;
}

function clearHighlights(className) {
    var els = document.querySelectorAll('.' + className);
    for (var i = 0; i < els.length; i++) els[i].classList.remove(className);
    var bgs = document.querySelectorAll('.' + className + '-bg');
    for (var i = bgs.length - 1; i >= 0; i--) bgs[i].remove();
}

/* ---- Page-aware overlay system ---- */

function setOverlayData(data) {
    overlayData = data || {motifs:[], crosspart:[], sections:[], nmf:[]};
    applyStoredOverlays();
}

function applyStoredOverlays() {
    clearHighlights('hl-motif');
    clearHighlights('hl-crosspart');
    clearHighlights('hl-section');
    clearHighlights('hl-nmf');

    var noteEls = document.querySelectorAll('.note[id]');
    var visibleSet = {};
    for (var i = 0; i < noteEls.length; i++) visibleSet[noteEls[i].id] = true;
    var visibleCount = Object.keys(visibleSet).length;

    if (visibleCount === 0 || timemap.length === 0) {
        console.log('[score] applyStoredOverlays: skip (visibleNotes=' +
                    visibleCount + ', timemap=' + timemap.length + ')');
        return;
    }

    var beatEntries = [];
    for (var i = 0; i < timemap.length; i++) {
        var entry = timemap[i];
        if (!entry.on) continue;
        var vis = [];
        for (var j = 0; j < entry.on.length; j++) {
            if (visibleSet[entry.on[j]]) vis.push(entry.on[j]);
        }
        if (vis.length > 0) {
            beatEntries.push({qs: _qs(entry), ids: vis});
        }
    }

    function idsNearBeat(beat, tol) {
        var result = [];
        for (var k = 0; k < beatEntries.length; k++) {
            if (Math.abs(beatEntries[k].qs - beat) <= tol) {
                result = result.concat(beatEntries[k].ids);
            }
        }
        return result;
    }

    function idsInRange(bStart, bEnd) {
        var result = [];
        for (var k = 0; k < beatEntries.length; k++) {
            if (beatEntries[k].qs >= bStart && beatEntries[k].qs <= bEnd) {
                result = result.concat(beatEntries[k].ids);
            }
        }
        return result;
    }

    var d = overlayData;
    var totalFound = 0;

    if (d.motifs) {
        for (var i = 0; i < d.motifs.length; i++) {
            var m = d.motifs[i];
            var ab = idsNearBeat(m.b1, 4.0).concat(idsNearBeat(m.b2, 4.0));
            if (ab.length) totalFound += highlightNotes(ab, m.color, 'hl-motif', m.label || '', i);
        }
    }

    if (d.crosspart) {
        for (var i = 0; i < d.crosspart.length; i++) {
            var cp = d.crosspart[i];
            var a = idsNearBeat(cp.b1, 4.0);
            var b = idsNearBeat(cp.b2, 4.0);
            var lbl = cp.label || '';
            if (a.length) totalFound += highlightNotes(a, '#FF6D00', 'hl-crosspart', lbl, -1, 'crosspart', i);
            if (b.length) totalFound += highlightNotes(b, '#AA00FF', 'hl-crosspart', lbl, -1, 'crosspart', i);
        }
    }

    if (d.sections) {
        for (var i = 0; i < d.sections.length; i++) {
            var sec = d.sections[i];
            var ids = idsInRange(sec.b1, sec.b2);
            if (ids.length) totalFound += highlightNotes(ids, sec.color, 'hl-section', sec.label || '', -1, 'section', i);
        }
    }

    if (d.nmf) {
        for (var i = 0; i < d.nmf.length; i++) {
            var nm = d.nmf[i];
            var ids = idsNearBeat(nm.beat, 2.0);
            if (ids.length) totalFound += highlightNotes(ids, nm.color, 'hl-nmf', nm.label || '', -1, 'nmf', i);
        }
    }

    console.log('[score] applyStoredOverlays: page=' + currentPage +
                ', visibleNotes=' + visibleCount +
                ', beatEntries=' + beatEntries.length +
                ', totalHighlighted=' + totalFound +
                ', motifs=' + (d.motifs ? d.motifs.length : 0) +
                ', crosspart=' + (d.crosspart ? d.crosspart.length : 0) +
                ', sections=' + (d.sections ? d.sections.length : 0) +
                ', nmf=' + (d.nmf ? d.nmf.length : 0));
}

function getTimemapRange() {
    if (timemap.length === 0)
        return JSON.stringify({count:0, min:0, max:0, hasQstamp:false, hasOn:false});
    var min = Infinity, max = -Infinity, onCount = 0;
    for (var i = 0; i < timemap.length; i++) {
        var q = _qs(timemap[i]);
        if (q < min) min = q;
        if (q > max) max = q;
        if (timemap[i].on) onCount++;
    }
    return JSON.stringify({
        count: timemap.length, min: min, max: max,
        onCount: onCount,
        hasQstamp: timemap[0].qstamp !== undefined,
        hasTstamp: timemap[0].tstamp !== undefined,
        sampleKeys: Object.keys(timemap[0]).join(',')
    });
}

/* ---- Navigation ---- */

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
        var qs = _qs(entry);
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


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f'{m}:{s:02d}'


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


class DebugWebPage(QWebEnginePage):
    """Routes JavaScript console output to Python stdout for diagnostics."""

    _LEVELS = {
        QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: 'INFO',
        QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: 'WARN',
        QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: 'ERROR',
    }

    def javaScriptConsoleMessage(self, level, message, line, source_id):
        tag = self._LEVELS.get(level, 'LOG')
        print(f'[ScoreJS {tag}] {message}')


class ScoreBridge(QObject):
    """Python-side receiver for callbacks from the Verovio JavaScript."""

    verovio_ready = Signal()
    score_loaded = Signal(int, str)
    page_changed = Signal(int, int)
    motif_overlay_clicked = Signal(int)

    @Slot()
    def onVerovioReady(self):
        self.verovio_ready.emit()

    @Slot(int, str)
    def onScoreLoaded(self, page_count: int, timemap_json: str):
        self.score_loaded.emit(page_count, timemap_json)

    @Slot(int, int)
    def onPageChanged(self, current: int, total: int):
        self.page_changed.emit(current, total)

    @Slot(int)
    def onMotifOverlayClicked(self, motif_index: int):
        self.motif_overlay_clicked.emit(motif_index)


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
        self._selected_recurrence_index: Optional[int] = None

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

        tb.addSpacing(12)
        legend_lbl = QLabel('Border: solid=Motifs  — — =Sections  - - =Cross-part  ···=NMF')
        legend_lbl.setStyleSheet('font-size: 10px; color: #5F6368;')
        legend_lbl.setToolTip('Highlight border style identifies overlay type at a glance.')
        tb.addWidget(legend_lbl)

        tb.addStretch()

        tb_widget = QWidget()
        tb_widget.setLayout(tb)
        tb_widget.setObjectName('toolbar')
        layout.addWidget(tb_widget)

        # -- recurrence context card (shown when a motif recurrence is selected) --
        self._context_card = QFrame()
        self._context_card.setObjectName('card')
        self._context_card.setVisible(False)
        card_layout = QVBoxLayout(self._context_card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        self._context_card_title = QLabel('Recurrence context')
        self._context_card_title.setStyleSheet('font-size: 12px; font-weight: 600;')
        card_layout.addWidget(self._context_card_title)
        self._context_card_scroll = QScrollArea()
        self._context_card_scroll.setWidgetResizable(True)
        self._context_card_scroll.setMaximumHeight(120)
        self._context_card_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._context_card_inner = QWidget()
        self._context_card_inner_layout = QVBoxLayout(self._context_card_inner)
        self._context_card_inner_layout.setContentsMargins(0, 0, 0, 0)
        self._context_card_scroll.setWidget(self._context_card_inner)
        card_layout.addWidget(self._context_card_scroll)
        layout.addWidget(self._context_card)

        # -- web view with debug page --
        self._debug_page = DebugWebPage()
        self._web_view = QWebEngineView()
        self._web_view.setPage(self._debug_page)

        self._bridge = ScoreBridge()
        self._channel = QWebChannel()
        self._channel.registerObject('bridge', self._bridge)
        self._debug_page.setWebChannel(self._channel)

        self._bridge.verovio_ready.connect(self._on_verovio_ready)
        self._bridge.score_loaded.connect(self._on_score_loaded)
        self._bridge.page_changed.connect(self._on_page_changed)
        self._bridge.motif_overlay_clicked.connect(self._on_motif_overlay_clicked)

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
        self._debug_page.runJavaScript(f'goToBeat({beat});')

    def navigate_to_seconds(self, seconds: float):
        if not self._results or not self._results.tempo_marks:
            return
        beats = _seconds_to_beats([seconds], self._results.tempo_marks)
        self.navigate_to_beat(beats[0])

    def set_selected_recurrence(self, index: Optional[int]):
        """Show the recurrence context card for the given motif index, or hide if None."""
        self._selected_recurrence_index = index
        if index is None or not self._results:
            self._context_card.setVisible(False)
            return
        contexts = getattr(self._results, 'motif_contexts', []) or []
        if index >= len(contexts):
            self._context_card.setVisible(False)
            return
        self._populate_context_card(contexts[index])
        self._context_card.setVisible(True)

    # --------------------------------------------------------------- internal

    def _load_score(self, musicxml: str):
        encoded = base64.b64encode(musicxml.encode('utf-8')).decode('ascii')
        self._debug_page.runJavaScript(
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

        print(f'[ScoreTab] Score loaded: pages={page_count}, '
              f'timemap_entries={len(self._timemap)}')

        if self._timemap:
            sample = self._timemap[0]
            keys = list(sample.keys())
            print(f'[ScoreTab] Timemap sample keys: {keys}')
            qs_vals = [e.get('qstamp', e.get('tstamp', None))
                       for e in self._timemap[:5]]
            print(f'[ScoreTab] First 5 qstamp values: {qs_vals}')

        self._debug_page.runJavaScript(
            'getTimemapRange();',
            lambda r: print(f'[ScoreTab] JS timemap range: {r}'))

        self._page_label.setText(f'Page 1 / {page_count}')
        self._send_overlay_data()

    def _on_page_changed(self, current: int, total: int):
        self._current_page = current
        self._page_count = total
        self._page_label.setText(f'Page {current} / {total}')

    # ------------------------------------------------------------- navigation

    def _prev_page(self):
        if self._current_page > 1:
            self._debug_page.runJavaScript(
                f'goToPage({self._current_page - 1});')

    def _next_page(self):
        if self._current_page < self._page_count:
            self._debug_page.runJavaScript(
                f'goToPage({self._current_page + 1});')

    def _on_zoom(self, value: int):
        self._zoom_val.setText(f'{value}%')
        self._debug_page.runJavaScript(f'setScale({value});')

    def _on_movement_jump(self, index: int):
        if index <= 0 or not self._results:
            return
        mov_idx = index - 1
        offsets = self._results.movement_offsets_beats
        if mov_idx < len(offsets):
            self.navigate_to_beat(offsets[mov_idx])

    def _on_motif_overlay_clicked(self, motif_index: int):
        self.set_selected_recurrence(motif_index)
        if self._results and motif_index < len(getattr(self._results, 'motif_contexts', [])):
            ctx = self._results.motif_contexts[motif_index]
            self.navigate_to_seconds(ctx['t1'])

    def _clear_context_card_inner(self):
        while self._context_card_inner_layout.count():
            item = self._context_card_inner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_context_card(self, ctx: dict):
        self._clear_context_card_inner()
        def line(lbl: str, val: str) -> QLabel:
            w = QLabel(f'{lbl}: {val}')
            w.setStyleSheet('font-size: 11px; padding: 1px 0;')
            w.setWordWrap(True)
            return w
        la = QLabel(f"Side A ({_fmt_time(ctx['t1'])})")
        la.setStyleSheet('font-size: 11px; font-weight: 600; margin-top: 4px;')
        self._context_card_inner_layout.addWidget(la)
        self._context_card_inner_layout.addWidget(
            line('Section', ctx.get('section_a', '—')))
        self._context_card_inner_layout.addWidget(
            line('Texture', ', '.join(ctx.get('texture_a', [])) or '—'))
        self._context_card_inner_layout.addWidget(
            line('Parts', (ctx.get('summary_a', '') + ': ' + ', '.join(ctx.get('parts_a', []))) if ctx.get('parts_a') else '—'))
        lb = QLabel(f"Side B ({_fmt_time(ctx['t2'])})")
        lb.setStyleSheet('font-size: 11px; font-weight: 600; margin-top: 8px;')
        self._context_card_inner_layout.addWidget(lb)
        self._context_card_inner_layout.addWidget(
            line('Section', ctx.get('section_b', '—')))
        self._context_card_inner_layout.addWidget(
            line('Texture', ', '.join(ctx.get('texture_b', [])) or '—'))
        self._context_card_inner_layout.addWidget(
            line('Parts', (ctx.get('summary_b', '') + ': ' + ', '.join(ctx.get('parts_b', []))) if ctx.get('parts_b') else '—'))

    # -------------------------------------------------------------- overlays

    def _refresh_overlays(self):
        self._send_overlay_data()

    def _send_overlay_data(self):
        """Build all overlay data as JSON and send to JS in one call."""
        if not self._results or not self._timemap:
            print(f'[ScoreTab] _send_overlay_data: skipped '
                  f'(results={self._results is not None}, '
                  f'timemap={len(self._timemap)})')
            return

        data = {'motifs': [], 'crosspart': [], 'sections': [], 'nmf': []}
        r = self._results

        if self._chk_motifs.isChecked() and r.motif_pairs and r.cluster_labels:
            all_secs = []
            for t1, t2 in r.motif_pairs:
                all_secs.extend([t1, t2])
            beats = _seconds_to_beats(all_secs, r.tempo_marks)
            frags = getattr(r, 'motif_fragments', []) or []
            for i, label in enumerate(r.cluster_labels):
                if i >= len(r.motif_pairs):
                    break
                t1, t2 = r.motif_pairs[i]
                frag_str = ' '.join(str(x) for x in frags[i]) if i < len(frags) else '—'
                data['motifs'].append({
                    'b1': beats[i * 2], 'b2': beats[i * 2 + 1],
                    'color': TAB10_HEX[label % 10],
                    'label': f'Motif Family {label} | {_fmt_time(t1)} → {_fmt_time(t2)} | Pattern: {frag_str}'
                })
            if data['motifs']:
                sample_beats = [data['motifs'][0]['b1'],
                                data['motifs'][0]['b2']]
                print(f'[ScoreTab] Motif overlay: {len(data["motifs"])} pairs, '
                      f'sample beats: {sample_beats}')

        if self._chk_crosspart.isChecked() and r.cross_part_pairs:
            all_secs = []
            for t1, t2 in r.cross_part_pairs:
                all_secs.extend([t1, t2])
            beats = _seconds_to_beats(all_secs, r.tempo_marks)
            details = getattr(r, 'cross_part_details', []) or []
            for i in range(len(r.cross_part_pairs)):
                d = details[i] if i < len(details) else {}
                part_a = d.get('part_a', 'A')
                part_b = d.get('part_b', 'B')
                dist = d.get('distance', 0)
                win = d.get('window', 0)
                data['crosspart'].append({
                    'b1': beats[i * 2], 'b2': beats[i * 2 + 1],
                    'label': f'{part_a} → {part_b} | Distance: {dist:.2f} | Window: {win}'
                })

        section_colors = [
            '#1A73E8', '#34A853', '#FBBC04', '#EA4335', '#9467bd',
            '#8c564b', '#e377c2', '#17becf', '#bcbd22', '#ff7f0e',
        ]
        if self._chk_sections.isChecked() and r.sections:
            all_secs = []
            for s in r.sections:
                all_secs.extend([s.get('start_sec', 0), s.get('end_sec', 0)])
            beats = _seconds_to_beats(all_secs, r.tempo_marks)
            for i, s in enumerate(r.sections):
                letter = s.get('letter', 'A')
                start_sec = s.get('start_sec', 0)
                end_sec = s.get('end_sec', 0)
                label_idx = ord(letter[0]) - ord('A')
                data['sections'].append({
                    'b1': beats[i * 2], 'b2': beats[i * 2 + 1],
                    'color': section_colors[label_idx % len(section_colors)],
                    'label': f'Section {letter} | {_fmt_time(start_sec)} – {_fmt_time(end_sec)}'
                })
            if data['sections']:
                print(f'[ScoreTab] Section overlay: {len(data["sections"])} '
                      f'sections, first range: '
                      f'{data["sections"][0]["b1"]:.1f}-'
                      f'{data["sections"][0]["b2"]:.1f}')

        if self._chk_nmf.isChecked() and r.nmf_profiles:
            all_peak_secs = []
            peak_comp_indices = []
            peak_profiles = []
            for profile in r.nmf_profiles:
                for t in profile.get('top_peaks_sec', [])[:5]:
                    all_peak_secs.append(t)
                    peak_comp_indices.append(profile['index'])
                    peak_profiles.append(profile)
            if all_peak_secs:
                beats = _seconds_to_beats(all_peak_secs, r.tempo_marks)
                comp_labels = getattr(r, 'comp_labels', None) or {}
                for beat, comp_idx, profile, t_sec in zip(beats, peak_comp_indices, peak_profiles, all_peak_secs):
                    comp_label = comp_labels.get(comp_idx) or profile.get('label') or profile.get('band') or f'C{comp_idx}'
                    data['nmf'].append({
                        'beat': beat,
                        'color': TAB10_HEX[comp_idx % 10],
                        'label': f'NMF Component {comp_idx} ({comp_label}) | Peak at {_fmt_time(t_sec)}'
                    })

        total = (len(data['motifs']) + len(data['crosspart'])
                 + len(data['sections']) + len(data['nmf']))
        print(f'[ScoreTab] Sending overlay data: '
              f'motifs={len(data["motifs"])}, '
              f'crosspart={len(data["crosspart"])}, '
              f'sections={len(data["sections"])}, '
              f'nmf={len(data["nmf"])}, total_items={total}')

        json_str = json.dumps(data)
        self._debug_page.runJavaScript(f'setOverlayData({json_str});')
