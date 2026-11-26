import os
import io
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from pypdf import PdfReader, PdfWriter, Transformation


TOKEN = os.getenv("BOT_TOKEN")

MAX_FILES = 5

A4_WIDTH = 595.28
A4_HEIGHT = 841.89

user_files = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_files[update.effective_user.id] = []

    text = (
        "👋 እንኳን ወደ Fayda PDF Converter በደህና መጡ!\n\n"
        "📄 PDF ፋይሎችን ይላኩ።\n\n"
        "📌 እስከ 5 PDF መላክ ይችላሉ።\n"
        "📌 እያንዳንዱ ለየብቻ ይዘጋጃል።\n"
        "📌 A4 Print ይሆናል።\n\n"
        "🚀 ለመጀመር PDF ይላኩ።"
    )

    await update.message.reply_text(text)


async def receive_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if user_id not in user_files:
        user_files[user_id] = []

    if len(user_files[user_id]) >= MAX_FILES:
        await update.message.reply_text(
            "⚠️ 5 PDF ደርሰዋል። /done ብለው ይጨርሱ።"
        )
        return

    document = update.message.document

    if not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text(
            "❌ PDF ፋይል ብቻ ይላኩ።"
        )
        return

    if document.file_size > 15 * 1024 * 1024:
        await update.message.reply_text(
            "⚠️ ፋይሉ ከ15MB በላይ ነው።"
        )
        return

    file = await context.bot.get_file(document.file_id)

    data = await file.download_as_bytearray()

    user_files[user_id].append({
        "name": document.file_name,
        "data": bytes(data)
    })

    count = len(user_files[user_id])

    await update.message.reply_text(
        f"✅ PDF ተቀብለናል።\n\n"
        f"📄 የተቀበልነው: {count}/5\n\n"
        "ተጨማሪ PDF ይላኩ ወይም /done ይጫኑ።"
    )


def prepare_pdf(pdf_data):

    reader = PdfReader(io.BytesIO(pdf_data))
    writer = PdfWriter()

    if reader.is_encrypted:
        raise ValueError("Encrypted PDF")

    for page in reader.pages:

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        margin = 20

        available_width = A4_WIDTH - margin * 2
        available_height = A4_HEIGHT - margin * 2

        scale = min(
            available_width / width,
            available_height / height
        )

        new_width = width * scale
        new_height = height * scale

        x = (A4_WIDTH - new_width) / 2
        y = (A4_HEIGHT - new_height) / 2

        output_page = writer.add_blank_page(
            width=A4_WIDTH,
            height=A4_HEIGHT
        )

        transform = (
            Transformation()
            .scale(scale)
            .translate(x, y)
        )

        output_page.merge_transformed_page(
            page,
            transform
        )

    output = io.BytesIO()

    writer.write(output)

    output.seek(0)

    return output


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    files = user_files.get(user_id, [])

    if not files:
        await update.message.reply_text(
            "❌ PDF አልተላከም።"
        )
        return

    await update.message.reply_text(
        "⏳ PDF ፋይሎችዎን እያዘጋጀን ነው..."
    )

    for index, item in enumerate(files, start=1):

        try:

            result = prepare_pdf(item["data"])

            filename = f"Fayda_Print_{index}.pdf"

            await update.message.reply_document(
                document=result,
                filename=filename,
                caption=f"✅ PDF {index} ተዘጋጅቷል።"
            )

        except Exception as error:

            logging.exception("PDF processing error")

            await update.message.reply_text(
                f"❌ PDF {index} ማዘጋጀት አልተቻለም።"
            )

    user_files[user_id] = []

    await update.message.reply_text(
        "🎉 ሥራው ተጠናቋል!\n\n"
        "ሌላ PDF ለመጀመር /start ይጫኑ።"
    )


def main():

    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("done", done))

    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            receive_pdf
        )
    )

    print("Fayda PDF Converter is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
