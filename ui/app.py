"""Main application window: toolbar + tabbed workspace (Setup + result tabs)."""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel,
)
from ui.theme import STYLESHEET, PRIMARY, TEXT_SECONDARY
from ui.worker import AnalysisWorker
from ui.widgets.toolbar import Toolbar
from ui.widgets.setup_tab import SetupTab
from ui.widgets.overview_tab import OverviewTab
from ui.widgets.score_tab import ScoreTab
from ui.widgets.arc_tab import ArcTab
from ui.widgets.ssm_tab import SsmTab
from ui.widgets.nmf_tab import NmfTab
from ui.widgets.validation_tab import ValidationTab
from pipeline import AnalysisResults


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Music Analysis Pipeline')
        self.setMinimumSize(1200, 800)
        self.resize(1440, 900)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Persistent toolbar
        self._toolbar = Toolbar()
        self._toolbar.run_clicked.connect(self._start_analysis)
        root.addWidget(self._toolbar)

        # Tabs
        self._tabs = QTabWidget()
        self._setup = SetupTab()
        self._setup.config_changed.connect(self._on_config_changed)
        self._overview = OverviewTab()
        self._score_tab = ScoreTab()
        self._arc_tab = ArcTab()
        self._ssm_tab = SsmTab()
        self._nmf_tab = NmfTab()
        self._val_tab = ValidationTab()

        self._tabs.addTab(self._setup, 'Setup')
        self._tabs.addTab(self._overview, 'Overview')
        self._tabs.addTab(self._score_tab, 'Score')
        self._tabs.addTab(self._arc_tab, 'Arc Plot')
        self._tabs.addTab(self._ssm_tab, 'SSM')
        self._tabs.addTab(self._nmf_tab, 'NMF')
        self._tabs.addTab(self._val_tab, 'Validation')

        self._arc_tab.show_in_score.connect(
            lambda sec, idx: self._show_in_score(sec, idx))
        self._nmf_tab.show_in_score.connect(
            lambda sec: self._show_in_score(sec, None))

        root.addWidget(self._tabs, stretch=1)

        self._worker = None

    def _on_config_changed(self):
        self._toolbar.set_ready(self._setup.is_ready())

    def _start_analysis(self):
        if self._worker is not None and self._worker.isRunning():
            return
        if not self._setup.is_ready():
            return

        params = self._setup.get_params()
        self._toolbar.on_started()

        self._worker = AnalysisWorker(**params)
        self._worker.progress.connect(self._toolbar.on_progress)
        self._worker.finished.connect(self._on_results)
        self._worker.error.connect(self._toolbar.on_error)
        self._worker.start()

    def _on_results(self, results: AnalysisResults):
        self._toolbar.on_finished()
        self._overview.update_results(results)
        self._score_tab.update_results(results)
        self._arc_tab.update_results(results)
        self._ssm_tab.update_results(results)
        self._nmf_tab.update_results(results)
        self._val_tab.update_results(results)
        self._tabs.setCurrentIndex(1)  # jump to Overview

    def _show_in_score(self, seconds: float, recurrence_index=None):
        self._tabs.setCurrentWidget(self._score_tab)
        self._score_tab.navigate_to_seconds(seconds)
        if recurrence_index is not None:
            self._score_tab.set_selected_recurrence(recurrence_index)

    def _on_error(self, msg: str):
        self._toolbar.on_error(msg)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
