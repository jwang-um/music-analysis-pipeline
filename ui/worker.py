"""Background QThread that runs the analysis pipeline."""

from PySide6.QtCore import QThread, Signal
from pipeline import run_analysis, AnalysisResults
from typing import Dict, List, Optional


class AnalysisWorker(QThread):
    """Runs run_analysis() off the UI thread, emitting progress and results."""

    progress = Signal(str, int, str)        # stage, pct, message
    finished = Signal(AnalysisResults)
    error = Signal(str)

    def __init__(
        self,
        midi_paths: List[str],
        audio_paths: List[str],
        movement_names: List[str],
        piece_title: str = 'Untitled',
        part_name_map: Optional[Dict[str, str]] = None,
        sr: int = 22050,
        hop_length: int = 512,
        n_bins: int = 84,
        bins_per_oct: int = 12,
        mp_window_sizes: Optional[List[int]] = None,
        nmf_components: int = 8,
        seg_k: int = 8,
        parent=None,
    ):
        super().__init__(parent)
        self.midi_paths = midi_paths
        self.audio_paths = audio_paths
        self.movement_names = movement_names
        self.piece_title = piece_title
        self.part_name_map = part_name_map or {}
        self.sr = sr
        self.hop_length = hop_length
        self.n_bins = n_bins
        self.bins_per_oct = bins_per_oct
        self.mp_window_sizes = mp_window_sizes or [8, 10]
        self.nmf_components = nmf_components
        self.seg_k = seg_k

    def _on_progress(self, stage: str, pct: int, msg: str):
        self.progress.emit(stage, pct, msg)

    def run(self):
        try:
            results = run_analysis(
                midi_paths=self.midi_paths,
                audio_paths=self.audio_paths,
                movement_names=self.movement_names,
                piece_title=self.piece_title,
                part_name_map=self.part_name_map,
                sr=self.sr,
                hop_length=self.hop_length,
                n_bins=self.n_bins,
                bins_per_oct=self.bins_per_oct,
                mp_window_sizes=self.mp_window_sizes,
                nmf_components=self.nmf_components,
                seg_k=self.seg_k,
                progress=self._on_progress,
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
