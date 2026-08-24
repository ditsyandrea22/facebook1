"""Bot Telegram: AI baca data trading Web3, tulis 3 angle berita, belajar dari feedback 👍/👎."""
import asyncio
import html
import logging
import os
from urllib.parse import quote

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import ai_writer
import feedback_store
import web3_data

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

POST_LANG = os.getenv("POST_LANG", "id")

STYLE_EMOJI = {"ANALITIS": "📊", "DRAMATIS": "🚨", "EDUKATIF": "🎓", "UMUM": "📝"}

# penyimpanan sementara postingan untuk keperluan feedback (id -> list of posts)
PENDING: dict[int, list] = {}
_counter = 0

WELCOME = (
    "👋 <b>Web3 News Bot</b>\n\n"
    "Aku membaca data pasar Web3 (harga, sentimen, funding rate, TVL, berita) lalu menulis "
    "<b>3 angle postingan</b> berbeda yang siap kamu <b>copy</b> ke <b>X</b> atau <b>Facebook</b>.\n\n"
    "Beri 👍/👎 pada postingan, dan aku akan <b>meniru gaya yang kamu sukai</b> di postingan berikutnya.\n\n"
    "Perintah:\n"
    "• /berita — buat 3 angle postingan dari data terkini\n"
    "• /trending — koin yang sedang trending\n"
    "• /stats — jumlah feedback yang sudah kukumpulkan\n"
    "• /help — bantuan"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(WELCOME)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(WELCOME)


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    liked, disliked = feedback_store.stats()
    await update.message.reply_html(
        f"📈 <b>Feedback terkumpul</b>\n👍 Disukai: {liked}\n👎 Kurang: {disliked}\n\n"
        f"{'Aku sudah mulai meniru gaya favoritmu.' if liked else 'Beri 👍 agar aku mulai belajar seleramu.'}"
    )


async def trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Mengambil koin trending...")
    try:
        coins = await asyncio.to_thread(web3_data.get_trending)
    except Exception as e:  # noqa: BLE001
        logger.exception("gagal ambil trending")
        await msg.edit_text(f"❌ Gagal mengambil data: {e}")
        return
    lines = ["🔥 <b>Koin Trending di Web3</b>\n"]
    for i, c in enumerate(coins, 1):
        rank = f" (rank #{c['rank']})" if c["rank"] else ""
        lines.append(f"{i}. {html.escape(c['name'])} ({c['symbol']}){rank}")
    await msg.edit_text("\n".join(lines), parse_mode="HTML")


def _post_keyboard(pid: int, idx: int, post: dict) -> InlineKeyboardMarkup:
    """Tombol share (X/Facebook) + feedback (👍/👎) untuk satu angle."""
    x_url = f"https://twitter.com/intent/tweet?text={quote(post['x'])}"
    fb_target = quote("https://www.coingecko.com/en/watchlists/trending-crypto")
    fb_url = f"https://www.facebook.com/sharer/sharer.php?u={fb_target}&quote={quote(post['facebook'])}"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🐦 Post ke X", url=x_url),
            InlineKeyboardButton("📘 Facebook", url=fb_url),
        ],
        [
            InlineKeyboardButton("👍 Suka gaya ini", callback_data=f"fb:{pid}:{idx}:1"),
            InlineKeyboardButton("👎 Kurang", callback_data=f"fb:{pid}:{idx}:0"),
        ],
        [InlineKeyboardButton("🔄 Buat batch baru", callback_data="regen")],
    ])


def _render(post: dict) -> str:
    emoji = STYLE_EMOJI.get(post.get("display", ""), "📝")
    return (
        f"{emoji} <b>Angle: {post.get('display', 'UMUM').title()}</b>\n"
        "<i>(tekan-tahan teks untuk menyalin)</i>\n\n"
        "🐦 <b>Versi X / Twitter</b>\n"
        f"<pre>{html.escape(post['x'])}</pre>\n"
        "📘 <b>Versi Facebook</b>\n"
        f"<pre>{html.escape(post['facebook'])}</pre>"
    )


async def _generate_and_send(context: ContextTypes.DEFAULT_TYPE, chat_id: int, status):
    global _counter
    try:
        summary, _ = await asyncio.to_thread(web3_data.build_market_summary)
        posts = await asyncio.to_thread(ai_writer.write_posts, summary, POST_LANG)
    except Exception as e:  # noqa: BLE001
        logger.exception("gagal membuat postingan")
        await status.edit_text(f"❌ Gagal membuat postingan: {e}")
        return

    _counter += 1
    pid = _counter
    PENDING[pid] = posts
    if len(PENDING) > 200:  # jaga memori
        for k in sorted(PENDING)[:-200]:
            PENDING.pop(k, None)

    await status.edit_text(f"✅ {len(posts)} angle siap. Pilih & bagikan yang paling cocok 👇")
    for idx, post in enumerate(posts):
        await context.bot.send_message(
            chat_id=chat_id, text=_render(post), parse_mode="HTML",
            reply_markup=_post_keyboard(pid, idx, post),
        )


async def berita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await update.message.reply_text("⏳ Membaca data pasar & menulis 3 angle berita...")
    await _generate_and_send(context, update.effective_chat.id, status)


async def on_regen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Membuat batch baru...")
    status = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="⏳ Membaca data pasar & menulis 3 angle berita...",
    )
    await _generate_and_send(context, query.message.chat_id, status)


async def on_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        _, pid, idx, liked = query.data.split(":")
        posts = PENDING.get(int(pid))
        post = posts[int(idx)] if posts else None
    except Exception:  # noqa: BLE001
        post = None
    if not post:
        await query.answer("Postingan ini sudah kedaluwarsa, buat batch baru ya.", show_alert=True)
        return

    is_like = liked == "1"
    await asyncio.to_thread(
        feedback_store.add_feedback, post["facebook"], post["style"], is_like
    )
    await query.answer("👍 Tersimpan! Gaya ini akan kutiru." if is_like
                       else "👎 Dicatat, akan kuhindari gaya ini.")
    # tandai di pesan bahwa feedback sudah masuk
    mark = "✅ 👍 Feedback: SUKA gaya ini" if is_like else "✅ 👎 Feedback: kurang cocok"
    try:
        await query.edit_message_text(
            text=query.message.text_html + f"\n\n<b>{mark}</b>",
            parse_mode="HTML",
        )
    except Exception:  # noqa: BLE001 — abaikan bila tak bisa diedit
        pass


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN belum diisi di .env")
    if not os.getenv("ANTHROPIC_AUTH_TOKEN"):
        logger.warning("ANTHROPIC_AUTH_TOKEN kosong — panggilan AI akan gagal.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("trending", trending))
    app.add_handler(CommandHandler("berita", berita))
    app.add_handler(CommandHandler("news", berita))
    app.add_handler(CallbackQueryHandler(on_regen, pattern="^regen$"))
    app.add_handler(CallbackQueryHandler(on_feedback, pattern="^fb:"))

    logger.info("Bot berjalan. Tekan Ctrl+C untuk berhenti.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
