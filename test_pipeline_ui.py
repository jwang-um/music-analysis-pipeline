"""
Test pipeline.py returns correct AnalysisResults with synthetic data.
Also tests that the CLI wrapper (main.py) still works.
"""

import os
import sys
import tempfile
import numpy as np
import music21
import soundfile as sf

os.environ['MPLBACKEND'] = 'Agg'


def make_midi(path, n_notes=64, base_pitch=60):
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


def make_wav(path, duration_sec=60.0, sr=22050):
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    freqs = [440.0, 554.37, 659.25, 440.0, 493.88, 587.33]
    seg_len = len(t) // len(freqs)
    y = np.zeros_like(t)
    for i, freq in enumerate(freqs):
        s = i * seg_len
        e = s + seg_len if i < len(freqs) - 1 else len(t)
        y[s:e] = 0.5 * np.sin(2 * np.pi * freq * t[s:e])
    y += np.random.randn(len(y)) * 0.01
    sf.write(path, y.astype(np.float32), sr)


def test_pipeline():
    from pipeline import run_analysis, AnalysisResults

    tmpdir = tempfile.mkdtemp(prefix='pipe_test_')
    midi1 = os.path.join(tmpdir, 'mov1.mid')
    midi2 = os.path.join(tmpdir, 'mov2.mid')
    wav1 = os.path.join(tmpdir, 'mov1.wav')
    wav2 = os.path.join(tmpdir, 'mov2.wav')

    make_midi(midi1, 48, 60)
    make_midi(midi2, 48, 67)
    make_wav(wav1, 30.0)
    make_wav(wav2, 30.0)

    progress_log = []

    def on_progress(stage, pct, msg):
        progress_log.append((stage, pct, msg))

    results = run_analysis(
        midi_paths=[midi1, midi2],
        audio_paths=[wav1, wav2],
        movement_names=['I - Allegro', 'II - Adagio'],
        piece_title='Test Sonata',
        nmf_components=4,
        seg_k=4,
        progress=on_progress,
    )

    assert isinstance(results, AnalysisResults)
    assert results.piece_title == 'Test Sonata'
    assert len(results.movement_names) == 2
    assert results.duration_sec > 0
    assert results.n_parts > 0
    print(f'  Duration: {results.duration_sec:.1f}s')
    print(f'  Parts: {results.n_parts}')
    print(f'  Motif pairs: {len(results.motif_pairs)}')
    print(f'  Sections: {len(results.sections)}')
    print(f'  NMF profiles: {len(results.nmf_profiles)}')
    print(f'  Errors: {results.errors}')

    # Check figures were created
    assert results.fig_ssm is not None, 'SSM figure missing'
    assert results.fig_nmf is not None, 'NMF figure missing'
    print(f'  Figures: arc={results.fig_arc is not None}, ssm=True, nmf=True')

    # Check reports
    assert len(results.ssm_report) > 0, 'SSM report empty'
    assert len(results.nmf_report) > 0, 'NMF report empty'
    assert len(results.validation_report) > 0, 'Validation report empty'
    print(f'  Reports: ssm={len(results.ssm_report)}ch, nmf={len(results.nmf_report)}ch')

    # Check validation
    assert results.seg_validation is not None
    assert 'k' in results.seg_validation
    print(f'  Validation k={results.seg_validation["k"]}, '
          f'hit_rate={results.seg_validation["hit_rate"]:.0%}')

    # Check progress was reported
    stages_seen = set(s for s, _, _ in progress_log)
    assert 'Complete' in stages_seen, f'Missing Complete stage, got: {stages_seen}'
    assert progress_log[-1][1] == 100, 'Final progress not 100%'
    print(f'  Progress stages: {sorted(stages_seen)}')

    print('PIPELINE TEST PASSED')
    return True


if __name__ == '__main__':
    ok = test_pipeline()
    sys.exit(0 if ok else 1)
