"""Cross-part motif tracking via Matrix Profile AB-join."""

import itertools
import stumpy
import numpy as np
from typing import Dict, List
from stages.clustering import is_valid_motif

# Simple heuristic for grouping parts into instrument families
_FAMILY_RULES = [
    ('strings',    ['violin', 'viola', 'cello', 'contrabass', 'bass',
                    'violoncell']),
    ('woodwinds',  ['flute', 'oboe', 'clarinet', 'bassoon', 'piccolo',
                    'cor anglais', 'english horn']),
    ('brass',      ['horn', 'trumpet', 'trombone', 'tuba']),
    ('percussion', ['timpani', 'percussion', 'snare', 'cymbal', 'triangle',
                    'xylophone', 'glockenspiel', 'celesta']),
    ('keys',       ['piano', 'harp', 'harpsichord', 'organ']),
]


def _classify_part(name: str) -> str:
    lower = name.lower()
    for family, keywords in _FAMILY_RULES:
        if any(kw in lower for kw in keywords):
            return family
    return name


def _merge_parts(sequences: Dict[str, Dict], groups: Dict[str, List[str]]):
    """Merge note streams for parts in the same family, sort by onset, recompute intervals."""
    merged = {}
    for family, part_names in groups.items():
        pitches_all, onsets_all = [], []
        for pn in sorted(part_names):
            data = sequences[pn]
            pitches_all.extend(data['pitches'])
            onsets_all.extend(data['onsets'])
        if len(pitches_all) < 20:
            continue
        order = np.argsort(onsets_all)
        sorted_onsets = [onsets_all[i] for i in order]
        sorted_pitches = [pitches_all[i] for i in order]
        intervals = [sorted_pitches[k + 1] - sorted_pitches[k]
                     for k in range(len(sorted_pitches) - 1)]
        merged[family] = {
            'intervals': intervals,
            'onsets': sorted_onsets,
        }
    return merged


def discover_cross_part_motifs(
    sequences: Dict[str, Dict],
    window_sizes: List[int],
    top_k: int = 10,
) -> List[dict]:
    """
    Find melodic motifs that appear across different instrument parts
    using Matrix Profile AB-join.

    Returns a list of dicts with keys:
        part_a, part_b, onset_a, onset_b, frag_a, frag_b, distance, window
    """
    part_names = [p for p in sequences if len(sequences[p]['intervals']) >= 20]

    if len(part_names) > 8:
        groups: Dict[str, List[str]] = {}
        for pn in part_names:
            family = _classify_part(pn)
            groups.setdefault(family, []).append(pn)
        streams = _merge_parts(sequences, groups)
    else:
        streams = {
            pn: {'intervals': sequences[pn]['intervals'],
                 'onsets': sequences[pn]['onsets']}
            for pn in part_names
        }

    stream_names = list(streams.keys())
    if len(stream_names) < 2:
        return []

    results = []
    for name_a, name_b in itertools.combinations(stream_names, 2):
        int_a = np.array(streams[name_a]['intervals'], dtype=float)
        int_b = np.array(streams[name_b]['intervals'], dtype=float)
        ons_a = streams[name_a]['onsets']
        ons_b = streams[name_b]['onsets']

        for m in window_sizes:
            if len(int_a) < 2 * m or len(int_b) < 2 * m:
                continue

            try:
                mp_ab = stumpy.stump(int_a, m, int_b)
            except Exception:
                continue

            distances = mp_ab[:, 0].astype(float)
            nn_indices = mp_ab[:, 1].astype(int)

            best_idx = np.argsort(distances)[:top_k]

            n_subs_b = len(int_b) - m
            for idx in best_idx:
                j = nn_indices[idx]
                if j < 0 or j > n_subs_b:
                    continue
                if idx + m > len(int_a) or j + m > len(int_b):
                    continue

                frag_a = tuple(int(x) for x in int_a[idx:idx + m])
                frag_b = tuple(int(x) for x in int_b[j:j + m])

                if not is_valid_motif(frag_a) or not is_valid_motif(frag_b):
                    continue

                onset_a = ons_a[min(idx, len(ons_a) - 1)]
                onset_b = ons_b[min(j, len(ons_b) - 1)]

                results.append({
                    'part_a': name_a,
                    'part_b': name_b,
                    'onset_a': onset_a,
                    'onset_b': onset_b,
                    'frag_a': frag_a,
                    'frag_b': frag_b,
                    'distance': float(distances[idx]),
                    'window': m,
                })

    results.sort(key=lambda r: r['distance'])
    return results
