import sqlite3

# الاتصال بقاعدة البيانات الحقيقية للمشروع
db_path = 'game_hall.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# جلب أسماء الاعمدة في جدول المستخدمين
cursor.execute("PRAGMA table_info(users)")
cols = [c[1] for c in cursor.fetchall()]

cursor.execute("SELECT * FROM users")
rows = cursor.fetchall()

print("=== قائمة المستخدمين الحالية ===")
if not rows:
    print("⚠️ لا يوجد أي مستخدمين مسجلين حالياً.")
else:
    for r in rows:
        user = dict(zip(cols, r))
        username = user.get('username', 'غير محدد')
        role = user.get('role', 'غير محدد')
        password = user.get('plain_password') or user.get('password') or 'مشفره'
        print(f"اسم المستخدم: {username} | الرتبة: {role} | كلمة السر النصية: {password}")

conn.close()