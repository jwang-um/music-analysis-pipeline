"""Persistent top toolbar: Run button, progress bar, status labels."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QProgressBar, QLabel,
)
from ui.theme import TEXT_SECONDARY


class Toolbar(QWidget):
    """Always-visible strip with Run button and progress feedback."""

    run_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('toolbar')
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self.run_btn = QPushButton('Run Analysis')
        self.run_btn.setObjectName('primaryBtn')
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self.run_clicked.emit)
        layout.addWidget(self.run_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(260)
        layout.addWidget(self.progress_bar)

        self.stage_label = QLabel('Idle')
        self.stage_label.setStyleSheet(f'font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY};')
        self.stage_label.setMinimumWidth(120)
        layout.addWidget(self.stage_label)

        self.detail_label = QLabel('')
        self.detail_label.setStyleSheet(f'font-size: 11px; color: {TEXT_SECONDARY};')
        self.detail_label.setWordWrap(False)
        layout.addWidget(self.detail_label, stretch=1)

    def set_ready(self, ready: bool):
        self.run_btn.setEnabled(ready)

    def on_progress(self, stage: str, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.stage_label.setText(stage)
        self.detail_label.setText(msg)

    def on_started(self):
        self.run_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setProperty('error', False)
        self.progress_bar.style().unpolish(self.progress_bar)
        self.progress_bar.style().polish(self.progress_bar)
        self.stage_label.setText('Starting…')
        self.detail_label.setText('')

    def on_finished(self):
        self.run_btn.setEnabled(True)
        self.stage_label.setText('Complete')

    def on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.progress_bar.setProperty('error', True)
        self.progress_bar.style().unpolish(self.progress_bar)
        self.progress_bar.style().polish(self.progress_bar)
        self.stage_label.setText('Error')
        self.detail_label.setText(msg)
