import os
import asyncio
import google.generativeai as genai # 1. Llama hata diya
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) # Safe kar diya
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # 2. Naya key

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("BOT_TOKEN ya GEMINI_API_KEY missing hai! Render Environment me daal")

genai.configure(api_key=GEMINI_API_KEY)
model_flash = genai.GenerativeModel('gemini-1.5-flash') # Free wala tez model

DB = {} # {user_id: {premium, uses, banned}}
MAINTENANCE = False
reply_mode = {}
user_photos = {}
broadcast_data = {}
yt_waiting = {}

async def get_ai_answer(user_msg, is_premium=False):
    system = "You are CreatorBuddy, a helpful, friendly AI mentor. You never abuse. You solve problems, teach skills, and help earn money. Reply in same language as user."

    if is_premium:
        prompt = f"{system}\nUser: {user_msg}\nGive a detailed, step-by-step answer."
    else:
        prompt = f"{system}\nUser: {user_msg}\nKeep answer short and to the point."

    # FIX: Gemini ko thread me chalao warna block hoga
    response = await asyncio.to_thread(model_flash.generate_content, prompt)
    return response.text.strip()

async def get_yt_analysis(user_input, is_premium=False):
    system = """You are a YouTube Growth Expert + SEO Expert. Goal: Rank video on 1st page.
    If user gives YT Link: Extract topic from link/title and create SEO.
    If user gives Topic: Create SEO for that topic.
    Output in Hindi with this format."""

    if is_premium:
        system += "\nGive EXTREMELY DETAILED answer with 10 title options, 300 word description, 20 tags, 5 hooks, 5 tips."
    else:
        system += "\nGive short answer with 3 titles, 200 word desc, 15 tags, 3 hooks, 3 tips."

    prompt = f"{system}\nUser Input: {user_input}"
    # FIX: Gemini ko thread me chalao
    response = await asyncio.to_thread(model_flash.generate_content, prompt)
    return response.text.strip()

# ========== COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if DB.get(user_id, {}).get("banned"): return await update.message.reply_text("🚫 Banned")
    if MAINTENANCE and user_id!= ADMIN_ID: return await update.message.reply_text("🛠️ Maintenance")

    if user_id not in DB: DB[user_id] = {"premium": False, "uses": 0, "banned": False}
    is_premium = DB[user_id]["premium"]
    is_admin = (user_id == ADMIN_ID)

    msg = f"Hey {update.effective_user.first_name}! Mai CreatorBuddy hun 💪\n⚡ **Fast AI Mentor - Powered by Gemini**\n📚 **FREE:**\n1. Koi bhi sawal - Short Answer\n2. `/message <text>` - Admin se baat\n3. Photo bhej kar - Admin ko direct\n"

    if is_premium or is_admin:
        msg += f"💎 **PREMIUM:**\n4. `/yt <link/topic>` - Detail SEO + 10 Titles\n5. Chat me detailed answer\n6. `/imagine` - Coming Soon\nPremium = Detail + Priority"
    else:
        msg += f"💎 **PREMIUM ME:**\n4. `/yt <link/topic> detail` - Full SEO Pack\n5. Chat me detail answer\n\nPremium lene ke liye: /message premium lena hai"

    await update.message.reply_text(msg)

async def yt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if DB.get(user_id, {}).get("banned"): return

    is_admin = (user_id == ADMIN_ID)
    is_premium = DB.get(user_id, {}).get("premium", False)

    if not is_admin and not is_premium:
        return await update.message.reply_text("🚫 **YT Pro Feature sirf Premium ke liye hai**\n\nAdmin: /message premium lena hai")

    if not context.args:
        return await update.message.reply_text("Use: `/yt https://youtube.com/...` ya `/yt AI se paise kaise kamaye`\nPremium: `/yt topic detail`")

    user_input = " ".join(context.args)
    await update.message.reply_text("🎯 Video analyze kar raha hun... 5 sec")

    analysis = await get_yt_analysis(user_input, is_premium)

    await update.message.reply_text(
        f"{analysis}\n\n"
        f"💡 Ye sab daalte hi video rank karegi. All the best!"
    )

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if DB.get(uid, {}).get("banned"): return
    if MAINTENANCE and uid!= ADMIN_ID: return
    if uid == ADMIN_ID and ADMIN_ID in reply_mode:
        target = reply_mode[ADMIN_ID]
        await context.bot.send_message(chat_id=target, text=f"📢 Admin: {update.message.text}")
        del reply_mode[ADMIN_ID]
        return await update.message.reply_text("Bhej diya ✅")

    is_premium = DB.get(uid, {}).get("premium", False)
    await update.message.reply_text("Soch raha hun...")
    reply = await get_ai_answer(update.message.text, is_premium)
    await update.message.reply_text(reply)

