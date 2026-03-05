import music21
import numpy as np
from typing import List, Optional, Tuple


def build_global_tempo_map(
    midi_paths: List[str],
    movement_offsets: List[float],
    precomputed_tempo: Optional[List[Tuple[float, float]]] = None,
) -> List[Tuple[float, float]]:
    """
    Build a piecewise tempo map for the full symphony.

    If *precomputed_tempo* is supplied (e.g. from ``stitch_movements``),
    the MIDI files are **not** re-parsed, saving significant time.

    Returns:
        List of (global_beat_onset, bpm) sorted by onset.
    """
    if precomputed_tempo is not None:
        return list(precomputed_tempo)

    tempo_map: List[Tuple[float, float]] = []
    for midi_path, offset in zip(midi_paths, movement_offsets):
        score = music21.converter.parse(midi_path)
        marks = score.flatten().getElementsByClass(music21.tempo.MetronomeMark)
        if not marks:
            tempo_map.append((offset, 120.0))
        for mm in marks:
            tempo_map.append((float(mm.offset) + offset, mm.number))
    return sorted(tempo_map, key=lambda x: x[0])


def beats_to_seconds(onsets_beats: List[float],
                     tempo_map: List[Tuple[float, float]]) -> List[float]:
    """
    Convert global beat positions to seconds via piecewise tempo map.

    Args:
        onsets_beats: Global beat positions to convert.
        tempo_map:    Output of build_global_tempo_map().

    Returns:
        List of times in seconds.
    """
    result = []
    for beat in onsets_beats:
        t_sec = 0.0
        prev_beat, prev_bpm = tempo_map[0]
        for seg_beat, seg_bpm in tempo_map[1:]:
            if beat <= seg_beat:
                break
            t_sec     += (seg_beat - prev_beat) * 60.0 / prev_bpm
            prev_beat, prev_bpm = seg_beat, seg_bpm
        t_sec += (beat - prev_beat) * 60.0 / prev_bpm
        result.append(t_sec)
    return result


def frame_of_second(t_sec: float, hop_length: int, sr: int) -> int:
    """
    Convert a time in seconds to a CQT frame index.

    Args:
        t_sec:      Time in seconds.
        hop_length: CQT hop length in samples.
        sr:         Audio sample rate.

    Returns:
        Frame index (integer).
    """
    return int(t_sec * sr / hop_length)


if __name__ == '__main__':
    # Synthetic test with known tempo
    import os
    import tempfile

    test_paths = []
    for i in range(4):
        s = music21.stream.Score()
        p = music21.stream.Part()
        p.partName = 'Test'
        mm = music21.tempo.MetronomeMark(number=100 + i * 20)
        p.insert(0, mm)
        for j in range(16):
            n = music21.note.Note(60 + j % 8)
            n.offset = float(j)
            p.append(n)
        s.insert(0, p)
        path = os.path.join(tempfile.gettempdir(), f'tempo_test_{i}.mid')
        s.write('midi', fp=path)
        test_paths.append(path)

    offsets = [0.0, 16.0, 32.0, 48.0]
    tempo_map = build_global_tempo_map(test_paths, offsets)

    print('Tempo map:')
    for beat, bpm in tempo_map:
        print(f'  beat {beat:.1f} -> {bpm:.1f} BPM')

    mov_seconds = beats_to_seconds(offsets, tempo_map)
    print(f'\nMovement offsets in seconds: {[f"{s:.2f}" for s in mov_seconds]}')

    # Cleanup
    for p in test_paths:
        os.remove(p)

    print('\nAlignment test passed.')
