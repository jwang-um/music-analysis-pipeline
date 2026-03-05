"""NMF tab: interactive Plotly heatmap + component interpretation cards."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSplitter,
    QScrollArea, QGridLayout, QSizePolicy, QApplication, QToolTip,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from ui.theme import PRIMARY, PRIMARY_LIGHT, TEXT_SECONDARY, SURFACE, BORDER, TAB10_HEX
from ui.utils import load_html_in_webview
from pipeline import AnalysisResults


def _fmt(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    return f'{m:02d}:{s:02d}'


def _band_color(band: str) -> str:
    mapping = {
        'low': '#34A853',
        'mid': '#1A73E8',
        'high': '#FBBC04',
        'very high': '#EA4335',
    }
    return mapping.get(band, '#5F6368')


class TimestampChip(QLabel):
    """Clickable timestamp pill. Left-click copies; double-click shows in score."""

    def __init__(self, seconds: float, movement: str = '',
                 score_callback=None, parent=None):
        text = _fmt(seconds)
        if movement:
            text += f' ({movement})'
        super().__init__(text, parent)
        self._seconds = seconds
        self._score_callback = score_callback
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip('Click: copy \u00b7 Double-click: show in score')
        self.setStyleSheet(
            f'background: #E8EAED; color: #202124; border-radius: 10px; '
            f'padding: 2px 10px; font-size: 11px; font-weight: 500;')

    def mousePressEvent(self, event):
        QApplication.clipboard().setText(_fmt(self._seconds))
        QToolTip.showText(event.globalPosition().toPoint(), 'Copied!', self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._score_callback:
            self._score_callback(self._seconds)
        super().mouseDoubleClickEvent(event)


class ComponentCard(QFrame):
    """Card displaying a single NMF component's interpretation."""

    def __init__(self, profile: dict, movement_names: list,
                 score_callback=None, parent=None):
        super().__init__(parent)
        self._score_callback = score_callback
        self.setObjectName('card')
        self.setMinimumWidth(340)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        idx_lbl = QLabel(f'Component {profile["index"]}')
        idx_lbl.setStyleSheet(f'font-size: 14px; font-weight: 600; color: {PRIMARY};')
        header.addWidget(idx_lbl)

        band = profile.get('band', 'unknown')
        bc = _band_color(band)
        badge = QLabel(f' {band.upper()} ')
        badge.setStyleSheet(
            f'background: {bc}; color: white; border-radius: 8px; '
            f'padding: 2px 8px; font-size: 10px; font-weight: 600;')
        header.addWidget(badge)
        header.addStretch()
        layout.addLayout(header)

        note_lbl = QLabel(
            f'Peak: {profile.get("peak_note", "?")}  \u00b7  '
            f'Range: {profile.get("range", "?")}  \u00b7  '
            f'{profile.get("bandwidth", "")}')
        note_lbl.setStyleSheet(f'font-size: 11px; color: {TEXT_SECONDARY};')
        layout.addWidget(note_lbl)

        dom = profile.get('dominant_movement', '')
        dom_lbl = QLabel(f'Dominant in: {dom}')
        dom_lbl.setStyleSheet('font-size: 12px; font-weight: 500;')
        layout.addWidget(dom_lbl)

        means = profile.get('mean_activation_by_movement')
        if means is not None and len(means) > 0:
            max_mean = float(max(means)) if max(means) > 0 else 1.0
            for i, val in enumerate(means):
                name = movement_names[i] if i < len(movement_names) else f'Mov {i+1}'
                bar_row = QHBoxLayout()
                bar_row.setSpacing(6)

                name_lbl = QLabel(name)
                name_lbl.setFixedWidth(150)
                name_lbl.setStyleSheet('font-size: 10px; color: #5F6368;')
                bar_row.addWidget(name_lbl)

                bar_bg = QFrame()
                bar_bg.setFixedHeight(8)
                bar_bg.setStyleSheet(
                    f'background: {BORDER}; border-radius: 4px;')
                bar_bg.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

                pct = val / max_mean if max_mean > 0 else 0
                bar_fill = QFrame(bar_bg)
                bar_fill.setFixedHeight(8)
                bar_fill.setStyleSheet(
                    f'background: {PRIMARY}; border-radius: 4px;')
                bar_fill.setFixedWidth(max(1, int(pct * 140)))

                bar_row.addWidget(bar_bg)

                val_lbl = QLabel(f'{val:.1f}')
                val_lbl.setFixedWidth(50)
                val_lbl.setStyleSheet('font-size: 10px; color: #5F6368;')
                val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                bar_row.addWidget(val_lbl)

                layout.addLayout(bar_row)

        peaks = profile.get('top_peaks_sec', [])
        if peaks:
            ts_label = QLabel('Peak activations:')
            ts_label.setStyleSheet(f'font-size: 11px; color: {TEXT_SECONDARY}; padding-top: 4px;')
            layout.addWidget(ts_label)

            chip_row = QHBoxLayout()
            chip_row.setSpacing(4)
            seen = set()
            for t in peaks[:5]:
                t_key = int(t)
                if t_key in seen:
                    continue
                seen.add(t_key)
                chip_row.addWidget(TimestampChip(
                    t, score_callback=self._score_callback))
            chip_row.addStretch()
            layout.addLayout(chip_row)


class NmfTab(QWidget):

    show_in_score = Signal(float)  # time in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tmp_html = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self._splitter)

        # Interactive plot
        self._web_view = QWebEngineView()
        self._web_view.setMinimumHeight(300)
        self._splitter.addWidget(self._web_view)

        # Cards scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._cards_widget = QWidget()
        self._cards_layout = QGridLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(8, 8, 8, 8)
        self._cards_layout.setSpacing(12)
        self._scroll.setWidget(self._cards_widget)
        self._splitter.addWidget(self._scroll)

        self._splitter.setStretchFactor(0, 2)
        self._splitter.setStretchFactor(1, 3)

    def update_results(self, r: AnalysisResults):
        if r.html_nmf:
            self._tmp_html = load_html_in_webview(
                self._web_view, r.html_nmf, self._tmp_html)

        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, profile in enumerate(r.nmf_profiles):
            card = ComponentCard(
                profile, r.movement_names,
                score_callback=lambda sec: self.show_in_score.emit(sec))
            self._cards_layout.addWidget(card, i // 2, i % 2)
