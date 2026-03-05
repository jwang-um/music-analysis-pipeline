import numpy as np
from scipy import stats
from typing import List, Dict, Tuple, Optional
from stages.segmentation import segment_structure


def validate_segmentation_boundaries(
        ssm: np.ndarray,
        movement_frames: List[int]
) -> Dict:
    """
    Run segmentation at k = n_movements and check alignment with known
    movement boundaries.

    A found boundary is a "hit" if it lands within 20 beat-sync frames
    of a known movement join.

    Args:
        ssm:              Self-similarity matrix, shape (n_beats, n_beats).
        movement_frames:  Beat-sync frame indices for movement starts.

    Returns:
        Dict with 'hits', 'misses', 'hit_rate', 'details' per boundary,
        plus 'k' indicating the segmentation parameter used.
    """
    known = movement_frames[1:]  # skip frame 0 (start of piece)
    n_movements = len(movement_frames)
    k = max(n_movements, 2)
    _, bounds_k = segment_structure(ssm, k=k)

    tolerance = 20
    details = []
    hits = 0
    for kf in known:
        if len(bounds_k) == 0:
            details.append({
                'known_frame': kf, 'nearest_found': None,
                'delta': None, 'hit': False})
            continue
        nearest = int(min(bounds_k, key=lambda b: abs(b - kf)))
        delta = abs(nearest - kf)
        is_hit = delta <= tolerance
        if is_hit:
            hits += 1
        details.append({
            'known_frame': kf, 'nearest_found': nearest,
            'delta': delta, 'hit': is_hit})

    return {
        'hits': hits,
        'misses': len(known) - hits,
        'hit_rate': hits / max(len(known), 1),
        'n_boundaries_found': len(bounds_k),
        'k': k,
        'details': details,
    }


def validate_nmf_internal(
        W: np.ndarray,
        H: np.ndarray,
        movement_frames: List[int]
) -> Dict:
    """
    Compute internal consistency metrics for NMF decomposition.

    Args:
        W:               Basis spectra, shape (n_bins, n_components).
        H:               Activations, shape (n_components, frames).
        movement_frames: Frame indices for movement starts (in CQT frame space,
                         not beat-sync space).

    Returns:
        Dict with 'correlation_matrix', 'sparsity_per_component',
        'anova_f_per_component', 'max_off_diagonal_corr'.
    """
    n_comp = H.shape[0]

    corr = np.corrcoef(H)  # shape: (n_comp, n_comp)
    off_diag = corr[np.triu_indices(n_comp, k=1)]
    max_off = float(np.max(np.abs(off_diag))) if len(off_diag) > 0 else 0.0

    sparsity = []
    for c in range(n_comp):
        row = H[c, :]
        threshold = row.max() * 0.1
        frac_active = float(np.mean(row > threshold))
        sparsity.append(frac_active)

    mov_bounds = list(movement_frames) + [H.shape[1]]
    anova_f = []
    for c in range(n_comp):
        groups = []
        for i in range(len(mov_bounds) - 1):
            segment = H[c, mov_bounds[i]:mov_bounds[i + 1]]
            if len(segment) > 0:
                groups.append(segment)
        if len(groups) >= 2 and all(len(g) > 1 for g in groups):
            f_stat, _ = stats.f_oneway(*groups)
            anova_f.append(float(f_stat))
        else:
            anova_f.append(0.0)

    return {
        'correlation_matrix': corr,
        'max_off_diagonal_corr': max_off,
        'sparsity_per_component': sparsity,
        'anova_f_per_component': anova_f,
    }


def validate_nmf_vs_ssm(
        H: np.ndarray,
        boundaries: np.ndarray,
        hop_length: int,
        sr: int,
        beat_frames: np.ndarray
) -> List[Dict]:
    """
    Check whether NMF activation shifts align with SSM segmentation boundaries.

    At each boundary, measure the L2 norm of the change in mean NMF activation
    vector across a 20-frame window before vs after.

    Args:
        H:            Activations, shape (n_components, cqt_frames).
        boundaries:   Beat-sync boundary frame indices.
        hop_length:   CQT hop length.
        sr:           Sample rate.
        beat_frames:  Beat frame positions from beat tracking.

    Returns:
        List of dicts per boundary with 'frame', 'time_sec', 'nmf_shift'.
    """
    results = []
    window = 20

    for b in boundaries:
        # Map beat-sync boundary frame to CQT frame
        if b >= len(beat_frames):
            continue
        cqt_frame = int(beat_frames[b])

        before_start = max(0, cqt_frame - window)
        after_end = min(H.shape[1], cqt_frame + window)

        if cqt_frame <= before_start or after_end <= cqt_frame:
            continue

        mean_before = H[:, before_start:cqt_frame].mean(axis=1)
        mean_after = H[:, cqt_frame:after_end].mean(axis=1)
        shift = float(np.linalg.norm(mean_after - mean_before))

        import librosa as _lr
        t_sec = float(_lr.frames_to_time(
            beat_frames[b], sr=sr, hop_length=hop_length))

        results.append({
            'beat_frame': int(b),
            'cqt_frame': cqt_frame,
            'time_sec': t_sec,
            'nmf_shift': shift,
        })

    results.sort(key=lambda x: x['nmf_shift'], reverse=True)
    return results


