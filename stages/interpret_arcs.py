import numpy as np
from collections import Counter, defaultdict
from typing import List, Tuple, Dict
from stages.factor_oracle import label_transformation


def _format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f'{m:02d}:{s:02d}'


def _movement_at(t_sec: float, mov_times: List[float],
                 mov_names: List[str]) -> Tuple[int, str]:
    """Return (index, name) of the movement containing t_sec."""
    idx = 0
    for i, mt in enumerate(mov_times):
        if t_sec >= mt:
            idx = i
    name = mov_names[idx] if idx < len(mov_names) else f'Mov {idx+1}'
    return idx, name


def _movement_pair_key(m1: int, m2: int) -> str:
    a, b = min(m1, m2), max(m1, m2)
    return f'{a+1}<->{b+1}'


def interpret_arcs(
        motif_pairs: List[Tuple[float, float]],
        motif_fragments: List[Tuple[int, ...]],
        family_labels: List[int],
        movement_times_sec: List[float],
        movement_names: List[str],
) -> str:
    """
    Produce a human-readable interpretation report for the arc plot.

    Args:
        motif_pairs:        List of (t1_sec, t2_sec) recurrence pairs.
        motif_fragments:    The interval-sequence fragment at each pair's first position.
        family_labels:      DTW cluster label per pair.
        movement_times_sec: Start time of each movement in seconds.
        movement_names:     Movement label strings.

    Returns:
        Multi-line report string.
    """
    n = len(motif_pairs)
    n_clusters = len(set(family_labels))
    duration = max(t for pair in motif_pairs for t in pair) if n else 0

    lines = []
    lines.append('=' * 72)
    lines.append('ARC PLOT INTERPRETATION REPORT')
    lines.append('=' * 72)
    lines.append('')
    lines.append(f'Total arcs:        {n}')
    lines.append(f'Motif families:    {n_clusters}')
    lines.append(f'Duration covered:  {_format_time(duration)}')
    lines.append('')

    # --- Classify each arc ---
    within_mov = 0
    cross_mov = 0
    mov_pair_counts: Dict[str, int] = Counter()
    per_cluster: Dict[int, List[int]] = defaultdict(list)

    arc_data = []
    for i, ((t1, t2), frag, label) in enumerate(
            zip(motif_pairs, motif_fragments, family_labels)):
        m1_idx, m1_name = _movement_at(t1, movement_times_sec, movement_names)
        m2_idx, m2_name = _movement_at(t2, movement_times_sec, movement_names)
        span = abs(t2 - t1)
        is_cross = m1_idx != m2_idx

        if is_cross:
            cross_mov += 1
        else:
            within_mov += 1

        mov_pair_counts[_movement_pair_key(m1_idx, m2_idx)] += 1
        per_cluster[label].append(i)

        arc_data.append({
            't1': t1, 't2': t2, 'span': span,
            'm1_idx': m1_idx, 'm2_idx': m2_idx,
            'm1_name': m1_name, 'm2_name': m2_name,
            'frag': frag, 'label': label, 'cross': is_cross,
        })

    # --- Summary ---
    lines.append('--- Arc Distribution ---')
    lines.append(f'  Within-movement: {within_mov} ({within_mov/max(n,1):.0%})')
    lines.append(f'  Cross-movement:  {cross_mov} ({cross_mov/max(n,1):.0%})')
    lines.append('')

    spans = [a['span'] for a in arc_data]
    if spans:
        lines.append(f'  Arc span: min={_format_time(min(spans))}, '
                     f'median={_format_time(np.median(spans))}, '
                     f'max={_format_time(max(spans))}')
    lines.append('')

    lines.append('--- Movement-Pair Connections ---')
    for key in sorted(mov_pair_counts, key=mov_pair_counts.get, reverse=True):
        cnt = mov_pair_counts[key]
        lines.append(f'  Mov {key}: {cnt} arcs')
    lines.append('')

    # --- Per-cluster profiles ---
    lines.append('=' * 72)
    lines.append('MOTIF FAMILY PROFILES')
    lines.append('=' * 72)
    lines.append('')

    for cluster_id in sorted(per_cluster):
        indices = per_cluster[cluster_id]
        cluster_arcs = [arc_data[i] for i in indices]

        lines.append(f'--- Family {cluster_id} ({len(indices)} arcs) ---')

        rep_frag = cluster_arcs[0]['frag']
        lines.append(f'  Representative interval pattern: {list(rep_frag)}')

        cluster_spans = [a['span'] for a in cluster_arcs]
        lines.append(f'  Span: min={_format_time(min(cluster_spans))}, '
                     f'median={_format_time(np.median(cluster_spans))}, '
                     f'max={_format_time(max(cluster_spans))}')

        n_cross = sum(1 for a in cluster_arcs if a['cross'])
        lines.append(f'  Cross-movement: {n_cross}/{len(indices)}')

        mov_dist = Counter()
        for a in cluster_arcs:
            mov_dist[a['m1_name']] += 1
            mov_dist[a['m2_name']] += 1
        lines.append('  Movement distribution (endpoint counts):')
        for name in movement_names:
            cnt = mov_dist.get(name, 0)
            bar = '#' * min(cnt, 40)
            lines.append(f'    {name:30s} {cnt:3d}  {bar}')

        # Transformation analysis: compare first fragment to others in cluster
        if len(cluster_arcs) > 1:
            transforms = Counter()
            for a in cluster_arcs[1:min(20, len(cluster_arcs))]:
                t = label_transformation(list(rep_frag), list(a['frag']))
                transforms[t] += 1
            lines.append('  Transformation types (vs representative):')
            for t_type, cnt in transforms.most_common():
                lines.append(f'    {t_type:30s} {cnt}')

        lines.append('')

    # --- Cross-movement arcs (the most interesting findings) ---
    cross_arcs = [a for a in arc_data if a['cross']]
    if cross_arcs:
        lines.append('=' * 72)
        lines.append('CROSS-MOVEMENT RECURRENCES (most analytically interesting)')
        lines.append('=' * 72)
        lines.append('')

        cross_arcs.sort(key=lambda a: a['span'])

        # Group by movement pair
        by_mov_pair: Dict[str, List] = defaultdict(list)
        for a in cross_arcs:
            key = _movement_pair_key(a['m1_idx'], a['m2_idx'])
            by_mov_pair[key].append(a)

        for key in sorted(by_mov_pair, key=lambda k: len(by_mov_pair[k]),
                          reverse=True):
            arcs = by_mov_pair[key]
            lines.append(f'--- Mov {key} ({len(arcs)} arcs) ---')

            # Show up to 10 shortest-span arcs (closest matches)
            for a in arcs[:10]:
                lines.append(
                    f'  {_format_time(a["t1"])} ({a["m1_name"][:12]}) <-> '
                    f'{_format_time(a["t2"])} ({a["m2_name"][:12]})  '
                    f'span={_format_time(a["span"])}  '
                    f'family={a["label"]}  '
                    f'intervals={list(a["frag"][:6])}{"..." if len(a["frag"])>6 else ""}')
            if len(arcs) > 10:
                lines.append(f'  ... and {len(arcs)-10} more')
            lines.append('')

    # --- Densest time regions ---
    lines.append('=' * 72)
    lines.append('DENSEST ARC REGIONS (hotspots of motivic activity)')
    lines.append('=' * 72)
    lines.append('')

    if arc_data:
        all_endpoints = []
        for a in arc_data:
            all_endpoints.extend([a['t1'], a['t2']])
        all_endpoints.sort()
        bin_width = 30.0
        bins = np.arange(0, duration + bin_width, bin_width)
        counts, _ = np.histogram(all_endpoints, bins=bins)
        top_bins = np.argsort(counts)[-5:][::-1]
        for bi in top_bins:
            t_start = bins[bi]
            t_end = bins[bi + 1]
            _, mov = _movement_at(t_start, movement_times_sec, movement_names)
            lines.append(
                f'  {_format_time(t_start)}-{_format_time(t_end)}: '
                f'{counts[bi]} endpoints  ({mov})')

    lines.append('')
    return '\n'.join(lines)


