import json
import os
import subprocess
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InputFile, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageChops

TOKEN = os.environ.get("BOT_TOKEN")

# የእርስዎን Telegram User ID በ Render Environment Variables ውስጥ በ ADMIN_IDS ያስገቡ
ADMIN_IDS = {
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

DATA_FILE = "bot_stats.json"

TEXTS = {
    "am": {
        "welcome": "ሰላም ውድ {name}! የፋይዳ ፒዲኤፍ (PDF) ይላኩ፤ ቆርጦ ለፕሪንት ተዘጋጅቶ ይላክልዎታል።",
        "btn_download": "pdf download",
        "btn_convert": "pdf converted",
        "btn_support": "support",
        "btn_lang": "language",
        "download_msg": "📄 PDF ለማውረድ ወደዚህ ቦት ይሂዱ፦ @sedoo_pdf_bot",
        "convert_msg": "🔄 ፋይል ለማቀናበር እዚሁ ቦት ላይ የፋይዳ PDF ፋይሉን ይላኩልኝ።",
        "support_msg": "🆘 እርዳታ ከፈለጉ @power_worked ን ያነጋግሩ።",
        "choose_lang": "🌐 እባክዎ የሚፈልጉትን ቋንቋ ይምረጡ፦",
        "lang_set": "✅ ቋንቋ ወደ አማርኛ ተቀይሯል።",
        "only_pdf": "እባክዎ ትክክለኛ የፋይዳ (Fayda) PDF ፋይል ብቻ ይላኩ!",
        "processing": "⏳ ፋይሉ እየተቀነባበረ ነው፣ እባክዎ ትንሽ ይጠብቁ...",
        "done_count": "✅ በጠቅላላው {count} መታወቂያዎች ለፕሪንት ተዘጋጅተዋል!",
        "caption": "🖨️ ለፕሪንት ዝግጁ የሆነ መታወቂያ",
        "error": "❌ ስህተት ተፈጥሯል: {err}",
    },
    "om": {
        "welcome": "Akkam jaallatamaa {name}! PDF Fayda ergaa; sirreeffamee maxxansaaf qophaa'ee isiniif ergama.",
        "btn_download": "pdf download",
        "btn_convert": "pdf converted",
        "btn_support": "support",
        "btn_lang": "language",
        "download_msg": "📄 PDF buufachuuf gara bot kanaa deemi፦ @sedoo_pdf_bot",
        "convert_msg": "🔄 Faayila sirreessuuf asuma irratti PDF Fayda ergaa.",
        "support_msg": "🆘 Gargaarsa yoo barbaaddan @power_worked qunnamaa.",
        "choose_lang": "🌐 Afaan barbaaddan filadhaa፦",
        "lang_set": "✅ Afaan gara Afaan Oromootti jijjiirameera.",
        "only_pdf": "Maaloo faayila PDF Fayda sirrii qofa ergaa!",
        "processing": "⏳ Faayilli hojjetamaa jira, xiqqoo eegaa...",
        "done_count": "✅ Walumaagalatti {count} maxxansaaf qophaa'eera!",
        "caption": "🖨️ Maxxansaaf qophaa'e",
        "error": "❌ Dogoggorri uumameera: {err}",
    },
    "en": {
        "welcome": "Hello dear {name}! Send your Fayda PDF; it will be cropped and sent ready for print.",
        "btn_download": "pdf download",
        "btn_convert": "pdf converted",
        "btn_support": "support",
        "btn_lang": "language",
        "download_msg": "📄 To download PDF, go to this bot: @sedoo_pdf_bot",
        "convert_msg": "🔄 To convert a file, send the Fayda PDF right here in this bot.",
        "support_msg": "🆘 For support, contact @power_worked.",
        "choose_lang": "🌐 Please select your preferred language:",
        "lang_set": "✅ Language changed to English.",
        "only_pdf": "Please send a valid Fayda PDF file only!",
        "processing": "⏳ Processing your file, please wait a moment...",
        "done_count": "✅ Total {count} ID card(s) prepared for print!",
        "caption": "🖨️ Ready for print",
        "error": "❌ An error occurred: {err}",
    },
}

LANG_LABELS = {
    "አማርኛ": "am",
    "Afan Oromo": "om",
    "English": "en",
}

def load_stats() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("users", {})
                    data.setdefault("logs", [])
                    data.setdefault("total_pdfs", 0)
                    return data
        except Exception:
            pass
    return {"users": {}, "logs": [], "total_pdfs": 0}

def save_stats(data: dict) -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def touch_user(user, action: str, detail: str = "") -> None:
    if not user:
        return
    data = load_stats()
    uid = str(user.id)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    existing = data["users"].get(uid, {})
    data["users"][uid] = {
        "id": user.id,
        "first_name": user.first_name or "",
        "username": f"@{user.username}" if user.username else "",
        "lang": existing.get("lang", "am"),
        "actions_count": existing.get("actions_count", 0) + 1,
        "last_seen": now,
        "last_action": action,
    }
    data["logs"].append({
        "time": now,
        "user_id": user.id,
        "name": user.first_name or "",
        "action": action,
        "detail": detail,
    })
    data["logs"] = data["logs"][-150:]
    save_stats(data)

def get_user_lang(user_id: int) -> str:
    data = load_stats()
    return data["users"].get(str(user_id), {}).get("lang", "am")

def set_user_lang(user_id: int, lang: str) -> None:
    data = load_stats()
    uid = str(user_id)
    if uid in data["users"]:
        data["users"][uid]["lang"] = lang
    else:
        data["users"][uid] = {"id": user_id, "lang": lang, "actions_count": 0}
    save_stats(data)

def main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["am"])
    return ReplyKeyboardMarkup(
        [
            [t["btn_download"], t["btn_convert"]],
            [t["btn_support"], t["btn_lang"]],
        ],
        resize_keyboard=True,
    )

