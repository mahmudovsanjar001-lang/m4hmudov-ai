import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# ============================================================
#  SOZLAMALAR — bu yerga o'z kalitlaringizni kiriting
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8512966183:AAELIhNU6BQNmQ4VFkhTAoI5ewPcXZW97NE")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY",  "AIzaSyCMsz882FlOQWZDGFAJf4ExMDuiDGKeTBc")

# Gemini ni sozlash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")  # bepul model

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
#  FOYDALANUVCHI MA'LUMOTLARI (xotira)
# ============================================================
# { user_id: { "history": [...], "mode": "chat" } }
user_data_store: dict = {}

def get_user(user_id: int) -> dict:
    if user_id not in user_data_store:
        user_data_store[user_id] = {
            "history": [],
            "mode": "chat",       # chat | translate | code | summarize
            "lang": "uz",         # javob tili
        }
    return user_data_store[user_id]


# ============================================================
#  ASOSIY MENYULAR
# ============================================================
def main_menu_keyboard():
    """Asosiy tugmalar menyusi"""
    keyboard = [
        ["💬 Suhbat", "🌐 Tarjima"],
        ["💻 Kod yozish", "📝 Xulosa chiqarish"],
        ["⚙️ Sozlamalar", "🗑 Tarixni tozalash"],
        ["ℹ️ Yordam"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def settings_inline_keyboard(user_id: int):
    """Sozlamalar uchun inline tugmalar"""
    user = get_user(user_id)
    mode = user["mode"]
    lang = user["lang"]

    lang_uz = "✅ O'zbek" if lang == "uz" else "O'zbek"
    lang_ru = "✅ Русский" if lang == "ru" else "Русский"
    lang_en = "✅ English"  if lang == "en" else "English"

    keyboard = [
        [InlineKeyboardButton("🌍 Til tanlash:", callback_data="noop")],
        [
            InlineKeyboardButton(lang_uz, callback_data="lang_uz"),
            InlineKeyboardButton(lang_ru, callback_data="lang_ru"),
            InlineKeyboardButton(lang_en, callback_data="lang_en"),
        ],
        [InlineKeyboardButton("📌 Rejim:", callback_data="noop")],
        [
            InlineKeyboardButton("💬 Suhbat" if mode != "chat" else "✅ Suhbat",      callback_data="mode_chat"),
            InlineKeyboardButton("🌐 Tarjima" if mode != "translate" else "✅ Tarjima", callback_data="mode_translate"),
        ],
        [
            InlineKeyboardButton("💻 Kod" if mode != "code" else "✅ Kod",            callback_data="mode_code"),
            InlineKeyboardButton("📝 Xulosa" if mode != "summarize" else "✅ Xulosa",  callback_data="mode_summarize"),
        ],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================
#  GEMINI BILAN GAPLASHISH
# ============================================================
async def ask_gemini(user_id: int, user_text: str) -> str:
    user = get_user(user_id)
    mode = user["mode"]
    lang = user["lang"]

    lang_names = {"uz": "o'zbek", "ru": "rus", "en": "ingliz"}
    lang_name = lang_names.get(lang, "o'zbek")

    # Rejimga qarab system prompt
    if mode == "chat":
        system = f"Sen foydali AI yordamchisan. Foydalanuvchiga {lang_name} tilida javob ber. Qisqa va aniq bo'l."
    elif mode == "translate":
        system = f"Sen tarjimon. Berilgan matnni {lang_name} tiliga tarjima qil. Faqat tarjimani ber, tushuntirma yozma."
    elif mode == "code":
        system = f"Sen dasturchi AI. Foydalanuvchi so'ragan kodni yoz. Kodga izoh ber. {lang_name} tilida tushuntir."
    elif mode == "summarize":
        system = f"Sen matn tahlilchisi. Berilgan matnning qisqa xulosasini {lang_name} tilida ber."
    else:
        system = f"{lang_name} tilida javob ber."

    # Suhbat tarixini qo'shish
    history = user["history"]
    history.append({"role": "user", "parts": [user_text]})

    # Tarixni 20 ta xabarga cheklash (token tejash)
    if len(history) > 20:
        history = history[-20:]
        user["history"] = history

    try:
        chat = model.start_chat(history=history[:-1])
        full_prompt = f"{system}\n\nFoydalanuvchi: {user_text}"
        response = chat.send_message(full_prompt)
        reply = response.text

        # AI javobini tarixga qo'shish
        history.append({"role": "model", "parts": [reply]})
        user["history"] = history

        return reply
    except Exception as e:
        logger.error(f"Gemini xatosi: {e}")
        return f"❌ Xato yuz berdi: {str(e)}\n\nIltimos, qayta urinib ko'ring."


# ============================================================
#  HANDLERS — KOMANDALAR
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id)  # foydalanuvchini ro'yxatga olish

    text = (
        f"Salom, {user.first_name}! 👋\n\n"
        "Men Gemini AI bilan ishlaydigon aqlli botman.\n\n"
        "📌 *Nima qila olaman:*\n"
        "• 💬 Savollaringizga javob beraman\n"
        "• 🌐 Matnlarni tarjima qilaman\n"
        "• 💻 Kod yozib beraman\n"
        "• 📝 Matnlardan xulosa chiqaraman\n\n"
        "Pastdagi menyudan foydalaning yoki savol yozing!"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ *Yordam*\n\n"
        "*Buyruqlar:*\n"
        "/start — Botni boshlash\n"
        "/help — Yordam\n"
        "/clear — Tarixni tozalash\n"
        "/mode — Rejim o'zgartirish\n"
        "/settings — Sozlamalar\n\n"
        "*Rejimlar:*\n"
        "💬 *Suhbat* — Oddiy suhbat\n"
        "🌐 *Tarjima* — Matn tarjima\n"
        "💻 *Kod* — Dasturlash\n"
        "📝 *Xulosa* — Qisqa xulosa\n\n"
        "*Maslahat:* Rasm yuborsangiz, uni ham tahlil qilaman!"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    user["history"] = []
    await update.message.reply_text(
        "🗑 Suhbat tarixi tozalandi!\nYangi suhbat boshlashingiz mumkin.",
        reply_markup=main_menu_keyboard()
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    mode_names = {"chat": "💬 Suhbat", "translate": "🌐 Tarjima", "code": "💻 Kod", "summarize": "📝 Xulosa"}
    lang_names  = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}

    text = (
        f"⚙️ *Sozlamalar*\n\n"
        f"📌 Joriy rejim: {mode_names.get(user['mode'], user['mode'])}\n"
        f"🌍 Til: {lang_names.get(user['lang'], user['lang'])}\n\n"
        "Quyidagi tugmalar orqali o'zgartiring:"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=settings_inline_keyboard(user_id)
    )


# ============================================================
#  HANDLERS — TUGMA BOSIMLARI (ReplyKeyboard)
# ============================================================
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user = get_user(user_id)

    if text == "💬 Suhbat":
        user["mode"] = "chat"
        await update.message.reply_text(
            "💬 *Suhbat rejimi* yoqildi!\nSavolingizni yozing.",
            parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )
    elif text == "🌐 Tarjima":
        user["mode"] = "translate"
        lang_names = {"uz": "o'zbek", "ru": "rus", "en": "ingliz"}
        await update.message.reply_text(
            f"🌐 *Tarjima rejimi* yoqildi!\n"
            "Matnni yuboring — tarjima qilaman.\n"
            f"(Tilni ⚙️ Sozlamalar dan o'zgartiring)",
            parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )
    elif text == "💻 Kod yozish":
        user["mode"] = "code"
        await update.message.reply_text(
            "💻 *Kod yozish rejimi* yoqildi!\n"
            "Qanday kod kerakligini yozing.\n\n"
            "Masalan: *Python da kalkulyator yoz*",
            parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )
    elif text == "📝 Xulosa chiqarish":
        user["mode"] = "summarize"
        await update.message.reply_text(
            "📝 *Xulosa rejimi* yoqildi!\n"
            "Matnni yuboring — qisqa xulosasini chiqaraman.",
            parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )
    elif text == "⚙️ Sozlamalar":
        await settings_command(update, context)
    elif text == "🗑 Tarixni tozalash":
        await clear_history(update, context)
    elif text == "ℹ️ Yordam":
        await help_command(update, context)
    else:
        # Oddiy xabar — AI ga yuborish
        await handle_message(update, context)


# ============================================================
#  HANDLERS — INLINE TUGMALAR (Sozlamalar)
# ============================================================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)
    data = query.data

    if data == "noop":
        return

    elif data.startswith("lang_"):
        lang = data.replace("lang_", "")
        user["lang"] = lang
        lang_names = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
        await query.answer(f"Til: {lang_names.get(lang, lang)}", show_alert=False)
        await query.edit_message_reply_markup(reply_markup=settings_inline_keyboard(user_id))

    elif data.startswith("mode_"):
        mode = data.replace("mode_", "")
        user["mode"] = mode
        mode_names = {"chat": "💬 Suhbat", "translate": "🌐 Tarjima", "code": "💻 Kod", "summarize": "📝 Xulosa"}
        await query.answer(f"Rejim: {mode_names.get(mode, mode)}", show_alert=False)
        await query.edit_message_reply_markup(reply_markup=settings_inline_keyboard(user_id))

    elif data == "back_main":
        await query.edit_message_text("Asosiy menyu:", reply_markup=None)


# ============================================================
#  HANDLERS — MATN XABARLARI
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # "Yozmoqda..." ko'rsatish
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    reply = await ask_gemini(user_id, user_text)

    # Javob 4096 dan uzun bo'lsa bo'lib yuborish
    if len(reply) > 4096:
        for i in range(0, len(reply), 4096):
            await update.message.reply_text(reply[i:i+4096])
    else:
        await update.message.reply_text(reply, reply_markup=main_menu_keyboard())


# ============================================================
#  HANDLERS — RASM / FAYL
# ============================================================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rasmni Gemini Vision bilan tahlil qilish"""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    photo = update.message.photo[-1]  # eng katta o'lcham
    file = await context.bot.get_file(photo.file_id)

    import httpx
    async with httpx.AsyncClient() as client:
        img_bytes = await client.get(file.file_path)

    import PIL.Image
    import io
    image = PIL.Image.open(io.BytesIO(img_bytes.content))

    caption = update.message.caption or "Bu rasmda nima bor? Batafsil tushuntir."

    try:
        vision_model = genai.GenerativeModel("gemini-1.5-flash")
        response = vision_model.generate_content([caption, image])
        reply = response.text
    except Exception as e:
        reply = f"❌ Rasm tahlil qilishda xato: {e}"

    await update.message.reply_text(reply, reply_markup=main_menu_keyboard())


# ============================================================
#  MAIN — BOTNI ISHGA TUSHIRISH
# ============================================================
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Komandalar
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("help",     help_command))
    app.add_handler(CommandHandler("clear",    clear_history))
    app.add_handler(CommandHandler("settings", settings_command))

    # Inline tugmalar
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Rasmlar
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Matn (menyular + oddiy xabarlar)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))

    logger.info("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
