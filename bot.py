import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
Application, CommandHandler, CallbackQueryHandler,
MessageHandler, filters, ContextTypes, ConversationHandler
)
from config import BOT_TOKEN, ADMIN_IDS, CHANNEL_ID

logging.basicConfig(format=’%(asctime)s - %(levelname)s - %(message)s’, level=logging.INFO)
logger = logging.getLogger(**name**)

SUBMIT_TEXT, SUBMIT_PHOTO = range(2)
REJECT_REASON = 10

# ===================== מסד נתונים =====================

def init_db():
conn = sqlite3.connect(‘posts.db’)
conn.execute(’’‘CREATE TABLE IF NOT EXISTS pending_posts (
post_id TEXT PRIMARY KEY,
user_id INTEGER,
username TEXT,
text TEXT,
photo_id TEXT
)’’’)
conn.commit()
conn.close()

def save_post(post_id, user_id, username, text, photo_id):
conn = sqlite3.connect(‘posts.db’)
conn.execute(“INSERT OR REPLACE INTO pending_posts VALUES (?,?,?,?,?)”,
(post_id, user_id, username, text, photo_id))
conn.commit()
conn.close()

def get_all_posts():
conn = sqlite3.connect(‘posts.db’)
rows = conn.execute(“SELECT * FROM pending_posts”).fetchall()
conn.close()
return [{‘post_id’: r[0], ‘user_id’: r[1], ‘username’: r[2], ‘text’: r[3], ‘photo’: r[4]} for r in rows]

def get_post(post_id):
conn = sqlite3.connect(‘posts.db’)
r = conn.execute(“SELECT * FROM pending_posts WHERE post_id=?”, (post_id,)).fetchone()
conn.close()
if r:
return {‘post_id’: r[0], ‘user_id’: r[1], ‘username’: r[2], ‘text’: r[3], ‘photo’: r[4]}
return None

def delete_post(post_id):
conn = sqlite3.connect(‘posts.db’)
conn.execute(“DELETE FROM pending_posts WHERE post_id=?”, (post_id,))
conn.commit()
conn.close()

def is_admin(user_id):
return user_id in ADMIN_IDS

# ===================== START =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user = update.effective_user
if is_admin(user.id):
keyboard = [
[InlineKeyboardButton(“🎉 שלח מסיבה לפרסום”, callback_data=“submit_post”)],
[InlineKeyboardButton(“📋 ממתינים לאישור”, callback_data=“pending_list”)],
]
await update.message.reply_text(
f”👋 שלום {user.first_name}!\n\n🛠 *פאנל אדמין — מסיבות בישראל*”,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode=“Markdown”
)
else:
keyboard = [[InlineKeyboardButton(“🎉 שלח מסיבה לפרסום”, callback_data=“submit_post”)]]
await update.message.reply_text(
f”👋 שלום {user.first_name}!\n\nברוך הבא לבוט *מסיבות בישראל* 🎉\n\nרוצה לפרסם מסיבה? לחץ כאן 👇”,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode=“Markdown”
)

# ===================== שליחת מסיבה =====================

async def submit_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
keyboard = [[InlineKeyboardButton(“❌ ביטול”, callback_data=“cancel”)]]
await query.edit_message_text(
“🎉 *שליחת מסיבה לפרסום*\n\n”
“שלח את *תיאור המסיבה*:\n\n”
“כתוב הכל במסר אחד:\n”
“• שם המסיבה\n• תאריך ושעה\n• מיקום\n• DJ / אמנים\n• כל פרט שתרצה”,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode=“Markdown”
)
return SUBMIT_TEXT

async def submit_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data[‘post_text’] = update.message.text
keyboard = [[InlineKeyboardButton(“⏭ דלג (ללא תמונה)”, callback_data=“skip_photo”)]]
await update.message.reply_text(
“📸 שלח *פליייר/תמונה*\n\n_או לחץ דלג_”,
reply_markup=InlineKeyboardMarkup(keyboard),
parse_mode=“Markdown”
)
return SUBMIT_PHOTO

async def submit_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data[‘post_photo’] = update.message.photo[-1].file_id
user = update.effective_user
post_id = f”{user.id}_{update.message.message_id}”
await _save_and_notify(context, post_id, user, context.user_data[‘post_text’], context.user_data[‘post_photo’])
await update.message.reply_text(“✅ *הפרסום שלך נשלח לאישור!*\n\nתקבל עדכון בקרוב 🙏”, parse_mode=“Markdown”)
return ConversationHandler.END

