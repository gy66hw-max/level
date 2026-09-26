import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template_string, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import Markup

import database as db
from auth import login_required, has_permission

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def user_can(perm):
    """التحقق من الصلاحية مع إعطاء المدير العام صلاحية كاملة دائماً"""
    if session.get('role') == 'admin':
        return True
    return has_permission(perm)

def ensure_db_schema():
    conn = db.get_db()
    try:
        conn.execute('ALTER TABLE sessions ADD COLUMN carried_over_cost REAL DEFAULT 0.0')
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS system_settings (key TEXT PRIMARY KEY, value TEXT)')
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS deleted_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                target_name TEXT,
                details TEXT,
                deleted_by TEXT,
                deleted_at TEXT
            )
        ''')
        conn.commit()
    except Exception:
        pass

ensure_db_schema()

def log_deletion(action_type, target_name, details):
    """دالة مساعدة لحفظ أي عملية حذف أو إلغاء في سجل الرقابة والمحذوفات"""
    try:
        conn = db.get_db()
        deleter = session.get('full_name') or session.get('username') or 'غير معروف'
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute('''
            INSERT INTO deleted_logs (action_type, target_name, details, deleted_by, deleted_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (action_type, target_name, details, deleter, now_str))
        conn.commit()
    except Exception as e:
        print("Error logging deletion:", e)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

