"""Panggil Claude (via gateway GoRouter) untuk menulis 3 angle postingan Web3 yang menarik."""
import os
import re
import anthropic

import feedback_store

_client = None

# label internal -> (nama tampilan, arahan gaya untuk AI)
STYLES = [
    ("analitis", "ANALITIS", "tajam & berbasis data, seperti analis pasar; soroti angka, "
     "korelasi, dan apa artinya bagi tren."),
    ("dramatis", "DRAMATIS", "penuh energi & bikin penasaran, seperti berita breaking; "
     "hook berani, tempo cepat (tetap faktual, tanpa clickbait bohong)."),
    ("edukatif", "EDUKATIF", "ramah pemula; jelaskan istilah singkat, beri konteks 'kenapa ini "
     "terjadi' agar orang awam paham."),
]


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # baca ANTHROPIC_AUTH_TOKEN & ANTHROPIC_BASE_URL dari .env
    return _client


def _model():
    return os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")


def _style_spec():
    return "\n".join(f"- {disp}: {desc}" for _, disp, desc in STYLES)


BASE_RULES = """Prinsip agar banyak peminat (berlaku untuk SEMUA versi):
- HOOK kuat di kalimat pertama (angka mengejutkan / pertanyaan / pernyataan berani).
- Pakai data spesifik dari DATA: harga, %, Fear & Greed, funding rate, TVL, gainer/loser, headline.
- Kaitkan angka dengan narasi 'kenapa ini penting'. Tetap faktual, TANPA nasihat finansial.
- Akhiri dengan CTA/pertanyaan yang mengundang komentar. 2-4 emoji relevan (jangan berlebihan).
- Jangan mengarang angka di luar DATA. Jangan menulis 'berdasarkan data yang diberikan'."""


def _system(lang: str) -> str:
    intro = ("Kamu content creator kripto/Web3 profesional berbahasa Indonesia yang postingannya "
             "sering viral." if lang != "en" else
             "You are a professional crypto/Web3 content creator whose posts often go viral. "
             "Write everything in English.")
    return f"""{intro}

Tugasmu: dari DATA PASAR, buat TIGA angle postingan dengan gaya berbeda:
{_style_spec()}

{BASE_RULES}

Untuk SETIAP gaya, keluarkan versi X (maks 280 karakter, 2-3 hashtag) dan versi FACEBOOK
(4-7 baris, poin data ber-bullet/emoji, 1 insight, 1 pertanyaan CTA, 3-5 hashtag).

Keluarkan TEPAT dengan format ini (jangan tambah teks lain):

===ANALITIS===
[X]
<teks x>
[FB]
<teks facebook>
===DRAMATIS===
[X]
<teks x>
[FB]
<teks facebook>
===EDUKATIF===
[X]
<teks x>
[FB]
<teks facebook>"""


def _extract(block: str):
    x_m = re.search(r"\[X\]\s*(.+?)\s*\[FB\]", block, re.S)
    fb_m = re.search(r"\[FB\]\s*(.+)$", block, re.S)
    x = (x_m.group(1).strip().strip('"')) if x_m else block.strip()[:277]
    fb = (fb_m.group(1).strip().strip('"')) if fb_m else block.strip()
    if len(x) > 280:
        x = x[:277].rstrip() + "..."
    return x, fb


def _parse(text: str):
    posts = []
    for label, disp, _ in STYLES:
        m = re.search(rf"==={disp}===\s*(.*?)(?===[A-Z]+===|$)", text, re.S)
        if not m:
            continue
        x, fb = _extract(m.group(1))
        posts.append({"style": label, "display": disp, "x": x, "facebook": fb})
    return posts


def write_posts(market_summary: str, lang: str = "id") -> list:
    """Hasilkan list of dict: [{style, display, x, facebook}, ...] (biasanya 3 angle)."""
    client = _get_client()
    examples = feedback_store.build_examples_block()
    user = "DATA PASAR WEB3 TERKINI:\n\n" + market_summary + "\n\n"
    if examples:
        user += examples + "\n\n"
    user += "Buat ketiga angle sekarang, ikuti format marker dengan tepat."

    resp = client.messages.create(
        model=_model(),
        max_tokens=2500,
        system=_system(lang),
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    posts = _parse(text)
    return posts or [{"style": "umum", "display": "UMUM",
                      "x": text[:277], "facebook": text}]
