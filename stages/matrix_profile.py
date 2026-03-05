import stumpy
import numpy as np
from typing import List, Dict


def compute_motifs(sequence: List[int],
                   window_sizes: List[int]) -> Dict:
    """
    Compute Matrix Profile for multiple window sizes.

    Args:
        sequence:     Interval sequence (list of pitch deltas).
        window_sizes: List of subsequence lengths to analyse.

    Returns:
        Dict mapping window size -> {
          'mp':       full matrix profile array, shape (n - m + 1, 4)
          'motifs':   list of (pos_a, pos_b) top-10 motif pairs
          'discords': list of positions for top-5 discords
        }
    """
    results = {}
    arr = np.array(sequence, dtype=float)  # shape: (n,)
    for m in window_sizes:
        if len(arr) < 2 * m:
            continue
        mp = stumpy.stump(arr, m)
        # mp[:,0] = distances; mp[:,1] = nearest-neighbor indices
        motif_idx   = np.argsort(mp[:, 0])[:10]
        discord_idx = np.argsort(mp[:, 0])[-5:]
        results[m] = {
            'mp':       mp,
            'motifs':   [(i, int(mp[i, 1])) for i in motif_idx],
            'discords': list(discord_idx),
        }
    return results


if __name__ == '__main__':
    seq = [2, 2, 1, -1, 2, 2, 1, -1, 3, 2, 1, 0, 2, 2, 1, -1, 2, 2, 1, -1, 5, 3, 2, 1]
    results = compute_motifs(seq, window_sizes=[4, 6])

    for m, res in results.items():
        print(f'\n=== Window size {m} ===')
        print(f'Top motif pairs (position_a, position_b):')
        for (i, j) in res['motifs'][:5]:
            sub_i = seq[i:i+m]
            sub_j = seq[j:j+m]
            print(f'  pos {i} -> {sub_i}  <==>  pos {j} -> {sub_j}  dist={res["mp"][i,0]:.4f}')
        print(f'Discord positions: {res["discords"]}')
        # The discord is where the subsequence has no close match
        for d in res['discords'][:2]:
            print(f'  Discord at pos {d}: {seq[d:d+m]} (dist={res["mp"][d,0]:.4f})')

    print('\nMatrix Profile test complete.')
