"""Greek text-to-speech with the bundled espeak-ng library -> MP3.
Usage: python3 tts_el.py input.txt output.mp3 [speed_wpm]
"""
import ctypes, sys, wave, subprocess, os, tempfile
import espeakng_loader as el

lib = ctypes.CDLL(el.get_library_path())
CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
samples = bytearray()

@CB
def callback(wav, n, events):
    if wav and n > 0:
        samples.extend(ctypes.string_at(wav, n * 2))
    return 0

AUDIO_OUTPUT_SYNCHRONOUS = 0x02
rate = lib.espeak_Initialize(AUDIO_OUTPUT_SYNCHRONOUS, 0, el.get_data_path().encode(), 0)
lib.espeak_SetSynthCallback(callback)
lib.espeak_SetVoiceByName(b"el+f3")
speed = int(sys.argv[3]) if len(sys.argv) > 3 else 135
lib.espeak_SetParameter(1, speed, 0)   # espeakRATE
lib.espeak_SetParameter(6, 8, 0)       # pause between words (x10ms)

text = open(sys.argv[1], encoding="utf-8").read().encode("utf-8")
espeakCHARS_UTF8 = 1
lib.espeak_Synth(ctypes.c_char_p(text), len(text) + 1, 0, 0, 0, espeakCHARS_UTF8, None, None)
lib.espeak_Synchronize()

tmp = tempfile.mktemp(suffix=".wav")
with wave.open(tmp, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(samples))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-ac", "1", "-b:a", "64k", sys.argv[2]], check=True)
os.remove(tmp)
print(sys.argv[2], round(len(samples) / 2 / rate, 1), "s")