ALL_PERMISSIONS = {
    'start_session': '🚀 بدء حجز جديد (تشغيل الأجهزة)',
    'end_session': '🛑 إنهاء الجلسات واستلام الفواتير',
    'cancel_session': '🚫 إلغاء الجلسات النشطة بدون حساب',
    'transfer_session': '🔀 نقل الجلسات بين الأجهزة والأقسام',
    'add_product_to_session': '➕ إضافة مأكولات/عصائر للجلسة النشطة',
    'delete_session_product': '✖ حذف طلب مأكولات من داخل الجلسة النشطة',
    'manage_items': '🎮 إضافة وحذف الأجهزة والطاولات',
    'edit_item_price': '✏️ تعديل أسعار الأجهزة المباشرة',
    'manage_products': '🥤 إضافة وتعديل وحذف قائمة المأكولات والخدمات',
    'manage_sections': '✨ إضافة وحذف الأقسام الرئيسية',
    'view_reports': '📊 عرض التقارير المالية والأرباح',
    'edit_reports': '✏️ تعديل وحذف الفواتير وسجلات التقارير المكتملة',
    'manage_staff': '👥 إدارة الموظفين وتخصيص الصلاحيات'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

COMMON_STYLE = '''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');
    
    * {
        box-sizing: border-box;
    }

    body {
        font-family: 'Tajawal', sans-serif;
        background: linear-gradient(-45deg, #070a12, #0d1527, #150f2a, #09131f);
        background-size: 400% 400%;
        animation: gradientAnimation 15s ease infinite;
        color: #f8fafc;
        min-height: 100vh;
        max-width: 100%;
        overflow-x: hidden;
    }

    @keyframes gradientAnimation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    @keyframes activeGlow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .animated-section-bg {
        background-size: 200% 200% !important;
        animation: activeGlow 6s ease infinite !important;
        border-radius: 14px;
    }

    .moving-icon {
        display: inline-block;
        animation: floatIcon 2.8s ease-in-out infinite;
        line-height: 1;
    }

    @keyframes floatIcon {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-4px) rotate(4deg); }
    }

    .glass-card {
        background: rgba(17, 24, 39, 0.92);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
    }

    .btn-glow-pink {
        background: linear-gradient(135deg, #ec4899, #f43f5e);
        color: white; font-weight: 700; border: none;
        box-shadow: 0 0 15px rgba(236, 72, 153, 0.4);
    }
    .btn-glow-purple {
        background: linear-gradient(135deg, #7c3aed, #6366f1);
        color: white; font-weight: 700; border: none;
        box-shadow: 0 0 15px rgba(124, 58, 237, 0.4);
    }
    .btn-glow-green {
        background: linear-gradient(135deg, #059669, #10b981);
        color: white; font-weight: 700; border: none;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
    }
    .btn-glow-cyan {
        background: linear-gradient(135deg, #0284c7, #06b6d4);
        color: white; font-weight: 700; border: none;
        box-shadow: 0 0 15px rgba(6, 182, 212, 0.4);
    }

    .nav-pills .nav-link {
        color: #cbd5e1;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        margin: 4px;
        font-weight: 700;
        transition: all 0.3s ease;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .nav-pills .nav-link.active {
        background: rgba(255, 255, 255, 0.18) !important;
        border-color: currentColor;
        box-shadow: 0 0 15px rgba(255, 255, 255, 0.25);
    }

    .status-badge-active {
        background: rgba(16, 185, 129, 0.2); color: #34d399;
        border: 1px solid #10b981; padding: 4px 12px; border-radius: 20px; font-weight: bold;
    }
    .status-badge-busy {
        background: rgba(239, 68, 68, 0.2); color: #f87171;
        border: 1px solid #ef4444; padding: 4px 12px; border-radius: 20px; font-weight: bold;
    }

    .countdown-timer {
        font-size: 1.3rem; font-weight: 900; letter-spacing: 2px;
        color: #38bdf8; background: #090d16; padding: 6px 14px;
        border-radius: 10px; border: 1px solid #0284c7;
    }
    .timer-ended { color: #ef4444 !important; border-color: #ef4444 !important; animation: blink 1s infinite; }
    @keyframes blink { 50% { opacity: 0.4; } }

    .table-dark-custom { 
        background-color: #0b1120 !important; 
        color: #f8fafc !important; 
        border-radius: 12px; 
        overflow: hidden; 
        border: 1px solid #1e293b !important;
        --bs-table-bg: #0b1120 !important;
        --bs-table-color: #f8fafc !important;
    }
    .table-dark-custom th { 
        background-color: #1e293b !important; 
        color: #38bdf8 !important; 
        font-weight: 800 !important;
        border-color: #334155 !important; 
        padding: 12px 14px !important;
    }
    .table-dark-custom td { 
        background-color: #0b1120 !important; 
        color: #f8fafc !important; 
        border-color: #1e293b !important; 
        padding: 12px 14px !important;
    }
    .table-dark-custom tbody tr:hover td { 
        background-color: #131d31 !important; 
    }

    optgroup { background-color: #1f293d; color: #38bdf8; font-weight: bold; }
    optgroup option { background-color: #111827; color: #ffffff; }

    .flash-alert-box {
        transition: opacity 0.6s ease, transform 0.6s ease;
    }

    @media (max-width: 768px) {
        body { padding: 10px !important; }
        .glass-card { padding: 15px !important; border-radius: 12px !important; }
        .moving-title { font-size: 1.6rem !important; }
        .nav-pills .nav-link { padding: 8px 12px !important; font-size: 0.9rem !important; }
        .btn-glow-pink, .btn-glow-purple, .btn-glow-green, .btn-glow-cyan {
            width: 100% !important;
            margin-bottom: 5px !important;
            font-size: 0.95rem !important;
        }
        .countdown-timer { font-size: 1.1rem !important; }
        .modal-dialog { margin: 10px !important; }
    }

    @media print {
        body { background: white !important; color: black !important; }
        .no-print { display: none !important; }
        .glass-card { background: none !important; border: none !important; box-shadow: none !important; color: black !important; }
        .table-dark-custom { color: black !important; background: none !important; }
        .table-dark-custom th { background: #eee !important; color: black !important; }
    }
</style>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() {
            let alerts = document.querySelectorAll('.flash-alert-box');
            alerts.forEach(function(alert) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-10px)';
                setTimeout(function() { alert.remove(); }, 600);
            });
        }, 3500);
    });
</script>
'''

@admin_bp.route('/')
@login_required
def dashboard():
    conn = db.get_db()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    items = conn.execute('SELECT * FROM items').fetchall()
    products = conn.execute('SELECT * FROM products').fetchall()
    active_sessions = conn.execute('SELECT * FROM sessions WHERE status = "active"').fetchall()
    
    session_prods = {}
    for s in active_sessions:
        session_prods[s['id']] = conn.execute('SELECT * FROM session_products WHERE session_id = ?', (s['id'],)).fetchall()

    free_items = conn.execute('''
        SELECT items.*, COALESCE(c1.name, c2.name, items.category) as category_name 
        FROM items 
        LEFT JOIN categories c1 ON items.category = c1.key 
        LEFT JOIN categories c2 ON items.category = c2.name 
        WHERE items.status = 'متاح'
        ORDER BY category_name ASC, items.name ASC
    ''').fetchall()

    return render_template_string('''
    <!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>إدارة الصالة والأجهزة والخدمات</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {{ COMMON_STYLE | safe }}
    </head>
    <body>
        <div class="container my-3">
            <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span class="fs-3 fw-bold text-white">الإدارة</span>
                    <span class="badge bg-primary fs-6 px-3 py-2 rounded-pill">⚡ {{ 'مدير عام' if session['role'] == 'admin' else 'موظف' }}</span>
                    <span class="badge bg-secondary fs-6 px-3 py-2 rounded-pill">{{ session['full_name'] }}</span>
                </div>
                <div class="d-flex gap-2 flex-wrap">
                    <a href="/" class="btn btn-outline-info rounded-pill px-3 fw-bold">🏠 الواجهة الرئيسية</a>
                    <button class="btn btn-outline-warning rounded-pill px-3 fw-bold" data-bs-toggle="modal" data-bs-target="#editProfileModal">
                        ⚙️ تعديل حسابي
                    </button>
                    <a href="{{ url_for('auth.logout') }}" class="btn btn-danger rounded-pill px-4 fw-bold">تسجيل الخروج ➔</a>
                </div>
            </div>

            <div class="text-center my-4">
                <h1 class="fw-black display-5 text-white mb-1">
                    <span class="moving-title">إدارة الصالة والأجهزة والخدمات</span> <span class="moving-icon">🎮</span>
                </h1>
                <p class="text-light opacity-75 fs-5">التحكم بالأقسام، نقل الجلسات، تعديل الأسعار وحساب الفواتير</p>
            </div>

            <div class="d-flex flex-wrap justify-content-center gap-3 mb-4">
                {% if session['role'] == 'admin' or 'manage_sections' in session['permissions'] %}
                <button class="btn btn-glow-pink px-4 py-2 rounded-pill fs-5" data-bs-toggle="modal" data-bs-target="#addSectionModal">
                    <span class="moving-icon">✨</span> إضافة قسم جديد +
                </button>
                {% endif %}
                {% if session['role'] == 'admin' or 'view_reports' in session['permissions'] %}
                <a href="{{ url_for('admin.reports') }}" class="btn btn-glow-green px-4 py-2 rounded-pill fs-5"><span class="moving-icon">📊</span> التقارير التفصيلية والـ PDF</a>
                {% endif %}
                {% if session['role'] == 'admin' or 'manage_staff' in session['permissions'] %}
                <a href="{{ url_for('admin.staff') }}" class="btn btn-glow-cyan px-4 py-2 rounded-pill fs-5"><span class="moving-icon">👥</span> الحسابات والصلاحيات</a>
                {% endif %}
            </div>

            <!-- تبويبات الأقسام -->
            <ul class="nav nav-pills justify-content-center mb-4 flex-wrap" id="mainTabs">
                {% for cat in categories %}
                <li class="nav-item">
                    <button class="nav-link {% if loop.first %}active{% endif %} px-4 py-2 fs-5 d-flex align-items-center gap-2" 
                            data-bs-toggle="pill" 
                            data-bs-target="#cat-{{ cat['id'] }}"
                            style="color: {{ cat['color'] }};">
                        <span class="moving-icon fs-5">{{ cat['icon'] }}</span> 
                        <span class="fw-bold">{{ cat['name'] }}</span>
                    </button>
                </li>
                {% endfor %}
            </ul>

            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} text-center fw-bold flash-alert-box shadow mb-3">{{ message }}</div>{% endfor %}{% endif %}
            {% endwith %}

            <!-- محتوى الأقسام -->
            <div class="tab-content">
                {% for cat in categories %}
                <div class="tab-pane fade {% if loop.first %}show active{% endif %}" id="cat-{{ cat['id'] }}">
                    <div class="glass-card p-4 mb-4" style="border-top: 4px solid {{ cat['color'] }} !important; box-shadow: 0 0 25px {{ cat['color'] }}30;">
                        <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
                            <h3 class="fw-bold m-0 d-flex align-items-center gap-2">
                                <span class="moving-icon fs-3">{{ cat['icon'] }}</span>
                                <span style="color: {{ cat['color'] }};">{{ cat['name'] }}</span>
                            </h3>

                            <div class="d-flex gap-2 flex-wrap">
                                {% if cat['type'] == 'game' %}
                                    {% if session['role'] == 'admin' or 'manage_items' in session['permissions'] %}
                                    <button class="btn text-white fw-bold px-3 py-2 rounded-pill" 
                                            style="background-color: {{ cat['color'] }};" 
                                            data-bs-toggle="modal" data-bs-target="#addItemModal" 
                                            onclick="setCategory('{{ cat['key'] }}')">
                                        + إضافة ميز/جهاز جديد
                                    </button>
                                    {% endif %}
                                {% else %}
                                    {% if session['role'] == 'admin' or 'manage_products' in session['permissions'] %}
                                    <button class="btn text-white fw-bold px-3 py-2 rounded-pill" 
                                            style="background-color: {{ cat['color'] }};" 
                                            data-bs-toggle="modal" data-bs-target="#addProductModal" 
                                            onclick="setProductCategory('{{ cat['name'] }}')">
                                        + إضافة منتج/خدمة بهذا القسم
                                    </button>
                                    {% endif %}
                                {% endif %}

                                {% if session['role'] == 'admin' or 'manage_sections' in session['permissions'] %}
                                <a href="{{ url_for('admin.delete_section', section_id=cat['id']) }}" 
                                   class="btn btn-outline-danger btn-sm rounded-pill px-3 d-flex align-items-center gap-1"
                                   onclick="return confirm('هل أنت تأكد من حذف هذا القسم بالكامل بما فيه من عناصر؟');">
                                    🗑️ حذف القسم
                                </a>
                                {% endif %}
                            </div>
                        </div>

                        {% if cat['type'] == 'game' %}
                            {{ render_items(items, cat['key'], active_sessions, session_prods, products, free_items, cat['color']) }}
                        {% else %}
                            {{ render_products(products, cat['name']) }}
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Modal تعديل بيانات الحساب -->
        <div class="modal fade" id="editProfileModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.update_profile') }}" class="modal-content glass-card text-white border-secondary">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-warning">⚙️ تعديل اسم المستخدم وكلمة المرور</h5>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="fw-bold mb-1">اسم المستخدم الجديد</label>
                            <input type="text" name="username" class="form-control bg-dark text-white border-secondary" value="{{ session['username'] }}" required>
                        </div>
                        <div class="mb-3">
                            <label class="fw-bold mb-1">كلمة المرور الجديدة (اتركها فارغة إذا لم ترد تغييرها)</label>
                            <input type="password" name="password" class="form-control bg-dark text-white border-secondary" placeholder="اكتب كلمة سر جديدة...">
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="submit" class="btn btn-glow-green w-100 py-2 fs-5">حفظ التغييرات 💾</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal البيع المباشر (طعام / مشروبات) -->
        <div class="modal fade" id="directSaleModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.direct_sale') }}" class="modal-content glass-card text-white border-secondary">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-success">🛍️ بيع مباشر (بدون حجز جهاز)</h5>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" name="product_id" id="directSaleProdId">
                        <h5 id="directSaleProdName" class="text-info fw-bold mb-3"></h5>
                        <p class="mb-2">سعر القطعة: <strong id="directSaleProdPrice" class="text-warning"></strong> د.ع</p>
                        <div class="mb-3">
                            <label class="fw-bold mb-1">الكمية المطلوبة:</label>
                            <input type="number" name="quantity" id="directSaleQuantity" value="1" min="1" class="form-control bg-dark text-white border-secondary fs-5" onchange="recalcDirectSaleTotal()" onkeyup="recalcDirectSaleTotal()" required>
                        </div>
                        <div class="p-3 bg-dark rounded border border-secondary text-center">
                            <span class="text-light opacity-75 d-block mb-1">المبلغ الإجمالي المستحق:</span>
                            <h3 class="text-warning fw-bold mb-0"><span id="directSaleTotal">0</span> د.ع</h3>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="submit" class="btn btn-glow-green w-100 py-2 fs-5">إتمام البيع المباشر واستلام المبلغ 💵</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal إنشاء قسم جديد -->
        <div class="modal fade" id="addSectionModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.create_section') }}" class="modal-content glass-card text-white border-secondary">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-pink">✨ إضافة قسم جديد</h5>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="fw-bold mb-1">اسم القسم الجديد</label>
                            <input type="text" name="section_name" class="form-control bg-dark text-white border-secondary" placeholder="مثال: قسم البلايستيشن" required>
                        </div>
                        <div class="mb-3">
                            <label class="fw-bold mb-1">نوع القسم</label>
                            <select name="section_type" class="form-select bg-dark text-white border-secondary" required>
                                <option value="game">🎮 قسم أجهزة ولعب (طاولات/أجهزة)</option>
                                <option value="product">🥤 قسم مأكولات/عصائر/أركيلة/خدمات</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="fw-bold mb-1">السمايل / الأيقونة</label>
                            <input type="text" name="section_icon" class="form-control bg-dark text-white border-secondary text-center fs-4" value="🎮" required>
                        </div>
                        <div class="mb-3">
                            <label class="fw-bold mb-1">لون القسم والبطاقات</label>
                            <input type="color" name="section_color" class="form-control form-control-color bg-dark border-secondary" value="#ec4899" style="width: 100%; height: 45px; cursor: pointer;">
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="submit" class="btn btn-glow-pink w-100 py-2 fs-5">حفظ وإنشاء القسم 🚀</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal نقل الجلسة -->
        <div class="modal fade" id="transferSessionModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.transfer_session') }}" class="modal-content glass-card text-white border-warning" style="background: rgba(13, 21, 39, 0.98) !important;">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-warning">🔀 نقل الجلسة إلى أي قسم/جهاز متاح</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="إغلاق"></button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" name="session_id" id="transferSessionId">
                        <p class="fs-5 text-white">الجلسة  على: <strong id="transferOldName" class="text-info"></strong></p>
                        <div class="mb-3">
                            <label class="fw-bold mb-2">اختر الميز / اللعبة الجديدة (مقسمة حسب الأقسام المتاحة):</label>
                            <select name="new_item_id" class="form-select bg-dark text-white border-secondary fs-6 py-2" required>
                                <option value="" disabled selected>-- اختر الجهاز/الطاولة الجديدة --</option>
                                {% set ns = namespace(current_cat="") %}
                                {% for fi in free_items %}
                                    {% if fi['category_name'] != ns.current_cat %}
                                        {% if not loop.first %}</optgroup>{% endif %}
                                        {% set ns.current_cat = fi['category_name'] %}
                                        <optgroup label="📂 {{ fi['category_name'] }}">
                                    {% endif %}
                                    <option value="{{ fi['id'] }}">📍 {{ fi['name'] }} (السعر: {{ fi['price'] }} د.ع)</option>
                                    {% if loop.last %}</optgroup>{% endif %}
                                {% else %}
                                    <option value="" disabled>لا يوجد أجهزة أو طاولات متاحة حالياً في أي قسم</option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-secondary px-3" data-bs-dismiss="modal">إلغاء</button>
                        <button type="submit" class="btn btn-glow-purple px-4 py-2 fs-5">تأكيد نقل الجلسة 🔄</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal تعديل السعر للجهاز مباشرة -->
        <div class="modal fade" id="editPriceModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.update_item_price') }}" class="modal-content glass-card text-white border-secondary">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-warning">✏️ تعديل سعر الجهاز/الطاولة</h5>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" name="item_id" id="editPriceItemId">
                        <h5 id="editPriceItemName" class="text-info fw-bold mb-3"></h5>
                        <div class="mb-3">
                            <label class="fw-bold mb-1">السعر الجديد (د.ع):</label>
                            <input type="number" step="250" name="price" id="editPriceValue" class="form-control bg-dark text-white border-secondary fs-5" required>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="submit" class="btn btn-glow-green w-100 py-2 fs-5">حفظ السعر الجديد 💾</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal تعديل المنتج -->
        <div class="modal fade" id="editProductModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.update_product') }}" class="modal-content glass-card text-white border-secondary">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-warning">✏️ تعديل بيانات المنتج</h5>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" name="product_id" id="editProdId">
                        <div class="mb-3">
                            <label class="fw-bold mb-1">اسم المنتج</label>
                            <input type="text" name="name" id="editProdName" class="form-control bg-dark text-white border-secondary" required>
                        </div>
                        <div class="mb-3">
                            <label class="fw-bold mb-1">السعر (د.ع)</label>
                            <input type="number" step="250" name="price" id="editProdPrice" class="form-control bg-dark text-white border-secondary" required>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="submit" class="btn btn-glow-green w-100 py-2 fs-5">تعديل المنتج 💾</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal تفاصيل كاملة قبل إنهاء الجلسة -->
        <div class="modal fade" id="endSessionPreviewModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <form method="POST" action="{{ url_for('admin.end_session') }}" class="modal-content glass-card text-white border-secondary" style="background: rgba(13, 21, 39, 0.98) !important;">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-danger">🧾 تفاصيل الفاتورة والحساب الكامل قبل الإنهاء</h5>
                    </div>
                    <div class="modal-body" id="endSessionPreviewBody">
                    </div>
                    <div class="modal-footer border-secondary d-flex justify-content-between flex-wrap gap-2">
                        <input type="hidden" name="session_id" id="previewSessionId">
                        <button type="button" class="btn btn-secondary px-3" data-bs-dismiss="modal">إلغاء / عودة</button>
                        
                        <div class="d-flex gap-2 flex-wrap">
                            <button type="button" class="btn btn-glow-purple px-3 fs-5 fw-bold shadow" onclick="openTransferFromPreview()">
                                🔀 نقل الجلسة
                            </button>
                            <button type="button" class="btn btn-warning px-3 fs-5 fw-bold shadow" onclick="openRenewFromPreview()">
                                🔄 تجديد اللعب
                            </button>
                            <button type="submit" class="btn btn-glow-green px-4 fs-5 fw-bold">تأكيد إنهاء الجلسة واستلام المبلغ 🛑</button>
                        </div>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal تجديد اللعب للجلسة -->
        <div class="modal fade" id="renewSessionModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.renew_session') }}" class="modal-content glass-card text-white border-warning" style="background: rgba(13, 21, 39, 0.98) !important;">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-warning">🔄 تجديد اللعب مرة أخرى</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="إغلاق"></button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" name="session_id" id="renewSessionId">
                        <h5 id="renewSessionItemName" class="text-info fw-bold mb-3"></h5>

                        <div class="alert alert-dark border border-secondary text-light small mb-3">
                            💡 سيتم حفظ وتثبيت حساب اللعب السابق وترحيله للفاتورة، والبدء بفترة لعب جديدة حسب الخيارات أدناه.
                        </div>
                        
                        <div class="mb-3">
                            <label class="fw-bold mb-2 text-warning">اختر نظام التجديد (طريقة اللعب):</label>
                            <select name="session_type" id="renewSessionTypeSelect" class="form-select bg-dark text-white border-secondary fs-6 py-2" onchange="toggleRenewTimeInputs()">
                                <option value="بالوقت">⏱️ بالوقت (تمديد/عداد تنازلي)</option>
                                <option value="وقت مفتوح">🔓 وقت مفتوح (عداد تصاعدي)</option>
                                <option value="بالكيم">🎮 بالكيم (كيم جديد بسعر محدد)</option>
                            </select>
                        </div>

                        <div class="mb-3 p-3 bg-dark rounded border border-secondary">
                            <label class="fw-bold text-warning mb-1">سعر اللعب الجديد (د.ع / للساعة أو للكيم):</label>
                            <input type="number" step="250" name="custom_price" id="renewSessionPrice" class="form-control bg-secondary text-white border-0 fs-5 fw-bold" required>
                            <small class="text-light opacity-75 d-block mt-1">يمكنك إبقاء السعر ثابتاً كما هو أو تغييره لهذه الفترة.</small>
                        </div>

                        <div id="renewTimeDurationBox" class="p-3 bg-dark rounded border border-secondary mb-3">
                            <label class="fw-bold text-warning mb-2">حدد الوقت المطلوب للإضافة:</label>
                            <div class="row">
                                <div class="col-6">
                                    <label class="small text-light opacity-75 mb-1">بالساعة:</label>
                                    <input type="number" name="hours" class="form-control bg-secondary text-white border-0 fs-5" value="1" min="0">
                                </div>
                                <div class="col-6">
                                    <label class="small text-light opacity-75 mb-1">بالدقائق:</label>
                                    <input type="number" name="minutes" class="form-control bg-secondary text-white border-0 fs-5" value="0" min="0" step="5">
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-secondary px-3" data-bs-dismiss="modal">إلغاء</button>
                        <button type="submit" class="btn btn-glow-green px-4 fs-5 fw-bold">تأكيد تجديد اللعب 🔄</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal Start Session مع إمكانية التحكم بالسعر -->
        <div class="modal fade" id="startSessionModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.start_session') }}" class="modal-content glass-card text-white border-secondary">
                    <div class="modal-header border-secondary"><h5 class="modal-title fw-bold">🚀 بدء حجز جديد</h5></div>
                    <div class="modal-body">
                        <input type="hidden" name="item_id" id="startSessionItemId">
                        <h5 id="startSessionItemName" class="text-info fw-bold mb-3"></h5>
                        
                        <div class="mb-3">
                            <label class="fw-bold mb-2">اختر نظام اللعب:</label>
                            <select name="session_type" id="sessionTypeSelect" class="form-select bg-dark text-white border-secondary" onchange="toggleTimeInputs()">
                                <option value="بالوقت">⏱️ بالوقت (عداد تنازلي)</option>
                                <option value="وقت مفتوح">🔓 وقت مفتوح (عداد تصاعدي)</option>
                                <option value="بالكيم">🎮 بالكيم (سعر ثابت بدون وقت)</option>
                            </select>
                        </div>

                        <div class="mb-3 p-3 bg-dark rounded border border-secondary">
                            <label class="fw-bold text-warning mb-1">سعر اللعب للجلسة (د.ع / للساعة أو للكيم):</label>
                            <input type="number" step="250" name="custom_price" id="startSessionPrice" class="form-control bg-secondary text-white border-0 fs-5 fw-bold" required>
                            <small class="text-light opacity-75 d-block mt-1">يمكنك تعديل السعر المباشر هنا قبل بدء الحجز.</small>
                        </div>

                        <div id="timeDurationBox" class="p-3 bg-dark rounded border border-secondary mb-3">
                            <label class="fw-bold text-warning mb-2">حدد الوقت المطلوب:</label>
                            <div class="row">
                                <div class="col-6">
                                    <label>بالساعة:</label>
                                    <input type="number" name="hours" class="form-control bg-secondary text-white border-0 fs-5" value="1" min="0">
                                </div>
                                <div class="col-6">
                                    <label>بالدقائق:</label>
                                    <input type="number" name="minutes" class="form-control bg-secondary text-white border-0 fs-5" value="0" min="0" step="5">
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="submit" class="btn btn-glow-green w-100 py-2 fs-5">بدء الحجز ◀</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal Add Item -->
        <div class="modal fade" id="addItemModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.create_item') }}" class="modal-content glass-card text-white border-secondary">
                    <div class="modal-header border-secondary"><h5 class="modal-title">إضافة جهاز / طاولة جديدة</h5></div>
                    <div class="modal-body">
                        <input type="hidden" name="category" id="itemCategory">
                        <div class="mb-3"><label>اسم الجهاز / الطاولة</label><input type="text" name="name" class="form-control bg-dark text-white border-secondary" required></div>
                        <div class="mb-3"><label>نظام اللعب الافتراضي</label>
                            <select name="play_mode" class="form-select bg-dark text-white border-secondary">
                                <option value="بالوقت">⏱️ بالوقت</option>
                                <option value="وقت مفتوح">🔓 وقت مفتوح</option>
                                <option value="بالكيم">🎮 بالكيم</option>
                            </select>
                        </div>
                        <div class="mb-3"><label>السعر (د.ع / للساعة أو بالكيم)</label><input type="number" step="250" name="price" class="form-control bg-dark text-white border-secondary" required></div>
                    </div>
                    <div class="modal-footer border-secondary"><button type="submit" class="btn btn-glow-purple w-100">حفظ العنصر</button></div>
                </form>
            </div>
        </div>

        <!-- Modal Add Product -->
        <div class="modal fade" id="addProductModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.create_product') }}" enctype="multipart/form-data" class="modal-content glass-card text-white border-secondary">
                    <div class="modal-header border-secondary"><h5 class="modal-title">إضافة منتج أو خدمة جديدة</h5></div>
                    <div class="modal-body">
                        <div class="mb-3"><label>اسم المنتج / المشروب / الخدمة</label><input type="text" name="name" class="form-control bg-dark text-white border-secondary" required></div>
                        <div class="mb-3"><label>التصنيف</label>
                            <input type="text" name="category" id="productCategoryInput" class="form-control bg-dark text-white border-secondary" required>
                        </div>
                        <div class="mb-3"><label>السعر (د.ع)</label><input type="number" step="250" name="price" class="form-control bg-dark text-white border-secondary" required></div>
                        <div class="mb-3">
                            <label>الصورة (اختياري)</label>
                            <input type="file" name="image_file" class="form-control bg-dark text-white border-secondary" accept="image/*">
                        </div>
                    </div>
                    <div class="modal-footer border-secondary"><button type="submit" class="btn btn-glow-pink w-100">حفظ المنتج</button></div>
                </form>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            let currentDirectUnitPrice = 0;
            let currentPreviewSessionData = null;

            function setCategory(cat) { document.getElementById('itemCategory').value = cat; }
            function setProductCategory(catName) { document.getElementById('productCategoryInput').value = catName; }
            
            function prepareStartSession(itemId, itemName, itemPrice, itemPlayMode) {
                document.getElementById('startSessionItemId').value = itemId;
                document.getElementById('startSessionItemName').innerText = itemName;
                document.getElementById('startSessionPrice').value = itemPrice;
                if (itemPlayMode) {
                    const select = document.getElementById('sessionTypeSelect');
                    select.value = itemPlayMode;
                    toggleTimeInputs();
                }
            }

            function prepareEditPrice(itemId, itemName, itemPrice) {
                document.getElementById('editPriceItemId').value = itemId;
                document.getElementById('editPriceItemName').innerText = itemName;
                document.getElementById('editPriceValue').value = itemPrice;
            }

            function prepareEditProduct(id, name, price) {
                document.getElementById('editProdId').value = id;
                document.getElementById('editProdName').value = name;
                document.getElementById('editProdPrice').value = price;
            }

            function prepareDirectSale(id, name, price) {
                document.getElementById('directSaleProdId').value = id;
                document.getElementById('directSaleProdName').innerText = name;
                document.getElementById('directSaleProdPrice').innerText = price;
                document.getElementById('directSaleQuantity').value = 1;
                currentDirectUnitPrice = price;
                recalcDirectSaleTotal();
            }

            function recalcDirectSaleTotal() {
                let qty = parseInt(document.getElementById('directSaleQuantity').value) || 1;
                document.getElementById('directSaleTotal').innerText = (qty * currentDirectUnitPrice).toLocaleString();
            }

            function prepareTransferSession(sessionId, oldName) {
                document.getElementById('transferSessionId').value = sessionId;
                document.getElementById('transferOldName').innerText = oldName;
            }

            function prepareRenewSession(sessionId, itemName, itemPrice, sessionType) {
                document.getElementById('renewSessionId').value = sessionId;
                document.getElementById('renewSessionItemName').innerText = 'الجهاز: ' + itemName;
                document.getElementById('renewSessionPrice').value = itemPrice || '';
                if (sessionType) {
                    document.getElementById('renewSessionTypeSelect').value = sessionType;
                }
                toggleRenewTimeInputs();
                let myModal = new bootstrap.Modal(document.getElementById('renewSessionModal'));
                myModal.show();
            }

            function openRenewFromPreview() {
                let previewModalEl = document.getElementById('endSessionPreviewModal');
                let previewModal = bootstrap.Modal.getInstance(previewModalEl);
                if (previewModal) {
                    previewModal.hide();
                }
                if (currentPreviewSessionData) {
                    prepareRenewSession(
                        currentPreviewSessionData.session_id,
                        currentPreviewSessionData.item_name,
                        currentPreviewSessionData.item_price,
                        currentPreviewSessionData.session_type
                    );
                }
            }

            function openTransferFromPreview() {
                let previewModalEl = document.getElementById('endSessionPreviewModal');
                let previewModal = bootstrap.Modal.getInstance(previewModalEl);
                if (previewModal) {
                    previewModal.hide();
                }
                if (currentPreviewSessionData) {
                    prepareTransferSession(
                        currentPreviewSessionData.session_id,
                        currentPreviewSessionData.item_name
                    );
                    let transferModal = new bootstrap.Modal(document.getElementById('transferSessionModal'));
                    transferModal.show();
                }
            }

            function toggleRenewTimeInputs() {
                const type = document.getElementById('renewSessionTypeSelect').value;
                document.getElementById('renewTimeDurationBox').style.display = (type === 'بالوقت') ? 'block' : 'none';
            }

            function previewEndSession(sessionId) {
                document.getElementById('previewSessionId').value = sessionId;
                fetch('/admin/session/details/' + sessionId)
                    .then(res => res.json())
                    .then(data => {
                        currentPreviewSessionData = data;
                        currentPreviewSessionData.session_id = sessionId;

                        let carriedHtml = data.carried_over_cost > 0 ? `<p class="mb-1 text-info fs-6">مبلغ مرحل من جولات/نقل سابق: <strong>${data.carried_over_cost.toLocaleString()} د.ع</strong></p>` : '';
                        let html = `
                            <div class="p-3 bg-dark rounded border border-secondary mb-3">
                                <h5>اسم العنصر: <span class="text-info">${data.item_name}</span></h5>
                                <p class="mb-1">نوع الجلسة: <strong>${data.session_type}</strong></p>
                                ${(data.session_type === 'بالوقت' || data.session_type === 'وقت مفتوح') ? `<p class="mb-1">الوقت المحتسب: <strong>${data.duration_minutes} دقيقة</strong></p>` : ''}
                                ${carriedHtml}
                                <p class="mb-0 text-warning fs-5">مجموع سعر اللعب للجلسة: <strong>${data.play_cost.toLocaleString()} د.ع</strong></p>
                            </div>
                            <h6 class="fw-bold text-white mb-2">قائمة الخدمات والمشروبات المضافة:</h6>
                        `;
                        
                        if (data.products && data.products.length > 0) {
                            html += '<ul class="list-group mb-3">';
                            data.products.forEach(p => {
                                html += `<li class="list-group-item bg-secondary text-white d-flex justify-content-between align-items-center">
                                    <span>${p.product_name} (x${p.quantity})</span>
                                    <div>
                                        <span class="text-warning fw-bold me-3">${p.total.toLocaleString()} د.ع</span>
                                        <a href="/admin/session/product/delete/${p.id}" class="btn btn-sm btn-outline-danger" onclick="return confirm('حذف الطلب؟')">🗑️</a>
                                    </div>
                                </li>`;
                            });
                            html += '</ul>';
                        } else {
                            html += '<div class="alert alert-secondary p-2 mb-3">لا توجد خدمات مضافة لهذه الجلسة.</div>';
                        }

                        html += `
                            <div class="p-3 bg-primary text-white text-center rounded">
                                <h4>المبلغ الإجمالي النهائي الواجب استلامه:</h4>
                                <h2 class="fw-bold text-warning mb-0">${data.total_cost.toLocaleString()} د.ع</h2>
                            </div>
                        `;
                        document.getElementById('endSessionPreviewBody').innerHTML = html;
                        let myModal = new bootstrap.Modal(document.getElementById('endSessionPreviewModal'));
                        myModal.show();
                    });
            }

            function toggleTimeInputs() {
                const type = document.getElementById('sessionTypeSelect').value;
                document.getElementById('timeDurationBox').style.display = (type === 'بالوقت') ? 'block' : 'none';
            }

            document.addEventListener('DOMContentLoaded', () => {
                const activeTabTarget = localStorage.getItem('activeAdminSectionTab');
                if (activeTabTarget) {
                    const tabBtn = document.querySelector(`#mainTabs button[data-bs-target="${activeTabTarget}"]`);
                    if (tabBtn) {
                        const tab = new bootstrap.Tab(tabBtn);
                        tab.show();
                    }
                }

                const mainTabButtons = document.querySelectorAll('#mainTabs button[data-bs-toggle="pill"]');
                mainTabButtons.forEach(btn => {
                    btn.addEventListener('shown.bs.tab', (e) => {
                        const target = e.target.getAttribute('data-bs-target');
                        localStorage.setItem('activeAdminSectionTab', target);
                    });
                });

                const timers = document.querySelectorAll('.countdown-timer');
                setInterval(() => {
                    timers.forEach(timer => {
                        const startAttr = timer.getAttribute('data-start');
                        if (startAttr && startAttr.trim() !== '') {
                            const startTime = new Date(startAttr.replace(/-/g, "/")).getTime();
                            if (!isNaN(startTime)) {
                                const now = new Date().getTime();
                                const diff = now - startTime;
                                if (diff >= 0) {
                                    const hours = Math.floor(diff / (1000 * 60 * 60));
                                    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                                    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
                                    timer.innerText = 
                                        (hours < 10 ? '0' + hours : hours) + ':' +
                                        (minutes < 10 ? '0' + minutes : minutes) + ':' +
                                        (seconds < 10 ? '0' + seconds : seconds);
                                }
                            }
                            return;
                        }

                        const targetAttr = timer.getAttribute('data-target');
                        if (!targetAttr || targetAttr.trim() === '') return;

                        const targetTime = new Date(targetAttr.replace(/-/g, "/")).getTime();
                        if (isNaN(targetTime)) return;

                        const now = new Date().getTime();
                        const difference = targetTime - now;

                        if (difference > 0) {
                            const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                            const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
                            const seconds = Math.floor((difference % (1000 * 60)) / 1000);

                            timer.innerText = 
                                (hours < 10 ? '0' + hours : hours) + ':' +
                                (minutes < 10 ? '0' + minutes : minutes) + ':' +
                                (seconds < 10 ? '0' + seconds : seconds);
                        } else {
                            if (!timer.classList.contains('timer-ended')) {
                                timer.innerText = "00:00:00 (انتهى الوقت - الحساب متوقف!)";
                                timer.classList.add('timer-ended');
                            }
                        }
                    });
                }, 1000);
            });
        </script>
    </body></html>
    ''', COMMON_STYLE=COMMON_STYLE, categories=categories, items=items, products=products, active_sessions=active_sessions, session_prods=session_prods, free_items=free_items)

@admin_bp.add_app_template_global
def render_items(items, target_cat, active_sessions, session_prods, products, free_items, cat_color="#ec4899"):
    filtered = [i for i in items if i['category'] == target_cat]
    if not filtered:
        return Markup('<div class="alert alert-secondary text-center text-white py-3">لا يوجد أجهزة أو طاولات مضافة في هذا القسم حالياً.</div>')
    
    html = '<div class="row">'
    for item in filtered:
        active_session = next((s for s in active_sessions if s['item_id'] == item['id']), None)
        status_badge = '<span class="status-badge-busy">مشغول</span>' if active_session else '<span class="status-badge-active">متاح</span>'
        
        animated_style = f"background: linear-gradient(-45deg, rgba(15, 23, 42, 0.95), {cat_color}45, #0d1527, {cat_color}30);" if active_session else "background: rgba(31, 41, 61, 0.6);"
        animated_class = "animated-section-bg" if active_session else ""
        
        html += f'''
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="glass-card p-3 h-100 d-flex flex-column justify-content-between {animated_class}" style="{animated_style} border: 1px solid {cat_color}50;">
                <div>
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h3 class="fw-bold m-0 text-white">{item['name']}</h3>
                        <div class="d-flex align-items-center gap-1">
                            {status_badge}
                            {f'<button class="btn btn-sm btn-outline-warning p-1 me-1" data-bs-toggle="modal" data-bs-target="#editPriceModal" onclick="prepareEditPrice({item["id"]}, \'{item["name"]}\', {item["price"]})" title="تعديل السعر">✏️</button>' if user_can('edit_item_price') else ''}
                            {f'<a href="/admin/item/delete/{item["id"]}" class="btn btn-sm btn-outline-danger p-1" onclick="return confirm(\'هل تريد حذف هذا العنصر؟\');">🗑️</a>' if user_can('manage_items') else ''}
                        </div>
                    </div>
        '''
        
        if active_session:
            prods = session_prods.get(active_session['id'], [])
            prod_items_html = []
            for p in prods:
                delete_btn = f"<a href='/admin/session/product/delete/{p['id']}' class='btn btn-sm text-danger p-0 me-1' title='حذف الطلب' onclick='return confirm(\"هل تريد حذف هذا الطلب؟\")'>✖</a>" if user_can('delete_session_product') else ""
                prod_items_html.append(f"<li class='d-flex justify-content-between align-items-center text-white fs-6 py-1 border-bottom border-secondary'><span>• {p['product_name']} (x{p['quantity']})</span> <div><span class='text-warning fw-bold me-2'>{p['total']} د.ع</span>{delete_btn}</div></li>")
            
            prod_html = "".join(prod_items_html)
            
            if active_session['session_type'] in ['بالكيم', 'بالجيم']:
                html += f'''
                <div class="text-center p-3 mb-3 rounded-3" style="background: rgba(0,0,0,0.4); border: 1px dashed {cat_color};">
                    <span class="badge fs-6 mb-2 px-3 py-2 rounded-pill" style="background-color: {cat_color}; color: #fff;">🎮 محجوز (نظام بالكيم)</span>
                    <div class="text-warning fw-bold fs-3 mt-1">{item['price']} د.ع</div>
                </div>
                '''
            elif active_session['session_type'] == 'وقت مفتوح':
                start_time_attr = active_session['start_time'] if active_session['start_time'] else ""
                html += f'''
                <div class="text-center p-3 mb-3 rounded-3" style="background: rgba(0,0,0,0.4); border: 1px dashed {cat_color};">
                    <span class="badge fs-6 mb-2 px-3 py-2 rounded-pill bg-success text-white">🔓 محجوز (وقت مفتوح)</span>
                    <div class="text-warning fw-bold mt-2">السعر: {item['price']} د.ع / ساعة</div>
                    <small class="text-light opacity-75 d-block fw-bold mb-1">⏱️ الوقت المنقضي:</small>
                    <div class="countdown-timer d-inline-block" data-start="{start_time_attr}">00:00:00</div>
                </div>
                '''
            else:
                target_time_attr = active_session['target_end_time'] if active_session['target_end_time'] else ""
                html += f'''
                <div class="text-center p-3 mb-3 rounded-3" style="background: rgba(0,0,0,0.4); border: 1px dashed {cat_color};">
                    <div class="text-warning fw-bold mt-2">السعر: {item['price']} د.ع / ساعة</div>
                '''
                if target_time_attr:
                    html += f'''
                    <small class="text-light opacity-75 d-block fw-bold mb-1">⏱️ الوقت المتبقي للجلسة:</small>
                    <div class="countdown-timer d-inline-block" data-target="{target_time_attr}">00:00:00</div>
                    '''
                html += '</div>'

            html += f'''
                <div class="p-2 mb-3 rounded" style="background: rgba(0,0,0,0.3);">
                    <div class="fw-bold text-info mb-1 fs-6">🍔 الطلبات المضافة للجلسة:</div>
                    <ul class="list-unstyled mb-0 px-1">{prod_html if prod_html else '<li class="small text-light opacity-75">لا يوجد طلبات مضافة بعد</li>'}</ul>
                </div>
            </div>
            
            <div class="d-flex flex-column gap-2 mt-2">
            '''
            
            if user_can('transfer_session'):
                html += f'''
                <button class="btn btn-glow-purple btn-sm fw-bold w-100 py-2 fs-6 shadow" data-bs-toggle="modal" data-bs-target="#transferSessionModal" onclick="prepareTransferSession({active_session['id']}, '{item['name']}')">
                    🔀 نقل الجلسة إلى ميز/قسم آخر
                </button>
                '''

            if user_can('start_session'):
                html += f'''
                <button class="btn btn-warning btn-sm fw-bold w-100 py-2 fs-6 shadow-sm" onclick="prepareRenewSession({active_session['id']}, '{item['name']}', {item['price']}, '{active_session['session_type']}')">
                    🔄 تجديد اللعب مرة أخرى
                </button>
                '''
            
            if user_can('add_product_to_session'):
                options = '<option value="" disabled selected>-- اختر طعام / عصير / خدمة --</option>' + "".join([f"<option value='{p['id']}'>{p['name']} ({p['price']} د.ع)</option>" for p in products])
                html += f'''
                <div class="p-2 rounded mt-1" style="background: rgba(0, 0, 0, 0.45); border: 1px solid rgba(255, 255, 255, 0.15);">
                    <div class="small fw-bold text-warning mb-1">➕ إضافة طلب للجلسة:</div>
                    <form method="POST" action="/admin/session/add_product">
                        <input type="hidden" name="session_id" value="{active_session['id']}">
                        <div class="row g-1 align-items-center">
                            <div class="col-6">
                                <select name="product_id" class="form-select form-select-sm bg-dark text-white border-secondary" required>
                                    {options}
                                </select>
                            </div>
                            <div class="col-3">
                                <input type="number" name="quantity" value="1" min="1" class="form-control form-control-sm bg-dark text-white border-secondary text-center" placeholder="العدد" title="العدد المطلوب">
                            </div>
                            <div class="col-3">
                                <button type="submit" class="btn btn-sm btn-glow-green w-100 fw-bold py-1">إضافة ➕</button>
                            </div>
                        </div>
                    </form>
                </div>
                '''

            cancel_btn = f'<a href="/admin/session/cancel/{active_session["id"]}" class="btn btn-outline-secondary btn-sm fw-bold py-2 px-2" onclick="return confirm(\'هل أنت تأكد من إلغاء هذه الجلسة دون احتساب أرباح؟\');" title="إلغاء الحجز">🚫 إلغاء</a>' if user_can('cancel_session') else ''
            
            if user_can('end_session'):
                html += f'''
                <div class="d-flex gap-1 mt-1">
                    <button class="btn btn-danger flex-grow-1 btn-sm fw-bold py-2 fs-6" onclick="previewEndSession({active_session['id']})">
                        📋 تفاصيل وإنهاء الجلسة 🛑
                    </button>
                    {cancel_btn}
                </div>
                '''
            elif cancel_btn:
                html += f'<div class="mt-1">{cancel_btn}</div>'

            html += '</div>'
        else:
            play_mode_label = item['play_mode'] if item['play_mode'] else "بالوقت"
            html += f'''
                <div class="bg-dark p-3 rounded-3 text-center my-4 border border-secondary">
                    <small class="text-light opacity-75 d-block mb-1">السعر المحدد للحجز:</small>
                    <span class="badge bg-secondary mb-1">{play_mode_label}</span>
                    <div class="text-warning fw-bold fs-4">{item['price']} د.ع</div>
                </div>
            </div>
            '''
            if user_can('start_session'):
                item_play_mode_escaped = item['play_mode'].replace("'", "\\'") if item['play_mode'] else 'بالوقت'
                html += f'''
                <button class="btn btn-glow-cyan w-100 py-2 fs-5 mt-2" data-bs-toggle="modal" data-bs-target="#startSessionModal" onclick="prepareStartSession({item['id']}, '{item['name']}', {item['price']}, '{item_play_mode_escaped}')">
                    بدء حجز ◀
                </button>
                '''
                
        html += '</div></div>'
    html += '</div>'
    return Markup(html)

@admin_bp.add_app_template_global
def render_products(products, cat_name):
    filtered = [p for p in products if p['category'] == cat_name]
    if not filtered:
        return Markup('<div class="alert alert-secondary text-center text-white py-3">لا يوجد منتجات مضافة لهذا القسم حالياً.</div>')
    
    html = '''
    <div class="table-responsive">
        <table class="table table-dark-custom align-middle">
            <thead>
                <tr><th>الصورة</th><th>اسم المنتج / الخدمة</th><th>السعر</th><th>إجراءات والبيع المباشر</th></tr>
            </thead>
            <tbody>
    '''
    for p in filtered:
        img_html = f'<img src="{p["image_url"]}" class="rounded border border-secondary" style="width: 60px; height: 60px; object-fit: contain; background-color: #0f172a; padding: 2px;">' if p['image_url'] else '<span class="badge bg-secondary">بدون صورة</span>'
        html += f'''
        <tr>
            <td>{img_html}</td>
            <td class="fw-bold fs-5 text-white">{p['name']}</td>
            <td class="text-warning fw-bold fs-5">{p['price']} د.ع</td>
            <td>
                <button class="btn btn-sm btn-glow-green me-1 fw-bold" data-bs-toggle="modal" data-bs-target="#directSaleModal" onclick="prepareDirectSale({p['id']}, \'{p['name']}\', {p['price']})">🛍️ بيع مباشر</button>
                {f'<button class="btn btn-sm btn-outline-warning me-1" data-bs-toggle="modal" data-bs-target="#editProductModal" onclick="prepareEditProduct({p["id"]}, \'{p["name"]}\', {p["price"]})">✏️ تعديل</button>' if user_can('manage_products') else ''}
                {f'<a href="/admin/product/delete/{p["id"]}" class="btn btn-sm btn-outline-danger" onclick="return confirm(\'هل تريد حذف هذا المنتج؟\');">🗑️ حذف</a>' if user_can('manage_products') else ''}
            </td>
        </tr>
        '''
    html += '</tbody></table></div>'
    return Markup(html)

@admin_bp.route('/product/direct_sale', methods=['POST'])
@login_required
def direct_sale():
    if not user_can('add_product_to_session') and not user_can('manage_products'):
        flash('ليس لديك صلاحية البيع المباشر!', 'danger')
        return redirect(url_for('admin.dashboard'))

    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    if not product_id:
        flash('يرجى اختيار المنتج المراد بيعه!', 'danger')
        return redirect(url_for('admin.dashboard'))

    conn = db.get_db()
    prod = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not prod:
        flash('المنتج غير موجود!', 'danger')
        return redirect(url_for('admin.dashboard'))

    total_price = prod['price'] * quantity
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sessions (item_id, item_name, session_type, start_time, target_end_time, duration_minutes, created_by, play_cost, products_cost, total_cost, status, carried_over_cost)
        VALUES (NULL, ?, 'بيع مباشر', ?, ?, 0, ?, 0.0, ?, ?, 'completed', 0.0)
    ''', ('بيع مباشر (طعام/مشروبات)', now_str, now_str, session['full_name'], total_price, total_price))
    
    sess_id = cursor.lastrowid
    
    cursor.execute('''
        INSERT INTO session_products (session_id, product_name, price, quantity, total)
        VALUES (?, ?, ?, ?, ?)
    ''', (sess_id, prod['name'], prod['price'], quantity, total_price))

    conn.commit()
    flash(f'تم إتمام البيع المباشر لـ ({prod["name"]} x{quantity}) بمبلغ {total_price:,.0f} د.ع وتسجيلها باسم ({session["full_name"]}) بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/section/create', methods=['POST'])
@login_required
def create_section():
    if not user_can('manage_sections'):
        flash('ليس لديك صلاحية إنشاء قسم!', 'danger')
        return redirect(url_for('admin.dashboard'))

    section_name = request.form.get('section_name')
    section_type = request.form.get('section_type', 'game')
    section_icon = request.form.get('section_icon', '🎮')
    section_color = request.form.get('section_color', '#ec4899')
    
    key = "sec_" + str(int(datetime.now().timestamp()))
    
    conn = db.get_db()
    conn.execute('INSERT INTO categories (key, name, icon, color, type) VALUES (?, ?, ?, ?, ?)',
                 (key, section_name, section_icon, section_color, section_type))
    conn.commit()
    
    flash(f'تم إنشاء القسم ({section_name}) بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/section/delete/<int:section_id>')
@login_required
def delete_section(section_id):
    if not user_can('manage_sections'):
        flash('ليس لديك صلاحية حذف الأقسام!', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    conn = db.get_db()
    cat = conn.execute('SELECT * FROM categories WHERE id = ?', (section_id,)).fetchone()
    if cat:
        log_deletion('حذف قسم كامل', cat['name'], f"تم حذف القسم ({cat['name']}) مع كافة عناصره وأجهزته ومنتجاته.")
        conn.execute('DELETE FROM items WHERE category = ?', (cat['key'],))
        conn.execute('DELETE FROM products WHERE category = ?', (cat['name'],))
        conn.execute('DELETE FROM categories WHERE id = ?', (section_id,))
        conn.commit()
        flash('تم حذف القسم وكافة عناصره بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/item/delete/<int:item_id>')
@login_required
def delete_item(item_id):
    if not user_can('manage_items'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    conn = db.get_db()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if item:
        log_deletion('حذف جهاز/طاولة', item['name'], f"تم حذف الجهاز ({item['name']}) - السعر الافتراضي: {item['price']} د.ع")
        conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
        flash('تم حذف العنصر بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/item/update_price', methods=['POST'])
@login_required
def update_item_price():
    if not user_can('edit_item_price'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))

    item_id = request.form.get('item_id')
    new_price = float(request.form.get('price', 0))
    
    conn = db.get_db()
    conn.execute('UPDATE items SET price = ? WHERE id = ?', (new_price, item_id))
    conn.commit()
    flash('تم تحديث سعر الجهاز/الطاولة بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/product/update', methods=['POST'])
@login_required
def update_product():
    if not user_can('manage_products'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))

    prod_id = request.form.get('product_id')
    name = request.form.get('name')
    price = float(request.form.get('price', 0))
    
    conn = db.get_db()
    conn.execute('UPDATE products SET name = ?, price = ? WHERE id = ?', (name, price, prod_id))
    conn.commit()
    flash('تم تعديل بيانات المنتج بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/product/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    if not user_can('manage_products'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    conn = db.get_db()
    prod = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if prod:
        log_deletion('حذف منتج/خدمة', prod['name'], f"تم حذف المنتج ({prod['name']}) - السعر: {prod['price']} د.ع - القسم: {prod['category']}")
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        flash('تم حذف المنتج بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/session/transfer', methods=['POST'])
@login_required
def transfer_session():
    if not user_can('transfer_session'):
        flash('ليس لديك صلاحية لنقل الجلسات!', 'danger')
        return redirect(url_for('admin.dashboard'))

    session_id = request.form.get('session_id')
    new_item_id = request.form.get('new_item_id')
    
    if not new_item_id:
        flash('يرجى اختيار ميز/جهاز متاح للنقل إليه!', 'danger')
        return redirect(url_for('admin.dashboard'))

    conn = db.get_db()
    sess = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    
    if not sess:
        flash('الجلسة غير موجودة!', 'danger')
        return redirect(url_for('admin.dashboard'))

    old_item = conn.execute('SELECT * FROM items WHERE id = ?', (sess['item_id'],)).fetchone()
    new_item = conn.execute('SELECT * FROM items WHERE id = ?', (new_item_id,)).fetchone()
    
    if sess and new_item:
        now = datetime.now()
        start_time = datetime.strptime(sess['start_time'], "%Y-%m-%d %H:%M:%S")
        elapsed_minutes = max(1, int((now - start_time).total_seconds() / 60))
        
        if sess['session_type'] == 'بالوقت':
            old_price = old_item['price'] if old_item else 0
            duration_lim = sess['duration_minutes'] or 0
            used_minutes = min(elapsed_minutes, duration_lim) if duration_lim > 0 else elapsed_minutes
            old_play_cost = (used_minutes / 60.0) * old_price
            old_play_cost = round(old_play_cost / 250.0) * 250.0
        elif sess['session_type'] == 'وقت مفتوح':
            old_price = old_item['price'] if old_item else 0
            old_play_cost = (elapsed_minutes / 60.0) * old_price
            old_play_cost = round(old_play_cost / 250.0) * 250.0
        else:
            old_play_cost = old_item['price'] if old_item else 0
            
        sess_dict = dict(sess)
        previous_carried_cost = sess_dict.get('carried_over_cost') or 0.0
        total_carried = float(previous_carried_cost) + float(old_play_cost)

        if sess['item_id']:
            conn.execute('UPDATE items SET status = "متاح" WHERE id = ?', (sess['item_id'],))
        conn.execute('UPDATE items SET status = "مشغول" WHERE id = ?', (new_item_id,))
        
        conn.execute('''
            UPDATE sessions 
            SET item_id = ?, item_name = ?, start_time = ?, carried_over_cost = ?
            WHERE id = ?
        ''', (new_item['id'], new_item['name'], now.strftime("%Y-%m-%d %H:%M:%S"), total_carried, session_id))
        
        conn.commit()
        flash(f'تم نقل الجلسة إلى ({new_item["name"]}) بنجاح، وترحيل مبلغ {total_carried:,.0f} د.ع للفاتورة.', 'success')

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/session/renew', methods=['POST'])
@login_required
def renew_session():
    if not user_can('start_session'):
        flash('ليس لديك صلاحية لتجديد الجلسة!', 'danger')
        return redirect(url_for('admin.dashboard'))

    session_id = request.form.get('session_id')
    new_session_type = request.form.get('session_type', 'بالوقت')
    custom_price = request.form.get('custom_price')

    raw_hours = request.form.get('hours', '').strip()
    raw_minutes = request.form.get('minutes', '').strip()

    hours = int(raw_hours) if raw_hours.isdigit() else 0
    minutes = int(raw_minutes) if raw_minutes.isdigit() else 0

    total_minutes = (hours * 60) + minutes
    if new_session_type == 'بالوقت' and total_minutes <= 0:
        total_minutes = 60

    conn = db.get_db()
    sess = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not sess:
        flash('الجلسة غير موجودة!', 'danger')
        return redirect(url_for('admin.dashboard'))

    item = conn.execute('SELECT * FROM items WHERE id = ?', (sess['item_id'],)).fetchone()

    now = datetime.now()
    start_time = datetime.strptime(sess['start_time'], "%Y-%m-%d %H:%M:%S")
    elapsed_minutes = max(1, int((now - start_time).total_seconds() / 60))

    item_price = item['price'] if item else 0

    if sess['session_type'] == 'بالوقت':
        duration_lim = sess['duration_minutes'] or 0
        used_minutes = min(elapsed_minutes, duration_lim) if duration_lim > 0 else elapsed_minutes
        old_play_cost = (used_minutes / 60.0) * item_price
        old_play_cost = round(old_play_cost / 250.0) * 250.0
    elif sess['session_type'] == 'وقت مفتوح':
        old_play_cost = (elapsed_minutes / 60.0) * item_price
        old_play_cost = round(old_play_cost / 250.0) * 250.0
    else:
        old_play_cost = item_price

    sess_dict = dict(sess)
    prev_carried = float(sess_dict.get('carried_over_cost') or 0.0)
    total_carried = prev_carried + float(old_play_cost)

    if custom_price and custom_price.replace('.', '', 1).isdigit() and item:
        new_price_val = float(custom_price)
        if new_price_val != item['price']:
            conn.execute('UPDATE items SET price = ? WHERE id = ?', (new_price_val, item['id']))

    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    target_str = (now + timedelta(minutes=total_minutes)).strftime("%Y-%m-%d %H:%M:%S") if new_session_type == 'بالوقت' else ""

    conn.execute('''
        UPDATE sessions 
        SET session_type = ?, start_time = ?, target_end_time = ?, duration_minutes = ?, carried_over_cost = ?
        WHERE id = ?
    ''', (new_session_type, now_str, target_str, total_minutes if new_session_type == 'بالوقت' else 0, total_carried, session_id))
    
    conn.commit()
    flash(f'تم تجديد اللعب بنجاح على ({sess["item_name"]}) بنظام ({new_session_type})، وتم ترحيل حساب الجولة السابقة ({total_carried:,.0f} د.ع) إلى الفاتورة.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/session/details/<int:session_id>')
@login_required
def session_details(session_id):
    conn = db.get_db()
    sess = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not sess:
        return jsonify({'error': 'Not found'}), 404

    item = conn.execute('SELECT * FROM items WHERE id = ?', (sess['item_id'],)).fetchone()
    products = conn.execute('SELECT * FROM session_products WHERE session_id = ?', (session_id,)).fetchall()
    
    prod_sum = sum([p['total'] for p in products])
    
    sess_dict = dict(sess)
    carried_cost = float(sess_dict.get('carried_over_cost') or 0.0)

    now = datetime.now()
    start_time = datetime.strptime(sess['start_time'], "%Y-%m-%d %H:%M:%S")
    elapsed_minutes = max(1, int((now - start_time).total_seconds() / 60))

    if sess['session_type'] == 'بالوقت':
        item_price = item['price'] if item else 0
        duration_lim = sess['duration_minutes'] or 0
        used_minutes = min(elapsed_minutes, duration_lim) if duration_lim > 0 else elapsed_minutes
        current_play_cost = (used_minutes / 60.0) * item_price
        current_play_cost = round(current_play_cost / 250.0) * 250.0
    elif sess['session_type'] == 'وقت مفتوح':
        item_price = item['price'] if item else 0
        used_minutes = elapsed_minutes
        current_play_cost = (used_minutes / 60.0) * item_price
        current_play_cost = round(current_play_cost / 250.0) * 250.0
    else:
        used_minutes = 0
        current_play_cost = item['price'] if item else 0
        
    play_cost = current_play_cost + carried_cost
    total_cost = play_cost + prod_sum

    return jsonify({
        'session_id': session_id,
        'item_id': sess['item_id'],
        'item_name': sess['item_name'],
        'item_price': item['price'] if item else 0,
        'session_type': sess['session_type'],
        'duration_minutes': used_minutes if sess['session_type'] in ['بالوقت', 'وقت مفتوح'] else sess['duration_minutes'],
        'play_cost': play_cost,
        'carried_over_cost': carried_cost,
        'products': [dict(p) for p in products],
        'products_cost': prod_sum,
        'total_cost': total_cost
    })

@admin_bp.route('/session/start', methods=['POST'])
@login_required
def start_session():
    if not user_can('start_session'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    item_id = request.form['item_id']
    session_type = request.form.get('session_type', 'بالوقت')
    custom_price = request.form.get('custom_price')
    
    raw_hours = request.form.get('hours', '').strip()
    raw_minutes = request.form.get('minutes', '').strip()
    
    hours = int(raw_hours) if raw_hours.isdigit() else 0
    minutes = int(raw_minutes) if raw_minutes.isdigit() else 0
    
    total_minutes = (hours * 60) + minutes
    if session_type == 'بالوقت' and total_minutes <= 0:
        total_minutes = 60

    now = datetime.now()
    target_end = now + timedelta(minutes=total_minutes)
    
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    target_str = target_end.strftime("%Y-%m-%d %H:%M:%S") if session_type == 'بالوقت' else ""
    
    conn = db.get_db()
    
    if custom_price and custom_price.replace('.', '', 1).isdigit():
        conn.execute('UPDATE items SET price = ? WHERE id = ?', (float(custom_price), item_id))
        conn.commit()

    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    
    if item:
        conn.execute('''
            INSERT INTO sessions (item_id, item_name, session_type, start_time, target_end_time, duration_minutes, created_by, carried_over_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0.0)
        ''', (item['id'], item['name'], session_type, now_str, target_str, total_minutes if session_type == 'بالوقت' else 0, session['full_name']))
        conn.execute('UPDATE items SET status = "مشغول" WHERE id = ?', (item_id,))
        conn.commit()
        flash(f'تم بدء حجز ({item["name"]}) بنجاح', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/product/create', methods=['POST'])
@login_required
def create_product():
    if not user_can('manage_products'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    image_path = ""
    file = request.files.get('image_file')
    if file and allowed_file(file.filename):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        image_path = f"/{UPLOAD_FOLDER}/{filename}"
    
    with db.get_db() as conn:
        conn.execute('''
            INSERT INTO products (name, category, price, image_url, show_to_user)
            VALUES (?, ?, ?, ?, 1)
        ''', (request.form['name'], request.form['category'], float(request.form['price']), image_path))
        conn.commit()
    flash('تم إضافة المنتج بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/item/create', methods=['POST'])
@login_required
def create_item():
    if not user_can('manage_items'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    with db.get_db() as conn:
        conn.execute('''
            INSERT INTO items (category, name, play_mode, pricing_type, price)
            VALUES (?, ?, ?, ?, ?)
        ''', (request.form['category'], request.form['name'], request.form['play_mode'], request.form['play_mode'], float(request.form['price'])))
        conn.commit()
    flash('تم إضافة العنصر بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/session/add_product', methods=['POST'])
@login_required
def add_product_to_session():
    if not user_can('add_product_to_session'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))

    sess_id = request.form['session_id']
    prod_id = request.form['product_id']
    qty = int(request.form['quantity'])
    
    conn = db.get_db()
    prod = conn.execute('SELECT * FROM products WHERE id = ?', (prod_id,)).fetchone()
    
    if prod:
        total = prod['price'] * qty
        conn.execute('INSERT INTO session_products (session_id, product_name, price, quantity, total) VALUES (?, ?, ?, ?, ?)',
                     (sess_id, prod['name'], prod['price'], qty, total))
        conn.commit()
        flash('تم إضافة الطلب للحساب', 'success')
        
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/session/product/delete/<int:sp_id>')
@login_required
def delete_session_product(sp_id):
    if not user_can('delete_session_product') and not user_can('add_product_to_session'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))

    conn = db.get_db()
    sp = conn.execute('SELECT * FROM session_products WHERE id = ?', (sp_id,)).fetchone()
    if sp:
        log_deletion('حذف طلب من جلسة', sp['product_name'], f"تم حذف طلب ({sp['product_name']} x{sp['quantity']}) بمبلغ {sp['total']} د.ع من الجلسة رقم #{sp['session_id']}")
        conn.execute('DELETE FROM session_products WHERE id = ?', (sp_id,))
        conn.commit()
        flash('تم حذف الطلب من الجلسة بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/session/cancel/<int:session_id>')
@login_required
def cancel_session(session_id):
    if not user_can('cancel_session') and not user_can('end_session'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))

    conn = db.get_db()
    sess = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    
    if sess:
        prods = conn.execute('SELECT * FROM session_products WHERE session_id = ?', (session_id,)).fetchall()
        prod_summary = ", ".join([f"{p['product_name']} (x{p['quantity']})" for p in prods]) if prods else "لا توجد طلبات مضافة"
        
        details = f"إلغاء حجز نشط - رقم الجلسة #{sess['id']} | نوع اللعب: {sess['session_type']} | بدأ: {sess['start_time']} | منشئ الجلسة: {sess['created_by']} | الطلبات الملحقة: {prod_summary}"
        log_deletion('إلغاء حجز جلسة', sess['item_name'] or f"جلسة #{sess['id']}", details)

        if sess['item_id']:
            conn.execute('UPDATE items SET status = "متاح" WHERE id = ?', (sess['item_id'],))
        conn.execute('DELETE FROM session_products WHERE session_id = ?', (session_id,))
        conn.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()
        flash('تم إلغاء الجلسة وإخلاء الجهاز بنجاح دون احتساب فاتورة.', 'warning')

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/session/end', methods=['POST'])
@login_required
def end_session():
    if not user_can('end_session'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))

    sess_id = request.form.get('session_id')
    conn = db.get_db()
    sess = conn.execute('SELECT * FROM sessions WHERE id = ?', (sess_id,)).fetchone()
    if not sess:
        flash('الجلسة غير موجودة!', 'danger')
        return redirect(url_for('admin.dashboard'))

    item = conn.execute('SELECT * FROM items WHERE id = ?', (sess['item_id'],)).fetchone()
    
    prod_sum = conn.execute('SELECT SUM(total) as total FROM session_products WHERE session_id = ?', (sess_id,)).fetchone()['total'] or 0.0
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    start_time = datetime.strptime(sess['start_time'], "%Y-%m-%d %H:%M:%S")
    elapsed_minutes = max(1, int((now - start_time).total_seconds() / 60))

    if sess['session_type'] == 'بالوقت':
        item_price = item['price'] if item else 0
        duration_lim = sess['duration_minutes'] or 0
        used_minutes = min(elapsed_minutes, duration_lim) if duration_lim > 0 else elapsed_minutes
        current_play_cost = (used_minutes / 60.0) * item_price
        current_play_cost = round(current_play_cost / 250.0) * 250.0
    elif sess['session_type'] == 'وقت مفتوح':
        item_price = item['price'] if item else 0
        current_play_cost = (elapsed_minutes / 60.0) * item_price
        current_play_cost = round(current_play_cost / 250.0) * 250.0
    else:
        current_play_cost = item['price'] if item else 0
        
    sess_dict = dict(sess)
    carried_cost = float(sess_dict.get('carried_over_cost') or 0.0)
    play_cost = current_play_cost + carried_cost
    total_cost = play_cost + prod_sum
    
    conn.execute('''
        UPDATE sessions SET target_end_time = ?, play_cost = ?, products_cost = ?, total_cost = ?, status = 'completed'
        WHERE id = ?
    ''', (now_str, play_cost, prod_sum, total_cost, sess_id))
    
    if sess['item_id']:
        conn.execute('UPDATE items SET status = "متاح" WHERE id = ?', (sess['item_id'],))
    conn.commit()
    
    flash(f'تم إنهاء الجلسة بنجاح. السعر الإجمالي: {total_cost:,.0f} د.ع', 'info')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/staff', methods=['GET', 'POST'])
@login_required
def staff():
    if not user_can('manage_staff'):
        flash('غير مصرح لك بالوصول!', 'danger')
        return redirect(url_for('admin.dashboard'))

    conn = db.get_db()
    if request.method == 'POST':
        username = request.form['username']
        plain_pass = request.form['password']
        password_hash = generate_password_hash(plain_pass)
        full_name = request.form['full_name']
        perms = json.dumps(request.form.getlist('permissions'))
        
        try:
            conn.execute('INSERT INTO users (username, password_hash, plain_password, full_name, role, permissions) VALUES (?, ?, ?, ?, "staff", ?)',
                         (username, password_hash, plain_pass, full_name, perms))
            conn.commit()
            flash('تم إضافة حساب الموظف وتحديد صلاحياته بنجاح!', 'success')
            return redirect(url_for('admin.staff'))
        except Exception:
            flash('اسم المستخدم مستعمل سابقاً!', 'danger')

    users = conn.execute("SELECT * FROM users WHERE role = 'staff' OR role IS NULL OR role != 'admin'").fetchall()

    return render_template_string('''
    <!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>إدارة الصلاحيات</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
    {{ COMMON_STYLE | safe }}
    </head>
    <body class="p-4"><div class="container glass-card p-4">
        <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
            <a href="{{ url_for('admin.dashboard') }}" class="btn btn-outline-light">⬅ عودة للوحة التحكم</a>
            <a href="/" class="btn btn-outline-info rounded-pill px-3 fw-bold">🏠 الواجهة الرئيسية</a>
        </div>
        <h3 class="fw-bold text-white mb-4">🔑 إدارة الموظفين والتراخيص والصلاحيات بالكامل</h3>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} text-center fw-bold flash-alert-box mb-3">{{ message }}</div>{% endfor %}{% endif %}
        {% endwith %}

        <form method="POST" class="p-4 rounded bg-dark mb-4 border border-secondary">
            <h5 class="text-warning mb-3">+ إضافة موظف جديد وتخصيص صلاحياته</h5>
            <div class="row g-3">
                <div class="col-md-4"><label class="mb-1 text-white">اسم المستخدم</label><input type="text" name="username" class="form-control bg-secondary text-white border-0" required></div>
                <div class="col-md-4"><label class="mb-1 text-white">كلمة المرور</label><input type="text" name="password" class="form-control bg-secondary text-white border-0" required></div>
                <div class="col-md-4"><label class="mb-1 text-white">الاسم الكامل للموظف</label><input type="text" name="full_name" class="form-control bg-secondary text-white border-0" required></div>
                
                <div class="col-12 mt-3">
                    <label class="fw-bold text-info mb-2">حدد الصلاحيات التفصيلية المسموحة للموظف:</label>
                    <div class="row bg-dark p-3 rounded border border-secondary">
                        {% for perm_key, perm_label in ALL_PERMISSIONS.items() %}
                        <div class="col-md-4 mb-2">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="permissions" value="{{ perm_key }}" id="perm_{{ perm_key }}">
                                <label class="form-check-label text-white" for="perm_{{ perm_key }}">{{ perm_label }}</label>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <div class="col-12 mt-3"><button type="submit" class="btn btn-glow-purple w-100 py-2 fs-5">إضافة الموظف مع الصلاحيات</button></div>
            </div>
        </form>

        <h4 class="fw-bold text-white mb-3">قائمة الموظفين الحاليين</h4>
        <div class="table-responsive">
            <table class="table table-dark-custom align-middle">
                <thead><tr><th>الاسم</th><th>اسم المستخدم</th><th>كلمة السر</th><th>الصلاحيات الممنوحة</th><th>إجراءات</th></tr></thead>
                <tbody>
                    {% for u in users %}
                    <tr>
                        <td class="fw-bold text-white">{{ u['full_name'] }}</td>
                        <td class="text-info">{{ u['username'] }}</td>
                        <td><code class="text-warning">{{ u['plain_password'] }}</code></td>
                        <td>
                            {% set u_perms = json_loads(u['permissions']) if u['permissions'] else [] %}
                            {% for p in u_perms %}
                                <span class="badge bg-primary me-1 mb-1">{{ ALL_PERMISSIONS.get(p, p) }}</span>
                            {% else %}
                                <span class="badge bg-secondary">بدون صلاحيات</span>
                            {% endfor %}
                        </td>
                        <td>
                            <a href="{{ url_for('admin.delete_staff', user_id=u['id']) }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('هل أنت تأكد من حذف هذا الموظف؟');">🗑️ حذف</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div></body></html>
    ''', COMMON_STYLE=COMMON_STYLE, users=users, ALL_PERMISSIONS=ALL_PERMISSIONS, json_loads=json.loads)

@admin_bp.route('/staff/delete/<int:user_id>')
@login_required
def delete_staff(user_id):
    if not user_can('manage_staff'):
        flash('ليس لديك صلاحية!', 'danger')
        return redirect(url_for('admin.dashboard'))
    conn = db.get_db()
    u = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if u:
        log_deletion('حذف حساب موظف', u['full_name'], f"تم حذف حساب الموظف {u['full_name']} (اسم المستخدم: {u['username']})")
        conn.execute('DELETE FROM users WHERE id = ? AND role != "admin"', (user_id,))
        conn.commit()
        flash('تم حذف حساب الموظف بنجاح', 'success')
    return redirect(url_for('admin.staff'))

@admin_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    new_username = request.form.get('username').strip()
    new_password = request.form.get('password').strip()
    user_id = session['user_id']
    
    conn = db.get_db()
    
    if new_password:
        hashed = generate_password_hash(new_password)
        conn.execute('UPDATE users SET username = ?, password_hash = ?, plain_password = ? WHERE id = ?',
                     (new_username, hashed, new_password, user_id))
    else:
        conn.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, user_id))
        
    conn.commit()
    session['username'] = new_username
    flash('تم تحديث الحساب (اسم المستخدم وكلمة المرور) بنجاح!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/reports/reset', methods=['POST'])
@login_required
def reset_reports():
    if not user_can('edit_reports'):
        flash('ليس لديك صلاحية تصفير الحسابات!', 'danger')
        return redirect(url_for('admin.reports'))
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db.get_db()
    conn.execute('INSERT OR REPLACE INTO system_settings (key, value) VALUES ("last_reset_time", ?)', (now_str,))
    conn.commit()
    log_deletion( 'تصفير الحسابات اليدوي', f"تم تصفير حسابات السجل يدوياً والبدء من جديد بتاريخ {now_str}")
    flash(f'تم تصفير الحسابات يدوياً بنجاح! تم بدء السجل الجديدة من توقيت: {now_str}', 'success')
    return redirect(url_for('admin.reports', period='today'))

@admin_bp.route('/reports')
@login_required
def reports():
    if not user_can('view_reports'):
        flash('غير مصرح لك بالوصول!', 'danger')
        return redirect(url_for('admin.dashboard'))

    period = request.args.get('period', 'today')
    conn = db.get_db()

    query = 'SELECT * FROM sessions WHERE status = "completed"'
    params = []

    # جلب توقيت آخر تصفير يدوي قام به المدير
    setting = conn.execute('SELECT value FROM system_settings WHERE key = "last_reset_time"').fetchone()
    last_reset_time = setting['value'] if setting and setting['value'] else None

    # الفلترة تعتمد حصراً على التصفير اليدوي دون أي تدخل لتوقيت 12 ليلاً
    if period == 'today':
        if last_reset_time:
            query += ' AND target_end_time >= ?'
            params.append(last_reset_time)
    elif period == 'month':
        month_str = datetime.now().strftime("%Y-%m")
        query += ' AND target_end_time LIKE ?'
        params.append(f'{month_str}%')

    query += ' ORDER BY id DESC'
    sessions = conn.execute(query, params).fetchall()
    total_sessions_cost = sum([s['total_cost'] or 0.0 for s in sessions])
    
    users_list = conn.execute("SELECT id, full_name, username, role FROM users").fetchall()
    user_map = {}
    admin_id = None
    for u in users_list:
        if u['role'] == 'admin':
            admin_id = u['id']
        if u['full_name']:
            user_map[u['full_name']] = u['id']
        if u['username']:
            user_map[u['username']] = u['id']
    if admin_id:
        user_map['الأدمن'] = admin_id
        user_map['ادمن'] = admin_id
        user_map['Admin'] = admin_id
        user_map['المدير العام'] = admin_id

    staff_summary = {}
    for s in sessions:
        staff_name = s['created_by'] if s['created_by'] else 'الأدمن'
        if staff_name not in staff_summary:
            uid = user_map.get(staff_name) or admin_id
            staff_summary[staff_name] = {'play_total': 0.0, 'products_total': 0.0, 'grand_total': 0.0, 'count': 0, 'user_id': uid}
        staff_summary[staff_name]['play_total'] += (s['play_cost'] or 0.0)
        staff_summary[staff_name]['products_total'] += (s['products_cost'] or 0.0)
        staff_summary[staff_name]['grand_total'] += (s['total_cost'] or 0.0)
        staff_summary[staff_name]['count'] += 1

    deleted_logs = []
    if session.get('role') == 'admin':
        deleted_logs = conn.execute('SELECT * FROM deleted_logs ORDER BY id DESC LIMIT 200').fetchall()

    return render_template_string('''
    <!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>التقارير التفصيلية والـ PDF</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    {{ COMMON_STYLE | safe }}
    </head>
    <body class="p-4">
        <div class="container glass-card p-4">
            <div class="d-flex justify-content-between align-items-center mb-4 no-print flex-wrap gap-2">
                <div class="d-flex gap-2">
                    <a href="{{ url_for('admin.dashboard') }}" class="btn btn-outline-light">⬅ عودة للوحة التحكم</a>
                    <a href="/" class="btn btn-outline-info rounded-pill px-3 fw-bold">🏠 الواجهة الرئيسية</a>
                </div>
                
                <div class="btn-group">
                    <a href="{{ url_for('admin.reports', period='today') }}" class="btn btn-sm {{ 'btn-warning' if period == 'today' else 'btn-outline-warning' }} fw-bold">اليوم   ⏳</a>
                    <a href="{{ url_for('admin.reports', period='month') }}" class="btn btn-sm {{ 'btn-warning' if period == 'month' else 'btn-outline-warning' }} fw-bold">هذا الشهر 🗓️</a>
                    <a href="{{ url_for('admin.reports', period='all') }}" class="btn btn-sm {{ 'btn-warning' if period == 'all' else 'btn-outline-warning' }} fw-bold">الكل 📊</a>
                </div>

                <div class="d-flex gap-2 flex-wrap">
                    {% if session['role'] == 'admin' %}
                    <button type="button" class="btn btn-danger rounded-pill px-3 fw-bold shadow" data-bs-toggle="modal" data-bs-target="#deletedLogsModal">
                        🗑️ سجل المحذوفات والملغيات ({{ deleted_logs|length }})
                    </button>

                    <form method="POST" action="{{ url_for('admin.reset_reports') }}" onsubmit="return confirm('هل أنت تأكد من تصفير الحسابات والبدء من جديد؟ سيتم تصفير سجل السجل  ويبدأ الحساب من الآن.');">
                        <button type="submit" class="btn btn-outline-danger rounded-pill px-3 fw-bold">🔄 تصفير الحسابات اليدوي</button>
                    </form>
                    {% endif %}
                    <button onclick="window.print()" class="btn btn-glow-green fs-5 px-4">🖨️ طباعة وتصدير PDF</button>
                </div>
            </div>

            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}{% for category, message in messages %}<div class="alert alert-{{ category }} text-center fw-bold flash-alert-box mb-3">{{ message }}</div>{% endfor %}{% endif %}
            {% endwith %}

            <h2 class="fw-bold text-center text-white mb-2">📊 تقرير مبيعات الجلسات والخدمات {{ ' ' if period == 'today' else ('أرباح الشهر' if period == 'month' else 'إجمالي الأرباح الكلية') }}</h2>
            
            {% if period == 'today' %}
                <div class="text-center mb-3">
                    {% if last_reset_time %}
                        <span class="badge bg-dark border border-secondary text-info fs-6 px-3 py-2">
                            ⏱️ السجل بداء منذ آخر تصفير يدوي: <strong class="text-warning font-monospace">{{ last_reset_time }}</strong> 
                        </span>
                    {% else %}
                        <span class="badge bg-dark border border-secondary text-info fs-6 px-3 py-2">
                            💡 لم يتم إجراء تصفير يدوي بعد، الحسابات مستمرة ومحفوظة بدون أي تصفير تلقائي.
                        </span>
                    {% endif %}
                </div>
            {% endif %}

            <div class="text-center p-3 bg-primary text-white rounded mb-4">
                <h4>مجموع الأرباح المحددة: <strong class="text-warning fs-3">{{ "{:,.0f}".format(total_sessions_cost) }} د.ع</strong></h4>
            </div>

            <div class="glass-card p-3 mb-4 border border-secondary">
                <h4 class="fw-bold text-warning mb-3">👥 تفاصيل مبيعات وحساب كل موظف (اضغط على الاسم للـعرض التفصيلي)</h4>
                <div class="table-responsive">
                    <table class="table table-dark-custom align-middle mb-0">
                        <thead>
                            <tr>
                                <th>اسم الموظف</th>
                                <th>عدد العمليات والمبيعات</th>
                                <th>لعب وطاولات</th>
                                <th>مأكولات وخدمات</th>
                                <th>المجموع الإجمالي المستلم (د.ع)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for s_name, s_data in staff_summary.items() %}
                            <tr>
                                <td class="fw-bold text-info">
                                    {% if s_data.get('user_id') %}
                                    <button type="button" class="btn btn-outline-info btn-sm fw-bold" onclick="loadStaffSales({{ s_data['user_id'] }})">
                                        <i class="fa-solid fa-user me-1"></i>{{ s_name }} 👁️
                                    </button>
                                    {% else %}
                                    <i class="fa-solid fa-user me-2"></i>{{ s_name }}
                                    {% endif %}
                                </td>
                                <td><span class="badge bg-secondary fs-6">{{ s_data['count'] }}</span></td>
                                <td class="text-white fw-bold">{{ "{:,.0f}".format(s_data['play_total']) }} د.ع</td>
                                <td class="text-white fw-bold">{{ "{:,.0f}".format(s_data['products_total']) }} د.ع</td>
                                <td class="text-warning fw-bold fs-5">{{ "{:,.0f}".format(s_data['grand_total']) }} د.ع</td>
                            </tr>
                            {% else %}
                            <tr><td colspan="5" class="text-center text-light py-3">لا توجد مبيعات مسجلة للموظفين في هذه السجل.</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <h4 class="fw-bold text-white mb-3">سجل الفواتير التفصيلية</h4>
            <div class="table-responsive">
                <table class="table table-dark-custom align-middle">
                    <thead>
                        <tr>
                            <th>رقم الجلسة</th>
                            <th>الميز / الجهاز</th>
                            <th>نوع اللعب</th>
                            <th>الموظف المسؤول</th>
                            <th>تاريخ/وقت الإغلاق</th>
                            <th>سعر اللعب</th>
                            <th>المأكولات والخدمات</th>
                            <th>المبلغ الإجمالي</th>
                            <th class="no-print">إجراءات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for s in sessions %}
                        <tr>
                            <td class="text-info fw-bold">#{{ s['id'] }}</td>
                            <td class="fw-bold text-white">{{ s['item_name'] }}</td>
                            <td><span class="badge bg-secondary text-white">{{ "بالكيم" if s['session_type'] in ["بالكيم", "بالجيم"] else s['session_type'] }}</span></td>
                            <td class="text-light fw-bold">{{ s['created_by'] if s['created_by'] else 'الأدمن' }}</td>
                            <td class="text-light font-monospace small">{{ s['target_end_time'] }}</td>
                            <td class="text-white fw-bold">{{ "{:,.0f}".format(s['play_cost']) }} د.ع</td>
                            <td class="text-white fw-bold">{{ "{:,.0f}".format(s['products_cost']) }} د.ع</td>
                            <td class="text-warning fw-bold fs-5">{{ "{:,.0f}".format(s['total_cost']) }} د.ع</td>
                            <td class="no-print">
                                {% if session['role'] == 'admin' or 'edit_reports' in session['permissions'] %}
                                <button class="btn btn-sm btn-outline-warning me-1" 
                                        onclick="openReportEditModal({{ s['id'] }}, '{{ s['item_name'] }}', {{ s['play_cost'] }}, {{ s['products_cost'] }}, {{ s['total_cost'] }})">
                                    ✏️ تعديل
                                </button>
                                <a href="{{ url_for('admin.delete_report', session_id=s['id'], period=period) }}" 
                                   class="btn btn-sm btn-outline-danger" 
                                   onclick="return confirm('هل تريد حذف هذا السجل نهائياً من التقارير والأرباح؟');">
                                    🗑️ حذف
                                </a>
                                {% else %}
                                <span class="text-light opacity-50 small">غير مصرح</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr><td colspan="9" class="text-center text-light py-4">لا توجد جلسات مكتملة مسجلة في هذه السجل.</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Modal تعديل التقرير / الفاتورة المكتملة -->
        <div class="modal fade" id="editReportModal" tabindex="-1">
            <div class="modal-dialog">
                <form method="POST" action="{{ url_for('admin.update_report') }}" class="modal-content glass-card text-white border-secondary">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-warning">✏️ تعديل بيانات السجل المالي</h5>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" name="session_id" id="reportSessionId">
                        <input type="hidden" name="period" value="{{ period }}">
                        
                        <h5 id="reportItemTitle" class="text-info fw-bold mb-3"></h5>
                        
                        <div class="mb-3">
                            <label class="fw-bold mb-1">سعر اللعب (د.ع):</label>
                            <input type="number" step="250" name="play_cost" id="reportPlayCost" class="form-control bg-dark text-white border-secondary" onchange="recalcReportTotal()" required>
                        </div>
                        <div class="mb-3">
                            <label class="fw-bold mb-1">مبلغ المأكولات والخدمات (د.ع):</label>
                            <input type="number" step="250" name="products_cost" id="reportProductsCost" class="form-control bg-dark text-white border-secondary" onchange="recalcReportTotal()" required>
                        </div>
                        <div class="mb-3">
                            <label class="fw-bold mb-1">المبلغ الإجمالي الكلي (د.ع):</label>
                            <input type="number" step="250" name="total_cost" id="reportTotalCost" class="form-control bg-secondary text-white border-0 fs-5 fw-bold" required>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="submit" class="btn btn-glow-green w-100 py-2 fs-5">حفظ التغييرات 💾</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Modal تفاصيل مبيعات وحساب الموظف بالكامل -->
        <div class="modal fade" id="staffSalesModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content glass-card text-white border-info" style="background: #090e1a !important;">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-info fs-4" id="staffModalTitle">📊 تفاصيل كشف حساب الموظف</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="إغلاق"></button>
                    </div>
                    <div class="modal-body p-3">
                        <div class="row g-3 mb-4 text-center">
                            <div class="col-md-4">
                                <div class="p-3 rounded-3" style="background: #111827; border: 1.5px solid #0284c7; box-shadow: 0 4px 15px rgba(2, 132, 199, 0.2);">
                                    <span class="fw-bold text-info fs-6 d-block mb-1">🎮 إجمالي اللعب والأجهزة</span>
                                    <h3 class="fw-bold text-white mb-0"><span id="staffPlayTotal">0</span> <small class="fs-6 text-info">د.ع</small></h3>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-3 rounded-3" style="background: #111827; border: 1.5px solid #ec4899; box-shadow: 0 4px 15px rgba(236, 72, 153, 0.2);">
                                    <span class="fw-bold fs-6 d-block mb-1" style="color: #f472b6 !important;">🥤 إجمالي المأكولات والخدمات</span>
                                    <h3 class="fw-bold text-white mb-0"><span id="staffProdTotal">0</span> <small class="fs-6" style="color: #f472b6;">د.ع</small></h3>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-3 rounded-3" style="background: linear-gradient(135deg, #064e3b, #047857); border: 1.5px solid #10b981; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);">
                                    <span class="fw-bold text-white fs-6 d-block mb-1">💰 المجموع الإجمالي المستلم</span>
                                    <h2 class="fw-black text-warning mb-0"><span id="staffGrandTotal">0</span> <small class="fs-5 text-white">د.ع</small></h2>
                                </div>
                            </div>
                        </div>

                        <h5 class="fw-bold text-white mb-3 d-flex align-items-center gap-2">
                            <span>📋</span> <span>سجل الجلسات والعمليات بالتفصيل (جلسة جلسة):</span>
                        </h5>
                        <div class="table-responsive rounded border border-secondary mb-4">
                            <table class="table table-dark table-hover align-middle mb-0" style="--bs-table-bg: #0b1120 !important;">
                                <thead>
                                    <tr style="background-color: #1e293b !important;">
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">#</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">الميز / الجهاز</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">نوع اللعب</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">سعر اللعب</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">الطلبات الملحقة</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">المجموع</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">وقت الإغلاق</th>
                                    </tr>
                                </thead>
                                <tbody id="staffSessionsTableBody">
                                </tbody>
                            </table>
                        </div>

                        <h6 class="fw-bold text-warning mb-3 d-flex align-items-center gap-2">
                            <span>🥤</span> <span>تفاصيل المأكولات والمشروبات المباشرة والملحقة:</span>
                        </h6>
                        <div class="table-responsive rounded border border-secondary">
                            <table class="table table-dark table-hover align-middle mb-0" style="--bs-table-bg: #0b1120 !important;">
                                <thead>
                                    <tr style="background-color: #1e293b !important;">
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">اسم المنتج / الخدمة</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">الكمية المباعة</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">إجمالي المبلغ</th>
                                    </tr>
                                </thead>
                                <tbody id="staffSalesTableBody">
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-secondary px-4 fw-bold" data-bs-dismiss="modal">إغلاق</button>
                    </div>
                </div>
            </div>
        </div>

        {% if session['role'] == 'admin' %}
        <!-- Modal سجل المحذوفات والعمليات الملغاة (خاص بالمدير فقط) -->
        <div class="modal fade" id="deletedLogsModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content glass-card text-white border-danger" style="background: #090e1a !important;">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title fw-bold text-danger">🗑️ سجل المحذوفات والعمليات الملغاة (خاص بالمدير فقط)</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="إغلاق"></button>
                    </div>
                    <div class="modal-body p-3">
                        <div class="alert alert-dark border border-secondary text-info mb-3">
                            <i class="fa-solid fa-shield-halved me-1"></i> يوثق هذا السجل تلقائياً أي عملية حذف أو إلغاء لجلسة أو فاتورة أو طلب أو جهاز مع اسم الشخص المنفّذ ووقت العملية وتفاصيل ما تم حذفه.
                        </div>
                        <div class="table-responsive rounded border border-secondary">
                            <table class="table table-dark table-hover align-middle mb-0" style="--bs-table-bg: #0b1120 !important;">
                                <thead>
                                    <tr style="background-color: #1e293b !important;">
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">نوع العملية</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">العنصر / الهدف</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">تفاصيل ما تم حذفه</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">من قام بالحذف</th>
                                        <th style="background-color: #1e293b !important; color: #38bdf8 !important;">تاريخ ووقت الحذف</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for log in deleted_logs %}
                                    <tr style="border-color: #1e293b !important; background-color: #0b1120 !important;">
                                        <td style="background-color: #0b1120 !important;">
                                            <span class="badge {% if 'إلغاء' in log['action_type'] %}bg-warning text-dark{% else %}bg-danger text-white{% endif %} fs-6 px-3 py-2">
                                                {{ log['action_type'] }}
                                            </span>
                                        </td>
                                        <td class="fw-bold text-info fs-5" style="background-color: #0b1120 !important;">{{ log['target_name'] }}</td>
                                        <td class="text-white fw-medium" style="background-color: #0b1120 !important; max-width: 450px; white-space: normal; line-height: 1.7; font-size: 0.95rem;">
                                            {{ log['details'] }}
                                        </td>
                                        <td class="fw-bold text-warning fs-6" style="background-color: #0b1120 !important;">
                                            <i class="fa-solid fa-user me-1"></i>{{ log['deleted_by'] }}
                                        </td>
                                        <td style="background-color: #0b1120 !important;">
                                            <span class="badge bg-dark border border-secondary text-light fs-6 font-monospace py-2 px-3">
                                                ⏱️ {{ log['deleted_at'] }}
                                            </span>
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="5" class="text-center text-light py-4" style="background-color: #0b1120 !important;">لا توجد عمليات حذف أو إلغاء مسجلة حتى الآن.</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-secondary px-4 fw-bold" data-bs-dismiss="modal">إغلاق</button>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            function openReportEditModal(id, itemName, playCost, prodCost, totalCost) {
                document.getElementById('reportSessionId').value = id;
                document.getElementById('reportItemTitle').innerText = 'الجلسة رقم #' + id + ' (' + itemName + ')';
                document.getElementById('reportPlayCost').value = playCost;
                document.getElementById('reportProductsCost').value = prodCost;
                document.getElementById('reportTotalCost').value = totalCost;
                
                let myModal = new bootstrap.Modal(document.getElementById('editReportModal'));
                myModal.show();
            }

            function recalcReportTotal() {
                let play = parseFloat(document.getElementById('reportPlayCost').value) || 0;
                let prod = parseFloat(document.getElementById('reportProductsCost').value) || 0;
                document.getElementById('reportTotalCost').value = play + prod;
            }

            function loadStaffSales(userId) {
                const currentPeriod = "{{ period }}";
                fetch(`/admin/api/staff-sales/${userId}?period=${currentPeriod}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            alert(data.error);
                            return;
                        }

                        document.getElementById('staffModalTitle').innerText = '📊 تفاصيل حساب ومبيعات: ' + data.staff_name;
                        document.getElementById('staffPlayTotal').innerText = (data.total_play || 0).toLocaleString();
                        document.getElementById('staffProdTotal').innerText = (data.total_products || 0).toLocaleString();
                        document.getElementById('staffGrandTotal').innerText = (data.grand_total || 0).toLocaleString();

                        let sessTbody = document.getElementById('staffSessionsTableBody');
                        sessTbody.innerHTML = '';
                        if (!data.sessions || data.sessions.length === 0) {
                            sessTbody.innerHTML = '<tr><td colspan="7" class="text-center text-light py-4" style="background-color: #0b1120 !important;">لا توجد جلسات مسجلة لهذا الموظف في هذه الفترة.</td></tr>';
                        } else {
                            data.sessions.forEach(s => {
                                let prodsHtml = '';
                                if (s.products_list && s.products_list.length > 0) {
                                    prodsHtml = s.products_list.map(p => `<span class="badge bg-secondary text-white me-1 mb-1 border border-secondary">${p.product_name} (x${p.quantity}) - ${p.total.toLocaleString()} د.ع</span>`).join('');
                                } else {
                                    prodsHtml = '<span class="text-light opacity-75 fst-italic">لا توجد طلبات</span>';
                                }

                                let playModeBadge = (s.session_type === 'بالكيم' || s.session_type === 'بالجيم') ? 'bg-secondary text-white' : 'bg-primary text-white';

                                sessTbody.innerHTML += `
                                    <tr style="border-color: #1e293b !important; background-color: #0b1120 !important;">
                                        <td style="background-color: #0b1120 !important;"><span class="badge bg-secondary text-white fw-bold">#${s.id}</span></td>
                                        <td style="background-color: #0b1120 !important;" class="fw-bold text-white fs-6">${s.item_name || 'بيع مباشر'}</td>
                                        <td style="background-color: #0b1120 !important;"><span class="badge ${playModeBadge}">${s.session_type}</span></td>
                                        <td style="background-color: #0b1120 !important;" class="text-white fw-bold">${(s.play_cost || 0).toLocaleString()} د.ع</td>
                                        <td style="background-color: #0b1120 !important;">${prodsHtml}</td>
                                        <td style="background-color: #0b1120 !important;" class="text-warning fw-black fs-6">${(s.total_cost || 0).toLocaleString()} د.ع</td>
                                        <td style="background-color: #0b1120 !important;">
                                            <span class="badge bg-dark border border-secondary text-light font-monospace fs-6 px-2 py-1">⏱️ ${s.target_end_time || '-'}</span>
                                        </td>
                                    </tr>
                                `;
                            });
                        }

                        let prodTbody = document.getElementById('staffSalesTableBody');
                        prodTbody.innerHTML = '';
                        if (!data.products_summary || data.products_summary.length === 0) {
                            prodTbody.innerHTML = '<tr><td colspan="3" class="text-center text-light py-3" style="background-color: #0b1120 !important;">لا توجد مأكولات أو خدمات مسجلة لهذا الموظف في هذه الفترة.</td></tr>';
                        } else {
                            data.products_summary.forEach(item => {
                                prodTbody.innerHTML += `
                                    <tr style="border-color: #1e293b !important; background-color: #0b1120 !important;">
                                        <td style="background-color: #0b1120 !important;" class="fw-bold text-white">${item.product_name}</td>
                                        <td style="background-color: #0b1120 !important;"><span class="badge bg-info text-dark fw-bold fs-6 px-3">${item.total_quantity}</span></td>
                                        <td style="background-color: #0b1120 !important;" class="text-warning fw-bold fs-6">${item.total_amount.toLocaleString()} د.ع</td>
                                    </tr>
                                `;
                            });
                        }

                        let modal = new bootstrap.Modal(document.getElementById('staffSalesModal'));
                        modal.show();
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('حدث خطأ أثناء جلب بيانات الموظف.');
                    });
            }
        </script>
    </body></html>
    ''', COMMON_STYLE=COMMON_STYLE, sessions=sessions, total_sessions_cost=total_sessions_cost, period=period, staff_summary=staff_summary, deleted_logs=deleted_logs, last_reset_time=last_reset_time)

@admin_bp.route('/report/update', methods=['POST'])
@login_required
def update_report():
    if not user_can('edit_reports'):
        flash('ليس لديك صلاحية تعديل التقارير!', 'danger')
        return redirect(url_for('admin.reports'))

    session_id = request.form.get('session_id')
    period = request.form.get('period', 'all')
    play_cost = float(request.form.get('play_cost', 0))
    products_cost = float(request.form.get('products_cost', 0))
    total_cost = float(request.form.get('total_cost', 0))

    conn = db.get_db()
    conn.execute('''
        UPDATE sessions 
        SET play_cost = ?, products_cost = ?, total_cost = ?
        WHERE id = ?
    ''', (play_cost, products_cost, total_cost, session_id))
    conn.commit()

    flash(f'تم تعديل الفاتورة رقم #{session_id} وحفظ البيانات الجديدة بنجاح!', 'success')
    return redirect(url_for('admin.reports', period=period))

@admin_bp.route('/report/delete/<int:session_id>')
@login_required
def delete_report(session_id):
    if not user_can('edit_reports'):
        flash('ليس لديك صلاحية حذف سجلات التقارير!', 'danger')
        return redirect(url_for('admin.reports'))

    period = request.args.get('period', 'all')
    conn = db.get_db()
    
    sess = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if sess:
        details = f"حذف فاتورة مكتملة #{sess['id']} نهائياً - الإجمالي: {sess['total_cost']} د.ع (سعر اللعب: {sess['play_cost']} د.ع | المأكولات: {sess['products_cost']} د.ع) | نوع: {sess['session_type']} | أغلقت في: {sess['target_end_time']} | منشئ الجلسة: {sess['created_by']}"
        log_deletion('حذف فاتورة نهائية', sess['item_name'] or f"جلسة #{sess['id']}", details)

    conn.execute('DELETE FROM session_products WHERE session_id = ?', (session_id,))
    conn.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
    conn.commit()

    flash(f'تم حذف الجلسة رقم #{session_id} نهائياً من التقارير وتوثيق العملية في سجل المحذوفات!', 'success')
    return redirect(url_for('admin.reports', period=period))


@admin_bp.route('/api/staff-sales/<int:user_id>')
@login_required
def get_staff_sales(user_id):
    conn = db.get_db()
    staff = conn.execute('SELECT id, username, full_name, role FROM users WHERE id = ?', (user_id,)).fetchone()
    if not staff:
        return jsonify({'error': 'الموظف غير موجود'}), 404
        
    period = request.args.get('period', 'all')
    
    query = 'SELECT * FROM sessions WHERE status = "completed"'
    params = []

    # جلب توقيت آخر تصفير يدوي قام به المدير
    setting = conn.execute('SELECT value FROM system_settings WHERE key = "last_reset_time"').fetchone()
    last_reset_time = setting['value'] if setting and setting['value'] else None

    # مطابقة نفس الفلترة اليدوية دون أي تصفير عند منتصف الليل
    if period == 'today':
        if last_reset_time:
            query += ' AND target_end_time >= ?'
            params.append(last_reset_time)
    elif period == 'month':
        month_str = datetime.now().strftime("%Y-%m")
        query += ' AND target_end_time LIKE ?'
        params.append(f'{month_str}%')

    if staff['role'] == 'admin':
        names = [n for n in [staff['full_name'], staff['username'], 'الأدمن', 'ادمن', 'Admin', 'المدير العام'] if n]
        placeholders = ','.join(['?'] * len(names))
        query += f' AND (created_by IN ({placeholders}) OR created_by IS NULL OR created_by = "")'
        params.extend(names)
    else:
        names = [n for n in [staff['full_name'], staff['username']] if n]
        if names:
            placeholders = ','.join(['?'] * len(names))
            query += f' AND created_by IN ({placeholders})'
            params.extend(names)
        else:
            query += ' AND 1 = 0'

    query += ' ORDER BY id DESC'
    sessions = conn.execute(query, params).fetchall()

    session_ids = [s['id'] for s in sessions]
    prods_by_session = {}
    if session_ids:
        s_placeholders = ','.join(['?'] * len(session_ids))
        prods = conn.execute(f'''
            SELECT session_id, product_name, quantity, price, total 
            FROM session_products 
            WHERE session_id IN ({s_placeholders})
        ''', session_ids).fetchall()
        for p in prods:
            sid = p['session_id']
            if sid not in prods_by_session:
                prods_by_session[sid] = []
            prods_by_session[sid].append(dict(p))

    sessions_list = []
    total_play = 0.0
    total_products = 0.0
    grand_total = 0.0
    prod_summary_map = {}

    for s in sessions:
        s_dict = dict(s)
        p_cost = s['play_cost'] or 0.0
        pr_cost = s['products_cost'] or 0.0
        t_cost = s['total_cost'] or 0.0
        total_play += p_cost
        total_products += pr_cost
        grand_total += t_cost
        
        session_products_list = prods_by_session.get(s['id'], [])
        s_dict['products_list'] = session_products_list
        sessions_list.append(s_dict)

        for p in session_products_list:
            pname = p['product_name']
            if pname not in prod_summary_map:
                prod_summary_map[pname] = {'product_name': pname, 'total_quantity': 0, 'total_amount': 0.0}
            prod_summary_map[pname]['total_quantity'] += p['quantity']
            prod_summary_map[pname]['total_amount'] += p['total']

    return jsonify({
        'staff_name': staff['full_name'] or staff['username'],
        'sessions_count': len(sessions_list),
        'total_play': total_play,
        'total_products': total_products,
        'grand_total': grand_total,
        'sessions': sessions_list,
        'products_summary': list(prod_summary_map.values())
    })
