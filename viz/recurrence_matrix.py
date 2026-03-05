import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import List, Optional
import numpy as np


def plot_ssm(ssm: np.ndarray,
             boundaries=None,
             movement_frames: Optional[List[int]] = None,
             movement_names: Optional[List[str]] = None,
             section_annotations: Optional[List[dict]] = None,
             title: str = 'Self-Similarity Matrix',
             save_path: str = 'output_ssm.png'):
    """
    Render the self-similarity matrix with optional boundary overlays.

    Args:
        ssm:                  Self-similarity matrix, shape (frames, frames).
        boundaries:           Array of frame indices for algorithmic boundaries (cyan).
        movement_frames:      Frame indices for known movement boundaries (white dashed).
        movement_names:       Label strings for each movement.
        section_annotations:  List of {'mid_frame': int, 'letter': str} dicts
                              for labeling sections along the diagonal.
        title:                Plot title.
        save_path:            Output image path.
    """
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.imshow(ssm, origin='lower', aspect='auto',
              cmap='magma', interpolation='nearest')
    if boundaries is not None:
        for b in boundaries:
            ax.axhline(b, color='cyan', lw=0.6, alpha=0.5)
            ax.axvline(b, color='cyan', lw=0.6, alpha=0.5)
    if movement_frames:
        for i, f in enumerate(movement_frames):
            ax.axhline(f, color='white', lw=1.2, alpha=0.8, linestyle='--')
            ax.axvline(f, color='white', lw=1.2, alpha=0.8, linestyle='--')
            if movement_names and i < len(movement_names):
                ax.text(f + 2, f + 2, movement_names[i],
                        color='white', fontsize=7, va='bottom')
    if section_annotations:
        for ann in section_annotations:
            mf = ann['mid_frame']
            ax.text(mf, mf, ann['letter'],
                    color='yellow', fontsize=8, fontweight='bold',
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.15',
                              facecolor='black', alpha=0.6))
    ax.set_title(title)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f'Saved {save_path}')
    return fig


if __name__ == '__main__':
    ssm = np.random.rand(100, 100)
    ssm = (ssm + ssm.T) / 2
    plot_ssm(ssm, boundaries=[25, 50, 75],
             movement_frames=[0, 25, 50, 75],
             movement_names=['Mov I', 'Mov II', 'Mov III', 'Mov IV'],
             save_path='output_ssm_test.png')
    print('Recurrence matrix viz test passed.')
