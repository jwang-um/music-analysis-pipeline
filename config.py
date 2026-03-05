# ============================================================
#  Music Analysis Pipeline — Configuration
# ============================================================
#
#  Fill in the fields below for your piece.
#  See config_shostakovich.py for a fully-worked example.
#
#  For a single-file piece (one WAV + one MIDI, no movement splits),
#  just use single-element lists and set MOVEMENT_NAMES to [''].
# ============================================================

# --- Piece metadata ---
PIECE_TITLE = 'Shostakovich Op.47'          # Used in plot titles & report headers

# --- Input files (one per movement, in order) ---
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

# --- Part name normalisation (optional) ---
# Maps variant instrument names across movements to a single canonical name.
# Set to {} if your MIDI files already use consistent part names.
PART_NAME_MAP = {
    'Violins':       'Violins 1',
    'Violin':        'Violins 1',
    'Grand Piano':   'Piano',
}

# --- Audio parameters ---
SR              = 22050       # Sample rate (Hz)
HOP_LENGTH      = 512         # CQT hop length (~23 ms at 22050 Hz)
N_BINS          = 84          # CQT frequency bins (7 octaves)
BINS_PER_OCT    = 12          # Semitone resolution

# --- Analysis parameters ---
MP_WINDOW_SIZES = [8, 10]     # Note-count windows for Matrix Profile motif discovery
NMF_COMPONENTS  = 8           # Number of NMF textural components
DTW_THRESHOLD   = 2.5         # DTW clustering linkage cutoff
SEG_K           = 8           # Laplacian eigenvectors for segmentation
