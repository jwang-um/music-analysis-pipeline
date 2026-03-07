"""
Core analysis pipeline — callback-driven, returns structured results.

Used by both the CLI (main.py) and the desktop UI (ui/worker.py).
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import median_filter

from stages.stitch import stitch_movements
from stages.matrix_profile import compute_motifs
from stages.audio_features import (stitch_audio, movement_samples_to_frames,
                                    compute_cqt, movement_samples_to_beat_frames,
                                    compute_chroma_ssm)
from stages.segmentation import segment_structure
from stages.nmf_texture import nmf_textures
from stages.clustering import cluster_motifs, is_valid_motif
from stages.cross_part import discover_cross_part_motifs
from stages.alignment import build_global_tempo_map, beats_to_seconds
from stages.interpret_nmf import (characterize_components, format_nmf_report,
                                   get_component_labels)
from stages.interpret_ssm import (build_form_chart, compute_cross_section_similarity,
                                   format_ssm_report, get_section_annotations)
from stages.interpret_arcs import interpret_arcs, format_cross_part_report
from stages.motif_context import compute_motif_contexts, compute_cross_part_contexts
from stages.validate import (validate_segmentation_boundaries,
                              validate_nmf_internal, validate_nmf_vs_ssm,
                              format_validation_report)
from viz.arc_plot import arc_plot
from viz.recurrence_matrix import plot_ssm
from viz.nmf_activations import plot_nmf_activations
from viz.plotly_plots import (arc_plot_interactive, ssm_plot_interactive,
                               nmf_plot_interactive)


ProgressCallback = Optional[Callable[[str, int, str], None]]


@dataclass
class AnalysisResults:
    motif_pairs: list = field(default_factory=list)
    motif_fragments: list = field(default_factory=list)
    cluster_labels: list = field(default_factory=list)
    movement_times_sec: list = field(default_factory=lambda: [0.0])
    movement_names: list = field(default_factory=list)
    sections: list = field(default_factory=list)
    cross_sim: list = field(default_factory=list)
    nmf_profiles: list = field(default_factory=list)
    comp_labels: Optional[Dict[int, str]] = None
    section_annots: Optional[list] = None
    seg_validation: Optional[dict] = None
    nmf_validation: Optional[dict] = None
    cross_validation: Optional[list] = None
    cross_part_pairs: list = field(default_factory=list)
    cross_part_details: list = field(default_factory=list)
    fig_arc: Optional[plt.Figure] = None
    fig_ssm: Optional[plt.Figure] = None
    fig_nmf: Optional[plt.Figure] = None
    html_arc: str = ''
    html_ssm: str = ''
    html_nmf: str = ''
    nmf_report: str = ''
    ssm_report: str = ''
    arc_report: str = ''
    validation_report: str = ''
    duration_sec: float = 0.0
    n_parts: int = 0
    piece_title: str = ''
    musicxml_data: str = ''
    movement_offsets_beats: list = field(default_factory=list)
    tempo_marks: list = field(default_factory=list)
    sequences: Optional[Dict] = None
    motif_contexts: list = field(default_factory=list)
    cross_part_contexts: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def run_analysis(
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
    progress: ProgressCallback = None,
) -> AnalysisResults:
    """Run the full analysis pipeline and return structured results."""

    if mp_window_sizes is None:
        mp_window_sizes = [8, 10]
    if part_name_map is None:
        part_name_map = {}

    res = AnalysisResults(movement_names=list(movement_names), piece_title=piece_title)

    def _progress(stage: str, pct: int, msg: str = ''):
        if progress:
            progress(stage, pct, msg)

    # ---- Stage 0: stitch ----
    _progress('Stitching MIDI', 0, 'Loading MIDI files...')
    sequences, mov_offsets, tempo_marks = {}, [0.0], None
    try:
        stitched = stitch_movements(midi_paths, part_name_map=part_name_map)
        sequences = stitched['sequences']
        mov_offsets = stitched['movement_offsets']
        tempo_marks = stitched['tempo_marks']
        res.musicxml_data = stitched.get('musicxml_data', '')
        res.movement_offsets_beats = list(mov_offsets)
        res.tempo_marks = tempo_marks or []
        res.sequences = sequences
        res.n_parts = len(sequences)
    except Exception as e:
        res.errors.append(f'MIDI stitch: {e}')

    _progress('Stitching audio', 5, 'Loading WAV files...')
    y_full, movement_samples, mov_frames = None, [], []
    try:
        y_full, movement_samples = stitch_audio(audio_paths, sr)
        mov_frames = movement_samples_to_frames(movement_samples, hop_length)
        res.duration_sec = len(y_full) / sr
    except Exception as e:
        res.errors.append(f'Audio stitch: {e}')

    # ---- Stage 1: MIDI motif discovery ----
    _progress('MIDI motif discovery', 15, 'Running Matrix Profile...')
    all_pairs, all_frags = [], []
    try:
        for part_name, data in sequences.items():
            if len(data['intervals']) < 20:
                continue
            mp_res = compute_motifs(data['intervals'], mp_window_sizes)
            for m, mp_data in mp_res.items():
                for (i, j) in mp_data['motifs']:
                    all_pairs.append((data['onsets'][i], data['onsets'][j]))
                    all_frags.append(tuple(data['intervals'][i:i+m]))
        keep = [i for i, f in enumerate(all_frags) if is_valid_motif(f)]
        all_pairs = [all_pairs[i] for i in keep]
        all_frags = [all_frags[i] for i in keep]
    except Exception as e:
        res.errors.append(f'MIDI analysis: {e}')

    # ---- Stage 1b: cross-part motif discovery ----
    _progress('Cross-part motifs', 22, 'Running AB-join across parts...')
    cross_part_raw = []
    try:
        cross_part_raw = discover_cross_part_motifs(sequences, mp_window_sizes)
    except Exception as e:
        res.errors.append(f'Cross-part motifs: {e}')

    # ---- Stage 2: audio analysis ----
    C_mag, ssm, labels, bounds, W, H = None, None, None, None, None, None
    beat_frames = None
    if y_full is not None:
        _progress('Audio analysis', 30, 'Computing CQT...')
        try:
            C_mag, C_complex = compute_cqt(y_full, sr, hop_length, n_bins, bins_per_oct)
            _progress('Audio analysis', 35, 'Beat tracking...')

            _, beat_frames = librosa.beat.beat_track(
                y=y_full, sr=sr, hop_length=hop_length)

            _progress('Audio analysis', 40, f'CQT {C_mag.shape} — computing SSM...')
            ssm, beat_frames = compute_chroma_ssm(
                y_full, sr, hop_length,
                C_complex=C_complex, beat_frames=beat_frames)
            del C_complex  # free memory
            ssm = median_filter(ssm, size=21)
            mov_frames = movement_samples_to_beat_frames(
                movement_samples, hop_length, beat_frames)
            _progress('Audio analysis', 50, f'SSM {ssm.shape[0]} beats — segmenting...')

            labels, bounds = segment_structure(ssm, k=seg_k)
            _progress('Audio analysis', 55, 'Running NMF...')
            W, H, _ = nmf_textures(C_mag, nmf_components)
        except Exception as e:
            res.errors.append(f'Audio analysis: {e}')

    # ---- Stage 3: alignment & clustering ----
    _progress('Alignment & clustering', 60, 'Building tempo map...')
    mov_times_sec = [0.0]
    cluster_labels = []
    t1s, t2s = [], []
    try:
        tempo_map = build_global_tempo_map(midi_paths, mov_offsets,
                                              precomputed_tempo=tempo_marks)
        mov_times_sec = beats_to_seconds(mov_offsets, tempo_map)
        if all_frags:
            cluster_labels, _ = cluster_motifs(all_frags)
            t1s = beats_to_seconds([p[0] for p in all_pairs], tempo_map)
            t2s = beats_to_seconds([p[1] for p in all_pairs], tempo_map)
    except Exception as e:
        res.errors.append(f'Clustering: {e}')

    res.movement_times_sec = mov_times_sec
    res.motif_pairs = list(zip(t1s, t2s)) if t1s else []
    res.motif_fragments = all_frags
    res.cluster_labels = list(cluster_labels)

    # Convert cross-part onsets to seconds
    try:
        if cross_part_raw and tempo_map:
            cp_t1 = beats_to_seconds([r['onset_a'] for r in cross_part_raw], tempo_map)
            cp_t2 = beats_to_seconds([r['onset_b'] for r in cross_part_raw], tempo_map)
            res.cross_part_pairs = list(zip(cp_t1, cp_t2))
            res.cross_part_details = [
                {'part_a': r['part_a'], 'part_b': r['part_b'],
                 'frag_a': r['frag_a'], 'frag_b': r['frag_b'],
                 'distance': r['distance'], 'window': r['window']}
                for r in cross_part_raw
            ]
    except Exception as e:
        res.errors.append(f'Cross-part alignment: {e}')

    # ---- Stage 4: interpretation ----
    _progress('Interpretation', 70, 'Characterising NMF components...')
    nmf_profiles = []
    try:
        if W is not None and H is not None:
            nmf_profiles = characterize_components(
                W, H, sr, hop_length, mov_times_sec, movement_names)
            res.nmf_profiles = nmf_profiles
            res.comp_labels = get_component_labels(nmf_profiles)
            res.nmf_report = format_nmf_report(nmf_profiles, movement_names)
    except Exception as e:
        res.errors.append(f'NMF interpretation: {e}')

    _progress('Interpretation', 75, 'Building form chart...')
    try:
        if labels is not None and bounds is not None and beat_frames is not None:
            res.sections = build_form_chart(
                labels, bounds, beat_frames, sr, hop_length,
                mov_frames, movement_names)
            res.cross_sim = compute_cross_section_similarity(ssm, res.sections)
            res.ssm_report = format_ssm_report(res.sections, res.cross_sim)
            res.section_annots = get_section_annotations(res.sections)
    except Exception as e:
        res.errors.append(f'SSM interpretation: {e}')

    _progress('Interpretation', 78, 'Interpreting arcs...')
    try:
        if res.motif_pairs and res.cluster_labels:
            res.arc_report = interpret_arcs(
                res.motif_pairs, res.motif_fragments,
                res.cluster_labels, mov_times_sec, movement_names)
    except Exception as e:
        res.errors.append(f'Arc interpretation: {e}')

    try:
        if res.cross_part_pairs:
            cp_report = format_cross_part_report(
                res.cross_part_pairs, res.cross_part_details,
                mov_times_sec, movement_names)
            res.arc_report = (res.arc_report + '\n' + cp_report).strip()
    except Exception as e:
        res.errors.append(f'Cross-part interpretation: {e}')

    # ---- Motif context (section, texture, parts per recurrence) ----
    _progress('Interpretation', 79, 'Computing motif contexts...')
    try:
        if res.motif_pairs and res.tempo_marks:
            res.motif_contexts = compute_motif_contexts(
                res.motif_pairs,
                H=H,
                sections=res.sections,
                sequences=res.sequences,
                tempo_marks=res.tempo_marks,
                comp_labels=res.comp_labels,
                hop_length=hop_length,
                sr=sr,
                window_sec=5.0,
            )
        if res.cross_part_pairs and res.tempo_marks:
            res.cross_part_contexts = compute_cross_part_contexts(
                res.cross_part_pairs,
                H=H,
                sections=res.sections,
                sequences=res.sequences,
                tempo_marks=res.tempo_marks,
                comp_labels=res.comp_labels,
                hop_length=hop_length,
                sr=sr,
                window_sec=5.0,
            )
    except Exception as e:
        res.errors.append(f'Motif context: {e}')

    # ---- Stage 5: validation ----
    _progress('Validation', 80, 'Validating segmentation...')
    try:
        if ssm is not None and H is not None:
            res.seg_validation = validate_segmentation_boundaries(ssm, mov_frames)
            cqt_mov_frames = movement_samples_to_frames(movement_samples, hop_length)
            res.nmf_validation = validate_nmf_internal(W, H, cqt_mov_frames)
            res.cross_validation = validate_nmf_vs_ssm(
                H, bounds, hop_length, sr, beat_frames)
            res.validation_report = format_validation_report(
                res.seg_validation, res.nmf_validation, res.cross_validation)
    except Exception as e:
        res.errors.append(f'Validation: {e}')

    # ---- Stage 6: visualisation ----
    _progress('Visualization', 90, 'Generating plots...')
    try:
        if t1s and t2s:
            duration = res.duration_sec or (max(t2s) * 1.1)
            res.fig_arc = arc_plot(
                res.motif_pairs, res.cluster_labels, duration,
                movement_times_sec=mov_times_sec,
                movement_names=movement_names,
                title=f'{piece_title} — Motif Recurrence',
                save_path=None)
    except Exception as e:
        res.errors.append(f'Arc plot: {e}')

    try:
        if ssm is not None:
            res.fig_ssm = plot_ssm(
                ssm, bounds, movement_frames=mov_frames,
                movement_names=movement_names,
                section_annotations=res.section_annots,
                title=f'{piece_title} — Self-Similarity Matrix',
                save_path=None)
    except Exception as e:
        res.errors.append(f'SSM plot: {e}')

    try:
        if H is not None:
            res.fig_nmf = plot_nmf_activations(
                H, hop_length, sr,
                movement_times_sec=mov_times_sec,
                movement_names=movement_names,
                component_labels=res.comp_labels,
                title=f'{piece_title} — Recurring Textural Components',
                save_path=None)
    except Exception as e:
        res.errors.append(f'NMF plot: {e}')

    # ---- Stage 6b: interactive Plotly plots (for UI) ----
    _progress('Visualization', 95, 'Generating interactive plots...')
    try:
        if t1s and t2s:
            duration = res.duration_sec or (max(t2s) * 1.1)
            res.html_arc = arc_plot_interactive(
                res.motif_pairs, res.cluster_labels, duration,
                movement_times_sec=mov_times_sec,
                movement_names=movement_names,
                cross_part_pairs=res.cross_part_pairs,
                cross_part_details=res.cross_part_details,
                title=f'{piece_title} — Motif Recurrence')
    except Exception as e:
        res.errors.append(f'Plotly arc: {e}')

    try:
        if ssm is not None:
            res.html_ssm = ssm_plot_interactive(
                ssm, bounds, movement_frames=mov_frames,
                movement_names=movement_names,
                section_annotations=res.section_annots,
                title=f'{piece_title} — Self-Similarity Matrix',
                sr=sr, hop_length=hop_length, beat_frames=beat_frames)
    except Exception as e:
        res.errors.append(f'Plotly SSM: {e}')

    try:
        if H is not None:
            res.html_nmf = nmf_plot_interactive(
                H, hop_length, sr,
                movement_times_sec=mov_times_sec,
                movement_names=movement_names,
                component_labels=res.comp_labels,
                title=f'{piece_title} — Recurring Textural Components')
    except Exception as e:
        res.errors.append(f'Plotly NMF: {e}')

    _progress('Complete', 100, 'Analysis finished.')
    return res
