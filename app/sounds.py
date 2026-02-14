from __future__ import annotations
import sys, os, math, wave, struct, tempfile, shutil, subprocess, threading

def _gen_sequence_wav(path: str, sequence: list[tuple[float, int, str]], volume: float = 0.8):
    sample_rate = 44100
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        
        for freq, dur_ms, wave_type in sequence:
            n = int(sample_rate * (dur_ms / 1000.0))
            # Transiciones más suaves para evitar clics ruidosos
            fade_size = min(400, n // 4) 
            
            for i in range(n):
                t = i / sample_rate
                if wave_type == "square":
                    val = 32767.0 * volume * (1 if math.sin(2 * math.pi * freq * t) > 0 else -1)
                elif wave_type == "saw": # Onda de sierra para más carácter (estilo sintetizador)
                    val = 32767.0 * volume * (2 * (t * freq - math.floor(0.5 + t * freq)))
                else: # sine
                    val = 32767.0 * volume * math.sin(2 * math.pi * freq * t)
                
                # Envolvente de volumen para naturalidad
                if i < fade_size: val *= (i / fade_size)
                if i > n - fade_size: val *= (n - i) / fade_size
                
                w.writeframes(struct.pack("<h", int(val)))

def _execute_play(sequence):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    try:
        _gen_sequence_wav(tmp.name, sequence)
        for player in ("paplay", "aplay", "afplay", "ffplay"):
            if shutil.which(player):
                subprocess.run([player, tmp.name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                return
    finally:
        try: os.unlink(tmp.name)
        except: pass

def play(event: str):
    # Secuencias inspiradas en hitos culturales (Base rítmica 3-4 segundos)
    mapping = {
        # "El despertar": Inspirado en la obertura de '2001: Odisea del Espacio' (Zarathustra)
        # Una quinta justa ascendente que simboliza el amanecer y el potencial humano.
        "work_start": [
            (261, 800, "sine"),   # Do (Raíz)
            (392, 800, "sine"),   # Sol (Quinta - Estabilidad)
            (523, 1500, "saw")    # Do Octava (Triunfo/Acción)
        ],
        
        # "La Meditación": Inspirado en el minimalismo de Brian Eno.
        # Sonidos descendentes y suaves para bajar el cortisol.
        "rest_start": [
            (523, 1000, "sine"), (440, 1000, "sine"), (349, 1500, "sine")
        ],
        
        # "El Ritual": Ataque rítmico inspirado en Kraftwerk (el ritmo de la máquina).
        # Secuencia rápida de 3 segundos para el Tabata agresivo.
        "tabata_work": [
            (880, 100, "square"), (0, 50, "sine"),
            (880, 100, "square"), (0, 50, "sine"),
            (880, 100, "square"), (0, 50, "sine"),
            (1760, 600, "saw"),   # ¡DALE! Impacto inicial
            (1318, 400, "saw"),   # Nota de apoyo
            (1760, 1500, "saw")   # Sostenido épico
        ],

        "tabata_victory": [
            (261, 800, "saw"),   # Do
            (349, 800, "saw"),   # Fa
            (392, 800, "saw"),   # Sol
            (523, 2600, "saw"),  # Do agudo final (Mantenido)
        ],
        
        # "Respiro": Dos tonos de campana tibetana artificial.
        "tabata_rest": [(659, 1500, "sine"), (523, 1500, "sine")],
        
        # "Llamado a la Conciencia": Frecuencia 432Hz (espiritual) alternada.
        "agenda_alert": [
            (432, 600, "saw"), (0, 100, "sine"),
            (432, 600, "saw"), (0, 100, "sine"),
            (544, 1200, "sine")
        ]
    }
    
    # Fallback si el evento no existe
    sequence = mapping.get(event, [(440, 1000, "sine")])
    threading.Thread(target=_execute_play, args=(sequence,), daemon=True).start()