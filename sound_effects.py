import numpy as np
import simpleaudio as sa

# calculate note frequencies
A_freq = 440
E_freq = A_freq * 2 ** (7 / 12)
E_low_freq = E_freq / 2

# get timesteps for each sample, T is note duration in seconds
sample_rate = 44100
T = 0.12
t = np.linspace(0, T, int(T * sample_rate), False)

# generate sine wave notes
A_note = np.sin(A_freq * t * 2 * np.pi)
E_low_note = np.sin(E_low_freq * t * 2 * np.pi)
E_note = np.sin(E_freq * t * 2 * np.pi)

cached_fourth = None
cached_fifth = None

def downward_perfect_fourth():
    global cached_fourth
    if cached_fourth is None:
        # Create interval
        audio = np.zeros((44100, 2))
        n = len(t)
        audio[0: n, 0] += A_note
        audio[0: n, 1] += A_note
        audio[n: 2 * n, 0] += E_low_note
        audio[n: 2 * n, 1] += E_low_note
        # convert to 16-bit data
        audio *= 32767 / np.max(np.abs(audio))
        cached_fourth = audio.astype(np.int16)
    # play
    sa.play_buffer(cached_fourth, 2, 2, sample_rate)

def perfect_fifth():
    global cached_fifth
    if cached_fifth is None:
        # Create interval
        audio = np.zeros((44100, 2))
        n = len(t)
        audio[0: n, 0] += A_note
        audio[0: n, 1] += A_note
        audio[n: 2 * n, 0] += E_note
        audio[n: 2 * n, 1] += E_note
        # Convert to 16-bit data
        audio *= 32767 / np.max(np.abs(audio))
        cached_fifth = audio.astype(np.int16)
    # Play
    sa.play_buffer(cached_fifth, 2, 2, sample_rate)
