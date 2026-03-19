import logging
import asyncio
from datetime import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from config import BOT_TOKEN, ADMIN_IDS, GROUP_IDS
from database import Database

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BROADCAST_MESSAGE, BROADCAST_CONFIRM = range(2)
ADD_CHANNEL, REMOVE_CHANNEL = range(2, 4)
BAN_USER, UNBAN_USER = range(4, 6)
(EVENT_NAME, EVENT_DJ, EVENT_LOCATION, EVENT_DATE, EVENT_LINK, EVENT_FLYER, EVENT_CONFIRM) = range(6, 13)
(AUTO_MSG_TEXT, AUTO_MSG_TIME) = range(13, 15)
(CUSTOM_BTN_TEXT, CUSTOM_BTN_URL) = range(15, 17)
RULES_EDIT = 17

db = Database()

SITE_URL = "https://www.talkingbdsm.net/"

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ===================== START =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.first_name or "")
    if is_admin(user.id):
        await show_admin_panel(update, context)
    else:
        keyboard = [
            [InlineKeyboardButton("🌐 האתר שלנו", url=SITE_URL)],
            [InlineKeyboardButton("📜 חוקי הקבוצה", callback_data="show_rules"),
             InlineKeyboardButton("📢 ערוצים", callback_data="show_channels")],
        ]
        await update.message.reply_text(
            f"👋 שלום {user.first_name}!\nברוך הבא לבוט *מסיבות בישראל* 🎉\n\nבחר מה שמעניין אותך:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

# ===================== פאנל אדמין =====================

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎉 פרסום אירוע", callback_data="event_publish"),
         InlineKeyboardButton("📢 פרסום חופשי", callback_data="broadcast")],
        [InlineKeyboardButton("📋 ניהול ערוצים", callback_data="manage_channels"),
         InlineKeyboardButton("👥 ניהול משתמשים", callback_data="manage_users")],
        [InlineKeyboardButton("⏰ הודעות אוטומטיות", callback_data="auto_messages"),
         InlineKeyboardButton("🔘 כפתורים מותאמים", callback_data="custom_buttons")],
        [InlineKeyboardButton("📜 ערוך חוקים", callback_data="edit_rules"),
         InlineKeyboardButton("📊 סטטיסטיקות", callback_data="stats")],
    ]
    text = "🛠 *פאנל ניהול — מסיבות בישראל*\n\nבחר פעולה:"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ===================== חוקי קבוצה =====================

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rules = db.get_rules()
    keyboard = [[InlineKeyboardButton("🔙 חזור", callback_data="back_start")]]
    await query.edit_message_text(
        rules or "📜 *חוקי הקבוצה*\n\nהחוקים טרם הוגדרו.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def edit_rules_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    current = db.get_rules() or "טרם הוגדרו"
    keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="admin_panel")]]
    await query.edit_message_text(
        f"📜 *עריכת חוקי הקבוצה*\n\n*החוקים הנוכחיים:*\n{current}\n\n✏️ שלח את החוקים החדשים:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return RULES_EDIT

async def edit_rules_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_rules(update.message.text.strip())
    await update.message.reply_text("✅ החוקים עודכנו בהצלחה!")
    return ConversationHandler.END

# ===================== כפתורים מותאמים =====================

async def custom_buttons_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buttons = db.get_custom_buttons()
    buttons_text = "\n".join([f"• {b['text']} → {b['url']}" for b in buttons]) if buttons else "אין כפתורים מותאמים"
    keyboard = [
        [InlineKeyboardButton("➕ הוסף כפתור", callback_data="add_custom_btn")],
        [InlineKeyboardButton("🗑 מחק כפתור", callback_data="del_custom_btn")],
        [InlineKeyboardButton("👁 הצג תפריט לקבוצה", callback_data="preview_group_menu")],
        [InlineKeyboardButton("🔙 חזור", callback_data="admin_panel")]
    ]
    await query.edit_message_text(
        f"🔘 *כפתורים מותאמים*\n\n{buttons_text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def add_custom_btn_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="custom_buttons")]]
    await query.edit_message_text(
        "➕ *הוספת כפתור חדש*\n\nשלב 1 — מה *הטקסט* של הכפתור?\n\nלדוגמה: `🎵 הפלייליסט שלנו`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CUSTOM_BTN_TEXT

async def add_custom_btn_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['btn_text'] = update.message.text.strip()
    keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="custom_buttons")]]
    await update.message.reply_text(
        f"✅ טקסט: *{context.user_data['btn_text']}*\n\nשלב 2 — מה ה*לינק* של הכפתור?\n\nלדוגמה: `https://open.spotify.com/...`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CUSTOM_BTN_URL

async def add_custom_btn_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ הלינק חייב להתחיל ב-`https://`", parse_mode="Markdown")
        return CUSTOM_BTN_URL
    db.add_custom_button(context.user_data['btn_text'], url)
    await update.message.reply_text(f"✅ הכפתור *{context.user_data['btn_text']}* נוסף!", parse_mode="Markdown")
    return ConversationHandler.END

async def del_custom_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buttons = db.get_custom_buttons()
    if not buttons:
        await query.edit_message_text("אין כפתורים למחיקה.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזור", callback_data="custom_buttons")]]))
        return
    keyboard = [[InlineKeyboardButton(f"🗑 {b['text']}", callback_data=f"del_btn_{b['id']}")] for b in buttons]
    keyboard.append([InlineKeyboardButton("❌ ביטול", callback_data="custom_buttons")])
    await query.edit_message_text("בחר כפתור למחיקה:", reply_markup=InlineKeyboardMarkup(keyboard))

