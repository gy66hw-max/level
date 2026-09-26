import json
from functools import wraps
from flask import Blueprint, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
import database as db
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

AUTH_STYLE = '''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&display=swap');
    
    body {
        font-family: 'Tajawal', sans-serif;
        background: linear-gradient(-45deg, #070a12, #0d1527, #150f2a, #09131f);
        background-size: 400% 400%;
        animation: gradientAnimation 15s ease infinite;
        color: #f3f4f6;
        min-height: 100vh;
    }

    @keyframes gradientAnimation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .glass-card {
        background: rgba(17, 24, 39, 0.85);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }

    .btn-glow-purple {
        background: linear-gradient(135deg, #7c3aed, #6366f1);
        color: white; font-weight: 700; border: none;
        box-shadow: 0 0 15px rgba(124, 58, 237, 0.4);
    }
</style>
'''

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapper

def has_permission(perm_name):
    if session.get('role') == 'admin':
        return True
    return perm_name in session.get('permissions', [])

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        conn = db.get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND is_active = 1', (request.form['username'],)).fetchone()
        
        if user and check_password_hash(user['password_hash'], request.form['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            session['permissions'] = json.loads(user['permissions']) if user['permissions'] else []
            return redirect(url_for('admin.dashboard'))
            
        flash('بيانات الدخول غير صحيحة!', 'danger')
            
    return render_template_string('''
    <!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8">
    <title>تسجيل الدخول</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
    {{ AUTH_STYLE | safe }}
    </head>
    <body class="d-flex align-items-center justify-content-center vh-100">
        <div class="glass-card p-4 text-white shadow" style="width: 380px;">
            <h3 class="text-center mb-4 text-primary fw-bold">🔐 تسجيل الدخول</h3>
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}{% for category, message in messages %}
                  <div class="alert alert-{{ category }} p-2 text-center">{{ message }}</div>
              {% endfor %}{% endif %}
            {% endwith %}
            <form method="POST">
                <div class="mb-3"><label>اسم المستخدم</label><input type="text" name="username" class="form-control bg-dark text-white border-secondary" required></div>
                <div class="mb-3"><label>كلمة المرور</label><input type="password" name="password" class="form-control bg-dark text-white border-secondary" required></div>
                <button type="submit" class="btn btn-glow-purple w-100 py-2">دخول</button>
            </form>
        </div>
    </body></html>
    ''', AUTH_STYLE=AUTH_STYLE)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

# رمز الطوارئ الثابت للتعيين (يمكنك تغييره لأي رمز تحبه)
MASTER_RECOVERY_KEY = "102030" 

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        recovery_key = request.form.get('recovery_key')
        new_username = request.form.get('username')
        new_password = request.form.get('password')
        
        if recovery_key == MASTER_RECOVERY_KEY:
            conn = db.get_db()
            hashed = generate_password_hash(new_password)
            # تحديث حساب الأدمن الأساسي
            conn.execute('UPDATE users SET username = ?, password_hash = ?, plain_password = ? WHERE role = "admin"',
                         (new_username, hashed, new_password))
            conn.commit()
            flash('تم استعادة الحساب وتغيير البيانات بنجاح! يمكنك الدخول الآن.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('رمز الطوارئ السري غير صحيح!', 'danger')

    return render_template_string('''
    <!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8">
    <title>استعادة الحساب</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
    {{ AUTH_STYLE | safe }}
    </head>
    <body class="d-flex align-items-center justify-content-center vh-100">
        <div class="glass-card p-4 text-white shadow" style="width: 400px;">
            <h4 class="text-center mb-4 text-warning fw-bold">🔑 استعادة حساب المدير</h4>
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}{% for category, message in messages %}
                  <div class="alert alert-{{ category }} p-2 text-center">{{ message }}</div>
              {% endfor %}{% endif %}
            {% endwith %}
            <form method="POST">
                <div class="mb-3"><label>رمز الطوارئ السري</label><input type="text" name="recovery_key" class="form-control bg-dark text-white border-secondary" placeholder="Master Key" required></div>
                <div class="mb-3"><label>اسم المستخدم الجديد</label><input type="text" name="username" class="form-control bg-dark text-white border-secondary" value="admin" required></div>
                <div class="mb-3"><label>كلمة المرور الجديدة</label><input type="password" name="password" class="form-control bg-dark text-white border-secondary" required></div>
                <button type="submit" class="btn btn-glow-purple w-100 py-2">إعادة تعيين الحساب 🚀</button>
            </form>
        </div>
    </body></html>
    ''', AUTH_STYLE=AUTH_STYLE)