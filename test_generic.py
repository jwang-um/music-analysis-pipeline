"""
Integration test: verify the pipeline works with a single WAV + single MIDI.
Creates synthetic data, runs core stages, and checks nothing crashes.

Usage:
    python test_generic.py
"""

import os
import sys
import tempfile
import numpy as np

os.environ['MPLBACKEND'] = 'Agg'

import music21
import soundfile as sf

from stages.stitch import stitch_movements
from stages.matrix_profile import compute_motifs
from stages.clustering import cluster_motifs, is_valid_motif
from stages.alignment import build_global_tempo_map, beats_to_seconds
from stages.audio_features import (stitch_audio, compute_cqt, compute_chroma_ssm,
                                    movement_samples_to_frames,
                                    movement_samples_to_beat_frames)
from stages.segmentation import segment_structure
from stages.nmf_texture import nmf_textures
from stages.validate import (validate_segmentation_boundaries,
                              validate_nmf_internal, validate_nmf_vs_ssm,
                              format_validation_report)
from stages.interpret_nmf import characterize_components, format_nmf_report, get_component_labels
from stages.interpret_ssm import (build_form_chart, compute_cross_section_similarity,
                                   format_ssm_report, get_section_annotations)
from viz.arc_plot import arc_plot
from viz.recurrence_matrix import plot_ssm
from viz.nmf_activations import plot_nmf_activations
from scipy.ndimage import median_filter


def make_synthetic_midi(path: str, n_notes: int = 64, base_pitch: int = 60):
    s = music21.stream.Score()
    p = music21.stream.Part()
    p.partName = 'Piano'
    mm = music21.tempo.MetronomeMark(number=120)
    p.insert(0, mm)
    for i in range(n_notes):
        n = music21.note.Note(base_pitch + (i % 12))
        n.offset = float(i)
        p.append(n)
    s.insert(0, p)
    s.write('midi', fp=path)


def make_synthetic_wav(path: str, duration_sec: float = 60.0, sr: int = 22050):
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    freqs = [440.0, 554.37, 659.25, 440.0, 493.88, 587.33]
    segment_len = len(t) // len(freqs)
    y = np.zeros_like(t)
    for i, freq in enumerate(freqs):
        start = i * segment_len
        end = start + segment_len if i < len(freqs) - 1 else len(t)
        y[start:end] = 0.5 * np.sin(2 * np.pi * freq * t[start:end])
    y += np.random.randn(len(y)) * 0.01
    sf.write(path, y.astype(np.float32), sr)


def test_single_movement():
    """Test pipeline with a single WAV + single MIDI."""
    tmpdir = tempfile.mkdtemp(prefix='pipeline_test_')
    midi_path = os.path.join(tmpdir, 'piece.mid')
    wav_path = os.path.join(tmpdir, 'piece.wav')
    out_prefix = os.path.join(tmpdir, 'out_')

    make_synthetic_midi(midi_path, n_notes=64)
    make_synthetic_wav(wav_path, duration_sec=60.0)
    print(f'Created synthetic files in {tmpdir}')

    midi_paths = [midi_path]
    audio_paths = [wav_path]
    movement_names = ['Full piece']
    piece_title = 'Test Piece'

    SR = 22050
    HOP_LENGTH = 512
    N_BINS = 84
    BINS_PER_OCT = 12
    NMF_COMPONENTS = 4
    SEG_K = 4
    MP_WINDOW_SIZES = [8]

    # Stage 0: stitch
    stitched = stitch_movements(midi_paths, part_name_map={})
    sequences = stitched['sequences']
    mov_offsets = stitched['movement_offsets']
    print(f'MIDI stitch: {len(sequences)} parts, offsets={mov_offsets}')
    assert len(mov_offsets) == 1
    assert mov_offsets[0] == 0.0

    y_full, movement_samples = stitch_audio(audio_paths, SR)
    print(f'Audio: {len(y_full)/SR:.1f}s, movements={movement_samples}')
    assert len(movement_samples) == 1

    # Stage 1: MIDI analysis
    all_pairs, all_frags = [], []
    for part_name, data in sequences.items():
        if len(data['intervals']) < max(MP_WINDOW_SIZES):
            print(f'  {part_name}: only {len(data["intervals"])} intervals, skipping MP')
            continue
        mp_res = compute_motifs(data['intervals'], MP_WINDOW_SIZES)
        for m, res in mp_res.items():
            for (i, j) in res['motifs']:
                all_pairs.append((data['onsets'][i], data['onsets'][j]))
                all_frags.append(tuple(data['intervals'][i:i+m]))
    n_raw = len(all_frags)
    keep = [i for i, f in enumerate(all_frags) if is_valid_motif(f)]
    all_pairs = [all_pairs[i] for i in keep]
    all_frags = [all_frags[i] for i in keep]
    print(f'Motifs: {n_raw} raw -> {len(all_frags)} filtered')

    # Stage 2: audio analysis
    C_mag = compute_cqt(y_full, SR, HOP_LENGTH, N_BINS, BINS_PER_OCT)
    print(f'CQT shape: {C_mag.shape}')

    ssm, beat_frames = compute_chroma_ssm(y_full, SR, HOP_LENGTH)
    ssm = median_filter(ssm, size=5)
    mov_frames = movement_samples_to_beat_frames(movement_samples, HOP_LENGTH, beat_frames)
    print(f'SSM shape: {ssm.shape}, beat_frames: {len(beat_frames)}, mov_frames: {mov_frames}')

    labels, bounds = segment_structure(ssm, k=SEG_K)
    W, H, nmf_err = nmf_textures(C_mag, NMF_COMPONENTS)
    print(f'NMF: W={W.shape}, H={H.shape}, err={nmf_err:.1f}')

    # Stage 3: alignment
    tempo_map = build_global_tempo_map(midi_paths, mov_offsets)
    mov_times_sec = beats_to_seconds(mov_offsets, tempo_map)
    print(f'Movement times (sec): {mov_times_sec}')

    t1s, t2s, cluster_labels = [], [], []
    if all_frags:
        cluster_labels, _ = cluster_motifs(all_frags)
        t1s = beats_to_seconds([p[0] for p in all_pairs], tempo_map)
        t2s = beats_to_seconds([p[1] for p in all_pairs], tempo_map)
        print(f'Clustered {len(all_frags)} motifs into {len(set(cluster_labels))} families')

    # Stage 4: interpretation
    nmf_profiles = characterize_components(
        W, H, SR, HOP_LENGTH, mov_times_sec, movement_names)
    comp_labels = get_component_labels(nmf_profiles)
    nmf_report = format_nmf_report(nmf_profiles, movement_names)
    print('NMF report generated OK')

    sections = build_form_chart(
        labels, bounds, beat_frames, SR, HOP_LENGTH, mov_frames, movement_names)
    cross_sim = compute_cross_section_similarity(ssm, sections)
    ssm_report = format_ssm_report(sections, cross_sim)
    section_annots = get_section_annotations(sections, min_duration_sec=2.0)
    print(f'SSM form chart: {len(sections)} sections, {len(section_annots)} annotations')

    # Stage 5: validation
    seg_val = validate_segmentation_boundaries(ssm, mov_frames)
    cqt_mov_frames = movement_samples_to_frames(movement_samples, HOP_LENGTH)
    nmf_val = validate_nmf_internal(W, H, cqt_mov_frames)
    cross_val = validate_nmf_vs_ssm(H, bounds, HOP_LENGTH, SR, beat_frames)
    val_report = format_validation_report(seg_val, nmf_val, cross_val)
    print(f'Validation: k={seg_val["k"]}, boundaries_found={seg_val["n_boundaries_found"]}')

    # Stage 6: visualizations
    if t1s and t2s:
        duration = len(y_full) / SR
        arc_plot(list(zip(t1s, t2s)), list(cluster_labels), duration,
                 movement_times_sec=mov_times_sec,
                 movement_names=movement_names,
                 title=f'{piece_title} — Motif Recurrence',
                 save_path=out_prefix + 'arc.png')

    plot_ssm(ssm, bounds, movement_frames=mov_frames,
             movement_names=movement_names,
             section_annotations=section_annots,
             title=f'{piece_title} — Self-Similarity Matrix',
             save_path=out_prefix + 'ssm.png')

    plot_nmf_activations(H, HOP_LENGTH, SR,
             movement_times_sec=mov_times_sec,
             movement_names=movement_names,
             component_labels=comp_labels,
             title=f'{piece_title} — Recurring Textural Components',
             save_path=out_prefix + 'nmf.png')

    print(f'\nAll outputs saved to {tmpdir}')
    print('SINGLE-MOVEMENT TEST PASSED')
    return True


