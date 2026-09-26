import sqlite3
from werkzeug.security import generate_password_hash

def get_db():
    conn = sqlite3.connect('game_hall.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. جدول الأقسام / الفئات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '🎮',
        color TEXT DEFAULT '#10b981',
        type TEXT DEFAULT 'game'
    )
    ''')

    # التحقق من وجود عمود type في جدول categories
    cursor.execute("PRAGMA table_info(categories)")
    cat_columns = [column[1] for column in cursor.fetchall()]
    if 'type' not in cat_columns:
        cursor.execute("ALTER TABLE categories ADD COLUMN type TEXT DEFAULT 'game'")

    # إضافة البيانات الافتراضية للأقسام
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO categories (key, name, icon, color, type) VALUES (?, ?, ?, ?, ?)
        ''', [
            ('billiards', 'قسم البليارد', '🎱', '#10b981', 'game'),
            ('playstation', 'قسم البلايستيشن', '🎮', '#3b82f6', 'game'),
            ('drinks', 'قسم المشروبات والعصائر', '🥤', '#f59e0b', 'product')
        ])

    # 2. جدول الألعاب والأجهزة
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        play_mode TEXT DEFAULT 'بالوقت',
        pricing_type TEXT DEFAULT 'بالوقت',
        price REAL NOT NULL,
        status TEXT DEFAULT 'متاح',
        show_to_user INTEGER DEFAULT 1
    )
    ''')

    # التحقق من وجود عمود show_to_user في جدول items
    cursor.execute("PRAGMA table_info(items)")
    item_columns = [column[1] for column in cursor.fetchall()]
    if 'show_to_user' not in item_columns:
        cursor.execute("ALTER TABLE items ADD COLUMN show_to_user INTEGER DEFAULT 1")

    # 3. جدول المنتجات والخدمات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        image_url TEXT,
        show_to_user INTEGER DEFAULT 1
    )
    ''')
    
    # 4. جدول الجلسات النشطة والمغلقة
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        item_name TEXT,
        session_type TEXT DEFAULT 'بالوقت',
        start_time TEXT,
        target_end_time TEXT,
        duration_minutes INTEGER DEFAULT 0,
        play_cost REAL DEFAULT 0,
        products_cost REAL DEFAULT 0,
        carried_over_cost REAL DEFAULT 0,
        total_cost REAL DEFAULT 0,
        status TEXT DEFAULT 'active',
        created_by TEXT
    )
    ''')

    # التحقق من وجود عمود carried_over_cost لإضافته في القواعد القديمة
    cursor.execute("PRAGMA table_info(sessions)")
    session_columns = [column[1] for column in cursor.fetchall()]
    if 'carried_over_cost' not in session_columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN carried_over_cost REAL DEFAULT 0")

    # 5. جدول طلبات المنتجات داخل الجلسة
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS session_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        product_name TEXT,
        price REAL,
        quantity INTEGER,
        total REAL
    )
    ''')

    # 6. جدول الإيرادات والمصروفات الإضافية
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        amount REAL NOT NULL,
        created_by TEXT,
        created_at TEXT
    )
    ''')

    # 7. جدول المستخدمين والموظفين
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        plain_password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'staff',
        permissions TEXT DEFAULT '[]',
        is_active INTEGER DEFAULT 1
    )
    ''')

    # إضافة حساب المدير الافتراضي تلقائياً عند أول تشغيل
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_user = 'admin'
        default_pass = 'admin123'
        pass_hash = generate_password_hash(default_pass)
        cursor.execute('''
            INSERT INTO users (username, password_hash, plain_password, full_name, role, permissions)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (default_user, pass_hash, default_pass, 'المدير الرئيسي', 'admin', '["all"]'))

    # 8. جدول الإعلانات والتحديثات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT
    )
    ''')

    conn.commit()
    conn.close()