LANG_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["አማርኛ", "Afan Oromo"],
        ["English"],
    ],
    resize_keyboard=True,
)

def trim_whitespace(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg)
    # ቀለም ያላቸውን ክፍሎች በደንብ ለመለየት threshold ማስተካከል
    mask = diff.convert("L").point(lambda x: 255 if x > 18 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return rgb
    pad = 10
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(rgb.width, bbox[2] + pad)
    bottom = min(rgb.height, bbox[3] + pad)
    return rgb.crop((left, top, right, bottom))

def build_printable_sheet(page_img: Image.Image) -> Image.Image:
    trimmed = trim_whitespace(page_img)
    w, h = trimmed.size

    # በተለምዶ የፋይዳ ካርድ (ፊት እና ኋላ) ጎን ለጎን ሲቀመጥ ስፋቱ ከቁመቱ ይበልጣል
    if w >= h:
        mid_x = w // 2
        front_card = trim_whitespace(trimmed.crop((0, 0, mid_x, h)))
        back_card = trim_whitespace(trimmed.crop((mid_x, 0, w, h)))

        gap = max(24, int(w * 0.02))
        pad = max(24, int(h * 0.04))

        out_w = front_card.width + back_card.width + gap + (pad * 2)
        out_h = max(front_card.height, back_card.height) + (pad * 2)

        sheet = Image.new("RGB", (out_w, out_h), (255, 255, 255))
        sheet.paste(front_card, (pad, pad))
        sheet.paste(back_card, (pad + front_card.width + gap, pad))
        return sheet

    # በቁመት ከሆነ የላይ እና የታች ክፍሎችን ለይቶ ጎን ለጎን ማቀናበር
    mid_y = h // 2
    top_part = trim_whitespace(trimmed.crop((0, 0, w, mid_y)))
    bot_part = trim_whitespace(trimmed.crop((0, mid_y, w, h)))

    gap = max(24, int(w * 0.03))
    pad = max(24, int(w * 0.03))

    out_w = top_part.width + bot_part.width + gap + (pad * 2)
    out_h = max(top_part.height, bot_part.height) + (pad * 2)

    sheet = Image.new("RGB", (out_w, out_h), (255, 255, 255))
    sheet.paste(top_part, (pad, pad))
    sheet.paste(bot_part, (pad + top_part.width + gap, pad))
    return sheet

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    touch_user(user, "/start")
    lang = get_user_lang(user.id)
    t = TEXTS.get(lang, TEXTS["am"])
    name = user.first_name if user and user.first_name else "ደንበኛ"
    await update.message.reply_text(
        t["welcome"].format(name=name),
        reply_markup=main_keyboard(lang),
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ ይህ ትዕዛዝ ለአድሚን ብቻ ነው።")
        return

    data = load_stats()
    users = data.get("users", {})
    logs = data.get("logs", [])[-12:]

    lines = [
        "🛡️ **ADMIN PANEL (ደንበኞችና እንቅስቃሴ)**",
        f"👥 ጠቅላላ ተጠቃሚዎች: {len(users)}",
        f"📄 የተቀነባበሩ PDF ፋይሎች: {data.get('total_pdfs', 0)}",
        "",
        "👤 **የደንበኞች ዝርዝር (የቅርብ ጊዜ 15):**",
    ]

    sorted_users = sorted(
        users.values(),
        key=lambda u: u.get("last_seen", ""),
        reverse=True,
    )[:15]

    for u in sorted_users:
        uname = u.get("first_name") or "User"
        handle = f" {u['username']}" if u.get("username") else ""
        ulang = u.get("lang", "am")
        last_act = u.get("last_action", "")
        lines.append(
            f"• ID `{u.get('id')}` — {uname}{handle} | ቋንቋ: `{ulang}` | `{last_act}`"
        )

    lines.append("")
    lines.append("🧾 **የቅርብ ጊዜ እንቅስቃሴዎች:**")
    for item in reversed(logs):
        u_name = item.get("name") or "User"
        lines.append(
            f"• `{item.get('user_id')}` ({u_name}): {item.get('action')} {item.get('detail')}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()
    lang = get_user_lang(user.id)
    t = TEXTS.get(lang, TEXTS["am"])

    if text in LANG_LABELS:
        chosen = LANG_LABELS[text]
        set_user_lang(user.id, chosen)
        touch_user(user, "set_language", chosen)
        new_t = TEXTS[chosen]
        await update.message.reply_text(new_t["lang_set"], reply_markup=main_keyboard(chosen))
        return

    touch_user(user, "button", text)

    if text == t["btn_download"] or text == "pdf download":
        await update.message.reply_text(t["download_msg"], reply_markup=main_keyboard(lang))
    elif text == t["btn_convert"] or text == "pdf converted":
        await update.message.reply_text(t["convert_msg"], reply_markup=main_keyboard(lang))
    elif text == t["btn_support"] or text == "support":
        await update.message.reply_text(t["support_msg"], reply_markup=main_keyboard(lang))
    elif text == t["btn_lang"] or text == "language":
        await update.message.reply_text(t["choose_lang"], reply_markup=LANG_KEYBOARD)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    lang = get_user_lang(user.id)
    t = TEXTS.get(lang, TEXTS["am"])

    file_name = message.document.file_name if message.document and message.document.file_name else ""
    if not message.document or not file_name.lower().endswith(".pdf"):
        await message.reply_text(t["only_pdf"], reply_markup=main_keyboard(lang))
        return

    touch_user(user, "sent_pdf", file_name)
    await message.reply_text(t["processing"])

    pdf_path = f"downloaded_{user.id}.pdf"
    page_files = []
    output_files = []

    try:
        file = await context.bot.get_file(message.document.file_id)
        await file.download_to_drive(pdf_path)

        subprocess.run(["pdftoppm", "-png", "-r", "300", pdf_path, f"page_{user.id}"], check=True)

        page_files = sorted([
            f for f in os.listdir(".")
            if f.startswith(f"page_{user.id}") and f.endswith(".png")
        ])

        for idx, p_file in enumerate(page_files, start=1):
            with Image.open(p_file) as base_img:
                printable = build_printable_sheet(base_img)
                out_pdf_name = f"Fayda_Print_{user.id}_{idx}.pdf"
                printable.save(out_pdf_name, "PDF", resolution=300)
                output_files.append(out_pdf_name)

        stats = load_stats()
        stats["total_pdfs"] = stats.get("total_pdfs", 0) + 1
        save_stats(stats)

        await message.reply_text(t["done_count"].format(count=len(output_files)))

        for out_pdf in output_files:
            with open(out_pdf, "rb") as pdf_file:
                await message.reply_document(
                    document=InputFile(pdf_file),
                    caption=t["caption"],
                )

    except Exception as e:
        await message.reply_text(t["error"].format(err=str(e)))

    finally:
        for path in [pdf_path] + page_files + output_files:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    threading.Thread(target=start_health_server, daemon=True).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    print("ቦቱ በመጀመር ላይ ነው...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