def format_cross_part_report(
        cross_part_pairs: List[Tuple[float, float]],
        cross_part_details: List[Dict],
        movement_times_sec: List[float],
        movement_names: List[str],
) -> str:
    """Summarise cross-part (theme-migration) motif discoveries."""
    if not cross_part_pairs:
        return ''

    lines = []
    lines.append('=' * 72)
    lines.append('CROSS-PART MOTIF TRACKING')
    lines.append('=' * 72)
    lines.append('')
    lines.append(f'Total cross-part matches: {len(cross_part_pairs)}')
    lines.append('')

    pair_counts: Dict[str, int] = Counter()
    pair_examples: Dict[str, List] = defaultdict(list)

    for (t1, t2), detail in zip(cross_part_pairs, cross_part_details):
        key = f'{detail["part_a"]} -> {detail["part_b"]}'
        pair_counts[key] += 1
        _, m1 = _movement_at(t1, movement_times_sec, movement_names)
        _, m2 = _movement_at(t2, movement_times_sec, movement_names)
        pair_examples[key].append({
            't1': t1, 't2': t2, 'm1': m1, 'm2': m2,
            'frag_a': detail['frag_a'], 'frag_b': detail['frag_b'],
            'distance': detail['distance'],
        })

    lines.append('--- Theme Migration Paths ---')
    for key in sorted(pair_counts, key=pair_counts.get, reverse=True):
        cnt = pair_counts[key]
        lines.append(f'  {key}: {cnt} matches')

        examples = sorted(pair_examples[key], key=lambda x: x['distance'])
        for ex in examples[:5]:
            lines.append(
                f'    {_format_time(ex["t1"])} ({ex["m1"][:12]}) <-> '
                f'{_format_time(ex["t2"])} ({ex["m2"][:12]})  '
                f'dist={ex["distance"]:.2f}  '
                f'pattern={list(ex["frag_a"][:6])}{"..." if len(ex["frag_a"])>6 else ""}')
        if cnt > 5:
            lines.append(f'    ... and {cnt - 5} more')
        lines.append('')

    lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    pairs = [(10.0, 50.0), (100.0, 1500.0), (200.0, 250.0)]
    frags = [(2, 2, 1, -1, 3, 2, 1, 0), (2, 2, 1, -1, 2, 2, 1, -1),
             (3, 1, -2, 1, 3, 1, -2, 1)]
    labels = [0, 0, 1]
    mov_times = [0.0, 500.0, 1100.0, 1800.0]
    mov_names = ['I', 'II', 'III', 'IV']

    report = interpret_arcs(pairs, frags, labels, mov_times, mov_names)
    print(report)
    print('interpret_arcs test passed.')