# BAKE SAB COMMAND WAHI RAHEGA
async def imagine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **Coming Soon**")
async def thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **Coming Soon**")
async def thumb_from_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **Coming Soon**")
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if DB.get(uid, {}).get("banned"): return
    msg = " ".join(context.args)
    if not msg: return await update.message.reply_text("Use: /message apna doubt")
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📩 Support from {update.effective_user.first_name} [{uid}]:\n{msg}")
    await update.message.reply_text("Admin ko bhej diya ✅")
async def admin_reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = int(query.data.split("_")[1])
    reply_mode[ADMIN_ID] = uid
    await query.message.reply_text(f"Ab jo likhoge wo {uid} ko jayega")
async def admin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    target = int(context.args[0])
    msg = " ".join(context.args[1:])
    await context.bot.send_message(chat_id=target, text=f"📢 Admin: {msg}")
    await update.message.reply_text("Bhej diya ✅")
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    await update.message.reply_text("👑 Admin Panel\n/stats /ban /unban /premium /maintenance /msg")
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    total = len(DB)
    prem = sum(1 for u in DB.values() if u['premium'])
    await update.message.reply_text(f"📊 Stats\nTotal: {total}\nPremium: {prem}")
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    uid = int(context.args[0])
    DB[uid] = DB.get(uid, {}) | {"banned": True}
    await update.message.reply_text(f"Banned {uid}")
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    uid = int(context.args[0])
    if uid in DB: DB[uid]["banned"] = False
    await update.message.reply_text(f"Unbanned {uid}")
async def maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MAINTENANCE
    if update.effective_user.id!= ADMIN_ID: return
    MAINTENANCE = context.args[0] == "on"
    await update.message.reply_text(f"Maintenance: {'ON' if MAINTENANCE else 'OFF'}")
async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    uid = int(context.args[1])
    DB[uid] = DB.get(uid, {}) | {"premium": True}
    await update.message.reply_text(f"Premium diya {uid} ko")
async def broadcast_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    if 'photo' in broadcast_data:
        for uid in DB.keys():
            try: await context.bot.send_photo(chat_id=uid, photo=broadcast_data['photo'], caption=broadcast_data['caption'])
            except: pass
        await update.message.reply_text("Broadcast ho gaya")
        broadcast_data.clear()
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if DB.get(uid, {}).get("banned"): return
    file_id = update.message.photo[-1].file_id
    caption = update.message.caption if update.message.caption else "No caption"
    if uid!= ADMIN_ID:
        keyboard = [[InlineKeyboardButton("Reply", callback_data=f"reply_{uid}")]]
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=f"📩 Photo from {update.effective_user.first_name} [{uid}]\n{caption}", reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text("Photo Admin ko bhej di ✅")
    else:
        broadcast_data['photo'] = file_id
        broadcast_data['caption'] = caption
        await update.message.reply_text("Broadcast karu? /broadcast yes")

# RENDER FIX - async main
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yt", yt_command))
    app.add_handler(CommandHandler("imagine", imagine))
    app.add_handler(CommandHandler("thumbnail", thumbnail))
    app.add_handler(CommandHandler("thumbfromphoto", thumb_from_photo))
    app.add_handler(CommandHandler("message", user_message))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("maintenance", maintenance))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("msg", admin_msg))
    app.add_handler(CommandHandler("broadcast", broadcast_yes))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    app.add_handler(CallbackQueryHandler(admin_reply_button))

    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