async def submit_skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
user = query.from_user
post_id = f”{user.id}_{query.message.message_id}”
await _save_and_notify(context, post_id, user, context.user_data[‘post_text’], None)
await query.edit_message_text(“✅ *הפרסום שלך נשלח לאישור!*\n\nתקבל עדכון בקרוב 🙏”, parse_mode=“Markdown”)
return ConversationHandler.END

async def *save_and_notify(context, post_id, user, text, photo):
save_post(post_id, user.id, user.username or user.first_name, text, photo)
keyboard = [
[InlineKeyboardButton(“✅ אשר ופרסם”, callback_data=f”approve*{post_id}”),
InlineKeyboardButton(“❌ דחה”, callback_data=f”reject_{post_id}”)]
]
admin_text = (
f”🔔 *פרסום חדש ממתין לאישור!*\n\n”
f”👤 שולח: @{user.username or user.first_name} (`{user.id}`)\n\n”
f”📝 *תוכן:*\n{text}”
)
for admin_id in ADMIN_IDS:
try:
if photo:
await context.bot.send_photo(admin_id, photo, caption=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
else:
await context.bot.send_message(admin_id, admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
except Exception as e:
logger.error(f”Admin notify error: {e}”)

# ===================== אישור =====================

async def approve_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
post_id = query.data.replace(“approve_”, “”)
post = get_post(post_id)
if not post:
await query.answer(“❌ הפרסום לא נמצא או כבר טופל.”, show_alert=True)
return
try:
if post[‘photo’]:
await context.bot.send_photo(CHANNEL_ID, post[‘photo’], caption=f”🎉 *מסיבות בישראל*\n\n{post[‘text’]}”, parse_mode=“Markdown”)
else:
await context.bot.send_message(CHANNEL_ID, f”🎉 *מסיבות בישראל*\n\n{post[‘text’]}”, parse_mode=“Markdown”)

```
    try:
        if post['photo']:
            await query.edit_message_caption("✅ *אושר ופורסם בערוץ!*", parse_mode="Markdown")
        else:
            await query.edit_message_text("✅ *אושר ופורסם בערוץ!*", parse_mode="Markdown")
    except: pass

    await context.bot.send_message(post['user_id'], "🎉 *הפרסום שלך אושר ופורסם בערוץ!*\n\nתודה 🙏", parse_mode="Markdown")
except Exception as e:
    await context.bot.send_message(query.from_user.id, f"❌ שגיאה: {str(e)}")
delete_post(post_id)
```

# ===================== דחייה =====================

async def reject_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
post_id = query.data.replace(“reject_”, “”)
post = get_post(post_id)
if not post:
await query.answer(“❌ הפרסום לא נמצא.”, show_alert=True)
return
context.user_data[‘rejecting_post_id’] = post_id
keyboard = [
[InlineKeyboardButton(“🌊 הצפת ערוץ”, callback_data=“reason_flood”)],
[InlineKeyboardButton(“🚫 לא מתאים לתוכן”, callback_data=“reason_content”)],
[InlineKeyboardButton(“📅 כפול / כבר פורסם”, callback_data=“reason_duplicate”)],
[InlineKeyboardButton(“📝 חסר פרטים”, callback_data=“reason_missing”)],
[InlineKeyboardButton(“✏️ סיבה אחרת”, callback_data=“reason_custom”)],
]
try:
if post[‘photo’]:
await query.edit_message_caption(“❌ *בחר סיבת דחייה:*”, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
else:
await query.edit_message_text(“❌ *בחר סיבת דחייה:*”, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=“Markdown”)
except Exception as e:
logger.error(f”Reject error: {e}”)

async def reject_with_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
reasons = {
“reason_flood”: “הערוץ מוגבל כרגע בכמות הפרסומים — נסה שוב מאוחר יותר 🌊”,
“reason_content”: “הפרסום אינו מתאים לתוכן הערוץ 🚫”,
“reason_duplicate”: “פרסום זהה כבר קיים בערוץ 📅”,
“reason_missing”: “הפרסום חסר פרטים — אנא השלם ושלח מחדש 📝”,
}
reason_key = query.data
post_id = context.user_data.get(‘rejecting_post_id’)
post = get_post(post_id)

```
if reason_key == "reason_custom":
    await query.edit_message_text("✏️ *כתוב את סיבת הדחייה:*", parse_mode="Markdown")
    return REJECT_REASON

if not post:
    return ConversationHandler.END

await _send_rejection(context, post, post_id, reasons[reason_key], query)
return ConversationHandler.END
```

async def reject_custom_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
post_id = context.user_data.get(‘rejecting_post_id’)
post = get_post(post_id)
if post:
await _send_rejection(context, post, post_id, update.message.text.strip(), None)
await update.message.reply_text(“✅ הדחייה נשלחה.”)
return ConversationHandler.END

async def _send_rejection(context, post, post_id, reason, query):
try:
await context.bot.send_message(
post[‘user_id’],
f”❌ *הפרסום שלך לא אושר*\n\n*סיבה:* {reason}\n\nאתה מוזמן לתקן ולשלוח מחדש 🙏”,
parse_mode=“Markdown”
)
except Exception as e:
logger.error(f”Reject notify error: {e}”)
if query:
try:
if post[‘photo’]:
await query.edit_message_caption(f”❌ *נדחה*\nסיבה: {reason}”, parse_mode=“Markdown”)
else:
await query.edit_message_text(f”❌ *נדחה*\nסיבה: {reason}”, parse_mode=“Markdown”)
except: pass
delete_post(post_id)

# ===================== רשימת ממתינים =====================

async def pending_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
posts = get_all_posts()
if not posts:
await query.edit_message_text(
“✅ *אין פרסומים ממתינים*”,
reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(“🔙 חזור”, callback_data=“back_start”)]]),
parse_mode=“Markdown”
)
return