def format_validation_report(
        seg_val: Dict,
        nmf_val: Dict,
        cross_val: List[Dict]
) -> str:
    """
    Format all validation results into a single text report.

    Args:
        seg_val:   Output of validate_segmentation_boundaries().
        nmf_val:   Output of validate_nmf_internal().
        cross_val: Output of validate_nmf_vs_ssm().

    Returns:
        Multi-line report string.
    """
    lines = []
    lines.append('=' * 72)
    lines.append('VALIDATION REPORT')
    lines.append('=' * 72)

    # --- Segmentation ---
    lines.append('')
    k_used = seg_val.get('k', '?')
    lines.append(f'--- SSM Segmentation vs Known Movement Boundaries (k={k_used}) ---')
    lines.append(f'  Boundaries found: {seg_val["n_boundaries_found"]}')
    lines.append(f'  Hit rate: {seg_val["hits"]}/{seg_val["hits"]+seg_val["misses"]} '
                 f'({seg_val["hit_rate"]:.0%})')
    for d in seg_val['details']:
        status = 'HIT' if d['hit'] else 'MISS'
        nearest = d['nearest_found'] if d['nearest_found'] is not None else 'N/A'
        delta = d['delta'] if d['delta'] is not None else 'N/A'
        lines.append(f'    Known frame {d["known_frame"]:5d}  '
                     f'nearest={nearest!s:>5s}  '
                     f'delta={delta!s:>4s}  {status}')

    # --- NMF internal ---
    lines.append('')
    lines.append('--- NMF Internal Consistency ---')
    lines.append(f'  Max off-diagonal correlation: '
                 f'{nmf_val["max_off_diagonal_corr"]:.3f} '
                 f'({"OK" if nmf_val["max_off_diagonal_corr"] < 0.5 else "HIGH - consider fewer components"})')

    lines.append('')
    lines.append(f'  {"Comp":>5s}  {"Sparsity":>9s}  {"ANOVA F":>9s}  Assessment')
    lines.append('  ' + '-' * 50)
    for c in range(len(nmf_val['sparsity_per_component'])):
        sp = nmf_val['sparsity_per_component'][c]
        f_val = nmf_val['anova_f_per_component'][c]
        if sp < 0.8 and f_val > 50:
            assessment = 'STRONG (sparse + movement-specific)'
        elif sp < 0.9:
            assessment = 'moderate (fairly sparse)'
        elif f_val > 50:
            assessment = 'moderate (movement-specific but dense)'
        else:
            assessment = 'weak (dense, uniform)'
        lines.append(f'  {c:5d}  {sp:9.2%}  {f_val:9.1f}  {assessment}')

    # --- Cross-output ---
    lines.append('')
    lines.append('--- NMF vs SSM Cross-Validation ---')
    lines.append('  NMF activation shift at each segmentation boundary:')
    if cross_val:
        median_shift = np.median([r['nmf_shift'] for r in cross_val])
        lines.append(f'  Median shift: {median_shift:.3f}')
        lines.append('')
        # Show top 5 strongest and bottom 5 weakest
        lines.append('  Strongest transitions (likely real):')
        for r in cross_val[:5]:
            m, s = divmod(int(r['time_sec']), 60)
            lines.append(f'    {m:02d}:{s:02d}  shift={r["nmf_shift"]:.3f}')
        lines.append('  Weakest transitions (possibly spurious):')
        for r in cross_val[-5:]:
            m, s = divmod(int(r['time_sec']), 60)
            lines.append(f'    {m:02d}:{s:02d}  shift={r["nmf_shift"]:.3f}')
    else:
        lines.append('  No boundaries to validate.')

    lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    np.random.seed(42)

    # Synthetic SSM with clear blocks
    ssm = np.zeros((200, 200))
    for i in range(4):
        s, e = i * 50, (i + 1) * 50
        ssm[s:e, s:e] = 1.0
    ssm += np.random.rand(200, 200) * 0.1
    ssm = (ssm + ssm.T) / 2

    seg_val = validate_segmentation_boundaries(ssm, [0, 50, 100, 150])
    print(f'Seg validation: {seg_val["hits"]}/{seg_val["hits"]+seg_val["misses"]} hits')

    H = np.random.rand(8, 500)
    nmf_val = validate_nmf_internal(
        np.random.rand(84, 8), H, [0, 125, 250, 375])
    print(f'Max corr: {nmf_val["max_off_diagonal_corr"]:.3f}')

    report = format_validation_report(seg_val, nmf_val, [])
    print(report)
    print('validate test passed.')
