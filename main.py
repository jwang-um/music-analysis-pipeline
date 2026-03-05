"""CLI entry point — runs the analysis pipeline and saves outputs to disk."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from config import (MIDI_PATHS, AUDIO_PATHS, MOVEMENT_NAMES, PIECE_TITLE,
                    PART_NAME_MAP, SR, HOP_LENGTH, N_BINS, BINS_PER_OCT,
                    MP_WINDOW_SIZES, NMF_COMPONENTS, SEG_K)
from pipeline import run_analysis


def _cli_progress(stage: str, pct: int, msg: str):
    print(f'[{pct:3d}%] {stage}: {msg}')


def run():
    results = run_analysis(
        midi_paths=MIDI_PATHS,
        audio_paths=AUDIO_PATHS,
        movement_names=MOVEMENT_NAMES,
        piece_title=PIECE_TITLE,
        part_name_map=PART_NAME_MAP,
        sr=SR,
        hop_length=HOP_LENGTH,
        n_bins=N_BINS,
        bins_per_oct=BINS_PER_OCT,
        mp_window_sizes=MP_WINDOW_SIZES,
        nmf_components=NMF_COMPONENTS,
        seg_k=SEG_K,
        progress=_cli_progress,
    )

    for report_name, attr in [('output_nmf_report.txt', 'nmf_report'),
                               ('output_ssm_report.txt', 'ssm_report'),
                               ('output_arc_report.txt', 'arc_report'),
                               ('output_validation_report.txt', 'validation_report')]:
        text = getattr(results, attr)
        if text:
            with open(report_name, 'w', encoding='utf-8') as f:
                f.write(text)
            print(text)
            print(f'Saved {report_name}')

    for fig_attr, path in [('fig_arc', 'output_arc.png'),
                            ('fig_ssm', 'output_ssm.png'),
                            ('fig_nmf', 'output_nmf.png')]:
        fig = getattr(results, fig_attr)
        if fig is not None:
            fig.savefig(path, dpi=150)
            plt.close(fig)
            print(f'Saved {path}')

    if results.errors:
        print(f'\n{len(results.errors)} error(s):')
        for e in results.errors:
            print(f'  - {e}')


if __name__ == '__main__':
    run()