async def del_btn_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    btn_id = int(query.data.replace("del_btn_", ""))
    db.delete_custom_button(btn_id)
    await query.edit_message_text("✅ הכפתור נמחק!")

async def preview_group_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = build_group_menu()
    await query.edit_message_text(
        "👁 *תצוגה מקדימה של תפריט הקבוצה:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def build_group_menu():
    keyboard = [
        [InlineKeyboardButton("🌐 האתר שלנו", url=SITE_URL)],
        [InlineKeyboardButton("📜 חוקי הקבוצה", callback_data="show_rules"),
         InlineKeyboardButton("📢 ערוצים", callback_data="show_channels")],
    ]
    buttons = db.get_custom_buttons()
    for b in buttons:
        keyboard.append([InlineKeyboardButton(b['text'], url=b['url'])])
    return keyboard

# ===================== הודעות אוטומטיות =====================

async def auto_messages_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msgs = db.get_auto_messages()
    msgs_text = "\n".join([f"• {m['send_time']} — {m['text'][:30]}..." for m in msgs]) if msgs else "אין הודעות אוטומטיות"
    keyboard = [
        [InlineKeyboardButton("➕ הוסף הודעה אוטומטית", callback_data="add_auto_msg")],
        [InlineKeyboardButton("🗑 מחק הודעה", callback_data="del_auto_msg")],
        [InlineKeyboardButton("🔙 חזור", callback_data="admin_panel")]
    ]
    await query.edit_message_text(
        f"⏰ *הודעות אוטומטיות*\n\n{msgs_text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def add_auto_msg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="auto_messages")]]
    await query.edit_message_text(
        "➕ *הוספת הודעה אוטומטית*\n\nשלב 1 — מה *תוכן ההודעה*?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return AUTO_MSG_TEXT

async def add_auto_msg_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['auto_text'] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("18:00 ערב", callback_data="auto_time_18:00")],
        [InlineKeyboardButton("08:00 בוקר", callback_data="auto_time_08:00")],
        [InlineKeyboardButton("22:00 לילה", callback_data="auto_time_22:00")],
        [InlineKeyboardButton("⌨️ שעה אחרת", callback_data="auto_time_custom")],
    ]
    await update.message.reply_text(
        "שלב 2 — באיזו *שעה* לשלוח? (כל יום)",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return AUTO_MSG_TIME

async def add_auto_msg_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "auto_time_custom":
        await query.edit_message_text("⌨️ שלח את השעה בפורמט `HH:MM` (לדוגמה: `20:30`)", parse_mode="Markdown")
        return AUTO_MSG_TIME
    time_str = query.data.replace("auto_time_", "")
    db.add_auto_message(context.user_data['auto_text'], time_str)
    await query.edit_message_text(f"✅ הודעה אוטומטית נוספה לשעה *{time_str}* בכל יום!", parse_mode="Markdown")
    await schedule_auto_messages(context.application)
    return ConversationHandler.END

async def add_auto_msg_time_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_str = update.message.text.strip()
    try:
        h, m = time_str.split(":")
        int(h), int(m)
        db.add_auto_message(context.user_data['auto_text'], time_str)
        await update.message.reply_text(f"✅ הודעה אוטומטית נוספה לשעה *{time_str}* בכל יום!", parse_mode="Markdown")
        await schedule_auto_messages(context.application)
    except:
        await update.message.reply_text("❌ פורמט שגוי. שלח בפורמט `HH:MM`", parse_mode="Markdown")
        return AUTO_MSG_TIME
    return ConversationHandler.END

async def del_auto_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msgs = db.get_auto_messages()
    if not msgs:
        await query.edit_message_text("אין הודעות.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזור", callback_data="auto_messages")]]))
        return
    keyboard = [[InlineKeyboardButton(f"🗑 {m['send_time']} — {m['text'][:20]}", callback_data=f"del_amsg_{m['id']}")] for m in msgs]
    keyboard.append([InlineKeyboardButton("❌ ביטול", callback_data="auto_messages")])
    await query.edit_message_text("בחר הודעה למחיקה:", reply_markup=InlineKeyboardMarkup(keyboard))

