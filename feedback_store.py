"""Simpan feedback 👍/👎 pengguna & sediakan contoh few-shot untuk generasi berikutnya."""
import json
import os
import time

# DATA_DIR bisa diarahkan ke Railway Volume (mis. /data) agar feedback tak hilang saat redeploy.
_DATA_DIR = os.getenv("DATA_DIR") or os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_DATA_DIR, "feedback.json")
MAX_STORE = 50        # batasi ukuran file
MAX_LIKED_EX = 3      # jumlah contoh disukai yang diinjeksikan ke prompt
MAX_DISLIKED_EX = 2   # jumlah contoh dihindari


def _load():
    if not os.path.exists(_PATH):
        return {"liked": [], "disliked": []}
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("liked", [])
        d.setdefault("disliked", [])
        return d
    except Exception:  # noqa: BLE001 — file rusak: mulai bersih
        return {"liked": [], "disliked": []}


def _save(d):
    d["liked"] = d["liked"][-MAX_STORE:]
    d["disliked"] = d["disliked"][-MAX_STORE:]
    os.makedirs(os.path.dirname(_PATH) or ".", exist_ok=True)
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def add_feedback(text: str, style: str, liked: bool):
    """Catat satu feedback. text = versi Facebook (yang paling kaya)."""
    d = _load()
    entry = {"text": text, "style": style, "ts": int(time.time())}
    (d["liked"] if liked else d["disliked"]).append(entry)
    _save(d)


def stats():
    d = _load()
    return len(d["liked"]), len(d["disliked"])


def build_examples_block() -> str:
    """Bangun blok few-shot untuk prompt. Kosong kalau belum ada feedback."""
    d = _load()
    liked = d["liked"][-MAX_LIKED_EX:]
    disliked = d["disliked"][-MAX_DISLIKED_EX:]
    if not liked and not disliked:
        return ""

    parts = []
    if liked:
        parts.append(
            "CONTOH POSTINGAN YANG TERBUKTI DISUKAI AUDIENS.\n"
            "Tiru NADA, STRUKTUR, dan ENERGI-nya — JANGAN menyalin angkanya "
            "(selalu pakai angka dari DATA terbaru):"
        )
        for i, e in enumerate(liked, 1):
            parts.append(f"[disukai · gaya {e['style']}]\n{e['text']}")
    if disliked:
        parts.append("\nGAYA BERIKUT KURANG disukai — HINDARI pola seperti ini:")
        for e in disliked:
            parts.append(f"[kurang disukai · gaya {e['style']}]\n{e['text']}")
    return "\n\n".join(parts)
