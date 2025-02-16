import os
import telebot
import time
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

# 🔹️ جلب توكن البوت من المتغيرات البيئية
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

# 🔥 تهيئة بوت التليجرام
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 🔥 تهيئة تطبيق Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sessions.db'

db = SQLAlchemy(app)

# 🔹️ نموذج تخزين جلسات المستخدمين
class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(50), unique=True, nullable=False)
    session_id = db.Column(db.String(100), unique=False, nullable=False)

# 📌 إنشاء قاعدة البيانات
with app.app_context():
    db.create_all()

# ✅ فحص المستخدم عند دخوله الجروب
@bot.message_handler(content_types=['new_chat_members'])
def check_user(message):
    for new_member in message.new_chat_members:
        user_id = new_member.id
        chat_id = message.chat.id
        session_id = str(message.date)  # نحفظ وقت الدخول كـ Session ID

        # 🔹️ فحص المستخدم في قاعدة البيانات
        user_sessions = Session.query.filter_by(telegram_id=user_id).all()

        if user_sessions:
            for session in user_sessions:
                if session.session_id != session_id:
                    bot.kick_chat_member(chat_id, user_id)
                    bot.send_message(chat_id, f"🚫 المستخدم @{new_member.username} طُرد لأنه حاول الدخول من جهاز آخر!")
                    return
        
        # 🔥 إذا كان المستخدم جديدًا، نضيف الجلسة
        new_session = Session(telegram_id=user_id, session_id=session_id)
        db.session.add(new_session)
        db.session.commit()
        bot.send_message(chat_id, f"✅ المستخدم @{new_member.username} تم تسجيله بنجاح!")

# 🚀 تشغيل Flask لاستقبال التحديثات من تليجرام
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return 'OK', 200

# ✅ تشغيل Webhook عند بدء التشغيل
@app.route('/')
def index():
    bot.remove_webhook()
    
    # 🔹️ تأكد من أن الرابط يحتوي على البورت الصحيح
    railway_domain = os.getenv('RAILWAY_APP_DOMAIN', 'telegram-bot-guard-production.up.railway.app')
    webhook_url = f"https://{railway_domain}/{TELEGRAM_BOT_TOKEN}"
    
    bot.set_webhook(url=webhook_url)
    return f"🚀 Bot is running! Webhook set to: {webhook_url}"

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
