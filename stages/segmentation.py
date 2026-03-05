from scipy.sparse.csgraph import laplacian
from scipy.sparse.linalg  import eigsh
from sklearn.cluster      import KMeans
import librosa
import numpy as np


def segment_structure(ssm: np.ndarray,
                      k: int = 8,
                      n_segments: int = None):
    """
    Laplacian structural segmentation of a self-similarity matrix.

    Treats the SSM as an affinity graph, computes the graph Laplacian,
    extracts the k smallest eigenvectors, and clusters frames via KMeans.
    Reference: Serra, Müller & Haro (2014).

    Args:
        ssm:         Self-similarity matrix, shape (frames, frames).
        k:           Number of Laplacian eigenvectors to use.
        n_segments:  Number of clusters (defaults to k).

    Returns:
        Tuple of (labels array shape (frames,), boundary indices array).
    """
    n_frames = ssm.shape[0]
    if n_frames < 2 * k + 1:
        labels = np.zeros(n_frames, dtype=int)
        return labels, np.array([], dtype=int)

    R = librosa.segment.recurrence_matrix(
            ssm, mode='affinity', sym=True)          # shape: (frames, frames)
    L = laplacian(R, normed=True)
    _, evecs = eigsh(L, k=k, which='SM')             # shape: (frames, k)
    labels = KMeans(n_clusters=n_segments or k,
                    random_state=42).fit_predict(evecs)
    boundaries = np.where(np.diff(labels) != 0)[0] + 1
    return labels, boundaries


if __name__ == '__main__':
    # Synthetic test: 4-block SSM
    block_size = 50
    ssm = np.zeros((200, 200))
    for i in range(4):
        s = i * block_size
        e = s + block_size
        ssm[s:e, s:e] = 1.0
    # Add some cross-block similarity
    ssm += np.random.rand(200, 200) * 0.1
    ssm = (ssm + ssm.T) / 2
    np.fill_diagonal(ssm, 1.0)

    labels, bounds = segment_structure(ssm, k=4)
    print(f'Labels shape: {labels.shape}')
    print(f'Unique labels: {np.unique(labels)}')
    print(f'Boundary positions: {bounds}')
    print(f'Expected boundaries near: [50, 100, 150]')

    # Check boundaries are roughly at block edges
    expected = [50, 100, 150]
    for exp in expected:
        nearest = min(bounds, key=lambda b: abs(b - exp))
        print(f'  Expected ~{exp}, nearest found: {nearest} (delta={abs(nearest-exp)})')

    print('\nSegmentation test passed.')
