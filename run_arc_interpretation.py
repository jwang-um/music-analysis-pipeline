"""
Lightweight runner: interprets the arc plot using only the MIDI pipeline.
Skips all audio stages (CQT, SSM, NMF) to run in seconds.

Usage:
    python run_arc_interpretation.py
"""

from config import *
from stages.stitch import stitch_movements
from stages.matrix_profile import compute_motifs
from stages.clustering import cluster_motifs, is_valid_motif
from stages.alignment import build_global_tempo_map, beats_to_seconds
from stages.interpret_arcs import interpret_arcs
import time


def run():
    t0 = time.perf_counter()

    # --- MIDI stitch ---
    stitched = stitch_movements(MIDI_PATHS, part_name_map=PART_NAME_MAP)
    sequences = stitched['sequences']
    mov_offsets = stitched['movement_offsets']
    print(f'MIDI stitch: {len(sequences)} parts, offsets={mov_offsets}')

    # --- Matrix Profile motif discovery ---
    all_pairs, all_frags, all_parts = [], [], []
    for part_name, data in sequences.items():
        mp_res = compute_motifs(data['intervals'], MP_WINDOW_SIZES)
        for m, res in mp_res.items():
            for (i, j) in res['motifs']:
                all_pairs.append((data['onsets'][i], data['onsets'][j]))
                all_frags.append(tuple(data['intervals'][i:i+m]))
                all_parts.append(part_name)
    n_raw = len(all_frags)
    keep = [i for i, f in enumerate(all_frags) if is_valid_motif(f)]
    all_pairs = [all_pairs[i] for i in keep]
    all_frags = [all_frags[i] for i in keep]
    all_parts = [all_parts[i] for i in keep]
    print(f'Motif fragments: {n_raw} raw -> {len(all_frags)} after zero-interval filter')

    # --- Alignment (tempo map) ---
    tempo_map = build_global_tempo_map(MIDI_PATHS, mov_offsets)
    mov_times_sec = beats_to_seconds(mov_offsets, tempo_map)
    t1s = beats_to_seconds([p[0] for p in all_pairs], tempo_map)
    t2s = beats_to_seconds([p[1] for p in all_pairs], tempo_map)

    # --- Clustering ---
    cluster_labels, centers = cluster_motifs(all_frags)
    print(f'DTW clustering -> {len(set(cluster_labels))} families')

    # --- Interpretation ---
    report = interpret_arcs(
        list(zip(t1s, t2s)),
        all_frags,
        list(cluster_labels),
        mov_times_sec,
        MOVEMENT_NAMES,
    )

    out_path = 'output_arc_report.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(report)
    print(f'\nSaved {out_path}')
    print(f'Total: {time.perf_counter()-t0:.1f}s')


if __name__ == '__main__':
    run()
