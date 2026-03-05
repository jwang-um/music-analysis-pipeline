import numpy as np
import librosa
from typing import List, Dict, Optional, Tuple

# CQT bin 0 = C1 at default librosa settings (fmin ~32.7 Hz).
# 84 bins at 12 bins/octave spans C1 to B7.
_NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F',
               'F#', 'G', 'G#', 'A', 'A#', 'B']
_BAND_RANGES = {
    'low':       (0, 23),    # C1-B2
    'mid':       (24, 47),   # C3-B4
    'high':      (48, 71),   # C5-B6
    'very high': (72, 83),   # C7-B7
}


def _bin_to_note(b: int) -> str:
    """Map a CQT bin index (0-83) to a note name like 'C4'."""
    octave = (b // 12) + 1
    return f'{_NOTE_NAMES[b % 12]}{octave}'


def _classify_band(peak_bin: int) -> str:
    """Classify a peak bin into a named frequency band."""
    for name, (lo, hi) in _BAND_RANGES.items():
        if lo <= peak_bin <= hi:
            return name
    return 'unknown'


def _bandwidth_label(n_active_bins: int) -> str:
    if n_active_bins < 6:
        return 'narrow-band'
    if n_active_bins > 24:
        return 'broadband'
    return 'moderate-band'


def _format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f'{m:02d}:{s:02d}'


def _frame_to_movement(frame: int, movement_frames: List[int],
                       movement_names: List[str]) -> str:
    """Return the movement name containing a given frame index."""
    mov = 0
    for i, mf in enumerate(movement_frames):
        if frame >= mf:
            mov = i
    return movement_names[mov] if mov < len(movement_names) else f'Mov {mov+1}'


def characterize_components(
        W: np.ndarray,
        H: np.ndarray,
        sr: int,
        hop_length: int,
        movement_times_sec: List[float],
        movement_names: List[str]
) -> List[Dict]:
    """
    Produce a human-readable profile for each NMF component.

    Args:
        W:                  Basis spectra, shape (n_bins, n_components).
        H:                  Activations, shape (n_components, frames).
        sr:                 Audio sample rate.
        hop_length:         CQT hop length.
        movement_times_sec: Start time of each movement in seconds.
        movement_names:     Label for each movement.

    Returns:
        List of dicts, one per component, with keys:
          'index', 'peak_note', 'band', 'bandwidth', 'dominant_movement',
          'mean_activation_by_movement', 'top_peaks_sec', 'label'
    """
    n_components = W.shape[1]
    n_frames = H.shape[1]
    times = librosa.frames_to_time(
        np.arange(n_frames), sr=sr, hop_length=hop_length)

    mov_frame_boundaries = _movement_sec_to_frames(
        movement_times_sec, times)

    profiles = []
    for c in range(n_components):
        profile = _profile_single_component(
            c, W[:, c], H[c, :], times,
            mov_frame_boundaries, movement_names)
        profiles.append(profile)
    return profiles


def _movement_sec_to_frames(movement_times_sec: List[float],
                            times: np.ndarray) -> List[int]:
    """Convert movement start times (seconds) to frame indices."""
    result = []
    for t in movement_times_sec:
        idx = int(np.searchsorted(times, t))
        result.append(min(idx, len(times) - 1))
    return result


def _profile_single_component(
        idx: int,
        w_col: np.ndarray,
        h_row: np.ndarray,
        times: np.ndarray,
        mov_frame_bounds: List[int],
        movement_names: List[str]
) -> Dict:
    """Build the profile dict for one component."""
    peak_bin = int(np.argmax(w_col))
    threshold = w_col[peak_bin] * 0.5
    active_bins = np.where(w_col >= threshold)[0]
    n_active = len(active_bins)

    band = _classify_band(peak_bin)
    bw = _bandwidth_label(n_active)
    peak_note = _bin_to_note(peak_bin)
    range_lo = _bin_to_note(int(active_bins[0]))
    range_hi = _bin_to_note(int(active_bins[-1]))

    mean_per_mov = _mean_activation_per_movement(
        h_row, mov_frame_bounds)
    dominant_idx = int(np.argmax(mean_per_mov))
    dominant_mov = (movement_names[dominant_idx]
                    if dominant_idx < len(movement_names)
                    else f'Mov {dominant_idx+1}')

    top_peaks = _find_top_peaks(h_row, times, n=5)

    label = (f'Comp {idx}: {band} {bw} '
             f'({range_lo}-{range_hi}), '
             f'dominant in {dominant_mov}')

    return {
        'index': idx,
        'peak_note': peak_note,
        'band': band,
        'bandwidth': bw,
        'range': f'{range_lo}-{range_hi}',
        'dominant_movement': dominant_mov,
        'dominant_movement_idx': dominant_idx,
        'mean_activation_by_movement': mean_per_mov,
        'top_peaks_sec': top_peaks,
        'label': label,
    }


def _mean_activation_per_movement(
        h_row: np.ndarray,
        mov_frame_bounds: List[int]) -> np.ndarray:
    """Compute mean activation within each movement's frame range."""
    n_mov = len(mov_frame_bounds)
    means = np.zeros(n_mov)
    for i in range(n_mov):
        start = mov_frame_bounds[i]
        end = (mov_frame_bounds[i + 1]
               if i + 1 < n_mov else len(h_row))
        if end > start:
            means[i] = np.mean(h_row[start:end])
    return means


def _find_top_peaks(h_row: np.ndarray,
                    times: np.ndarray, n: int = 5) -> List[float]:
    """Find the n highest-activation timestamps."""
    top_indices = np.argsort(h_row)[-n:][::-1]
    return [float(times[i]) for i in top_indices if i < len(times)]


def format_nmf_report(profiles: List[Dict],
                      movement_names: List[str]) -> str:
    """
    Format the component profiles into a human-readable text report.

    Args:
        profiles:       Output of characterize_components().
        movement_names: Movement label strings.

    Returns:
        Multi-line report string.
    """
    lines = []
    lines.append('=' * 72)
    lines.append('NMF COMPONENT INTERPRETATION REPORT')
    lines.append('=' * 72)
    lines.append('')

    for p in profiles:
        lines.append(f'--- Component {p["index"]} ---')
        lines.append(f'  Frequency band:    {p["band"]} ({p["bandwidth"]})')
        lines.append(f'  Peak note:         {p["peak_note"]}')
        lines.append(f'  Active range:      {p["range"]}')
        lines.append(f'  Dominant movement: {p["dominant_movement"]}')

        lines.append('  Mean activation by movement:')
        for i, mean_val in enumerate(p['mean_activation_by_movement']):
            name = (movement_names[i]
                    if i < len(movement_names) else f'Mov {i+1}')
            bar = '#' * int(mean_val / max(p['mean_activation_by_movement'].max(), 1e-8) * 30)
            lines.append(f'    {name:30s} {mean_val:8.2f}  {bar}')

        lines.append('  Top-5 peak activations:')
        for t in p['top_peaks_sec']:
            lines.append(f'    {_format_time(t)}')
        lines.append(f'  AUTO-LABEL: {p["label"]}')
        lines.append('')

    return '\n'.join(lines)


def get_component_labels(profiles: List[Dict]) -> Dict[int, str]:
    """
    Extract a compact label dict for use by the plot function.

    Args:
        profiles: Output of characterize_components().

    Returns:
        Dict mapping component index -> short label string.
    """
    return {p['index']: p['label'] for p in profiles}


if __name__ == '__main__':
    np.random.seed(42)
    W = np.random.rand(84, 4)
    H = np.random.rand(4, 500)
    # Make component 0 peak in low bins, component 1 in high bins
    W[:24, 0] *= 5
    W[60:, 1] *= 5
    H[0, 100:200] *= 10
    H[1, 300:400] *= 10

    profiles = characterize_components(
        W, H, sr=22050, hop_length=512,
        movement_times_sec=[0.0, 2.9, 5.8, 8.7],
        movement_names=['I', 'II', 'III', 'IV'])

    report = format_nmf_report(profiles, ['I', 'II', 'III', 'IV'])
    print(report)
    print('interpret_nmf test passed.')