async def del_auto_msg_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg_id = int(query.data.replace("del_amsg_", ""))
    db.delete_auto_message(msg_id)
    await query.edit_message_text("✅ ההודעה נמחקה!")
    await schedule_auto_messages(context.application)

async def send_auto_message(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    text = job.data['text']
    for chat_id in GROUP_IDS:
        try:
            await context.bot.send_message(chat_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Auto msg error: {e}")
    for user in db.get_all_users():
        try:
            await context.bot.send_message(user['user_id'], text, parse_mode="Markdown")
            await asyncio.sleep(0.05)
        except:
            pass

async def schedule_auto_messages(app):
    # מחיקת jobs קיימות
    current_jobs = app.job_queue.jobs()
    for job in current_jobs:
        if job.name and job.name.startswith("auto_msg_"):
            job.schedule_removal()

    # הוספת jobs חדשות
    msgs = db.get_auto_messages()
    for msg in msgs:
        try:
            h, m = msg['send_time'].split(":")
            t = time(hour=int(h), minute=int(m))
            app.job_queue.run_daily(
                send_auto_message,
                time=t,
                name=f"auto_msg_{msg['id']}",
                data={'text': msg['text']}
            )
            logger.info(f"Scheduled auto message at {msg['send_time']}")
        except Exception as e:
            logger.error(f"Schedule error: {e}")

# ===================== פרסום אירוע =====================

async def event_publish_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['event'] = {}
    keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="admin_panel")]]
    await query.edit_message_text(
        "🎉 *פרסום אירוע חדש*\n\n*שלב 1/6* — מה *שם האירוע*?\n\nלדוגמה: `TECHNO NIGHT TEL AVIV`",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )
    return EVENT_NAME

