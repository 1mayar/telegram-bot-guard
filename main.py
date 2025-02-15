import os
import hashlib
import telebot
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

# 🔹 جلب توكن البوت من المتغيرات البيئية
TELEGRAM_BOT_TOKEN= os.getenv("TELEGRAM_BOT_TOKEN")

# 🔥 تهيئة بوت التليجرام
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 🔥 تهيئة تطبيق Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)

# 🔹 نموذج تخزين بيانات المستخدمين
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(50), unique=True, nullable=False)
    device_id = db.Column(db.String(100), unique=True, nullable=True)

# 📌 إنشاء قاعدة البيانات
with app.app_context():
    db.create_all()

# 🔐 دالة توليد بصمة الجهاز
def generate_device_id(user):
    return hashlib.sha256(str(user.id).encode()).hexdigest()

# ✅ فحص المستخدم عند دخوله الجروب
@bot.message_handler(content_types=['new_chat_members'])
def check_user(message):
    for new_member in message.new_chat_members:
        user_id = new_member.id
        chat_id = message.chat.id

        # 🔹 فحص المستخدم في قاعدة البيانات
        user = User.query.filter_by(telegram_id=user_id).first()
        device_id = generate_device_id(new_member)

        if user:
            if user.device_id and user.device_id != device_id:
                bot.kick_chat_member(chat_id, user_id)
                bot.send_message(chat_id, f"🚫 المستخدم @{new_member.username} محظور لأنه حاول الدخول من جهاز آخر!")
                return
        else:
            new_user = User(telegram_id=user_id, device_id=device_id)
            db.session.add(new_user)
            db.session.commit()
            bot.send_message(chat_id, f"✅ المستخدم @{new_member.username} تم تسجيل جهازه بنجاح!")

# 🚀 تشغيل Flask مع Webhook للبوت
@app.route('/' + TELEGRAM_BOT_TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return 'OK', 200

# ✅ تشغيل Webhook عند بدء التشغيل
@app.route('/')
def index():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.getenv('RAILWAY_APP_DOMAIN')}/{TELEGRAM_BOT_TOKEN}")
    return "Bot is running!"

if __name__ == "__main__":
    app.run(port=5000)

