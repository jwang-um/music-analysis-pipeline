"""
Motif recurrence context: section, texture (NMF), and surrounding parts
for each (t1, t2) pair, for comparison across recurrences.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np

from stages.alignment import frame_of_second


def _seconds_to_beats(
    times_sec: List[float],
    tempo_marks: List[Tuple[float, float]],
) -> List[float]:
    """Convert seconds to global beat positions via piecewise tempo map."""
    if not tempo_marks:
        return list(times_sec)
    cum_sec = [0.0]
    cum_beats = [tempo_marks[0][0]]
    for i in range(1, len(tempo_marks)):
        prev_beat, prev_bpm = tempo_marks[i - 1]
        curr_beat, _ = tempo_marks[i]
        delta_sec = (curr_beat - prev_beat) * 60.0 / prev_bpm
        cum_sec.append(cum_sec[-1] + delta_sec)
        cum_beats.append(curr_beat)
    result = []
    for t in times_sec:
        idx = 0
        for i in range(1, len(cum_sec)):
            if t >= cum_sec[i]:
                idx = i
            else:
                break
        remaining = t - cum_sec[idx]
        bpm = tempo_marks[idx][1]
        beat = cum_beats[idx] + remaining * bpm / 60.0
        result.append(beat)
    return result


def _bpm_at_beat(beat: float, tempo_marks: List[Tuple[float, float]]) -> float:
    """Return BPM for the segment containing the given beat."""
    if not tempo_marks:
        return 120.0
    bpm = tempo_marks[0][1]
    for seg_beat, seg_bpm in tempo_marks:
        if beat >= seg_beat:
            bpm = seg_bpm
    return bpm


def _section_at_time(
    t_sec: float,
    sections: List[Dict],
) -> Optional[Dict]:
    """Return the section dict containing t_sec, or None."""
    for s in sections:
        start = s.get('start_sec', 0)
        end = s.get('end_sec', 0)
        if start <= t_sec < end:
            return s
    return None


def _texture_at_time(
    t_sec: float,
    H: np.ndarray,
    comp_labels: Optional[Dict[int, str]],
    hop_length: int,
    sr: int,
    window_sec: float,
    top_k: int = 3,
) -> List[str]:
    """
    Return top NMF component labels in a window around t_sec.
    H shape: (n_components, n_frames).
    """
    if H is None or H.size == 0:
        return []
    center = frame_of_second(t_sec, hop_length, sr)
    half = max(1, int(window_sec * sr / hop_length / 2))
    lo = max(0, center - half)
    hi = min(H.shape[1], center + half)
    if lo >= hi:
        return []
    mean_act = np.mean(H[:, lo:hi], axis=1)
    order = np.argsort(-mean_act)[:top_k]
    labels = []
    for idx in order:
        if mean_act[idx] <= 0:
            continue
        name = (comp_labels or {}).get(int(idx)) or f'C{idx}'
        labels.append(name)
    return labels


def _parts_at_time(
    t_sec: float,
    sequences: Dict[str, Dict],
    tempo_marks: List[Tuple[float, float]],
    window_sec: float,
) -> Tuple[List[str], str]:
    """
    Return (list of part names with notes in window, summary string).
    sequences: part_name -> {'onsets': [...], ...} with onsets in global beats.
    """
    if not sequences or not tempo_marks:
        return [], ''
    beats = _seconds_to_beats([t_sec], tempo_marks)
    beat_center = beats[0]
    bpm = _bpm_at_beat(beat_center, tempo_marks)
    delta_beat = window_sec * bpm / 60.0
    beat_lo = beat_center - delta_beat
    beat_hi = beat_center + delta_beat
    active = []
    for part_name, data in sequences.items():
        onsets = data.get('onsets', [])
        if not onsets:
            continue
        count = sum(1 for o in onsets if beat_lo <= o <= beat_hi)
        if count > 0:
            active.append((part_name, count))
    active.sort(key=lambda x: -x[1])
    part_names = [p for p, _ in active]
    n = len(part_names)
    if n == 0:
        summary = 'no activity'
    elif n == 1:
        summary = 'solo'
    elif n <= 4:
        summary = 'small group'
    else:
        summary = 'tutti'
    return part_names, summary


def compute_motif_contexts(
    motif_pairs: List[Tuple[float, float]],
    H: Optional[np.ndarray],
    sections: List[Dict],
    sequences: Optional[Dict[str, Dict]],
    tempo_marks: List[Tuple[float, float]],
    comp_labels: Optional[Dict[int, str]],
    hop_length: int,
    sr: int,
    window_sec: float = 5.0,
) -> List[Dict]:
    """
    For each (t1, t2) in motif_pairs, compute context at both times:
    section, top NMF components, and active parts.

    Returns list of dicts with keys:
      t1, t2, section_a, section_b, texture_a, texture_b,
      parts_a, parts_b, summary_a, summary_b
    """
    result = []
    for (t1, t2) in motif_pairs:
        sec_a = _section_at_time(t1, sections)
        sec_b = _section_at_time(t2, sections)
        section_a = f"{sec_a['letter']} ({sec_a['movement']})" if sec_a else '—'
        section_b = f"{sec_b['letter']} ({sec_b['movement']})" if sec_b else '—'

        texture_a = []
        texture_b = []
        if H is not None:
            texture_a = _texture_at_time(
                t1, H, comp_labels, hop_length, sr, window_sec)
            texture_b = _texture_at_time(
                t2, H, comp_labels, hop_length, sr, window_sec)

        parts_a, summary_a = [], ''
        parts_b, summary_b = [], ''
        if sequences:
            parts_a, summary_a = _parts_at_time(
                t1, sequences, tempo_marks, window_sec)
            parts_b, summary_b = _parts_at_time(
                t2, sequences, tempo_marks, window_sec)

        result.append({
            't1': t1,
            't2': t2,
            'section_a': section_a,
            'section_b': section_b,
            'texture_a': texture_a,
            'texture_b': texture_b,
            'parts_a': parts_a,
            'parts_b': parts_b,
            'summary_a': summary_a,
            'summary_b': summary_b,
        })
    return result


def compute_cross_part_contexts(
    cross_part_pairs: List[Tuple[float, float]],
    H: Optional[np.ndarray],
    sections: List[Dict],
    sequences: Optional[Dict[str, Dict]],
    tempo_marks: List[Tuple[float, float]],
    comp_labels: Optional[Dict[int, str]],
    hop_length: int,
    sr: int,
    window_sec: float = 5.0,
) -> List[Dict]:
    """Same structure as compute_motif_contexts for cross-part recurrences."""
    return compute_motif_contexts(
        cross_part_pairs,
        H=H,
        sections=sections,
        sequences=sequences,
        tempo_marks=tempo_marks,
        comp_labels=comp_labels,
        hop_length=hop_length,
        sr=sr,
        window_sec=window_sec,
    )
