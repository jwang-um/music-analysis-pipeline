import librosa
import numpy as np
from typing import List, Optional, Tuple
from sklearn.preprocessing import normalize


def stitch_audio(audio_paths: List[str],
                 sr: int = 22050) -> Tuple[np.ndarray, List[int]]:
    """
    Load and concatenate per-movement WAV files.

    Args:
        audio_paths: Ordered list of WAV paths, one per movement.
        sr:          Target sample rate; files are resampled if needed.

    Returns:
        Tuple of:
          stitched         : np.ndarray shape (total_samples,)
          movement_samples : list of sample indices where each movement starts
    """
    segments, movement_samples, cursor = [], [], 0
    for path in audio_paths:
        y, _ = librosa.load(path, sr=sr, mono=True)  # shape: (samples,)
        movement_samples.append(cursor)
        segments.append(y)
        cursor += len(y)
    return np.concatenate(segments), movement_samples


def movement_samples_to_frames(movement_samples: List[int],
                                hop_length: int) -> List[int]:
    """
    Convert sample offsets to CQT frame indices.

    Args:
        movement_samples: List of sample indices for movement starts.
        hop_length:       CQT hop length in samples.

    Returns:
        List of CQT frame indices.
    """
    return [s // hop_length for s in movement_samples]


def compute_cqt(y: np.ndarray,
                sr: int = 22050,
                hop_length: int = 512,
                n_bins: int = 84,
                bins_per_octave: int = 12) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute Constant-Q Transform magnitude spectrogram.

    Returns:
        Tuple of:
          C_mag:    CQT magnitude in dB, shape (n_bins, frames).
          C_complex: Complex CQT, retained for downstream chroma reuse.
    """
    C = librosa.cqt(y, sr=sr, hop_length=hop_length,
                    n_bins=n_bins, bins_per_octave=bins_per_octave)
    C_mag = librosa.amplitude_to_db(np.abs(C), ref=np.max)
    return C_mag, C


def beat_sync_cqt(C_mag: np.ndarray, y: np.ndarray,
                  sr: int = 22050,
                  hop_length: int = 512) -> Tuple[np.ndarray, np.ndarray]:
    """
    Reduce CQT to one frame per beat for tractable SSM computation.

    Args:
        C_mag:      CQT magnitude, shape (n_bins, frames).
        y:          Audio signal, shape (samples,).
        sr:         Sample rate.
        hop_length: CQT hop length.

    Returns:
        Tuple of:
          C_sync:      Beat-synchronous CQT, shape (n_bins, n_beats)
          beat_frames: Beat frame positions, shape (n_beats,)
    """
    tempo, beat_frames = librosa.beat.beat_track(
        y=y, sr=sr, hop_length=hop_length)
    C_sync = librosa.util.sync(
        C_mag, beat_frames, aggregate=np.median)  # shape: (n_bins, n_beats)
    return C_sync, beat_frames


def movement_samples_to_beat_frames(movement_samples: List[int],
                                     hop_length: int,
                                     beat_frames: np.ndarray) -> List[int]:
    """
    Map movement sample offsets to beat-synchronous frame indices.

    Args:
        movement_samples: Sample offsets for each movement start.
        hop_length:       CQT hop length.
        beat_frames:      Array of beat frame positions from beat tracking.

    Returns:
        List of beat-sync frame indices closest to each movement boundary.
    """
    mov_cqt_frames = [s // hop_length for s in movement_samples]
    result = []
    for mf in mov_cqt_frames:
        idx = int(np.argmin(np.abs(beat_frames - mf)))
        result.append(idx)
    return result


def compute_chroma_ssm(
    y: np.ndarray,
    sr: int = 22050,
    hop_length: int = 512,
    C_complex: Optional[np.ndarray] = None,
    beat_frames: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute a beat-synchronous chroma SSM.

    If *C_complex* is supplied the chroma is derived from it instead of
    recomputing the CQT.  If *beat_frames* is supplied the beat tracker
    is skipped entirely.
    """
    if beat_frames is None:
        _, beat_frames = librosa.beat.beat_track(
            y=y, sr=sr, hop_length=hop_length)

    if C_complex is not None:
        chroma = librosa.feature.chroma_cqt(
            C=np.abs(C_complex), sr=sr, hop_length=hop_length)
    else:
        chroma = librosa.feature.chroma_cqt(
            y=y, sr=sr, hop_length=hop_length)

    chroma_sync = librosa.util.sync(
        chroma, beat_frames, aggregate=np.median)
    C_norm = normalize(chroma_sync.T, norm='l2')
    ssm = C_norm @ C_norm.T
    return ssm, beat_frames


def compute_ssm(C_mag: np.ndarray) -> np.ndarray:
    """
    Compute cosine self-similarity matrix from CQT magnitude.

    Args:
        C_mag: CQT magnitude, shape (n_bins, frames).

    Returns:
        ssm: Cosine self-similarity matrix, shape (frames, frames).
    """
    C_norm = normalize(C_mag.T, norm='l2')  # shape: (frames, n_bins)
    ssm    = C_norm @ C_norm.T              # shape: (frames, frames)
    return ssm


if __name__ == '__main__':
    # Synthetic test with generated audio
    duration_sec = 2.0
    sr = 22050
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    y_test = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # shape: (samples,)

    # Simulate 4 movements by splitting
    chunk = len(y_test) // 4
    segments = [y_test[i*chunk:(i+1)*chunk] for i in range(4)]
    movement_samples = [i * chunk for i in range(4)]

    y_full = np.concatenate(segments)
    print(f'Total samples: {len(y_full)}, duration: {len(y_full)/sr:.2f}s')
    print(f'Movement sample offsets: {movement_samples}')
    assert len(movement_samples) == 4

    mov_frames = movement_samples_to_frames(movement_samples, hop_length=512)
    print(f'Movement frame offsets: {mov_frames}')

    C_mag = compute_cqt(y_full, sr=sr)
    print(f'CQT shape: {C_mag.shape}')

    ssm = compute_ssm(C_mag)
    print(f'SSM shape: {ssm.shape}')

    print('\nAudio features test passed.')
