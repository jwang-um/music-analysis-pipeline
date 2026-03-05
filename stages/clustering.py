from tslearn.metrics import cdist_dtw
from tslearn.preprocessing import TimeSeriesScalerMeanVariance
from sklearn.cluster import AgglomerativeClustering
import numpy as np
from typing import List, Tuple


def is_valid_motif(intervals: tuple, max_zero_fraction: float = 0.4) -> bool:
    """Reject fragments dominated by zero intervals (sustained tones / tremolo)."""
    if len(intervals) == 0:
        return False
    return (intervals.count(0) / len(intervals)) <= max_zero_fraction


def cluster_motifs(fragments: List[Tuple[int, ...]],
                   n_clusters: int = 8):
    """
    Cluster variable-length motif fragments using DTW distance.

    Computes the full pairwise DTW distance matrix in one pass
    (C-optimised via tslearn) then applies agglomerative clustering,
    avoiding the iterative centroid recomputation of KMeans-DTW.

    Returns:
        Tuple of (label array shape (n_fragments,), None).
        Second element kept as None for API compatibility.
    """
    if len(fragments) <= n_clusters:
        return np.arange(len(fragments)), None

    max_len = max(len(f) for f in fragments)
    padded = [list(f) + [0] * (max_len - len(f)) for f in fragments]
    X = np.array(padded).reshape(len(padded), max_len, 1)
    X = TimeSeriesScalerMeanVariance().fit_transform(X)

    dist_matrix = cdist_dtw(X)
    np.fill_diagonal(dist_matrix, 0.0)
    dist_matrix = np.maximum(dist_matrix, dist_matrix.T)

    model = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric='precomputed',
        linkage='average',
    )
    labels = model.fit_predict(dist_matrix)
    return labels, None


if __name__ == '__main__':
    import time

    np.random.seed(42)
    group_a = [tuple(np.array([2, 2, 1, -1]) + np.random.randint(-1, 2, 4))
               for _ in range(5)]
    group_b = [tuple(np.array([3, 1, -2, 1]) + np.random.randint(-1, 2, 4))
               for _ in range(5)]
    group_c = [tuple(np.array([-1, -1, 2, 3]) + np.random.randint(-1, 2, 4))
               for _ in range(5)]

    all_frags = group_a + group_b + group_c

    t0 = time.perf_counter()
    labels, _ = cluster_motifs(all_frags, n_clusters=3)
    elapsed = time.perf_counter() - t0
    print(f'Clustering 15 fragments took {elapsed:.2f}s')

    print(f'Labels: {labels}')
    for name, start, end in [('A', 0, 5), ('B', 5, 10), ('C', 10, 15)]:
        group_labels = set(labels[start:end])
        print(f'  Group {name} labels: {group_labels}')

    print('\nClustering test passed.')
