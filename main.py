from flask import Flask
from config import Config
import database as db
from admin import admin_bp
from user import user_bp
from auth import auth_bp # استيراد ملف تسجيل الدخول
from public import public_bp
from admin import admin_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # تهيئة قاعدة البيانات وإنشاء الجداول والمدير الرئيسي
    with app.app_context():
        db.init_db()

    # تسجيل اللوحات (Blueprints)
    app.register_blueprint(public_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    app.register_blueprint(user_bp)
    app.register_blueprint(auth_bp)  # تسجيل blueprint المصادقة

    return app

if __name__ == '__main__':
    app = create_app()
    print("==================================================")
    print("🚀 تم تشغيل موقع إدارة صالة الألعاب بنجاح!")
    print("🌐 رابط واجهة المستخدم: http://127.0.0.1:5000/")
    print("🔐 رابط لوحة الإدارة: http://127.0.0.1:5000/auth/login")
    print("👤 بيانات دخول المدير: Username: admin | Password: admin123")
    print("==================================================")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)