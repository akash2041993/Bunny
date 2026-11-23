"""Bunny's ears: speech-to-text with faster-whisper, fully offline on this PC.
The model is included in the installer (or downloaded once on first start when running from source)."""
import io
import os
import threading
import wave

from . import config

_model = None
_lock = threading.Lock()
status = {"ready": False, "error": None, "model": None}

PROMPT = "बनी, Bunny. फोटोशॉप खोलो, क्रोम बंद करो, प्रीमियर प्रो, यूट्यूब, कंप्यूटर।"


def _model_path(size):
    for root in (os.path.join(config.bundle_dir(), "models"), os.path.join(config.app_dir(), "models")):
        p = os.path.join(root, f"whisper-{size}")
        if os.path.isfile(os.path.join(p, "model.bin")):
            return p
    return None


def load(size=None):
    global _model
    size = size or config.load().get("whisper_model", "small")
    with _lock:
        if _model is not None and status["model"] == size:
            return _model
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            status["error"] = f"faster-whisper is not installed: {e}"
            raise
        path = _model_path(size)
        if not path:  # first start from source: download once into Bunny's folder
            path = size
        try:
            _model = WhisperModel(path, device="cpu", compute_type="int8",
                                  download_root=os.path.join(config.app_dir(), "models", "hf"),
                                  cpu_threads=max(2, (os.cpu_count() or 4) - 1))
        except Exception as e:  # noqa: BLE001
            status["error"] = str(e)
            raise
        status.update(ready=True, error=None, model=size)
        return _model


def wav_to_float(data):
    """16-bit mono WAV bytes -> float32 numpy array at the WAV's own rate (the face page sends 16 kHz)."""
    import numpy as np
    with wave.open(io.BytesIO(data), "rb") as w:
        rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError("WAV must be 16-bit")
    a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    if rate != 16000:  # simple resample
        n = int(len(a) * 16000 / rate)
        a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)
    return a


def _detect(model, audio):
    """'en' or 'hi'. Whisper often labels Hindi speech as Urdu, so anything not English counts as Hindi."""
    try:
        lang, prob, _all = model.detect_language(audio)
    except Exception:  # noqa: BLE001 - older faster-whisper
        _segs, info = model.transcribe(audio[:16000 * 10], beam_size=1, language=None)
        lang, prob = info.language, info.language_probability
    return "en" if lang == "en" and prob >= 0.5 else "hi"


def transcribe(wav_bytes):
    """Returns (spoken text, 'hi' | 'en'). Text is '' for noise."""
    cfg = config.load()
    model = load(cfg.get("whisper_model"))
    audio = wav_to_float(wav_bytes)
    if len(audio) < 16000 * 0.25:
        return "", "hi"
    lang = cfg.get("stt_language") or "auto"
    if lang == "auto":
        lang = _detect(model, audio)
    prompt = PROMPT if lang == "hi" else "Bunny, open Photoshop, close Chrome, Premiere Pro, YouTube."
    segments, _info = model.transcribe(audio, language=lang, beam_size=3, vad_filter=True,
                                       condition_on_previous_text=False, initial_prompt=prompt,
                                       no_speech_threshold=0.6, temperature=0.0)
    parts = []
    for s in segments:
        if s.no_speech_prob > 0.7 and s.avg_logprob < -0.8:
            continue
        parts.append(s.text.strip())
    text = " ".join(p for p in parts if p).strip()
    # whisper sometimes "hears" its own prompt or stock phrases in noise
    if text.strip(" ।.,") in ("", PROMPT.strip(" ।"), prompt.strip(" ."), "Thank you", "धन्यवाद", "सब्सक्राइब करें"):
        return "", lang
    return text, lang