async def event_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event']['name'] = update.message.text.strip()
    keyboard = [[InlineKeyboardButton("⏭ דלג", callback_data="skip_dj")]]
    await update.message.reply_text("🎧 *שלב 2/6* — מי ה-DJ?\n\nלדוגמה: `Shlomi Aber`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return EVENT_DJ

async def event_dj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event']['dj'] = update.message.text.strip()
    await update.message.reply_text("📍 *שלב 3/6* — מיקום:", parse_mode="Markdown")
    return EVENT_LOCATION

async def event_skip_dj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['event']['dj'] = None
    await query.edit_message_text("📍 *שלב 3/6* — מיקום:", parse_mode="Markdown")
    return EVENT_LOCATION

async def event_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event']['location'] = update.message.text.strip()
    await update.message.reply_text("📅 *שלב 4/6* — תאריך ושעה:\n\nלדוגמה: `שישי 21.03 | 23:00`", parse_mode="Markdown")
    return EVENT_DATE

async def event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event']['date'] = update.message.text.strip()
    keyboard = [[InlineKeyboardButton("⏭ דלג", callback_data="skip_link")]]
    await update.message.reply_text("🔗 *שלב 5/6* — לינק לכרטיסים:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return EVENT_LINK

async def event_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event']['link'] = update.message.text.strip()
    keyboard = [[InlineKeyboardButton("⏭ ללא פליייר", callback_data="skip_flyer")]]
    await update.message.reply_text("📸 *שלב 6/6* — שלח פליייר:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return EVENT_FLYER

async def event_skip_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['event']['link'] = None
    keyboard = [[InlineKeyboardButton("⏭ ללא פליייר", callback_data="skip_flyer")]]
    await query.edit_message_text("📸 *שלב 6/6* — שלח פליייר:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return EVENT_FLYER

async def event_flyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['event']['flyer'] = update.message.photo[-1].file_id if update.message.photo else None
    await show_event_preview(update, context)
    return EVENT_CONFIRM

async def event_skip_flyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['event']['flyer'] = None
    event = context.user_data['event']
    text = build_event_text(event)
    keyboard = [[InlineKeyboardButton("✅ פרסם!", callback_data="confirm_event"), InlineKeyboardButton("❌ ביטול", callback_data="admin_panel")]]
    await query.edit_message_text(f"👁 *תצוגה:*\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return EVENT_CONFIRM

def build_event_text(event):
    lines = ["🎉 *אירוע חדש — מסיבות בישראל* 🎉", "", f"🎪 *{event['name']}*", ""]
    if event.get('dj'): lines.append(f"🎧 *DJ:* {event['dj']}")
    lines.append(f"📍 *מיקום:* {event['location']}")
    lines.append(f"📅 *מתי:* {event['date']}")
    if event.get('link'): lines.append(f"🎟 *כרטיסים:* {event['link']}")
    lines += ["", "🔥 *מסיבות בישראל* — הקהילה שלנו מחכה לך!", f"🌐 {SITE_URL}"]
    return "\n".join(lines)

async def show_event_preview(update, context):
    event = context.user_data['event']
    text = build_event_text(event)
    keyboard = [[InlineKeyboardButton("✅ פרסם!", callback_data="confirm_event"), InlineKeyboardButton("❌ ביטול", callback_data="admin_panel")]]
    preview = f"👁 *תצוגה:*\n\n{text}"
    if event.get('flyer'):
        await update.message.reply_photo(event['flyer'], caption=preview, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(preview, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def event_confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    event = context.user_data.get('event', {})
    text = build_event_text(event)
    success, failed = 0, 0
    for channel in db.get_channels():
        try:
            if event.get('flyer'):
                await context.bot.send_photo(channel['chat_id'], event['flyer'], caption=text, parse_mode="Markdown")
            else:
                await context.bot.send_message(channel['chat_id'], text, parse_mode="Markdown")
            success += 1
        except Exception as e:
            logger.error(f"Channel: {e}"); failed += 1
    for user in db.get_all_users():
        try:
            if event.get('flyer'):
                await context.bot.send_photo(user['user_id'], event['flyer'], caption=text, parse_mode="Markdown")
            else:
                await context.bot.send_message(user['user_id'], text, parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05)
        except: failed += 1
    await query.edit_message_text(f"✅ *פורסם!*\n✔️ {success} | ❌ {failed}", parse_mode="Markdown")
    return ConversationHandler.END

# ===================== פרסום חופשי =====================

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="admin_panel")]]
    await query.edit_message_text("📢 שלח הודעה, תמונה או וידאו:", reply_markup=InlineKeyboardMarkup(keyboard))
    return BROADCAST_MESSAGE

async def broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['broadcast_msg'] = update.message
    keyboard = [[InlineKeyboardButton("✅ שלח", callback_data="confirm_broadcast"), InlineKeyboardButton("❌ ביטול", callback_data="admin_panel")]]
    await update.message.reply_text(f"ישלח ל-{db.get_users_count()} משתמשים. לשלוח?", reply_markup=InlineKeyboardMarkup(keyboard))
    return BROADCAST_CONFIRM

async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = context.user_data.get('broadcast_msg')
    success, failed = 0, 0
    for channel in db.get_channels():
        try:
            if msg.photo: await context.bot.send_photo(channel['chat_id'], msg.photo[-1].file_id, caption=msg.caption)
            elif msg.video: await context.bot.send_video(channel['chat_id'], msg.video.file_id, caption=msg.caption)
            else: await context.bot.send_message(channel['chat_id'], msg.text)
            success += 1
        except: failed += 1
    for user in db.get_all_users():
        try:
            if msg.photo: await context.bot.send_photo(user['user_id'], msg.photo[-1].file_id, caption=msg.caption)
            elif msg.video: await context.bot.send_video(user['user_id'], msg.video.file_id, caption=msg.caption)
            else: await context.bot.send_message(user['user_id'], msg.text)
            success += 1
            await asyncio.sleep(0.05)
        except: failed += 1
    await query.edit_message_text(f"✅ *הושלם!*\n✔️ {success} | ❌ {failed}", parse_mode="Markdown")
    return ConversationHandler.END

# ===================== ניהול ערוצים =====================

async def manage_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = db.get_channels()
    channels_text = "\n".join([f"• {ch['name']}" for ch in channels]) if channels else "אין ערוצים"
    keyboard = [[InlineKeyboardButton("➕ הוסף", callback_data="add_channel"), InlineKeyboardButton("➖ הסר", callback_data="remove_channel")], [InlineKeyboardButton("🔙 חזור", callback_data="admin_panel")]]
    await query.edit_message_text(f"📋 *ניהול ערוצים*\n\n{channels_text}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("➕ שלח Chat ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ ביטול", callback_data="manage_channels")]]))
    return ADD_CHANNEL

async def add_channel_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = int(update.message.text.strip())
        chat = await context.bot.get_chat(chat_id)
        db.add_channel(chat_id, chat.title or str(chat_id))
        await update.message.reply_text(f"✅ *{chat.title}* נוסף!", parse_mode="Markdown")
    except ValueError: await update.message.reply_text("❌ ID לא תקין.")
    except Exception as e: await update.message.reply_text(f"❌ {str(e)}")
    return ConversationHandler.END

async def remove_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = db.get_channels()
    if not channels:
        await query.edit_message_text("אין ערוצים.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="manage_channels")]]))
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"🗑 {ch['name']}", callback_data=f"del_channel_{ch['chat_id']}")] for ch in channels]
    keyboard.append([InlineKeyboardButton("❌ ביטול", callback_data="manage_channels")])
    await query.edit_message_text("בחר ערוץ:", reply_markup=InlineKeyboardMarkup(keyboard))
    return REMOVE_CHANNEL

async def remove_channel_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db.remove_channel(int(query.data.replace("del_channel_", "")))
    await query.edit_message_text("✅ הוסר!")
    return ConversationHandler.END

# ===================== ניהול משתמשים =====================

async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🚫 חסום", callback_data="ban_user"), InlineKeyboardButton("✅ שחרר", callback_data="unban_user")], [InlineKeyboardButton("📋 חסומים", callback_data="list_banned")], [InlineKeyboardButton("🔙 חזור", callback_data="admin_panel")]]
    await query.edit_message_text(f"👥 *משתמשים*\n\n👤 {db.get_users_count()}\n🚫 {db.get_banned_count()} חסומים", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def ban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🚫 שלח User ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ ביטול", callback_data="manage_users")]]))
    return BAN_USER

async def ban_user_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text.strip())
        db.ban_user(user_id)
        await update.message.reply_text(f"✅ `{user_id}` נחסם.", parse_mode="Markdown")
    except: await update.message.reply_text("❌ ID לא תקין.")
    return ConversationHandler.END

async def unban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ שלח User ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ ביטול", callback_data="manage_users")]]))
    return UNBAN_USER

async def unban_user_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text.strip())
        db.unban_user(user_id)
        await update.message.reply_text(f"✅ `{user_id}` שוחרר.", parse_mode="Markdown")
    except: await update.message.reply_text("❌ ID לא תקין.")
    return ConversationHandler.END

async def list_banned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    banned = db.get_banned_users()
    text = "🚫 *חסומים:*\n\n" + "\n".join([f"• `{u['user_id']}`" for u in banned]) if banned else "✅ אין חסומים."
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזור", callback_data="manage_users")]]), parse_mode="Markdown")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"📊 *סטטיסטיקות*\n\n👤 {db.get_users_count()} משתמשים\n📢 {len(db.get_channels())} ערוצים\n🚫 {db.get_banned_count()} חסומים",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזור", callback_data="admin_panel")]]), parse_mode="Markdown"
    )