def test_two_movements():
    """Test pipeline with 2 WAVs + 2 MIDIs (multi-movement, non-4)."""
    tmpdir = tempfile.mkdtemp(prefix='pipeline_test_2mov_')
    midi_paths, audio_paths = [], []

    for i in range(2):
        midi_path = os.path.join(tmpdir, f'mov{i+1}.mid')
        wav_path = os.path.join(tmpdir, f'mov{i+1}.wav')
        make_synthetic_midi(midi_path, n_notes=48, base_pitch=60 + i * 7)
        make_synthetic_wav(wav_path, duration_sec=30.0)
        midi_paths.append(midi_path)
        audio_paths.append(wav_path)

    movement_names = ['I — Allegro', 'II — Adagio']
    SR = 22050
    HOP_LENGTH = 512
    NMF_COMPONENTS = 4
    SEG_K = 4

    stitched = stitch_movements(midi_paths, part_name_map={})
    mov_offsets = stitched['movement_offsets']
    assert len(mov_offsets) == 2

    y_full, movement_samples = stitch_audio(audio_paths, SR)
    assert len(movement_samples) == 2

    ssm, beat_frames = compute_chroma_ssm(y_full, SR, HOP_LENGTH)
    ssm = median_filter(ssm, size=5)
    mov_frames = movement_samples_to_beat_frames(movement_samples, HOP_LENGTH, beat_frames)

    labels, bounds = segment_structure(ssm, k=SEG_K)

    seg_val = validate_segmentation_boundaries(ssm, mov_frames)
    assert seg_val['k'] == 2, f'Expected k=2 for 2 movements, got k={seg_val["k"]}'
    print(f'2-movement validation: k={seg_val["k"]}, '
          f'hit_rate={seg_val["hit_rate"]:.0%}')

    sections = build_form_chart(
        labels, bounds, beat_frames, SR, HOP_LENGTH, mov_frames, movement_names)
    ssm_report = format_ssm_report(
        sections, compute_cross_section_similarity(ssm, sections))
    print(f'2-movement form chart: {len(sections)} sections')
    print('TWO-MOVEMENT TEST PASSED')
    return True


if __name__ == '__main__':
    ok = True
    try:
        test_single_movement()
    except Exception as e:
        print(f'SINGLE-MOVEMENT TEST FAILED: {e}')
        import traceback; traceback.print_exc()
        ok = False

    try:
        test_two_movements()
    except Exception as e:
        print(f'TWO-MOVEMENT TEST FAILED: {e}')
        import traceback; traceback.print_exc()
        ok = False

    sys.exit(0 if ok else 1)
