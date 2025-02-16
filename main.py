import os
import hashlib
import telebot
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
import random

# 🔹️ جلب توكن البوت
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

# 🔥 تهيئة بوت التليجرام
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 🔥 تهيئة تطبيق Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# 🔹️ نموذج تخزين بيانات المستخدمين
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(50), unique=True, nullable=False)
    session_id = db.Column(db.String(100), unique=False, nullable=True)

# 📌 إنشاء قاعدة البيانات
with app.app_context():
    db.create_all()

# 🔒 دالة توليد معرف الجلسة (Session ID)
def generate_session_id():
    return hashlib.sha256(str(random.randint(1000, 9999)).encode()).hexdigest()

# ✅ التحقق عند إرسال رسالة
@bot.message_handler(func=lambda message: True)
def check_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    session_id = generate_session_id()

    # 🔹️ فحص المستخدم في قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()

    if user:
        if user.session_id and user.session_id != session_id:
            bot.kick_chat_member(chat_id, user_id)
            bot.send_message(chat_id, f"🚫 المستخدم @{message.from_user.username} طُرد لأنه استخدم جهاز آخر!")
            return
    else:
        new_user = User(telegram_id=user_id, session_id=session_id)
        db.session.add(new_user)
        db.session.commit()
        bot.send_message(chat_id, f"✅ المستخدم @{message.from_user.username} تم تسجيل جهازه!")

# ✅ استقبال أمر /start
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "🚀 البوت شغال بنجاح!")

# 🚀 تشغيل Flask مع Webhook للبوت
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return 'OK', 200

# ✅ تشغيل Webhook عند بدء التشغيل
@app.route('/')
def index():
    bot.remove_webhook()
    
    railway_domain = os.getenv('RAILWAY_APP_DOMAIN', 'telegram-bot-guard-production.up.railway.app')
    webhook_url = f"https://{railway_domain}/{TELEGRAM_BOT_TOKEN}"
    
    bot.set_webhook(url=webhook_url)
    return f"🚀 Bot is running! Webhook set to: {webhook_url}"

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
