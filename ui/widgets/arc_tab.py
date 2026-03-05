"""Arc Plot tab: interactive Plotly plot + motif recurrence table."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QSizePolicy,
    QTabWidget, QPushButton,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from ui.theme import PRIMARY, PRIMARY_LIGHT, TEXT_SECONDARY, TAB10_HEX, SURFACE, BORDER
from ui.utils import load_html_in_webview
from pipeline import AnalysisResults


def _fmt(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f'{m:02d}:{s:02d}'


def _mov_at(t: float, mov_times, mov_names):
    idx = 0
    for i, mt in enumerate(mov_times):
        if t >= mt:
            idx = i
    return mov_names[idx] if idx < len(mov_names) else f'Mov {idx+1}'


class ArcTab(QWidget):

    show_in_score = Signal(float)  # time in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results = None
        self._tmp_html = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self._splitter)

        # Interactive plot area
        self._web_view = QWebEngineView()
        self._web_view.setMinimumHeight(260)
        self._splitter.addWidget(self._web_view)

        # Bottom: table + side panel
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(8, 4, 8, 8)
        bottom_layout.setSpacing(8)

        # Recurrence table
        table_container = QWidget()
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(4)

        table_title = QLabel('Motif Recurrences')
        table_title.setStyleSheet('font-size: 13px; font-weight: 600;')
        tc_layout.addWidget(table_title)

        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            'Time 1', 'Time 2', 'Mov 1', 'Mov 2', 'Family',
            'Interval Pattern', 'Span', ''])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.doubleClicked.connect(self._on_row_double_click)
        tc_layout.addWidget(self._table)
        bottom_layout.addWidget(table_container, stretch=3)

        # Side panel with tabs: Densest Regions + Theme Migrations
        self._side_tabs = QTabWidget()
        self._side_tabs.setFixedWidth(260)

        self._densest_panel = QFrame()
        self._densest_panel.setObjectName('card')
        self._densest_layout = QVBoxLayout(self._densest_panel)
        self._densest_layout.setContentsMargins(12, 12, 12, 12)
        densest_title = QLabel('Densest Regions')
        densest_title.setStyleSheet('font-size: 12px; font-weight: 600;')
        self._densest_layout.addWidget(densest_title)
        self._densest_layout.addStretch()
        self._side_tabs.addTab(self._densest_panel, 'Density')

        self._migration_panel = QFrame()
        self._migration_panel.setObjectName('card')
        self._migration_layout = QVBoxLayout(self._migration_panel)
        self._migration_layout.setContentsMargins(12, 12, 12, 12)
        mig_title = QLabel('Theme Migrations')
        mig_title.setStyleSheet('font-size: 12px; font-weight: 600;')
        self._migration_layout.addWidget(mig_title)
        self._migration_layout.addStretch()
        self._side_tabs.addTab(self._migration_panel, 'Cross-Part')

        bottom_layout.addWidget(self._side_tabs, stretch=0)

        self._splitter.addWidget(bottom)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)

    def update_results(self, r: AnalysisResults):
        self._results = r
        if r.html_arc:
            self._tmp_html = load_html_in_webview(
                self._web_view, r.html_arc, self._tmp_html)

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(r.motif_pairs))
        for row, ((t1, t2), frag, label) in enumerate(
                zip(r.motif_pairs, r.motif_fragments, r.cluster_labels)):
            m1 = _mov_at(t1, r.movement_times_sec, r.movement_names)
            m2 = _mov_at(t2, r.movement_times_sec, r.movement_names)
            span = abs(t2 - t1)
            is_cross = m1 != m2

            items = [
                _fmt(t1), _fmt(t2), m1, m2,
                str(label), str(list(frag[:8])) + ('\u2026' if len(frag) > 8 else ''),
                _fmt(span),
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 4:
                    color = TAB10_HEX[label % 10]
                    item.setForeground(QColor(color))
                    item.setData(Qt.ItemDataRole.UserRole, label)
                if col == 6:
                    item.setData(Qt.ItemDataRole.UserRole, span)
                if is_cross:
                    item.setBackground(QColor(PRIMARY_LIGHT))
                self._table.setItem(row, col, item)

            btn = QPushButton('\U0001F3BC')
            btn.setToolTip('Show in Score')
            btn.setFixedSize(28, 24)
            btn.setStyleSheet('font-size: 13px; border: none; background: transparent;')
            btn.clicked.connect(lambda checked, s=t1: self.show_in_score.emit(s))
            self._table.setCellWidget(row, 7, btn)

        self._table.setSortingEnabled(True)
        self._table.sortByColumn(6, Qt.SortOrder.DescendingOrder)

        # Densest regions
        self._clear_layout(self._densest_layout, keep=1)
        if r.arc_report:
            in_densest = False
            for line in r.arc_report.split('\n'):
                if 'DENSEST ARC REGIONS' in line:
                    in_densest = True
                    continue
                if in_densest and line.strip().startswith('='):
                    continue
                if in_densest and line.strip():
                    lbl = QLabel(line.strip())
                    lbl.setStyleSheet('font-size: 11px; padding: 2px 0;')
                    lbl.setWordWrap(True)
                    self._densest_layout.addWidget(lbl)
                elif in_densest and not line.strip():
                    break
        self._densest_layout.addStretch()

        # Theme migrations (cross-part)
        self._clear_layout(self._migration_layout, keep=1)
        if r.cross_part_pairs:
            from collections import Counter
            pair_counts = Counter()
            for detail in r.cross_part_details:
                key = f'{detail["part_a"]} \u2192 {detail["part_b"]}'
                pair_counts[key] += 1
            for key, cnt in pair_counts.most_common(10):
                lbl = QLabel(f'{key}: {cnt} matches')
                lbl.setStyleSheet('font-size: 11px; padding: 2px 0;')
                lbl.setWordWrap(True)
                self._migration_layout.addWidget(lbl)
            total = QLabel(f'\nTotal: {len(r.cross_part_pairs)} cross-part matches')
            total.setStyleSheet(f'font-size: 11px; font-weight: 600; color: {PRIMARY};')
            self._migration_layout.addWidget(total)
        else:
            lbl = QLabel('No cross-part motifs detected.')
            lbl.setStyleSheet(f'font-size: 11px; color: {TEXT_SECONDARY};')
            self._migration_layout.addWidget(lbl)
        self._migration_layout.addStretch()

    def _on_row_double_click(self, index):
        row = index.row()
        if self._results and row < len(self._results.motif_pairs):
            t1, _ = self._results.motif_pairs[row]
            self.show_in_score.emit(t1)

    @staticmethod
    def _clear_layout(layout, keep=1):
        while layout.count() > keep:
            item = layout.takeAt(keep)
            if item.widget():
                item.widget().deleteLater()
