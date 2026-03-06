This is a WIP. Algorithms still need development for accuracy improvements.
# Music Analysis Pipeline

An unsupervised music analysis toolkit that discovers recurring motifs, structural sections, and textural patterns in multi-movement orchestral works. Combines MIDI score analysis with audio feature extraction to produce interactive visualizations and a rendered score with analysis overlays.

Built for and tested on Shostakovich's Symphony No. 5, but designed to work with any multi-movement piece given paired MIDI and audio files.

## Features

- **Motif Discovery** — Matrix Profile (STUMPY) identifies recurring melodic patterns within and across instrument parts, clustered into families via DTW + agglomerative clustering
- **Cross-Part Motif Tracking** — Detects thematic migration between instrument families using STUMPY AB-join
- **Structural Segmentation** — Spectral clustering on a chroma self-similarity matrix discovers formal sections (sonata-form regions, scherzo/trio, etc.)
- **Textural Analysis** — Non-negative Matrix Factorization decomposes the CQT spectrogram into interpretable textural components with per-movement activation profiles
- **Interactive Visualizations** — Plotly-powered arc plots, SSM heatmaps, and NMF activation maps with hover tooltips, zoom, and click-to-copy timestamps
- **Interactive Score** — Verovio WebAssembly renders the combined MusicXML score with toggleable analysis overlays (motif highlights, section boundaries, NMF peaks, cross-part markers)
- **Validation** — Automated checks for segmentation boundary alignment, NMF internal consistency, and NMF/SSM cross-agreement

## Architecture

```
music_analysis/
├── run_gui.py              # GUI entry point
├── main.py                 # CLI entry point
├── pipeline.py             # Core analysis engine (used by both CLI and GUI)
├── config.py               # Configuration template
├── config_shostakovich.py  # Worked example for Shostakovich Op. 47
│
├── stages/                 # Pure computation — no I/O or plotting
│   ├── stitch.py           #   Combine per-movement MIDI + audio
│   ├── alignment.py        #   Tempo map and beat-to-seconds conversion
│   ├── midi_parse.py       #   MIDI → interval sequences via music21
│   ├── matrix_profile.py   #   STUMPY motif discovery
│   ├── cross_part.py       #   Cross-part motif tracking (AB-join)
│   ├── clustering.py       #   DTW + agglomerative motif clustering
│   ├── audio_features.py   #   CQT, chroma, SSM, beat tracking
│   ├── segmentation.py     #   Spectral clustering for form
│   ├── nmf_texture.py      #   NMF textural decomposition
│   ├── interpret_*.py      #   Human-readable report generation
│   └── validate.py         #   Automated validation checks
│
├── viz/                    # Visualization generators
│   ├── plotly_plots.py     #   Interactive Plotly HTML figures
│   ├── arc_plot.py         #   Static matplotlib arc plot
│   ├── recurrence_matrix.py#   Static matplotlib SSM
│   └── nmf_activations.py  #   Static matplotlib NMF heatmap
│
├── ui/                     # PySide6 desktop application
│   ├── app.py              #   Main window and tab layout
│   ├── theme.py            #   Color scheme and QSS stylesheet
│   ├── worker.py           #   Background analysis thread
│   ├── utils.py            #   Shared UI utilities
│   └── widgets/            #   Tab implementations
│       ├── setup_tab.py    #     Full configuration + config file loader
│       ├── overview_tab.py #     Summary statistics and text reports
│       ├── score_tab.py    #     Interactive Verovio score viewer
│       ├── arc_tab.py      #     Arc plot + motif recurrence table
│       ├── ssm_tab.py      #     SSM heatmap + form chart
│       ├── nmf_tab.py      #     NMF heatmap + component cards
│       ├── validation_tab.py#    Validation results
│       └── toolbar.py      #     Run button and progress bar
│
├── build.py                # PyInstaller build helper
├── music_analysis.spec     # PyInstaller spec file
└── .github/workflows/
    └── build.yml           # CI: automated Windows + macOS builds
```

## Installation

### From source (recommended for development)

Requires Python 3.10+.

```bash
git clone https://github.com/jwang-um/music-analysis-pipeline.git
cd music-analysis-pipeline
pip install -r requirements.txt
```

### Pre-built executables

