"""Validation tab: traffic-light metrics, boundary table, NMF consistency."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QSizePolicy, QGridLayout,
)
from ui.theme import PRIMARY, TEXT_SECONDARY, SURFACE, BORDER, SUCCESS, WARNING, ERROR
from pipeline import AnalysisResults


def _fmt(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f'{m:02d}:{s:02d}'


def _traffic_light(value: float, thresholds: tuple) -> tuple:
    """Return (color, label) for a traffic-light indicator.
    thresholds = (good_below, warn_below) — lower is better."""
    good, warn = thresholds
    if value <= good:
        return SUCCESS, 'Good'
    elif value <= warn:
        return WARNING, 'Fair'
    else:
        return ERROR, 'Poor'


def _traffic_light_high(value: float, thresholds: tuple) -> tuple:
    """Higher is better variant."""
    good, warn = thresholds
    if value >= good:
        return SUCCESS, 'Good'
    elif value >= warn:
        return WARNING, 'Fair'
    else:
        return ERROR, 'Poor'


class TrafficCircle(QFrame):
    """Large colored circle with a value and label."""

    def __init__(self, color: str, value_text: str, label_text: str, parent=None):
        super().__init__(parent)
        self.setObjectName('card')
        self.setFixedSize(200, 140)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        circle = QLabel('●')
        circle.setStyleSheet(f'font-size: 48px; color: {color};')
        circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(circle)

        val = QLabel(value_text)
        val.setStyleSheet('font-size: 18px; font-weight: 700;')
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(val)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(f'font-size: 11px; color: {TEXT_SECONDARY};')
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)


class ValidationTab(QScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._inner = QWidget()
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)

        placeholder = QLabel('Run an analysis to see validation results.')
        placeholder.setStyleSheet(f'color: {TEXT_SECONDARY}; font-size: 14px;')
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(placeholder)
        self._layout.addStretch()

        self.setWidget(self._inner)

    def update_results(self, r: AnalysisResults):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # ---- Traffic light summary row ----
        lights_row = QHBoxLayout()
        lights_row.setSpacing(16)

        if r.seg_validation:
            hr = r.seg_validation.get('hit_rate', 0)
            color, _ = _traffic_light_high(hr, (0.9, 0.5))
            lights_row.addWidget(TrafficCircle(
                color, f'{hr:.0%}', 'Movement Boundary\nDetection'))

        if r.nmf_validation:
            mc = r.nmf_validation.get('max_off_diagonal_corr', 0)
            color, _ = _traffic_light(mc, (0.5, 0.7))
            lights_row.addWidget(TrafficCircle(
                color, f'{mc:.3f}', 'Max Component\nCorrelation'))

        if r.cross_validation:
            import numpy as np
            med = np.median([x['nmf_shift'] for x in r.cross_validation])
            color, _ = _traffic_light_high(med, (30, 10))
            lights_row.addWidget(TrafficCircle(
                color, f'{med:.1f}', 'Median NMF Shift\nat Boundaries'))

        lights_row.addStretch()
        lights_widget = QWidget()
        lights_widget.setLayout(lights_row)
        self._layout.addWidget(lights_widget)

        # ---- Segmentation boundary details ----
        if r.seg_validation:
            self._add_section_title('Segmentation Boundary Details')
            details = r.seg_validation.get('details', [])
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(['Known Frame', 'Nearest Found', 'Delta', 'Result'])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setMaximumHeight(max(120, len(details) * 30 + 40))
            table.setRowCount(len(details))

            for row, d in enumerate(details):
                items = [
                    str(d.get('known_frame', '')),
                    str(d.get('nearest_found', 'N/A')),
                    str(d.get('delta', 'N/A')),
                    'HIT' if d.get('hit') else 'MISS',
                ]
                for col, text in enumerate(items):
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if col == 3:
                        item.setForeground(
                            QColor(SUCCESS) if d.get('hit') else QColor(ERROR))
                    table.setItem(row, col, item)

            self._layout.addWidget(table)

        # ---- NMF sparsity / ANOVA ----
        if r.nmf_validation:
            self._add_section_title('NMF Component Consistency')

            sparsity = r.nmf_validation.get('sparsity_per_component', [])
            anova = r.nmf_validation.get('anova_f_per_component', [])

            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(['Component', 'Sparsity', 'ANOVA F', 'Assessment'])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setMaximumHeight(max(120, len(sparsity) * 30 + 40))
            table.setRowCount(len(sparsity))

            for row in range(len(sparsity)):
                sp = sparsity[row]
                f_val = anova[row] if row < len(anova) else 0.0
                if sp < 0.8 and f_val > 50:
                    assessment = 'Strong'
                    badge_color = SUCCESS
                elif sp < 0.9:
                    assessment = 'Moderate'
                    badge_color = WARNING
                elif f_val > 50:
                    assessment = 'Moderate'
                    badge_color = WARNING
                else:
                    assessment = 'Weak'
                    badge_color = ERROR

                for col, text in enumerate([
                    str(row), f'{sp:.1%}', f'{f_val:.1f}', assessment
                ]):
                    item = QTableWidgetItem(text)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if col == 3:
                        item.setForeground(QColor(badge_color))
                    table.setItem(row, col, item)

            self._layout.addWidget(table)

        # ---- Cross-validation transitions ----
        if r.cross_validation:
            self._add_section_title('NMF vs SSM Boundary Transitions')

            strongest_title = QLabel('Strongest transitions (likely real):')
            strongest_title.setStyleSheet('font-size: 12px; font-weight: 500; padding-top: 4px;')
            self._layout.addWidget(strongest_title)

            for x in r.cross_validation[:5]:
                lbl = QLabel(f'   {_fmt(x["time_sec"])}   shift = {x["nmf_shift"]:.3f}')
                lbl.setStyleSheet('font-size: 12px; font-family: monospace;')
                self._layout.addWidget(lbl)

            weakest_title = QLabel('Weakest transitions (possibly spurious):')
            weakest_title.setStyleSheet(f'font-size: 12px; font-weight: 500; padding-top: 8px; color: {TEXT_SECONDARY};')
            self._layout.addWidget(weakest_title)

            for x in r.cross_validation[-5:]:
                lbl = QLabel(f'   {_fmt(x["time_sec"])}   shift = {x["nmf_shift"]:.3f}')
                lbl.setStyleSheet(f'font-size: 12px; font-family: monospace; color: {TEXT_SECONDARY};')
                self._layout.addWidget(lbl)

        self._layout.addStretch()

    def _add_section_title(self, text: str):
        lbl = QLabel(text)
        lbl.setStyleSheet('font-size: 14px; font-weight: 600; padding-top: 12px;')
        self._layout.addWidget(lbl)
