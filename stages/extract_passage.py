import numpy as np
import soundfile as sf
import os
from typing import List, Tuple
from stages.audio_features import stitch_audio


def extract_passage(y: np.ndarray,
                    sr: int,
                    t_sec: float,
                    duration: float = 5.0,
                    output_path: str = 'check.wav') -> str:
    """
    Extract a short audio clip at a given timestamp from stitched audio.

    Args:
        y:           Full stitched audio array, shape (samples,).
        sr:          Sample rate.
        t_sec:       Start time in seconds.
        duration:    Clip duration in seconds.
        output_path: Output WAV file path.

    Returns:
        The output_path written to.
    """
    start = int(t_sec * sr)
    end = min(int((t_sec + duration) * sr), len(y))
    start = max(0, start)
    if end <= start:
        return output_path

    clip = y[start:end]
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    sf.write(output_path, clip, sr)
    return output_path


def extract_cross_section_pairs(
        y: np.ndarray,
        sr: int,
        sections: List[dict],
        cross_sim: List[Tuple[str, str, float]],
        output_dir: str = 'output_checks',
        duration: float = 8.0
) -> List[str]:
    """
    Auto-extract audio snippets for the top cross-section similarity pairs.

    For each pair, extracts a clip from the midpoint of each section.

    Args:
        y:          Full stitched audio, shape (samples,).
        sr:         Sample rate.
        sections:   Output of build_form_chart().
        cross_sim:  Output of compute_cross_section_similarity().
        output_dir: Directory for output WAV files.
        duration:   Clip duration in seconds.

    Returns:
        List of paths written.
    """
    os.makedirs(output_dir, exist_ok=True)
    section_by_letter = {s['letter']: s for s in sections}

    paths = []
    for rank, (letter_a, letter_b, sim) in enumerate(cross_sim):
        sec_a = section_by_letter.get(letter_a)
        sec_b = section_by_letter.get(letter_b)
        if sec_a is None or sec_b is None:
            continue

        mid_a = (sec_a['start_sec'] + sec_a['end_sec']) / 2
        mid_b = (sec_b['start_sec'] + sec_b['end_sec']) / 2

        path_a = os.path.join(
            output_dir,
            f'pair{rank+1}_{letter_a}_at_{int(mid_a)}s.wav')
        path_b = os.path.join(
            output_dir,
            f'pair{rank+1}_{letter_b}_at_{int(mid_b)}s.wav')

        extract_passage(y, sr, mid_a - duration / 2, duration, path_a)
        extract_passage(y, sr, mid_b - duration / 2, duration, path_b)
        paths.extend([path_a, path_b])
        print(f'  Pair {rank+1}: {letter_a} ({int(mid_a)}s) <-> '
              f'{letter_b} ({int(mid_b)}s)  sim={sim:.4f}')

    return paths


if __name__ == '__main__':
    y = np.random.randn(22050 * 10).astype(np.float32)
    path = extract_passage(y, 22050, 2.0, 3.0, 'test_clip.wav')
    info = sf.info(path)
    print(f'Wrote {path}: {info.duration:.1f}s, {info.samplerate}Hz')
    os.remove(path)
    print('extract_passage test passed.')
