from flask import Flask, request, jsonify
import sqlite3
import datetime
import threading
import time
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__)

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect('bans.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS bans (
    user_id INTEGER PRIMARY KEY,
    reason TEXT,
    banned_by TEXT,
    time TEXT
)
''')
conn.commit()

# ========== НАСТРОЙКИ ==========
SECRET_KEY = "MySecretKey123"
BOT_TOKEN = "8950125978:AAFrB1cxr1a3HPK1a-3gjzcG-vwBDgZGzrQ"

# ========== API ДЛЯ ROBLOX ==========
@app.route('/check/<int:user_id>')
def check_ban(user_id):
    cursor.execute('SELECT reason, banned_by FROM bans WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        return jsonify({'banned': True, 'reason': result[0], 'banned_by': result[1]})
    return jsonify({'banned': False})

@app.route('/ban', methods=['POST'])
def ban_user():
    data = request.json
    if data.get('key') != SECRET_KEY:
        return jsonify({'error': 'Неверный ключ'}), 403
    
    user_id = data.get('user_id')
    reason = data.get('reason', 'Нарушение правил')
    banned_by = data.get('banned_by', 'Система')
    
    cursor.execute('INSERT OR REPLACE INTO bans VALUES (?, ?, ?, ?)',
                   (user_id, reason, banned_by, str(datetime.datetime.now())))
    conn.commit()
    return jsonify({'success': True})

@app.route('/unban', methods=['POST'])
def unban_user():
    data = request.json
    if data.get('key') != SECRET_KEY:
        return jsonify({'error': 'Неверный ключ'}), 403
    
    user_id = data.get('user_id')
    cursor.execute('DELETE FROM bans WHERE user_id = ?', (user_id,))
    conn.commit()
    return jsonify({'success': True})

@app.route('/')
def home():
    return "🤖 Бан-система работает!"

# ========== TELEGRAM БОТ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Бан-система Roblox*\n\n"
        "Команды:\n"
        "/ban <ID> <причина> - забанить игрока\n"
        "/unban <ID> - разбанить игрока\n"
        "/check <ID> - проверить бан\n"
        "/bans - список всех забаненных\n\n"
        "Пример: /ban 123456789 Читер",
        parse_mode='Markdown'
    )

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /ban <ID> <причина>")
        return
    
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
        banned_by = update.effective_user.first_name
        
        cursor.execute('INSERT OR REPLACE INTO bans VALUES (?, ?, ?, ?)',
                       (user_id, reason, banned_by, str(datetime.datetime.now())))
        conn.commit()
        
        await update.message.reply_text(
            f"✅ Игрок `{user_id}` забанен!\n"
            f"Причина: {reason}\n"
            f"Кто: {banned_by}",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("❌ Использование: /unban <ID>")
        return
    
    try:
        user_id = int(context.args[0])
        cursor.execute('DELETE FROM bans WHERE user_id = ?', (user_id,))
        conn.commit()
        await update.message.reply_text(f"✅ Игрок `{user_id}` разбанен!", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("❌ Использование: /check <ID>")
        return
    
    try:
        user_id = int(context.args[0])
        cursor.execute('SELECT reason, banned_by, time FROM bans WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            await update.message.reply_text(
                f"🚫 Игрок `{user_id}` ЗАБАНЕН\n"
                f"Причина: {result[0]}\n"
                f"Кто: {result[1]}\n"
                f"Время: {result[2]}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"✅ Игрок `{user_id}` НЕ забанен", parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")

async def bans_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute('SELECT user_id, reason, banned_by FROM bans LIMIT 20')
    results = cursor.fetchall()
    
    if not results:
        await update.message.reply_text("📭 Список банов пуст")
        return
    
    text = "📋 *Список забаненных:*\n\n"
    for user_id, reason, banned_by in results:
        text += f"• `{user_id}` - {reason} (кто: {banned_by})\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("bans", bans_list))
    print("🤖 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# ========== ПИНГ ДЛЯ БЕСПЛАТНОГО ХОСТИНГА ==========
def keep_alive():
    url = "https://ban-system.onrender.com"
    while True:
        try:
            requests.get(url)
            print("🔄 Пинганул сервер")
        except:
            print("❌ Ошибка пинга")
        time.sleep(600)

if __name__ == '__main__':
    threading.Thread(target=keep_alive, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
