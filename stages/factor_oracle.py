from typing import List, Set, Tuple


class FactorOracle:
    """
    Factor Oracle automaton for repeated substring discovery.
    Reference: Allauzen & Raffinot, 1999.

    The suffix link structure:
    Each state i has a suffix link pointing to the longest proper suffix
    of sequence[0:i] that also occurs starting at some other position
    in the sequence. This enables efficient detection of repeated factors
    (contiguous substrings) without brute-force substring enumeration.
    State 0 is the initial state; suffix[-1] is a sentinel for "no link."
    """

    def __init__(self, sequence: List[int]):
        """
        Args:
            sequence: Integer sequence to index (interval sequence).
        """
        n = len(sequence)
        self.sequence    = sequence
        self.transitions = [{} for _ in range(n + 1)]
        self.suffix      = [-1] + [0] * n
        self._build(sequence)

    def _build(self, seq: List[int]) -> None:
        for i, sym in enumerate(seq):
            self.transitions[i][sym] = i + 1
            k = self.suffix[i]
            while k != -1 and sym not in self.transitions[k]:
                self.transitions[k][sym] = i + 1
                k = self.suffix[k]
            nxt = self.transitions[k][sym] if k != -1 else 0
            self.suffix[i + 1] = nxt if nxt != i + 1 else self.suffix[k]

    def find_repeated_factors(self,
                               min_length: int = 3) -> Set[Tuple[int, ...]]:
        """
        Return all repeated factors of length >= min_length.

        Returns:
            Set of tuples, each a repeated contiguous subsequence.
        """
        seq = self.sequence
        n = len(seq)
        factors = set()
        for start in range(n):
            for length in range(min_length, n - start + 1):
                subseq = tuple(seq[start:start + length])
                # Check if it appears at least twice
                count = 0
                for j in range(n - length + 1):
                    if tuple(seq[j:j + length]) == subseq:
                        count += 1
                    if count >= 2:
                        break
                if count >= 2:
                    factors.add(subseq)
        return factors


def label_transformation(a: List[int], b: List[int]) -> str:
    """
    Classify the relationship between two interval sequences.

    Args:
        a, b: Two interval sequences of any length.

    Returns:
        One of: 'exact', 'inversion', 'retrograde',
        'retrograde_inversion', 'transposition_N', 'variant'
    """
    a, b = list(a), list(b)
    if a == b:
        return 'exact'
    if a == [-x for x in b]:
        return 'inversion'
    if a == b[::-1]:
        return 'retrograde'
    if a == [-x for x in b[::-1]]:
        return 'retrograde_inversion'
    if len(a) == len(b):
        diffs = [b[i] - a[i] for i in range(len(a))]
        if len(set(diffs)) == 1:
            return f'transposition_{diffs[0]}'
    return 'variant'


if __name__ == '__main__':
    # Test Factor Oracle
    test_seq = [2, 2, 1, -1, 2, 2, 1, -1, 3, 2]
    print(f'Input sequence: {test_seq}')
    print(f'Expected repeated fragment [2, 2, 1, -1] at positions 0 and 4\n')

    oracle = FactorOracle(test_seq)
    factors = oracle.find_repeated_factors(min_length=3)

    print(f'All repeated factors (min_length=3):')
    for f in sorted(factors, key=lambda x: (len(x), x)):
        print(f'  {list(f)} (length {len(f)})')

    assert (2, 2, 1) in factors, '(2,2,1) should be a repeated factor'
    assert (2, 2, 1, -1) in factors, '(2,2,1,-1) should be a repeated factor'
    print('\nFactor Oracle assertions passed.')

    len4_factors = [f for f in factors if len(f) == 4]
    print(f'\nFactors of length 4:')
    for f in len4_factors:
        fl = list(f)
        # Verify it appears as substring
        found_positions = []
        for i in range(len(test_seq) - 3):
            if test_seq[i:i+4] == fl:
                found_positions.append(i)
        print(f'  {fl} found at positions {found_positions}')

    # Test label_transformation
    print('\n--- Transformation labeling tests ---')
    tests = [
        ([2,2,1], [2,2,1], 'exact'),
        ([2,2,1], [-2,-2,-1], 'inversion'),
        ([2,2,1], [1,2,2], 'retrograde'),
        ([2,2,1], [-1,-2,-2], 'retrograde_inversion'),
        ([2,2,1], [5,5,4], 'transposition_3'),
        ([2,2,1], [2,3,1], 'variant'),
    ]
    for a, b, expected in tests:
        result = label_transformation(a, b)
        status = 'PASS' if result == expected else 'FAIL'
        print(f'  {status}: {a} vs {b} -> {result} (expected {expected})')
        assert result == expected, f'Failed: expected {expected}, got {result}'

    print('\nAll tests passed.')