```
await query.edit_message_text(f"📋 *{len(posts)} פרסומים ממתינים:*", parse_mode="Markdown")

for post in posts:
    keyboard = [
        [InlineKeyboardButton("✅ אשר ופרסם", callback_data=f"approve_{post['post_id']}"),
         InlineKeyboardButton("❌ דחה", callback_data=f"reject_{post['post_id']}")]
    ]
    admin_text = (
        f"🔔 *ממתין לאישור*\n\n"
        f"👤 @{post['username']} (`{post['user_id']}`)\n\n"
        f"📝 {post['text']}"
    )
    try:
        if post['photo']:
            await context.bot.send_photo(query.from_user.id, post['photo'], caption=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await context.bot.send_message(query.from_user.id, admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Pending list send error: {e}")
```

# ===================== callbacks =====================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
keyboard = [[InlineKeyboardButton(“🎉 שלח מסיבה לפרסום”, callback_data=“submit_post”)]]
await query.edit_message_text(“בוטל.”, reply_markup=InlineKeyboardMarkup(keyboard))
return ConversationHandler.END

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
data = update.callback_query.data
if data == “pending_list”:
await pending_list(update, context)
elif data == “back_start”:
await update.callback_query.answer()
user = update.effective_user
if is_admin(user.id):
keyboard = [[InlineKeyboardButton(“🎉 שלח מסיבה לפרסום”, callback_data=“submit_post”)], [InlineKeyboardButton(“📋 ממתינים לאישור”, callback_data=“pending_list”)]]
else:
keyboard = [[InlineKeyboardButton(“🎉 שלח מסיבה לפרסום”, callback_data=“submit_post”)]]
await update.callback_query.edit_message_text(“בחר פעולה:”, reply_markup=InlineKeyboardMarkup(keyboard))
elif data.startswith(“approve_”):
await approve_post(update, context)

# ===================== הפעלה =====================

def main():
init_db()
app = Application.builder().token(BOT_TOKEN).build()

```
submit_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(submit_post_start, pattern="^submit_post$")],
    states={
        SUBMIT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, submit_text_received)],
        SUBMIT_PHOTO: [
            MessageHandler(filters.PHOTO, submit_photo_received),
            CallbackQueryHandler(submit_skip_photo, pattern="^skip_photo$"),
        ],
    },
    fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
)

reject_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(reject_post, pattern="^reject_")],
    states={
        0: [CallbackQueryHandler(reject_with_reason, pattern="^reason_")],
        REJECT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, reject_custom_reason)],
    },
    fallbacks=[],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(submit_conv)
app.add_handler(reject_conv)
app.add_handler(CallbackQueryHandler(callback_handler))

logger.info("🤖 הבוט פועל!")
app.run_polling(drop_pending_updates=True)
```

if **name** == “**main**”:
main()
