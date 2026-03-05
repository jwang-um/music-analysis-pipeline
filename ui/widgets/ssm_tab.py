"""SSM tab: interactive Plotly SSM heatmap + form chart table + cross-section similarity."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QSizePolicy,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from ui.theme import PRIMARY, TEXT_SECONDARY, TAB10_HEX, SURFACE, BORDER
from ui.utils import load_html_in_webview
from pipeline import AnalysisResults

_LETTER_COLORS = {}


def _letter_color(letter: str) -> str:
    base = letter.rstrip('0123456789')
    if base not in _LETTER_COLORS:
        idx = len(_LETTER_COLORS)
        _LETTER_COLORS[base] = TAB10_HEX[idx % len(TAB10_HEX)]
    return _LETTER_COLORS[base]


def _fmt(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f'{m:02d}:{s:02d}'


class SsmTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tmp_html = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self._splitter)

        # Top row: interactive plot + form chart
        top = QSplitter(Qt.Orientation.Horizontal)

        self._web_view = QWebEngineView()
        self._web_view.setMinimumSize(400, 400)
        top.addWidget(self._web_view)

        # Form chart table
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(4, 8, 8, 4)
        chart_layout.setSpacing(4)

        chart_title = QLabel('Structural Form Chart')
        chart_title.setStyleSheet('font-size: 13px; font-weight: 600;')
        chart_layout.addWidget(chart_title)

        self._chart_table = QTableWidget()
        self._chart_table.setColumnCount(6)
        self._chart_table.setHorizontalHeaderLabels([
            '#', 'Section', 'Start', 'End', 'Duration', 'Movement'])
        self._chart_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self._chart_table.horizontalHeader().setStretchLastSection(True)
        self._chart_table.setAlternatingRowColors(True)
        self._chart_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._chart_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        chart_layout.addWidget(self._chart_table)

        top.addWidget(chart_container)
        top.setStretchFactor(0, 1)
        top.setStretchFactor(1, 1)
        self._splitter.addWidget(top)

        # Bottom: cross-section similarities
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(8, 4, 8, 8)
        bottom_layout.setSpacing(8)

        sim_title = QLabel('Top Cross-Section Similarities')
        sim_title.setStyleSheet('font-size: 13px; font-weight: 600;')
        bottom_layout.addWidget(sim_title)

        self._sim_row = QHBoxLayout()
        self._sim_row.setSpacing(12)
        bottom_layout.addLayout(self._sim_row)
        bottom_layout.addStretch()

        self._splitter.addWidget(bottom)
        self._splitter.setStretchFactor(0, 4)
        self._splitter.setStretchFactor(1, 1)

    def update_results(self, r: AnalysisResults):
        _LETTER_COLORS.clear()

        if r.html_ssm:
            self._tmp_html = load_html_in_webview(
                self._web_view, r.html_ssm, self._tmp_html)

        # Populate form chart
        self._chart_table.setRowCount(len(r.sections))
        for row, s in enumerate(r.sections):
            items_data = [
                str(s['index']),
                s['letter'],
                _fmt(s['start_sec']),
                _fmt(s['end_sec']),
                _fmt(s['duration_sec']),
                s['movement'],
            ]
            for col, text in enumerate(items_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 1:
                    item.setForeground(QColor(_letter_color(s['letter'])))
                self._chart_table.setItem(row, col, item)

        # Cross-section similarity cards
        while self._sim_row.count():
            item = self._sim_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for a, b, sim in r.cross_sim[:5]:
            card = self._sim_card(a, b, sim)
            self._sim_row.addWidget(card)
        self._sim_row.addStretch()

    def _sim_card(self, section_a: str, section_b: str, similarity: float) -> QFrame:
        card = QFrame()
        card.setObjectName('card')
        card.setFixedSize(180, 80)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        pair_lbl = QLabel(f'{section_a}  \u2194  {section_b}')
        pair_lbl.setStyleSheet(f'font-size: 14px; font-weight: 600; color: {PRIMARY};')
        pair_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pair_lbl)

        sim_lbl = QLabel(f'Similarity: {similarity:.4f}')
        sim_lbl.setStyleSheet(f'font-size: 11px; color: {TEXT_SECONDARY};')
        sim_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sim_lbl)

        bar = QFrame()
        bar.setFixedHeight(4)
        pct = max(0, min(100, int(similarity * 100)))
        bar.setStyleSheet(
            f'background: qlineargradient(x1:0,y1:0,x2:1,y2:0,'
            f'stop:0 {PRIMARY}, stop:{pct/100} {PRIMARY}, '
            f'stop:{pct/100 + 0.01} {BORDER}, stop:1 {BORDER});'
            f'border-radius: 2px;')
        layout.addWidget(bar)

        return card
