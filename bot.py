import os
import subprocess
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image

TOKEN = os.environ.get("")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ሰላም! 🤖 የፋይዳ ፒዲኤፍ (PDF) ይላኩኝ፤ ቆርጦ ለፕሪንት አዘጋጅቼ እልክልዎታለሁ።")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    
    if not message.document or not message.document.file_name.lower().endswith('.pdf'):
        await message.reply_text("እባክዎ ትክክለኛ የፋይዳ (Fayda) PDF ፋይል ብቻ ይላኩ!")
        return

    await message.reply_text("⏳ ፋይሉ እየተቀነባበረ ነው፣ እባክዎ ትንሽ ይጠብቁ...")

    try:
        file = await context.bot.get_file(message.document.file_id)
        pdf_path = f"downloaded_{user.id}.pdf"
        await file.download_to_drive(pdf_path)

        subprocess.run(["pdftoppm", "-png", "-r", "300", pdf_path, f"page_{user.id}"], check=True)
        
        page_files = sorted([f for f in os.listdir('.') if f.startswith(f"page_{user.id}") and f.endswith('.png')])
        
        id_count = 0
        output_files = []

        for p_file in page_files:
            base_img = Image.open(p_file)
            
            front_card = base_img.crop((1648, 374, 2314, 1389))
            back_card = base_img.crop((1654, 1404, 2307, 2404))

            w1, h1 = front_card.size
            w2, h2 = back_card.size
            
            combined_width = w1 + w2 + 60
            combined_height = max(h1, h2) + 60
            
            combined_img = Image.new("RGB", (combined_width, combined_height), (255, 255, 255))
            combined_img.paste(front_card, (30, 30))
            combined_img.paste(back_card, (w1 + 50, 30))

            id_count += 1
            out_pdf_name = f"Fayda_ID_{user.id}_{id_count}.pdf"
            combined_img.save(out_pdf_name, "PDF", resolution=300)
            output_files.append(out_pdf_name)

        await message.reply_text(f"✅ በጠቅላላው {id_count} መታወቂያዎች ተለይተው ተዘጋጅተዋል!")
        
        for out_pdf in output_files:
            with open(out_pdf, 'rb') as pdf_file:
                await message.reply_document(
                    document=InputFile(pdf_file),
                    caption=f"🖨️ ለፕሪንት ዝግጁ የሆነ መታወቂያ"
                )

        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        for p_file in page_files:
            if os.path.exists(p_file):
                os.remove(p_file)
        for out_pdf in output_files:
            if os.path.exists(out_pdf):
                os.remove(out_pdf)

    except Exception as e:
        await message.reply_text(f"❌ ስህተት ተፈጥሯል: {str(e)}")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    print("ቦቱ በመጀመር ላይ ነው...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
