PIECE_TITLE = 'Shostakovich — Symphony No. 5 in D minor, Op. 47'

# Movement files — order must match actual movement order.
# The stitching stage uses list position to assign movement numbers;
# swapping files here will silently produce wrong labels throughout.
MIDI_PATHS = [
    'data/mov1.mid',   # I:   Moderato
    'data/mov2.mid',   # II:  Allegretto
    'data/mov3.mid',   # III: Largo
    'data/mov4.mid',   # IV:  Allegro non troppo
]
AUDIO_PATHS = [
    'data/mov1.wav',
    'data/mov2.wav',
    'data/mov3.wav',
    'data/mov4.wav',
]
MOVEMENT_NAMES = [
    'I — Moderato',
    'II — Allegretto',
    'III — Largo',
    'IV — Allegro non troppo',
]

# Normalize part names across movements. Movement 3 (Largo) uses divisi
# names ("Violins" x3 instead of "Violins 1"/"Violins 2") and movement 4
# uses "Grand Piano" instead of "Piano". Map all variants to canonical names
# so stitch_movements() unifies them into continuous cross-movement streams.
PART_NAME_MAP = {
    'Violins':       'Violins 1',   # mov 3 divisi — first occurrence maps to Vln 1
    'Violin':        'Violins 1',   # solo violin in mov 1/2 folds into Vln 1
    'Grand Piano':   'Piano',       # mov 3/4 vs mov 1
}

SR              = 22050       # Audio sample rate
HOP_LENGTH      = 512         # CQT hop length (~23ms at SR=22050)
N_BINS          = 84          # CQT frequency bins (7 octaves)
BINS_PER_OCT    = 12          # Semitone resolution
MP_WINDOW_SIZES = [8, 10]    # Note-count windows for Matrix Profile
NMF_COMPONENTS  = 8           # Number of NMF textural components
DTW_THRESHOLD   = 2.5         # DTW clustering linkage cutoff
SEG_K           = 8           # Laplacian eigenvectors for segmentation
