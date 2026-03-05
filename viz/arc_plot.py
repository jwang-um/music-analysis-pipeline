import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import List, Tuple, Optional


def arc_plot(motif_pairs: List[Tuple[float, float]],
             family_labels: List[int],
             duration_sec: float,
             movement_times_sec: Optional[List[float]] = None,
             movement_names: Optional[List[str]] = None,
             title: str = '',
             save_path: str = 'output_arc.png'):
    """
    Draw an arc plot connecting recurring motif positions.

    Each arc connects two time positions where the same motif recurs,
    coloured by motif family. Arcs crossing a movement boundary are
    cross-movement recurrences.

    Args:
        motif_pairs:        List of (t1_sec, t2_sec) recurrence pairs.
        family_labels:      Integer cluster label for each pair.
        duration_sec:       Total symphony duration in seconds.
        movement_times_sec: Start time of each movement in seconds.
        movement_names:     Label string for each movement.
        title:              Plot title.
        save_path:          Output image path.
    """
    fig, ax = plt.subplots(figsize=(20, 5))
    colors  = plt.cm.tab10(np.linspace(0, 1, 10))

    for (t1, t2), label in zip(motif_pairs, family_labels):
        mid    = (t1 + t2) / 2
        width  = abs(t2 - t1)
        height = min(np.sqrt(width) * 0.08, 0.6)
        alpha  = max(0.2, 0.8 - width / duration_sec)
        arc = mpatches.Arc(
            (mid, 0), width, height * 2,
            angle=0, theta1=0, theta2=180,
            color=colors[label % 10], lw=0.8, alpha=alpha)
        ax.add_patch(arc)

    if movement_times_sec:
        for i, t in enumerate(movement_times_sec):
            ax.axvline(t, color='black', lw=1.2, alpha=0.5, linestyle='--')
            if movement_names and i < len(movement_names):
                ax.text(t + 1, 0.92, movement_names[i],
                        fontsize=7, color='#333333', va='top')

    ax.set_xlim(0, duration_sec)
    ax.set_ylim(-0.05, 1.0)
    ax.set_xlabel('Time (seconds)')
    ax.set_title(title)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f'Saved {save_path}')
    return fig


if __name__ == '__main__':
    np.random.seed(42)
    duration = 2700.0
    n_pairs = 30
    t1s = np.random.uniform(0, duration * 0.8, n_pairs)
    t2s = t1s + np.random.uniform(50, 500, n_pairs)
    pairs = list(zip(t1s.tolist(), t2s.tolist()))
    labels = np.random.randint(0, 5, n_pairs).tolist()
    mov_times = [0, 500, 1100, 1800]
    mov_names = ['I — Moderato', 'II — Allegretto', 'III — Largo', 'IV — Allegro non troppo']

    arc_plot(pairs, labels, duration,
             movement_times_sec=mov_times, movement_names=mov_names,
             title='Test Arc Plot', save_path='output_arc_test.png')
    print('Arc plot viz test passed.')
