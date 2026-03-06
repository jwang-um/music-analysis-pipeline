import os
import tempfile
import music21
from typing import List, Dict, Tuple


def _normalize_part_name(raw_name: str, part_name_map: Dict[str, str]) -> str:
    return part_name_map.get(raw_name, raw_name)


_COMMON_ABBREVIATIONS: Dict[str, str] = {
    'violin': 'Vln', 'viola': 'Vla', 'cello': 'Vc', 'violoncello': 'Vc',
    'contrabass': 'Cb', 'double bass': 'Cb', 'bass': 'B',
    'flute': 'Fl', 'oboe': 'Ob', 'clarinet': 'Cl', 'bassoon': 'Bsn',
    'horn': 'Hn', 'trumpet': 'Tpt', 'trombone': 'Tbn', 'tuba': 'Tba',
    'timpani': 'Timp', 'percussion': 'Perc', 'harp': 'Hp', 'piano': 'Pno',
    'piccolo': 'Picc', 'english horn': 'E.Hn', 'cor anglais': 'C.A.',
    'contrabassoon': 'Cbsn', 'celesta': 'Cel', 'xylophone': 'Xyl',
}


def _abbreviate_part_name(name: str) -> str:
    lower = name.lower().strip()
    for full, abbr in _COMMON_ABBREVIATIONS.items():
        if lower.startswith(full):
            suffix = name[len(full):].strip()
            return f'{abbr} {suffix}'.strip() if suffix else abbr
    words = name.split()
    if len(words) == 1:
        return name[:4] + '.' if len(name) > 4 else name
    return ''.join(w[0].upper() for w in words if w)


def stitch_movements(midi_paths: List[str],
                     part_name_map: Dict[str, str] = None) -> Dict:
    """
    Concatenate multiple MIDI files into a single unified timeline.

    Also extracts tempo marks during the same parse pass so that
    ``build_global_tempo_map`` can reuse them without re-parsing.

    Returns:
        Dict with keys:
          'sequences'         : per-part dict with global-beat onsets
          'movement_offsets'  : list of beat offsets where each movement starts
          'movement_durations': list of beat durations for each movement
          'tempo_marks'       : sorted list of (global_beat, bpm) tuples
    """
    movement_offsets, movement_durations = [], []
    tempo_marks: List[Tuple[float, float]] = []
    cumulative_offset = 0.0
    all_movement_data = []

    for midi_path in midi_paths:
        score = music21.converter.parse(midi_path)
        movement_offsets.append(cumulative_offset)
        duration = float(score.duration.quarterLength)
        movement_durations.append(duration)

        marks = score.flatten().getElementsByClass(music21.tempo.MetronomeMark)
        if not marks:
            tempo_marks.append((cumulative_offset, 120.0))
        for mm in marks:
            tempo_marks.append((float(mm.offset) + cumulative_offset, mm.number))

        cumulative_offset += duration
        all_movement_data.append((score, midi_path))

    tempo_marks.sort(key=lambda x: x[0])

    unified: Dict[str, Dict] = {}
    for mov_idx, (score, _) in enumerate(all_movement_data):
        offset = movement_offsets[mov_idx]
        for part in score.parts:
            notes = [n for n in part.flatten().notes
                     if isinstance(n, music21.note.Note)]
            if len(notes) < 8:
                continue
            raw_name = part.partName or f'Part_{part.id}'
            name = _normalize_part_name(raw_name, part_name_map or {})
            if name not in unified:
                unified[name] = {'intervals': [], 'pitches': [],
                                 'onsets': [], 'movements': []}
            pitches   = [n.pitch.midi for n in notes]
            onsets    = [float(n.offset) + offset for n in notes]
            intervals = [pitches[i+1] - pitches[i]
                         for i in range(len(pitches) - 1)]
            unified[name]['pitches'].extend(pitches)
            unified[name]['onsets'].extend(onsets)
            unified[name]['intervals'].extend(intervals)
            unified[name]['movements'].extend([mov_idx] * len(notes))

    # Build a combined MusicXML score from all movements
    musicxml_data = ''
    try:
        combined = music21.stream.Score()
        combined.metadata = music21.metadata.Metadata()
        combined.metadata.title = 'Combined Score'

        part_streams: Dict[str, music21.stream.Part] = {}
        for mov_idx, (score, _) in enumerate(all_movement_data):
            offset = movement_offsets[mov_idx]
            for part in score.parts:
                raw_name = part.partName or f'Part_{part.id}'
                name = _normalize_part_name(raw_name, part_name_map or {})
                if name not in part_streams:
                    p = music21.stream.Part()
                    p.partName = name
                    p.partAbbreviation = _abbreviate_part_name(name)
                    part_streams[name] = p
                for el in part.flatten().notesAndRests:
                    new_el = el.__deepcopy__({})
                    new_el.offset = float(el.offset) + offset
                    part_streams[name].insert(new_el.offset, new_el)
        for p in part_streams.values():
            combined.insert(0, p)

        tmp = tempfile.NamedTemporaryFile(suffix='.musicxml', delete=False)
        tmp.close()
        combined.write('musicxml', fp=tmp.name)
        with open(tmp.name, 'r', encoding='utf-8') as f:
            musicxml_data = f.read()
        os.unlink(tmp.name)
    except Exception:
        pass

    return {
        'sequences':          unified,
        'movement_offsets':   movement_offsets,
        'movement_durations': movement_durations,
        'tempo_marks':        tempo_marks,
        'musicxml_data':      musicxml_data,
    }


def movement_of_onset(onset_beat: float, movement_offsets: List[float]) -> int:
    """
    Return the 0-based movement index that contains a given global beat onset.

    Args:
        onset_beat:       Global beat position.
        movement_offsets: List of beat offsets where each movement starts.

    Returns:
        0-based movement index.
    """
    mov = 0
    for i, off in enumerate(movement_offsets):
        if onset_beat >= off:
            mov = i
    return mov


if __name__ == '__main__':
    import os
    import sys
    import tempfile

    # Create 4 synthetic MIDI "movements" for testing
    test_paths = []
    for mov_num in range(4):
        s = music21.stream.Score()
        p = music21.stream.Part()
        p.partName = 'Violin'
        base_pitch = 60 + mov_num * 5
        for i in range(16):
            n = music21.note.Note(base_pitch + (i % 8))
            n.offset = float(i)
            p.append(n)
        s.insert(0, p)
        path = os.path.join(tempfile.gettempdir(), f'test_mov{mov_num+1}.mid')
        s.write('midi', fp=path)
        test_paths.append(path)
        print(f'Created synthetic movement {mov_num+1}: {path}')

    result = stitch_movements(test_paths)
    sequences = result['sequences']
    mov_offsets = result['movement_offsets']
    mov_durations = result['movement_durations']

    print(f'\nParts found: {list(sequences.keys())}')
    for name, data in sequences.items():
        print(f'  {name}: {len(data["pitches"])} notes, {len(data["intervals"])} intervals')
    print(f'\nMovement offsets (beats): {mov_offsets}')
    print(f'Movement durations (beats): {mov_durations}')
    assert mov_offsets[0] == 0.0, 'First movement offset must be 0.0'
    print(f'\nFirst 10 intervals of first part: {list(sequences.values())[0]["intervals"][:10]}')

    # Cleanup
    for p in test_paths:
        os.remove(p)

    print('\nStitch test passed.')
