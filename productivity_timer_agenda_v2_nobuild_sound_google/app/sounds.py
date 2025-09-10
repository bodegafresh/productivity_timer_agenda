from __future__ import annotations
import sys, os, math, wave, struct, tempfile, shutil, subprocess

def _win_beep(freq=880, dur_ms=200):
    try:
        import winsound
        winsound.Beep(int(freq), int(dur_ms))
        return True
    except Exception:
        return False

def _mac_beep():
    try:
        from AppKit import NSBeep  # type: ignore
        NSBeep()
        return True
    except Exception:
        return False

def _gen_tone_wav(path: str, freq=880, dur_ms=200, volume=0.25, sample_rate=44100):
    n = int(sample_rate * (dur_ms/1000.0))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for i in range(n):
            val = int(32767.0 * volume * math.sin(2*math.pi*freq*(i/sample_rate)))
            w.writeframes(struct.pack("<h", val))

def _play_with_system_player(freq=880, dur_ms=200):
    # Try common CLI players if available
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    try:
        _gen_tone_wav(tmp.name, freq=freq, dur_ms=dur_ms)
        for player in ("paplay", "aplay", "ffplay", "afplay"):  # Linux/Pulse, Linux/ALSA, FFmpeg, macOS
            if shutil.which(player):
                try:
                    if player == "ffplay":
                        subprocess.run([player, "-nodisp", "-autoexit", "-loglevel", "quiet", tmp.name], check=True)
                    else:
                        subprocess.run([player, tmp.name], check=True)
                    return True
                except Exception:
                    continue
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
    return False

def play(event: str):
    """
    event in {'start','end','alert'}
    Order: native Windows beep -> native mac beep -> system player (wav) -> no-op.
    """
    mapping = {
        "start": (880, 120),
        "end": (523, 220),   # C5
        "alert": (988, 150), # B5
    }
    freq, dur = mapping.get(event, (880, 120))
    if _win_beep(freq, dur):
        return
    if _mac_beep():
        return
    _play_with_system_player(freq, dur)
