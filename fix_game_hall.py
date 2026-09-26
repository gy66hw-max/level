import sqlite3
from werkzeug.security import generate_password_hash

db_path = 'game_hall.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# جلب أسماء أعمدة جدول users في قاعدة البيانات الحقيقية
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]

# حذف حساب المدير القديم إن وجد لمنع التكرار
cursor.execute("DELETE FROM users WHERE username = 'admin'")

pass_hash = generate_password_hash('admin123')

# تجهيز البيانات لتطابق هيكلية الجدول الموجودة
user_data = {
    'username': 'admin',
    'password_hash': pass_hash,
    'password': pass_hash,  # يتم التشفير بجميع الحالات لضمان التوافق
    'plain_password': 'admin123',
    'full_name': 'المدير العام',
    'name': 'المدير العام',
    'role': 'admin',
    'is_admin': 1,
    'is_active': 1,
    'permissions': '[]'
}

# تصفية البيانات لتشمل الأعمدة الموجودة بالفعل داخل الجدول
valid_data = {k: v for k, v in user_data.items() if k in columns}

if valid_data:
    cols = ", ".join(valid_data.keys())
    placeholders = ", ".join(["?"] * len(valid_data))
    sql = f"INSERT INTO users ({cols}) VALUES ({placeholders})"
    cursor.execute(sql, list(valid_data.values()))
    conn.commit()
    print("✅ تم إضافة حساب المدير بنجاح في قاعدة البيانات (game_hall.db)!")
else:
    print("❌ لم يتم العثور على حقول سليمة في جدول users.")

conn.close()