async def show_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = db.get_channels()
    if not channels:
        await query.edit_message_text("אין ערוצים עדיין.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזור", callback_data="back_start")]]))
        return
    keyboard = [[InlineKeyboardButton(f"📢 {ch['name']}", url=f"https://t.me/{ch.get('username','')}")] for ch in channels if ch.get('username')]
    keyboard.append([InlineKeyboardButton("🔙 חזור", callback_data="back_start")])
    await query.edit_message_text("📢 *הערוצים שלנו:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ===================== callback handler =====================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "admin_panel": await show_admin_panel(update, context)
    elif data == "manage_channels": await manage_channels(update, context)
    elif data == "manage_users": await manage_users(update, context)
    elif data == "stats": await show_stats(update, context)
    elif data == "list_banned": await list_banned(update, context)
    elif data == "show_channels": await show_channels(update, context)
    elif data == "show_rules": await show_rules(update, context)
    elif data == "auto_messages": await auto_messages_menu(update, context)
    elif data == "add_auto_msg": await add_auto_msg_start(update, context)
    elif data == "del_auto_msg": await del_auto_msg(update, context)
    elif data == "custom_buttons": await custom_buttons_menu(update, context)
    elif data == "add_custom_btn": await add_custom_btn_start(update, context)
    elif data == "del_custom_btn": await del_custom_btn(update, context)
    elif data == "preview_group_menu": await preview_group_menu(update, context)
    elif data.startswith("del_btn_"): await del_btn_confirm(update, context)
    elif data.startswith("del_amsg_"): await del_auto_msg_confirm(update, context)
    elif data == "back_start": await start(update, context)

# ===================== הפעלה =====================

async def post_init(app: Application):
    await schedule_auto_messages(app)

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    event_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(event_publish_start, pattern="^event_publish$")],
        states={
            EVENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_name)],
            EVENT_DJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_dj), CallbackQueryHandler(event_skip_dj, pattern="^skip_dj$")],
            EVENT_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_location)],
            EVENT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_date)],
            EVENT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_link), CallbackQueryHandler(event_skip_link, pattern="^skip_link$")],
            EVENT_FLYER: [MessageHandler(filters.PHOTO, event_flyer), CallbackQueryHandler(event_skip_flyer, pattern="^skip_flyer$")],
            EVENT_CONFIRM: [CallbackQueryHandler(event_confirm_send, pattern="^confirm_event$")],
        },
        fallbacks=[CallbackQueryHandler(callback_handler)],
    )

    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(broadcast_start, pattern="^broadcast$")],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_receive)],
            BROADCAST_CONFIRM: [CallbackQueryHandler(broadcast_confirm, pattern="^confirm_broadcast$")],
        },
        fallbacks=[CallbackQueryHandler(callback_handler)],
    )

    channels_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_channel_start, pattern="^add_channel$"), CallbackQueryHandler(remove_channel_start, pattern="^remove_channel$")],
        states={
            ADD_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_channel_receive)],
            REMOVE_CHANNEL: [CallbackQueryHandler(remove_channel_confirm, pattern="^del_channel_")],
        },
        fallbacks=[CallbackQueryHandler(callback_handler)],
    )

    users_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(ban_user_start, pattern="^ban_user$"), CallbackQueryHandler(unban_user_start, pattern="^unban_user$")],
        states={
            BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ban_user_receive)],
            UNBAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, unban_user_receive)],
        },
        fallbacks=[CallbackQueryHandler(callback_handler)],
    )

    auto_msg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_auto_msg_start, pattern="^add_auto_msg$")],
        states={
            AUTO_MSG_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_auto_msg_text)],
            AUTO_MSG_TIME: [
                CallbackQueryHandler(add_auto_msg_time, pattern="^auto_time_(?!custom)"),
                CallbackQueryHandler(add_auto_msg_time, pattern="^auto_time_custom$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_auto_msg_time_custom)
            ],
        },
        fallbacks=[CallbackQueryHandler(callback_handler)],
    )

    custom_btn_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_custom_btn_start, pattern="^add_custom_btn$")],
        states={
            CUSTOM_BTN_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_custom_btn_text)],
            CUSTOM_BTN_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_custom_btn_url)],
        },
        fallbacks=[CallbackQueryHandler(callback_handler)],
    )

    rules_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_rules_start, pattern="^edit_rules$")],
        states={RULES_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_rules_receive)]},
        fallbacks=[CallbackQueryHandler(callback_handler)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(event_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(channels_conv)
    app.add_handler(users_conv)
    app.add_handler(auto_msg_conv)
    app.add_handler(custom_btn_conv)
    app.add_handler(rules_conv)
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("🤖 הבוט פועל!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