Download the latest release from the [Releases](https://github.com/jwang-um/music-analysis-pipeline/releases) page. Extract the zip and run `MusicAnalysis.exe` (Windows) or `MusicAnalysis.app` (macOS). No Python installation required.

## Usage

### Desktop GUI

```bash
python run_gui.py
```

1. Open the **Setup** tab
2. Click **Load Config File** to load a `.py` config (e.g. `config_shostakovich.py`), or manually add MIDI/WAV files and configure parameters
3. Click **Run Analysis** in the toolbar
4. Browse results across the **Overview**, **Score**, **Arc Plot**, **SSM**, **NMF**, and **Validation** tabs

### Command line

```bash
# Edit config.py with your file paths and parameters, then:
python main.py
```

Produces text reports (`output_*_report.txt`) and figures (`output_*.png`) in the working directory.

## Preparing input data

The pipeline analyzes a piece by combining information from two sources — a MIDI score and an audio recording — for each movement. You need to supply both.

Audio and MIDI files are **not included in this repository** (they are gitignored due to size). You must provide your own.

### What you need

For each movement of the piece you want to analyze, prepare:

1. **A MIDI file** (`.mid`) containing the full orchestral score with separate tracks per instrument. These are used for motif extraction, part identification, interval sequence computation, and interactive score rendering.

2. **An audio file** (`.wav`) of a performance of the same movement. These are used for CQT spectrogram computation, chroma features, beat tracking, self-similarity matrix construction, and NMF textural analysis.

The MIDI and audio files must correspond to the same movements and be listed in the same order.

### Where to get them

| Source | MIDI | Audio |
|--------|------|-------|
| [IMSLP](https://imslp.org/) | Many public-domain scores available as MIDI exports | Some public-domain recordings |
| [MuseScore](https://musescore.com/) | Community-uploaded scores (export as MIDI) | — |
| Notation software (Sibelius, Finale, MuseScore) | Export your own scores to MIDI | — |
| CD / streaming rips | — | Record or rip your own WAV files |

### MIDI requirements

- **Multi-track**: Each instrument should be on its own MIDI track (not a single merged piano-roll). The pipeline parses individual parts for motif discovery.
- **One file per movement**: If your MIDI has all movements in one file, split it into separate files per movement.
- **Standard MIDI format**: Type 0 or Type 1 `.mid` files. music21 handles the parsing.

### File layout

Create a `data/` directory and place your files there:

```
data/
├── mov1.mid    # Movement I  — MIDI score
├── mov1.wav    # Movement I  — audio recording
├── mov2.mid    # Movement II
├── mov2.wav
├── mov3.mid    # Movement III
├── mov3.wav
├── mov4.mid    # Movement IV
└── mov4.wav
```

Then either edit `config.py` to point to these paths, or create your own config file (see [`config_shostakovich.py`](config_shostakovich.py) for a complete example). In the GUI, you can load a config file from the Setup tab or add files manually.

### Part name normalization

Different movements may use different names for the same instrument (e.g. "Violins" vs "Violin" vs "Violins 1", or "Grand Piano" vs "Piano"). The `PART_NAME_MAP` config option lets you map variant names to a single canonical name so the pipeline can track parts across movements. If your MIDI files already use consistent names, set this to `{}`.

## Configuration

All parameters are documented in [`config.py`](config.py). Key settings:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SR` | 22050 | Audio sample rate (Hz) |
| `HOP_LENGTH` | 512 | CQT hop length (~23ms) |
| `N_BINS` | 84 | CQT frequency bins (7 octaves) |
| `MP_WINDOW_SIZES` | [8, 10] | Note-count windows for Matrix Profile |
| `NMF_COMPONENTS` | 8 | Number of NMF textural components |
| `PART_NAME_MAP` | {} | Maps variant instrument names to canonical names |

See [`config_shostakovich.py`](config_shostakovich.py) for a fully worked example.

## Building executables

```bash
pip install pyinstaller
python build.py          # Build only
python build.py --zip    # Build + create distributable zip
python build.py --clean  # Clean previous artifacts first
```

Output is written to `dist/MusicAnalysis/`. The GitHub Actions workflow (`.github/workflows/build.yml`) automates this for Windows and macOS on tagged releases.

## Dependencies

| Package | Role |
|---------|------|
| [music21](https://web.mit.edu/music21/) | MIDI parsing and MusicXML score generation |
| [STUMPY](https://stumpy.readthedocs.io/) | Matrix Profile motif discovery |
| [librosa](https://librosa.org/) | Audio feature extraction (CQT, chroma, beats) |
| [scikit-learn](https://scikit-learn.org/) | NMF, K-means, agglomerative clustering |
| [tslearn](https://tslearn.readthedocs.io/) | DTW distance computation |
| [Plotly](https://plotly.com/python/) | Interactive HTML visualizations |
| [PySide6](https://doc.qt.io/qtforpython/) | Desktop GUI framework (includes QtWebEngine) |
| [Verovio](https://www.verovio.org/) | Score rendering (loaded via CDN at runtime) |

## License

MIT
