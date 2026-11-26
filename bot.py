import json
import os
import subprocess
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InputFile, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from PIL import Image, ImageChops

TOKEN = os.environ.get("BOT_TOKEN")

ADMIN_IDS = {
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

DATA_FILE = "bot_stats.json"
QUICK_ADD_POINTS = 1  # የደንበኛውን ቁልፍ ሲነኩ የሚጨመር የፖይንት መጠን

TEMPLATES = [
    ("T1 C", "T1 W"),
    ("T2 C", "T2 W"),
    ("T3 C", "T3 W"),
    ("T4 C", "T4 W"),
    ("T5 C", "T5 W"),
    ("T6 C", "T6 W"),
    ("---", "T7 W"),
]

VALID_TEMPLATES = {t for row in TEMPLATES for t in row if t != "---"}

TEXTS = {
    "am": {
        "btn_start": "🚀 ጀምር",
        "btn_points": "💰 ፖይንት ግዛ ({pts})",
        "btn_settings": "⚙️ የፎርማት ማስተካከያ",
        "btn_color": "🎨 ቀለም",
        "btn_mirror": "🔄 መስታወት",
        "btn_templates": "🖼️ ቴምፕሌቶች",
        "btn_lang": "🌐 ቋንቋ (Language)",
        "btn_done": "✅ ጨርሻለሁ",
        "btn_cancel": "❌ ስርዝ",
        "btn_back": "⬅️ Back",
        "welcome": "ሰላም {name}! የፋይዳ ፒዲኤፍ ፋይሎችን ለማቀናበር ዝግጁ ነኝ። ቴምፕሌት ይምረጡ ወይም PDF ይላኩ።",
        "choose_lang": "🌐 ቋንቋውን ይምረጡ፦",
        "lang_set": "✅ ቋንቋው ወደ አማርኛ ተቀይሯል!",
        "buy_points": (
            "💰 የአሁኑ ፖይንትዎ፦ **{pts}**\n"
            "• 1 ፖይንት = 1 የPDF ሂደት\n"
            "• ፖይንት ለመግዛት @power_worked ን ያነጋግሩ እና User IDዎን (`{uid}`) ይላኩ።"
        ),
        "templates_intro": "🖼️ የሚገኙ የመታወቂያ ቴምፕሌቶች፦",
        "choose_template": "ለመታወቂያው የሚጠቀሙትን ቴምፕሌት ይንኩ፦",
        "template_set": "✅ ቴምፕሌት **{tpl}** ተመርጧል። መታወቂያዎቹ አሁን ይህን ይጠቀማሉ።",
        "settings_msg": "⚙️ የአሁኑ ቅንብር፦ ቴምፕሌት **{tpl}** | ቀለም **{color}** | መስታወት **{mirror}**",
        "color_msg": "🎨 ቀለም ወደ ጥርት ያለ የህትመት ጥራት (300 DPI) ተስተካክሏል።",
        "mirror_msg": "🔄 የመስታወት/አቀማመጥ ሁኔታ ተቀይሯል።",
        "only_pdf": "እባክዎ ትክክለኛ የፋይዳ (Fayda) PDF ፋይል ብቻ ይላኩ!",
        "no_points": (
            "❌ **ፖይንት አይበቃም**\n\n"
            "PDF ለማውረድ ቢያንስ 1 ፖይንት ያስፈልጋል።\n"
            "ያሉት ቀሪ፦ **{pts} ፖይንት**\n\n"
            "💰 ፖይንት ግዛ ይጫኑ።"
        ),
        "batch_added": (
            "📥 ፒዲኤፍ(PDF) ተከ metadata ተይዟል (ድምር: **{count}**/100)\n"
            "ተጨማሪ ፋይል ይላኩ፤ ወይም ሲጨርሱ **✅ ጨርሻለሁ** ን ይጫኑ።"
        ),
        "batch_cleared": "🗑️ የተከማቹ PDF ፋይሎች ተሰርዘዋል።",
        "batch_empty": "⚠️ ምንም የተከማቸ PDF ፋይል የለም። በመጀመሪያ PDF ይላኩ።",
        "processing": "⏳ ፋይሉ እየተቀነባበረ ነው፣ እባክዎ ትንሽ ይጠብቁ...",
        "multi_note": (
            "ℹ️ ማሳሰቢያ፦ በአንድ ጊዜ ብዙ መታወቂያዎችን ወይም የተለያዩ ፋይሎችን በአንድ ወረቀት ላይ "
            "በራስ-ሰር የማዋሃድ አገልግሎት ውሱንነት ሊኖረው ይችላል። እያንዳንዱ ገጽ ለፕሪንት ተዘጋጅቶ ይላካል።"
        ),
        "done_count": "✅ በጠቅላላው **{count}** ገጽ/ፋይል ለፕሪንት ተዘጋጅቷል! ቀሪ ፖይንት፦ **{pts}**",
        "caption": "🖨️ ለፕሪንት ዝግጁ ({tpl})",
        "error": "❌ ስህተት ተፈጥሯል: {err}",
    },
    "om": {
        "btn_start": "🚀 Jalqabi",
        "btn_points": "💰 Pooyintii Biti ({pts})",
        "btn_settings": "⚙️ Sirreeffama Foormaatii",
        "btn_color": "🎨 Halluu",
        "btn_mirror": "🔄 Daawitii",
        "btn_templates": "🖼️ Teempileetota",
        "btn_lang": "🌐 Afaan (Language)",
        "btn_done": "✅ Xumureera",
        "btn_cancel": "❌ Haqi",
        "btn_back": "⬅️ Back",
        "welcome": "Akkam {name}! PDF Fayda qopheessuuf qophiidha. Teempileetii filadhaa ykn PDF ergaa.",
        "choose_lang": "🌐 Afaan filadhaa፦",
        "lang_set": "✅ Afaan gara Afaan Oromootti jijjiirameera!",
        "buy_points": (
            "💰 Pooyintii ammaa፦ **{pts}**\n"
            "• 1 Pooyintii = Hojii PDF 1\n"
            "• Pooyintii bitachuuf @power_worked qunnamaa fi User ID keessan (`{uid}`) ergaa."
        ),
        "templates_intro": "🖼️ Teempileetota waraqaa eenyummaa፦",
        "choose_template": "Teempileetii fayyadamtan filadhaa፦",
        "template_set": "✅ Teempileetiin **{tpl}** filatameera.",
        "settings_msg": "⚙️ Qindaa'ina ammaa፦ Teempileetii **{tpl}** | Halluu **{color}** | Daawitii **{mirror}**",
        "color_msg": "🎨 Halluu fi qulqullinni maxxansaa (300 DPI) sirreeffameera.",
        "mirror_msg": "🔄 Haalli daawitii jijjiirameera.",
        "only_pdf": "Maaloo faayila PDF Fayda qofa ergaa!",
        "no_points": (
            "❌ **Pooyintiin hin ga'u**\n\n"
            "PDF buufachuuf yoo xiqqaate pooyintii 1 barbaachisa.\n"
            "Kan hafe፦ **{pts} Pooyintii**\n\n"
            "💰 Pooyintii Biti cuqaasaa."
        ),
        "batch_added": (
            "📥 PDF kuufameera (Ida'ama: **{count}**/100)\n"
            "Faayila dabalataa ergaa; yoo xumurtan **✅ Xumureera** cuqaasaa."
        ),
        "batch_cleared": "🗑️ Faayiloonni PDF kuufaman haqamaniiru.",
        "batch_empty": "⚠️ Faayilli PDF kuufame hin jiru. Dura PDF ergaa.",
        "processing": "⏳ Faayilli hojjetamaa jira, xiqqoo eegaa...",
        "multi_note": (
            "ℹ️ Hubachiisa፦ Waraqaa tokko irratti walitti makuun daangaa qabaachuu danda'a. "
            "Fuulli hunduu maxxansaaf qophaa'ee ergama."
        ),
        "done_count": "✅ Walumaagalatti fuulli/faayilli **{count}** qophaa'eera! Pooyintii hafe፦ **{pts}**",
        "caption": "🖨️ Maxxansaaf qophaa'e ({tpl})",
        "error": "❌ Dogoggorri uumameera: {err}",
    },
    "en": {
        "btn_start": "🚀 Start",
        "btn_points": "💰 Buy Points ({pts})",
        "btn_settings": "⚙️ Format Settings",
        "btn_color": "🎨 Color",
        "btn_mirror": "🔄 Mirror",
        "btn_templates": "🖼️ Templates",
        "btn_lang": "🌐 Language",
        "btn_done": "✅ Done",
        "btn_cancel": "❌ Cancel",
        "btn_back": "⬅️ Back",
        "welcome": "Hello {name}! Ready to convert Fayda PDFs. Choose a template or send PDF files.",
        "choose_lang": "🌐 Select your language:",
        "lang_set": "✅ Language changed to English!",
        "buy_points": (
            "💰 Current points: **{pts}**\n"
            "• 1 Point = 1 PDF processing job\n"
            "• To buy points, contact @power_worked and send your User ID (`{uid}`)."
        ),
        "templates_intro": "🖼️ Available ID templates:",
        "choose_template": "Choose the template to use for your IDs፦",
        "template_set": "✅ Template **{tpl}** selected.",
        "settings_msg": "⚙️ Current settings: Template **{tpl}** | Color **{color}** | Mirror **{mirror}**",
        "color_msg": "🎨 Print color & quality (300 DPI) updated.",
        "mirror_msg": "🔄 Mirror mode toggled.",
        "only_pdf": "Please send a valid Fayda PDF file only!",
        "no_points": (
            "❌ **Insufficient Points**\n\n"
            "At least 1 point is required to process/download PDF.\n"
            "Remaining: **{pts} Point(s)**\n\n"
            "💰 Tap Buy Points."
        ),
        "batch_added": (
            "📥 PDF queued (Total: **{count}**/100)\n"
            "Send more PDFs, or tap **✅ Done** when finished."
        ),
        "batch_cleared": "🗑️ Queued PDF files cleared.",
        "batch_empty": "⚠️ No queued PDF files. Send a PDF first.",
        "processing": "⏳ Processing your file(s), please wait...",
        "multi_note": (
            "ℹ️ Notice: Combining multiple IDs onto one sheet may have layout limits. "
            "Each page is prepared for print and sent."
        ),
        "done_count": "✅ Total **{count}** page(s) ready for print! Remaining points: **{pts}**",
        "caption": "🖨️ Ready for print ({tpl})",
        "error": "❌ Error: {err}",
    },
}

LANG_CHOICE_BUTTONS = [
    ["English 🇺🇸", "Amharic 🇪🇹"],
    ["Afaan-Oromo 🌳"],
    ["⬅️ Back"],
]

LANG_MAP = {
    "English 🇺🇸": "en",
    "English": "en",
    "Amharic 🇪🇹": "am",
    "አማርኛ": "am",
    "Afaan-Oromo 🌳": "om",
    "Afan Oromo": "om",
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

def ensure_user_record(data: dict, user_id: int, first_name: str = "", username: str = "") -> dict:
    uid = str(user_id)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    rec = data["users"].get(uid, {})
    rec.setdefault("id", user_id)
    rec.setdefault("first_name", first_name)
    rec.setdefault("username", f"@{username}" if username and not username.startswith("@") else (username or ""))
    rec.setdefault("lang", "am")
    rec.setdefault("points", 0)
    rec.setdefault("template", "T1 C")
    rec.setdefault("mirror", False)
    rec.setdefault("color_mode", "Standard")
    rec.setdefault("actions_count", 0)
    rec.setdefault("last_seen", now)
    rec.setdefault("last_action", "")
    if first_name:
        rec["first_name"] = first_name
    if username:
        rec["username"] = f"@{username}" if not username.startswith("@") else username
    data["users"][uid] = rec
    return rec

def touch_user(user, action: str, detail: str = "") -> dict:
    data = load_stats()
    if not user:
        return data
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    rec = ensure_user_record(data, user.id, user.first_name or "", user.username or "")
    rec["actions_count"] = rec.get("actions_count", 0) + 1
    rec["last_seen"] = now
    rec["last_action"] = action
    data["logs"].append({
        "time": now,
        "user_id": user.id,
        "name": user.first_name or "",
        "action": action,
        "detail": detail,
    })
    data["logs"] = data["logs"][-200:]
    save_stats(data)
    return data

def get_user_rec(user_id: int) -> dict:
    data = load_stats()
    return ensure_user_record(data, user_id)

def main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    rec = get_user_rec(user_id)
    lang = rec.get("lang", "am")
    pts = rec.get("points", 0)
    t = TEXTS.get(lang, TEXTS["am"])
    return ReplyKeyboardMarkup(
        [
            [t["btn_start"]],
            [t["btn_points"].format(pts=pts), t["btn_settings"]],
            [t["btn_color"], t["btn_mirror"]],
            [t["btn_templates"], t["btn_lang"]],
        ],
        resize_keyboard=True,
    )

def templates_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    rec = get_user_rec(user_id)
    lang = rec.get("lang", "am")
    active = rec.get("template", "T1 C")
    t = TEXTS.get(lang, TEXTS["am"])
    rows = []
    for left, right in TEMPLATES:
        l_lbl = f"✅ {left}" if left == active and left != "---" else left
        r_lbl = f"✅ {right}" if right == active and right != "---" else right
        rows.append([l_lbl, r_lbl])
    rows.append([t["btn_back"]])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def batch_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    rec = get_user_rec(user_id)
    lang = rec.get("lang", "am")
    t = TEXTS.get(lang, TEXTS["am"])
    return ReplyKeyboardMarkup(
        [[t["btn_done"], t["btn_cancel"]]],
        resize_keyboard=True,
    )

def build_users_inline_keyboard(users_dict: dict, limit: int = 20) -> InlineKeyboardMarkup:
    sorted_users = sorted(
        users_dict.values(),
        key=lambda u: u.get("last_seen", ""),
        reverse=True,
    )[:limit]

    keyboard = []
    for u in sorted_users:
        uid = u.get("id")
        if uid is None:
            continue
        uname = (u.get("first_name") or "User").strip()
        pts = u.get("points", 0)
        label = f"➕{QUICK_ADD_POINTS} | {uname} ({uid}) • {pts}pt"
        keyboard.append([
            InlineKeyboardButton(text=label[:64], callback_data=f"addpt:{uid}:{QUICK_ADD_POINTS}")
        ])
    return InlineKeyboardMarkup(keyboard)

def trim_whitespace(img: Image.Image, tol: int = 24) -> Image.Image:
    rgb = img.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg)
    mask = diff.convert("L").point(lambda x: 255 if x > tol else 0)
    bbox = mask.getbbox()
    if not bbox:
        return rgb
    pad = 14
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(rgb.width, bbox[2] + pad)
    bottom = min(rgb.height, bbox[3] + pad)
    return rgb.crop((left, top, right, bottom))

def build_printable_sheet(page_img: Image.Image, template: str = "T1 C", mirror: bool = False) -> Image.Image:
    rgb = page_img.convert("RGB")
    w, h = rgb.size

    if w < h:
        right_start_x = int(w * 0.54)
        right_end_x = int(w * 0.95)

        top_card_box = (right_start_x, int(h * 0.28), right_end_x, int(h * 0.49))
        bottom_card_box = (right_start_x, int(h * 0.50), right_end_x, int(h * 0.71))

        card_top = trim_whitespace(rgb.crop(top_card_box))
        card_bottom = trim_whitespace(rgb.crop(bottom_card_box))

        if card_top.width > 80 and card_top.height > 60 and card_bottom.width > 80 and card_bottom.height > 60:
            if mirror:
                card_top = card_top.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                card_bottom = card_bottom.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

            gap = 36
            pad = 48
            target_h = max(card_top.height, card_bottom.height)

            top_resized = card_top.resize(
                (max(1, int(card_top.width * (target_h / card_top.height))), target_h),
                Image.Resampling.LANCZOS,
            )
            bottom_resized = card_bottom.resize(
                (max(1, int(card_bottom.width * (target_h / card_bottom.height))), target_h),
                Image.Resampling.LANCZOS,
            )

            is_white_bg = template.endswith("W")
            bg_color = (255, 255, 255) if is_white_bg else (245, 248, 245)

            out_w = top_resized.width + bottom_resized.width + gap + (pad * 2)
            out_h = target_h + (pad * 2)

            sheet = Image.new("RGB", (out_w, out_h), bg_color)
            sheet.paste(top_resized, (pad, pad))
            sheet.paste(bottom_resized, (pad + top_resized.width + gap, pad))
            return sheet

    trimmed = trim_whitespace(rgb)
    if mirror:
        trimmed = trimmed.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    tw, th = trimmed.size
    pad = max(32, int(min(tw, th) * 0.04))
    is_white_bg = template.endswith("W")
    bg_color = (255, 255, 255) if is_white_bg else (245, 248, 245)
    sheet = Image.new("RGB", (tw + pad * 2, th + pad * 2), bg_color)
    sheet.paste(trimmed, (pad, pad))
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
    context.user_data.pop("pending_pdfs", None)
    touch_user(user, "/start")
    rec = get_user_rec(user.id)
    t = TEXTS.get(rec.get("lang", "am"), TEXTS["am"])
    name = user.first_name if user and user.first_name else "ደንበኛ"
    await update.message.reply_text(
        t["welcome"].format(name=name),
        reply_markup=main_keyboard(user.id),
    )

async def users_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ቦቱን የሚጠቀሙ ደንበኞችን ዝርዝር ያሳያል፤ ቁልፉን ሲነኩ ፖይንት ይጨምራል።"""
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ ይህ ትዕዛዝ ለአድሚን ብቻ ነው።")
        return

    data = load_stats()
    users = data.get("users", {})
    if not users:
        await update.message.reply_text("ℹ️ እስካሁን የተመዘገበ ደንበኛ የለም።")
        return

    lines = [
        "👥 **የደንበኞች ዝርዝር (ፖይንት ለመጨመር የደንበኛውን ቁልፍ ይንኩ)**",
        f"ጠቅላላ ደንበኞች፦ **{len(users)}** | በአንድ ንክኪ የሚጨመር፦ **+{QUICK_ADD_POINTS}**",
        "",
    ]

    sorted_users = sorted(
        users.values(),
        key=lambda u: u.get("last_seen", ""),
        reverse=True,
    )[:20]

    for u in sorted_users:
        uname = u.get("first_name") or "User"
        handle = f" {u['username']}" if u.get("username") else ""
        lines.append(
            f"• `{u.get('id')}` — {uname}{handle} | ፖይንት: **{u.get('points', 0)}**"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=build_users_inline_keyboard(users, limit=20),
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    admin_user = query.from_user
    if not admin_user or admin_user.id not in ADMIN_IDS:
        await query.answer("⛔ ለአድሚን ብቻ ነው።", show_alert=True)
        return

    data_str = query.data or ""
    if data_str.startswith("addpt:"):
        parts = data_str.split(":")
        if len(parts) == 3 and parts[1].isdigit():
            target_id = int(parts[1])
            try:
                delta = int(parts[2])
            except ValueError:
                delta = QUICK_ADD_POINTS

            stats = load_stats()
            rec = ensure_user_record(stats, target_id)
            new_pts = max(0, rec.get("points", 0) + delta)
            rec["points"] = new_pts
            save_stats(stats)
            touch_user(admin_user, "tap_add_points", f"{target_id} ({delta:+d} -> {new_pts})")

            uname = rec.get("first_name") or str(target_id)
            await query.answer(
                f"✅ {uname} ({target_id}): +{delta} ፖይንት ተጨምሯል! ቀሪ፦ {new_pts}",
                show_alert=False,
            )

            try:
                await query.edit_message_reply_markup(
                    reply_markup=build_users_inline_keyboard(stats.get("users", {}), limit=20)
                )
            except Exception:
                pass

async def add_points_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ ይህ ትዕዛዝ ለአድሚን ብቻ ነው።")
        return

    args = context.args or []
    if len(args) != 2 or not args[0].isdigit():
        await update.message.reply_text("አጠቃቀም፦ `/addpoints <user_id> <amount>`", parse_mode="Markdown")
        return

    target_id = int(args[0])
    try:
        delta = int(args[1])
    except ValueError:
        await update.message.reply_text("ፖይንት ቁጥር መሆን አለበት።")
        return

    data = load_stats()
    rec = ensure_user_record(data, target_id)
    new_pts = max(0, rec.get("points", 0) + delta)
    rec["points"] = new_pts
    save_stats(data)
    touch_user(user, "add_points", f"{target_id} ({delta:+d} -> {new_pts})")

    await update.message.reply_text(
        f"✅ ለተጠቃሚ `{target_id}` ፖይንት ተቀይሯል ({delta:+d})። አሁን ያለው ቀሪ፦ **{new_pts}**",
        parse_mode="Markdown",
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
        "🛡️ **ADMIN PANEL**",
        f"👥 ጠቅላላ ተጠቃሚዎች: {len(users)}",
        f"📄 የተቀነባበሩ PDF ፋይሎች: {data.get('total_pdfs', 0)}",
        "• ደንበኞችን ለማየት እና በንክኪ ፖይንት ለመጨመር፦ `/users`",
        "• ብዙ ፖይንት ለመጨመር፦ `/addpoints <user_id> <amount>`",
        "",
        "👤 **ደንበኞች (የቅርብ ጊዜ 15):**",
    ]

    sorted_users = sorted(
        users.values(),
        key=lambda u: u.get("last_seen", ""),
        reverse=True,
    )[:15]

    for u in sorted_users:
        uname = u.get("first_name") or "User"
        handle = f" {u['username']}" if u.get("username") else ""
        lines.append(
            f"• `{u.get('id')}` — {uname}{handle} | ፖይንት: `{u.get('points', 0)}` | ቋንቋ: `{u.get('lang', 'am')}` | ቴምፕሌት: `{u.get('template', 'T1 C')}`"
        )

    lines.append("")
    lines.append("🧾 **የቅርብ ጊዜ እንቅስቃሴዎች:**")
    for item in reversed(logs):
        lines.append(f"• `{item.get('user_id')}`: {item.get('action')} {item.get('detail')}")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=build_users_inline_keyboard(users, limit=10) if users else None,
    )

async def process_pdf_list(update: Update, context: ContextTypes.DEFAULT_TYPE, pdf_paths: list[str]):
    user = update.effective_user
    message = update.message
    data = load_stats()
    rec = ensure_user_record(data, user.id, user.first_name or "", user.username or "")
    lang = rec.get("lang", "am")
    t = TEXTS.get(lang, TEXTS["am"])
    pts = rec.get("points", 0)

    if pts < 1:
        await message.reply_text(t["no_points"].format(pts=pts), parse_mode="Markdown", reply_markup=main_keyboard(user.id))
        return

    tpl = rec.get("template", "T1 C")
    mirror = bool(rec.get("mirror", False))

    await message.reply_text(t["processing"], reply_markup=main_keyboard(user.id))

    page_files = []
    output_files = []

    try:
        for p_idx, pdf_path in enumerate(pdf_paths, start=1):
            prefix = f"page_{user.id}_{p_idx}"
            subprocess.run(["pdftoppm", "-png", "-r", "300", pdf_path, prefix], check=True)
            found = sorted([f for f in os.listdir(".") if f.startswith(prefix) and f.endswith(".png")])
            page_files.extend(found)

        if len(page_files) > 1:
            await message.reply_text(t["multi_note"])

        for idx, p_file in enumerate(page_files, start=1):
            with Image.open(p_file) as base_img:
                printable = build_printable_sheet(base_img, template=tpl, mirror=mirror)
                out_pdf_name = f"Fayda_Print_{user.id}_{idx}.pdf"
                printable.save(out_pdf_name, "PDF", resolution=300)
                output_files.append(out_pdf_name)

        rec["points"] = max(0, pts - 1)
        data["total_pdfs"] = data.get("total_pdfs", 0) + len(pdf_paths)
        save_stats(data)

        await message.reply_text(
            t["done_count"].format(count=len(output_files), pts=rec["points"]),
            parse_mode="Markdown",
            reply_markup=main_keyboard(user.id),
        )

        for out_pdf in output_files:
            with open(out_pdf, "rb") as pdf_file:
                await message.reply_document(
                    document=InputFile(pdf_file),
                    caption=t["caption"].format(tpl=tpl),
                )

    except Exception as e:
        await message.reply_text(t["error"].format(err=str(e)), reply_markup=main_keyboard(user.id))

    finally:
        for path in pdf_paths + page_files + output_files:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()
    data = load_stats()
    rec = ensure_user_record(data, user.id, user.first_name or "", user.username or "")
    lang = rec.get("lang", "am")
    t = TEXTS.get(lang, TEXTS["am"])

    if text in LANG_MAP:
        chosen = LANG_MAP[text]
        rec["lang"] = chosen
        save_stats(data)
        touch_user(user, "set_language", chosen)
        new_t = TEXTS[chosen]
        await update.message.reply_text(new_t["lang_set"], reply_markup=main_keyboard(user.id))
        return

    clean_tpl = text.replace("✅ ", "").strip()
    if clean_tpl in VALID_TEMPLATES:
        rec["template"] = clean_tpl
        save_stats(data)
        touch_user(user, "set_template", clean_tpl)
        await update.message.reply_text(
            t["template_set"].format(tpl=clean_tpl),
            parse_mode="Markdown",
            reply_markup=templates_keyboard(user.id),
        )
        return

    if text in {v["btn_back"] for v in TEXTS.values()} or text == "⬅️ Back":
        await update.message.reply_text(t["welcome"].format(name=user.first_name or "ደንበኛ"), reply_markup=main_keyboard(user.id))
        return

    if text in {v["btn_done"] for v in TEXTS.values()}:
        queued = context.user_data.pop("pending_pdfs", [])
        if not queued:
            await update.message.reply_text(t["batch_empty"], reply_markup=main_keyboard(user.id))
            return
        touch_user(user, "batch_done", f"{len(queued)} files")
        await process_pdf_list(update, context, queued)
        return

    if text in {v["btn_cancel"] for v in TEXTS.values()}:
        queued = context.user_data.pop("pending_pdfs", [])
        for p in queued:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        touch_user(user, "batch_cancel")
        await update.message.reply_text(t["batch_cleared"], reply_markup=main_keyboard(user.id))
        return

    touch_user(user, "button", text)

    if text in {v["btn_start"] for v in TEXTS.values()} or text == "🚀 ጀምር":
        context.user_data.pop("pending_pdfs", None)
        await update.message.reply_text(t["welcome"].format(name=user.first_name or "ደንበኛ"), reply_markup=main_keyboard(user.id))
    elif text.startswith("💰") or text == t["btn_points"].format(pts=rec.get("points", 0)):
        await update.message.reply_text(
            t["buy_points"].format(pts=rec.get("points", 0), uid=user.id),
            parse_mode="Markdown",
            reply_markup=main_keyboard(user.id),
        )
    elif text in {v["btn_settings"] for v in TEXTS.values()}:
        await update.message.reply_text(
            t["settings_msg"].format(
                tpl=rec.get("template", "T1 C"),
                color=rec.get("color_mode", "Standard"),
                mirror="ON" if rec.get("mirror") else "OFF",
            ),
            parse_mode="Markdown",
            reply_markup=main_keyboard(user.id),
        )
    elif text in {v["btn_color"] for v in TEXTS.values()}:
        rec["color_mode"] = "High-DPI (300)"
        save_stats(data)
        await update.message.reply_text(t["color_msg"], reply_markup=main_keyboard(user.id))
    elif text in {v["btn_mirror"] for v in TEXTS.values()}:
        rec["mirror"] = not bool(rec.get("mirror", False))
        save_stats(data)
        await update.message.reply_text(t["mirror_msg"], reply_markup=main_keyboard(user.id))
    elif text in {v["btn_templates"] for v in TEXTS.values()}:
        await update.message.reply_text(
            f"{t['templates_intro']}\n{t['choose_template']}",
            reply_markup=templates_keyboard(user.id),
        )
    elif text in {v["btn_lang"] for v in TEXTS.values()}:
        await update.message.reply_text(
            t["choose_lang"],
            reply_markup=ReplyKeyboardMarkup(LANG_CHOICE_BUTTONS, resize_keyboard=True),
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    data = load_stats()
    rec = ensure_user_record(data, user.id, user.first_name or "", user.username or "")
    lang = rec.get("lang", "am")
    t = TEXTS.get(lang, TEXTS["am"])

    file_name = message.document.file_name if message.document and message.document.file_name else ""
    if not message.document or not file_name.lower().endswith(".pdf"):
        await message.reply_text(t["only_pdf"], reply_markup=main_keyboard(user.id))
        return

    pts = rec.get("points", 0)
    if pts < 1:
        touch_user(user, "blocked_no_points", file_name)
        await message.reply_text(
            t["no_points"].format(pts=pts),
            parse_mode="Markdown",
            reply_markup=main_keyboard(user.id),
        )
        return

    touch_user(user, "queued_pdf", file_name)
    queued = context.user_data.setdefault("pending_pdfs", [])
    pdf_path = f"batch_{user.id}_{len(queued) + 1}.pdf"

    tg_file = await context.bot.get_file(message.document.file_id)
    await tg_file.download_to_drive(pdf_path)
    queued.append(pdf_path)

    await message.reply_text(
        t["batch_added"].format(count=len(queued)),
        parse_mode="Markdown",
        reply_markup=batch_keyboard(user.id),
    )

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    threading.Thread(target=start_health_server, daemon=True).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("users", users_panel))
    application.add_handler(CommandHandler("addpoints", add_points_cmd))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    print("ቦቱ በመጀመር ላይ ነው...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
