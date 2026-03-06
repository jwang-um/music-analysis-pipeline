# ============================================================
#  DEMO CONFIG — Shostakovich Symphony No. 5 in D minor, Op. 47
# ============================================================
#
#  This is a reference configuration for a large-scale orchestral
#  symphony with four movements. It demonstrates every option the
#  pipeline accepts and can be loaded directly into the GUI via
#  "Load Config File..." on the Setup tab.
#
#  To analyse a different piece, copy this file, rename it, and
#  adjust the paths and parameters below. See config.py for a
#  minimal template with inline documentation.
#
#  MIDI and audio files are NOT included in the repository.
#  See README.md § "Preparing input data" for where to obtain
#  them and how the data/ directory should be structured.
# ============================================================

# Display name used in plot titles, report headers, and the GUI
# title bar. Can be any arbitrary string.
PIECE_TITLE = 'Shostakovich — Symphony No. 5 in D minor, Op. 47'

# ── Input files ──────────────────────────────────────────────
# One MIDI file and one audio file per movement, in performance
# order. The pipeline stitches them into a single timeline; list
# position determines movement numbering, so the order matters.
#
# Paths are relative to the working directory (usually the repo
# root). Absolute paths also work.
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

# Human-readable movement labels for plots and reports.
# Must be the same length as MIDI_PATHS / AUDIO_PATHS.
MOVEMENT_NAMES = [
    'I — Moderato',
    'II — Allegretto',
    'III — Largo',
    'IV — Allegro non troppo',
]

# ── Part name normalisation ──────────────────────────────────
# MIDI part names often vary between movements (different
# transcribers, divisi conventions, etc.). This map merges
# variant names into a single canonical name so the pipeline
# can track each instrument across the entire symphony.
#
# Keys   = variant names that appear in the MIDI files
# Values = canonical name to normalise to
#
# Set to {} if your MIDI files already use consistent names.
#
# Shostakovich 5 specifics:
#   - Mov III (Largo) labels the first violins simply "Violins"
#     instead of "Violins 1" / "Violins 2".
#   - Mov III–IV use "Grand Piano" where Mov I uses "Piano".
#   - Solo "Violin" passages in Mov I–II fold into "Violins 1".
PART_NAME_MAP = {
    'Violins':       'Violins 1',
    'Violin':        'Violins 1',
    'Grand Piano':   'Piano',
}

# ── Audio parameters ─────────────────────────────────────────
# These control the Constant-Q Transform (CQT) used for the
# Self-Similarity Matrix, NMF, and chroma features. The defaults
# work well for most orchestral recordings; change only if you
# have a specific reason (e.g. very low-pitched solo instrument).
SR              = 22050   # Sample rate in Hz (audio is resampled to this)
HOP_LENGTH      = 512     # CQT hop length in samples (~23 ms at 22050 Hz)
N_BINS          = 84      # Frequency bins — 84 = 7 octaves of semitones
BINS_PER_OCT    = 12      # Bins per octave (12 = semitone resolution)

# ── Analysis parameters ──────────────────────────────────────
# MP_WINDOW_SIZES: note-count windows for Matrix Profile motif
#   discovery. Each value defines a motif length (in notes) to
#   search for. Larger windows find longer recurring patterns;
#   smaller windows find short melodic cells. Using [8, 10]
#   captures both phrase-level and sub-phrase-level recurrences.
MP_WINDOW_SIZES = [8, 10]

# NMF_COMPONENTS: number of Non-negative Matrix Factorisation
#   components. Each component captures a distinct spectral
#   texture (e.g. brass chorale, string tremolo, woodwind solo).
#   8 is a good starting point for a full orchestral work; use
#   fewer for chamber music, more for dense late-Romantic scores.
NMF_COMPONENTS  = 8

# DTW_THRESHOLD: Dynamic Time Warping distance cutoff for
#   agglomerative clustering of discovered motifs. Lower values
#   produce more, smaller motif families; higher values merge
#   loosely related patterns into fewer families.
DTW_THRESHOLD   = 2.5

# SEG_K: number of eigenvectors for spectral clustering of the
#   Self-Similarity Matrix. Determines how many structural
#   sections the piece is divided into. For a four-movement
#   symphony, 8 typically captures the major formal divisions.
SEG_K           = 8
