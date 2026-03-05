import numpy as np
import librosa
from typing import List, Dict, Optional, Tuple
import string


def _format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f'{m:02d}:{s:02d}'


def _frame_to_movement(frame: int, movement_frames: List[int],
                       movement_names: List[str]) -> str:
    """Return the movement name for a given beat-sync frame."""
    mov = 0
    for i, mf in enumerate(movement_frames):
        if frame >= mf:
            mov = i
    return movement_names[mov] if mov < len(movement_names) else f'Mov {mov+1}'


def _merge_consecutive_labels(labels: np.ndarray) -> List[Tuple[int, int, int]]:
    """
    Collapse consecutive frames with the same label into (start, end, label) runs.
    This eliminates single-beat flicker in the segmentation.
    """
    runs = []
    current_label = labels[0]
    start = 0
    for i in range(1, len(labels)):
        if labels[i] != current_label:
            runs.append((start, i, int(current_label)))
            current_label = labels[i]
            start = i
    runs.append((start, len(labels), int(current_label)))
    return runs


def _merge_short_runs(runs: List[Tuple[int, int, int]],
                      min_frames: int = 15) -> List[Tuple[int, int, int]]:
    """
    Absorb runs shorter than min_frames into their longest neighbor.
    Prevents the form chart from being cluttered with sub-second flicker.
    """
    if len(runs) <= 1:
        return list(runs)

    merged = list(runs)
    changed = True
    while changed:
        changed = False
        new: List[Tuple[int, int, int]] = []
        i = 0
        while i < len(merged):
            start, end, lab = merged[i]
            if (end - start) < min_frames:
                if new:
                    # Absorb into previous run
                    prev = new[-1]
                    new[-1] = (prev[0], end, prev[2])
                    changed = True
                elif i + 1 < len(merged):
                    # First run is short — absorb into next run
                    nxt = merged[i + 1]
                    merged[i + 1] = (start, nxt[1], nxt[2])
                    changed = True
                else:
                    new.append((start, end, lab))
            else:
                new.append((start, end, lab))
            i += 1
        merged = new
    return merged


def build_form_chart(
        labels: np.ndarray,
        boundaries: np.ndarray,
        beat_frames: np.ndarray,
        sr: int,
        hop_length: int,
        movement_frames: List[int],
        movement_names: List[str]
) -> List[Dict]:
    """
    Convert segmentation labels and boundaries into a structural form chart.

    Consecutive frames with the same label are merged into a single section,
    and sections shorter than ~7 seconds are absorbed into neighbors to
    produce a readable chart rather than a beat-level dump.

    Args:
        labels:          Cluster label per beat-sync frame, shape (n_beats,).
        boundaries:      Array of boundary frame indices.
        beat_frames:     Beat frame positions from beat tracking.
        sr:              Audio sample rate.
        hop_length:      CQT hop length.
        movement_frames: Beat-sync frame indices for movement starts.
        movement_names:  Label for each movement.

    Returns:
        List of section dicts with keys:
          'index', 'start_frame', 'end_frame', 'start_sec', 'end_sec',
          'duration_sec', 'label_id', 'letter', 'movement'
    """
    n_frames = len(labels)

    def _frame_to_sec(f: int) -> float:
        if f >= len(beat_frames):
            f = len(beat_frames) - 1
        return float(librosa.frames_to_time(
            beat_frames[f], sr=sr, hop_length=hop_length))

    runs = _merge_consecutive_labels(labels)
    runs = _merge_short_runs(runs, min_frames=40)

    unique_labels = sorted(set(r[2] for r in runs))
    label_to_letter = {}
    for i, lab in enumerate(unique_labels):
        if i < 26:
            label_to_letter[lab] = string.ascii_uppercase[i]
        else:
            label_to_letter[lab] = f'Z{i - 25}'

    letter_counts = {}
    sections = []

    for idx, (s_frame, e_frame, label_id) in enumerate(runs):
        base_letter = label_to_letter[label_id]
        count = letter_counts.get(base_letter, 0)
        letter_counts[base_letter] = count + 1
        letter = base_letter if count == 0 else f'{base_letter}{count + 1}'

        s_sec = _frame_to_sec(s_frame)
        e_sec = _frame_to_sec(min(e_frame, n_frames - 1))
        movement = _frame_to_movement(
            s_frame, movement_frames, movement_names)

        sections.append({
            'index': idx,
            'start_frame': s_frame,
            'end_frame': e_frame,
            'start_sec': s_sec,
            'end_sec': e_sec,
            'duration_sec': e_sec - s_sec,
            'label_id': label_id,
            'letter': letter,
            'movement': movement,
        })

    return sections


