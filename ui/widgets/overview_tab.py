"""Overview tab: summary dashboard with stat cards and key findings."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QScrollArea, QSizePolicy,
)
from ui.theme import PRIMARY, TEXT_SECONDARY, SURFACE, BORDER, SUCCESS, WARNING
from pipeline import AnalysisResults


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f'{m}:{s:02d}'


def _stat_card(value: str, label: str) -> QFrame:
    card = QFrame()
    card.setObjectName('card')
    card.setFixedSize(180, 100)
    layout = QVBoxLayout(card)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    val_lbl = QLabel(value)
    val_lbl.setObjectName('statValue')
    val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(val_lbl)

    desc_lbl = QLabel(label)
    desc_lbl.setObjectName('statLabel')
    desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc_lbl.setWordWrap(True)
    layout.addWidget(desc_lbl)

    return card


class OverviewTab(QScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._inner = QWidget()
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(20)

        self._placeholder = QLabel('Run an analysis to see results here.')
        self._placeholder.setStyleSheet(f'color: {TEXT_SECONDARY}; font-size: 16px;')
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch()

        self.setWidget(self._inner)

    def update_results(self, r: AnalysisResults):
        # Clear old content
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Title
        title = QLabel(r.piece_title)
        title.setStyleSheet(f'font-size: 22px; font-weight: 700; color: {PRIMARY};')
        self._layout.addWidget(title)

        # Stat cards grid
        grid = QGridLayout()
        grid.setSpacing(12)

        n_families = len(set(r.cluster_labels)) if r.cluster_labels else 0
        n_motifs = len(r.motif_pairs)
        n_sections = len(r.sections)
        unique_types = len(set(
            s['letter'].rstrip('0123456789') for s in r.sections)) if r.sections else 0
        n_cross = sum(1 for (t1, t2), lbl in zip(r.motif_pairs, r.cluster_labels or [])
                      if self._is_cross(t1, t2, r.movement_times_sec)) if r.motif_pairs else 0

        cards = [
            (_fmt_time(r.duration_sec), 'Duration'),
            (str(r.n_parts), 'Instrument Parts'),
            (str(len(r.movement_names)), 'Movements'),
            (str(n_motifs), 'Motif Recurrences'),
            (str(n_families), 'Motif Families'),
            (str(n_sections), 'Structural Sections'),
            (str(unique_types), 'Section Types'),
            (str(n_cross), 'Cross-Movement Arcs'),
        ]

        for i, (val, lbl) in enumerate(cards):
            grid.addWidget(_stat_card(val, lbl), i // 4, i % 4)

        grid_widget = QWidget()
        grid_widget.setLayout(grid)
        self._layout.addWidget(grid_widget)

        # Key findings
        findings_title = QLabel('Key Findings')
        findings_title.setStyleSheet('font-size: 16px; font-weight: 600; padding-top: 8px;')
        self._layout.addWidget(findings_title)

        findings = self._build_findings(r)
        for text in findings:
            bullet = QLabel(f'  •  {text}')
            bullet.setWordWrap(True)
            bullet.setStyleSheet('font-size: 13px; padding: 2px 0;')
            self._layout.addWidget(bullet)

        # Errors
        if r.errors:
            err_title = QLabel('Warnings')
            err_title.setStyleSheet(f'font-size: 14px; font-weight: 600; color: {WARNING}; padding-top: 12px;')
            self._layout.addWidget(err_title)
            for e in r.errors:
                err_lbl = QLabel(f'  ⚠  {e}')
                err_lbl.setWordWrap(True)
                err_lbl.setStyleSheet('font-size: 12px; color: #5F6368;')
                self._layout.addWidget(err_lbl)

        self._layout.addStretch()

    def _is_cross(self, t1, t2, mov_times):
        def _mov(t):
            idx = 0
            for i, mt in enumerate(mov_times):
                if t >= mt:
                    idx = i
            return idx
        return _mov(t1) != _mov(t2)

    def _build_findings(self, r: AnalysisResults):
        findings = []

        if r.duration_sec > 0:
            findings.append(
                f'Total duration: {_fmt_time(r.duration_sec)} across '
                f'{len(r.movement_names)} movement(s).')

        if r.nmf_profiles:
            dominant_counts = {}
            for p in r.nmf_profiles:
                dm = p.get('dominant_movement', '')
                dominant_counts[dm] = dominant_counts.get(dm, 0) + 1
            top_mov = max(dominant_counts, key=dominant_counts.get)
            findings.append(
                f'NMF texture analysis: most components are dominated by {top_mov}.')

        if r.sections:
            unique_letters = set(s['letter'].rstrip('0123456789') for s in r.sections)
            findings.append(
                f'Structural segmentation found {len(r.sections)} sections '
                f'of {len(unique_letters)} distinct types.')

        if r.seg_validation:
            hr = r.seg_validation.get('hit_rate', 0)
            findings.append(
                f'Movement boundary detection: {hr:.0%} hit rate '
                f'({r.seg_validation.get("hits", 0)}/{r.seg_validation.get("hits", 0) + r.seg_validation.get("misses", 0)}).')

        if r.nmf_validation:
            mc = r.nmf_validation.get('max_off_diagonal_corr', 0)
            status = 'low (good)' if mc < 0.5 else 'high (consider fewer components)'
            findings.append(f'NMF component correlation: {mc:.3f} — {status}.')

        return findings
