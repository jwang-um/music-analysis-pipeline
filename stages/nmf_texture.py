from sklearn.decomposition import NMF
import numpy as np


def nmf_textures(C_mag: np.ndarray,
                 n_components: int = 12):
    """
    Decompose CQT magnitude into basis spectra and temporal activations via NMF.

    Components loosely correspond to recurring timbral/harmonic gestures.
    Manual labelling by listening to high-activation passages is required.

    Args:
        C_mag:        CQT magnitude, shape (n_bins, frames).
        n_components: Number of basis textures to extract.
                      12 is a reasonable default for a ~45-minute symphony.

    Returns:
        Tuple of:
          W:     Basis spectra, shape (n_bins, n_components)
          H:     Activations, shape (n_components, frames)
          error: Frobenius norm reconstruction error (float)
    """
    C_nn  = C_mag - C_mag.min()  # shift to non-negative; shape: (n_bins, frames)
    model = NMF(n_components=n_components,
                init='nndsvda', max_iter=400, tol=1e-4, random_state=42)
    W     = model.fit_transform(C_nn)   # shape: (n_bins, n_components)
    H     = model.components_           # shape: (n_components, frames)
    return W, H, model.reconstruction_err_


if __name__ == '__main__':
    # Synthetic test: random non-negative matrix
    np.random.seed(42)
    C_mag = np.random.rand(84, 200) * 80  # shape: (84, 200)

    for nc in [4, 8, 12]:
        W, H = nmf_textures(C_mag, n_components=nc)
        print(f'n_components={nc}: W shape={W.shape}, H shape={H.shape}')

    print('\nNMF texture test passed.')
