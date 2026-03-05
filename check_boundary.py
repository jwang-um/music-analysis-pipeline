"""
Investigate the suspected NMF stitching artifact at the movement I/II boundary.

Loads only the stitched audio, reports the boundary timestamp, and extracts
a 30-second clip centered on the join for listening verification.

Usage:
    python check_boundary.py
"""

from config import AUDIO_PATHS, SR
from stages.audio_features import stitch_audio
from stages.extract_passage import extract_passage


def run():
    y, movement_samples = stitch_audio(AUDIO_PATHS, SR)
    total_sec = len(y) / SR

    print(f'Total stitched duration: {total_sec:.1f}s ({int(total_sec)//60}m{int(total_sec)%60}s)')
    print()

    for i, samp in enumerate(movement_samples):
        t = samp / SR
        print(f'  Movement {i+1} starts at sample {samp:>10d}  = {t:8.2f}s  '
              f'({int(t)//60:02d}:{int(t)%60:02d})')

    boundary_sec = movement_samples[1] / SR
    suspect_sec = 16 * 60 + 21  # 16:21 = 981s
    delta = abs(boundary_sec - suspect_sec)

    print()
    print(f'I/II audio boundary:     {boundary_sec:.2f}s  '
          f'({int(boundary_sec)//60:02d}:{int(boundary_sec)%60:02d})')
    print(f'NMF Component 2 peak:    {suspect_sec}s  (16:21)')
    print(f'Delta:                   {delta:.2f}s')
    print()

    if delta < 5.0:
        print('** CLOSE MATCH — the NMF peak is likely a stitching artifact.')
    elif delta < 30.0:
        print('** NEARBY — could be a boundary-adjacent artifact or genuine passage.')
    else:
        print('** FAR APART — the NMF peak is probably a genuine musical feature.')

    clip_center = boundary_sec
    clip_dur = 30.0
    out = extract_passage(y, SR, clip_center - clip_dur / 2, clip_dur,
                          'boundary_check_I_II.wav')
    print(f'\nExtracted boundary clip: {out}')
    print(f'  Covers {clip_center - clip_dur/2:.1f}s to {clip_center + clip_dur/2:.1f}s')
    print('  Listen for clicks, silence, or discontinuity at the midpoint.')


if __name__ == '__main__':
    run()
