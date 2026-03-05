import music21
from typing import Dict


def load_interval_sequences(midi_path: str) -> Dict:
    """
    Parse a single MIDI file into per-part interval sequences.

    Args:
        midi_path: Path to a single MIDI file.

    Returns:
        Dict mapping part name -> {'intervals', 'pitches', 'onsets'}
    """
    score = music21.converter.parse(midi_path)
    sequences = {}
    for part in score.parts:
        notes = [n for n in part.flatten().notes
                 if isinstance(n, music21.note.Note)]
        if len(notes) < 8:
            continue
        pitches   = [n.pitch.midi for n in notes]
        intervals = [pitches[i+1] - pitches[i]
                     for i in range(len(pitches)-1)]
        onsets    = [float(n.offset) for n in notes]
        sequences[part.partName] = {
            'intervals': intervals,
            'pitches':   pitches,
            'onsets':    onsets
        }
    return sequences


if __name__ == '__main__':
    import os
    import tempfile

    s = music21.stream.Score()

    violin = music21.stream.Part()
    violin.partName = 'Violin'
    # 16-note C major scale starting at C4 (MIDI 60)
    c_major_pitches = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84, 86]
    for i, p in enumerate(c_major_pitches):
        n = music21.note.Note(p)
        n.offset = float(i)
        violin.append(n)

    cello = music21.stream.Part()
    cello.partName = 'Cello'
    for i, p in enumerate(c_major_pitches):
        n = music21.note.Note(p)
        n.offset = float(i)
        cello.append(n)

    s.insert(0, violin)
    s.insert(0, cello)

    test_path = os.path.join(tempfile.gettempdir(), 'test.mid')
    s.write('midi', fp=test_path)
    print(f'Wrote test MIDI to {test_path}')

    result = load_interval_sequences(test_path)
    for name, data in result.items():
        print(f'\nPart: {name}')
        print(f'  Intervals: {data["intervals"]}')
        print(f'  Pitches:   {data["pitches"]}')

    first_part = list(result.values())[0]
    assert first_part['intervals'][0] == 2, f'Expected first interval=2 (C->D), got {first_part["intervals"][0]}'
    print('\nAll assertions passed.')
    os.remove(test_path)
