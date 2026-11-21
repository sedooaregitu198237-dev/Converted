import os
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InputFile, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image

TOKEN = os.environ.get("BOT_TOKEN")

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["Le pdf", "Le convert"],
        ["Le erdata"],
    ],
    resize_keyboard=True,
)

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
    name = user.first_name if user and user.first_name else "ደንበኛ"
    await update.message.reply_text(
        f"ሰላም ውድ {name}! የፋይዳ ፒዲኤፍ (PDF) ይላኩ፤ ቆርጦ ለፕሪንት ተዘጋጅቶ ይላክልዎታል።",
        reply_markup=MENU_KEYBOARD,
    )

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if text == "Le pdf":
        await update.message.reply_text(
            "📄 PDF ለማውረድ ወደዚህ ቦት ይሂዱ፦ @sedoo_pdf_bot",
            reply_markup=MENU_KEYBOARD,
        )
    elif text == "Le convert":
        await update.message.reply_text(
            "🔄 ፋይል ለማቀናበር እዚሁ ቦት ላይ የፋይዳ PDF ፋይሉን ይላኩልኝ።",
            reply_markup=MENU_KEYBOARD,
        )
    elif text == "Le erdata":
        await update.message.reply_text(
            "🆘 እርዳታ ከፈለጉ @power_worked ን ያነጋግሩ።",
            reply_markup=MENU_KEYBOARD,
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message

    if not message.document or not message.document.file_name.lower().endswith(".pdf"):
        await message.reply_text("እባክዎ ትክክለኛ የፋይዳ (Fayda) PDF ፋይል ብቻ ይላኩ!", reply_markup=MENU_KEYBOARD)
        return

    await message.reply_text("⏳ ፋይሉ እየተቀነባበረ ነው፣ እባክዎ ትንሽ ይጠብቁ...")

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

        id_count = 0

        for p_file in page_files:
            with Image.open(p_file) as base_img:
                img_rgb = base_img.convert("RGB")
                w, h = img_rgb.size

                # ጎን ለጎን የተቀመጡ የፊት (ግራ) እና የኋላ (ቀኝ) ክፍሎችን መለየት
                mid_x = w // 2
                front_card = img_rgb.crop((0, 0, mid_x, h))
                back_card = img_rgb.crop((mid_x, 0, w, h))

                w1, h1 = front_card.size
                w2, h2 = back_card.size

                gap = max(20, int(w * 0.02))
                pad = max(20, int(h * 0.02))

                combined_width = w1 + w2 + gap + (pad * 2)
                combined_height = max(h1, h2) + (pad * 2)

                combined_img = Image.new("RGB", (combined_width, combined_height), (255, 255, 255))
                combined_img.paste(front_card, (pad, pad))
                combined_img.paste(back_card, (pad + w1 + gap, pad))

                id_count += 1
                out_pdf_name = f"Fayda_ID_{user.id}_{id_count}.pdf"
                combined_img.save(out_pdf_name, "PDF", resolution=300)
                output_files.append(out_pdf_name)

        await message.reply_text(f"✅ በጠቅላላው {id_count} መታወቂያዎች ተለይተው ተዘጋጅተዋል!")

        for out_pdf in output_files:
            with open(out_pdf, "rb") as pdf_file:
                await message.reply_document(
                    document=InputFile(pdf_file),
                    caption="🖨️ ለፕሪንት ዝግጁ የሆነ መታወቂያ",
                )

    except Exception as e:
        await message.reply_text(f"❌ ስህተት ተፈጥሯል: {str(e)}")

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    print("ቦቱ በመጀመር ላይ ነው...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