def compute_cross_section_similarity(
        ssm: np.ndarray,
        sections: List[Dict],
        top_n: int = 5
) -> List[Tuple[str, str, float]]:
    """
    Find the most similar non-adjacent section pairs.

    Args:
        ssm:      Self-similarity matrix, shape (n_beats, n_beats).
        sections: Output of build_form_chart().
        top_n:    Number of top pairs to return.

    Returns:
        List of (section_a_letter, section_b_letter, mean_similarity) tuples,
        sorted by similarity descending.
    """
    n = len(sections)
    pairs = []
    for i in range(n):
        for j in range(i + 2, n):
            si = sections[i]
            sj = sections[j]
            block = ssm[si['start_frame']:si['end_frame'],
                        sj['start_frame']:sj['end_frame']]
            if block.size == 0:
                continue
            mean_sim = float(np.mean(block))
            pairs.append((si['letter'], sj['letter'], mean_sim))

    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs[:top_n]


def format_ssm_report(sections: List[Dict],
                      cross_sim: List[Tuple[str, str, float]]) -> str:
    """
    Format the form chart and cross-section similarity into a text report.

    Args:
        sections:  Output of build_form_chart().
        cross_sim: Output of compute_cross_section_similarity().

    Returns:
        Multi-line report string.
    """
    lines = []
    lines.append('=' * 72)
    lines.append('STRUCTURAL FORM CHART')
    lines.append('=' * 72)
    lines.append('')
    lines.append(f'{"Sect":>5s}  {"Letter":>6s}  {"Start":>6s}  {"End":>6s}  '
                 f'{"Dur":>5s}  {"Movement"}')
    lines.append('-' * 72)

    for s in sections:
        lines.append(
            f'{s["index"]:5d}  {s["letter"]:>6s}  '
            f'{_format_time(s["start_sec"]):>6s}  '
            f'{_format_time(s["end_sec"]):>6s}  '
            f'{_format_time(s["duration_sec"]):>5s}  '
            f'{s["movement"]}')

    lines.append('')
    lines.append(f'Total sections: {len(sections)}')
    unique_letters = set(s['letter'].rstrip('0123456789') for s in sections)
    lines.append(f'Unique section types: {len(unique_letters)} '
                 f'({", ".join(sorted(unique_letters))})')

    lines.append('')
    lines.append('=' * 72)
    lines.append('TOP CROSS-SECTION SIMILARITIES (non-adjacent)')
    lines.append('=' * 72)
    lines.append('')
    for a, b, sim in cross_sim:
        lines.append(f'  {a:>6s} <-> {b:<6s}  similarity = {sim:.4f}')

    lines.append('')
    return '\n'.join(lines)


def get_section_annotations(sections: List[Dict],
                            min_duration_sec: float = 25.0) -> List[Dict]:
    """
    Extract minimal annotation data for the SSM plot.

    Only includes sections longer than min_duration_sec to keep the
    diagonal labels legible at full-symphony scale.

    Args:
        sections:         Output of build_form_chart().
        min_duration_sec: Minimum section duration to include in annotations.

    Returns:
        List of dicts with 'mid_frame' and 'letter' for plot annotation.
    """
    return [
        {
            'mid_frame': (s['start_frame'] + s['end_frame']) // 2,
            'letter': s['letter'],
        }
        for s in sections
        if s['duration_sec'] >= min_duration_sec
    ]


if __name__ == '__main__':
    np.random.seed(42)
    # Synthetic: 200-frame SSM with 4 blocks
    labels = np.array([0]*50 + [1]*50 + [2]*50 + [0]*50)
    boundaries = np.array([50, 100, 150])
    beat_frames = np.arange(200) * 10
    movement_frames = [0, 50, 100, 150]
    movement_names = ['I', 'II', 'III', 'IV']

    sections = build_form_chart(
        labels, boundaries, beat_frames,
        sr=22050, hop_length=512,
        movement_frames=movement_frames,
        movement_names=movement_names)

    ssm = np.random.rand(200, 200)
    ssm = (ssm + ssm.T) / 2
    cross_sim = compute_cross_section_similarity(ssm, sections)

    report = format_ssm_report(sections, cross_sim)
    print(report)

    annots = get_section_annotations(sections)
    for a in annots:
        print(f'  frame {a["mid_frame"]}: {a["letter"]}')

    assert sections[0]['letter'] == 'A'
    if len(sections) > 3:
        # Fourth section should be A2 (second occurrence of label 0)
        a_recurrences = [s for s in sections if s['letter'].startswith('A')]
        assert len(a_recurrences) >= 2, f'Expected A to recur, got {[s["letter"] for s in sections]}'
    print('\ninterpret_ssm test passed.')
