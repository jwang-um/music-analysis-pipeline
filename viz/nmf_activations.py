import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import librosa
import numpy as np
from typing import List, Optional, Dict


def plot_nmf_activations(H: np.ndarray,
                         hop_length: int,
                         sr: int,
                         movement_times_sec: Optional[List[float]] = None,
                         movement_names: Optional[List[str]] = None,
                         component_labels: Optional[Dict[int, str]] = None,
                         title: str = 'NMF Textures',
                         save_path: str = 'output_nmf.png'):
    """
    Plot NMF activation matrix as a heatmap with movement boundaries.

    Args:
        H:                  Activations, shape (n_components, frames).
        hop_length:         CQT hop length in samples.
        sr:                 Audio sample rate.
        movement_times_sec: Start time of each movement in seconds.
        movement_names:     Label string for each movement.
        component_labels:   Optional dict mapping component index -> label string.
        title:              Plot title.
        save_path:          Output image path.
    """
    times = librosa.frames_to_time(
        np.arange(H.shape[1]), sr=sr, hop_length=hop_length)  # shape: (frames,)
    H_display = np.log1p(H)  # compress dynamic range to reveal quiet components
    fig, ax = plt.subplots(figsize=(20, 8))
    img = ax.imshow(H_display, aspect='auto', origin='lower',
                    extent=[times[0], times[-1], 0, H.shape[0]],
                    cmap='viridis')
    if movement_times_sec:
        for i, t in enumerate(movement_times_sec):
            ax.axvline(t, color='white', lw=1.2, alpha=0.8, linestyle='--')
            if movement_names and i < len(movement_names):
                ax.text(t + 1, H.shape[0] - 0.5, movement_names[i],
                        color='white', fontsize=7, va='top')
    if component_labels:
        tick_positions = [i + 0.5 for i in range(H.shape[0])]
        tick_labels = [component_labels.get(i, f'Comp {i}')
                       for i in range(H.shape[0])]
        ax.set_yticks(tick_positions)
        ax.set_yticklabels(tick_labels, fontsize=5.5)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('NMF Component')
    ax.set_title(title)
    plt.colorbar(img, ax=ax)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f'Saved {save_path}')
    return fig


if __name__ == '__main__':
    H = np.random.rand(12, 200)
    plot_nmf_activations(H, hop_length=512, sr=22050,
                         movement_times_sec=[0, 1.2, 2.4, 3.6],
                         movement_names=['I', 'II', 'III', 'IV'],
                         save_path='output_nmf_test.png')
    print('NMF activations viz test passed.')
