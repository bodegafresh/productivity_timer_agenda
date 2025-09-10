from __future__ import annotations
import sys, os, math, wave, struct, tempfile
from pathlib import Path

# Try platform-specific first, then fallback to simpleaudio if installed
def _win_beep(freq=880, dur_ms=200):
    try:
        import winsound
        winsound.Beep(int(freq), int(dur_ms))
        return True
    except Exception:
        return False

def _mac_beep():
    try:
        # macOS system beep
        from AppKit import NSBeep  # type: ignore
        NSBeep()
        return True
    except Exception:
        return False

def _simpleaudio_play(freq=880, dur_ms=200):
    try:
        import simpleaudio as sa
        sample_rate = 44100
        t = int(sample_rate * (dur_ms/1000.0))
        audio = bytearray()
        for i in range(t):
            val = int(32767.0 * 0.25 * math.sin(2*math.pi*freq*(i/sample_rate)))
            audio += struct.pack('<h', val)
        # mono, 2 bytes per sample
        play_obj = sa.play_buffer(bytes(audio), 1, 2, sample_rate)
        play_obj.wait_done()
        return True
    except Exception:
        return False

def play(event: str):
    """
    event in {'start','end','alert'}
    """
    # Map simple tones per event
    if event == "start":
        # quick rising chirp feel
        if _win_beep(880, 120): return
        if _mac_beep(): return
        if _simpleaudio_play(880, 120): return
    elif event == "end":
        if _win_beep(523, 220): return  # C5
        if _mac_beep(): return
        if _simpleaudio_play(523, 220): return
    else:  # alert / default
        if _win_beep(988, 150): return  # B5
        if _mac_beep(): return
        if _simpleaudio_play(988, 150): return
    # final fallback: no-op
    return
