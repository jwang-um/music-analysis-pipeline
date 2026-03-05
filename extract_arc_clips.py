"""
Extract audio clips for the most important cross-movement arc connections.

Loads only the stitched audio — no CQT/SSM/NMF needed.

Usage:
    python extract_arc_clips.py
"""

import os
from config import AUDIO_PATHS, SR
from stages.audio_features import stitch_audio
from stages.extract_passage import extract_passage

OUTPUT_DIR = 'output_checks'

CLIPS = [
    # (label, time_seconds, description)
    # --- Family 3/0: I↔IV chromatic neighbour-note (highest confidence) ---
    ('fam3_I_12m37',   12 * 60 + 37,  'Fam 3/0: Mov I development climax (12:37)'),
    ('fam3_IV_39m37',  39 * 60 + 37,  'Fam 3/0: Mov IV finale climax (39:37)'),

    # --- Family 5: I↔II secondary theme connection ---
    ('fam5_I_10m55',   10 * 60 + 55,  'Fam 5: Mov I secondary theme area (10:55)'),
    ('fam5_II_18m17',  18 * 60 + 17,  'Fam 5: Mov II secondary theme echo (18:17)'),

    # --- Family 7: I↔II wide-leap / octave-displaced line ---
    ('fam7_I_12m55',   12 * 60 + 55,  'Fam 7: Mov I wide-leap passage (12:55)'),
    ('fam7_II_21m26',  21 * 60 + 26,  'Fam 7: Mov II octave-displaced echo (21:26)'),
]

CLIP_DURATION = 10.0


def run():
    y, _ = stitch_audio(AUDIO_PATHS, SR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f'Extracting {len(CLIPS)} clips ({CLIP_DURATION}s each) '
          f'to {OUTPUT_DIR}/\n')

    for label, t_sec, desc in CLIPS:
        out_path = os.path.join(OUTPUT_DIR, f'{label}.wav')
        extract_passage(y, SR, t_sec - CLIP_DURATION / 2, CLIP_DURATION,
                        out_path)
        m, s = divmod(int(t_sec), 60)
        print(f'  {out_path:40s}  {m:02d}:{s:02d}  {desc}')

    print(f'\nDone. Listen to paired clips to verify cross-movement connections.')


if __name__ == '__main__':
    run()
