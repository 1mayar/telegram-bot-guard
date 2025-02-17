import os
import telebot
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
import requests

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
    ip_address = db.Column(db.String(50), nullable=True)

# 📌 إنشاء قاعدة البيانات
with app.app_context():
    db.create_all()

# ✅ وظيفة لجلب عنوان الـ IP باستخدام API خارجي
def get_ip():
    try:
        response = requests.get("https://api64.ipify.org?format=json")
        return response.json().get("ip")
    except:
        return None

# ✅ التحقق عند إرسال رسالة
@bot.message_handler(func=lambda message: True)
def check_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_ip = get_ip()  # ✅ جلب عنوان الـ IP الصحيح

    if not user_ip:
        bot.send_message(chat_id, "⚠️ فشل في جلب عنوان IP المستخدم!")
        return

    # 🔹️ جلب المستخدم من قاعدة البيانات
    user = User.query.filter_by(telegram_id=user_id).first()

    # ✅ التحقق مما إذا كان المستخدم لا يزال في الجروب
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        if chat_member.status in ["left", "kicked"]:
            if user:
                db.session.delete(user)
                db.session.commit()
            return  # المستخدم غادر الجروب، لا داعي لمعالجته
    except Exception as e:
        print(f"⚠️ خطأ في جلب حالة المستخدم: {e}")
        return

    if user:
        # ✅ التحقق من تغير IP المستخدم (إذا دخل من جهاز آخر)
        if user.ip_address and user.ip_address != user_ip:
            bot.kick_chat_member(chat_id, user_id)
            bot.send_message(chat_id, f"🚫 المستخدم @{message.from_user.username} طُرد لاستخدام جهاز مختلف!")
            return
    else:
        # ✅ تسجيل المستخدم لأول مرة
        new_user = User(telegram_id=user_id, ip_address=user_ip)
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
    json_str = request.stream.read().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'OK', 200

# ✅ تشغيل Webhook عند بدء التشغيل
@app.route('/')
def index():
    bot.remove_webhook()  # إزالة الـ Webhook القديم إذا كان موجود
    railway_domain = os.getenv('RAILWAY_APP_DOMAIN', 'telegram-bot-guard-production.up.railway.app')
    webhook_url = f"https://{railway_domain}/{TELEGRAM_BOT_TOKEN}"
    bot.set_webhook(url=webhook_url)  # تعيين الـ Webhook الجديد

    # التحقق من حالة Webhook
    webhook_info = bot.get_webhook_info()
    print(webhook_info)

    return f"🚀 Bot is running! Webhook set to: {webhook_url}"

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
