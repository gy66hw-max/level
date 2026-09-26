from flask import Blueprint, render_template_string
from markupsafe import Markup
import database as db

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def index():
    conn = db.get_db()
    items = conn.execute('SELECT * FROM items WHERE show_to_user = 1').fetchall()
    products = conn.execute('SELECT * FROM products WHERE show_to_user = 1').fetchall()
    announcements = conn.execute('SELECT * FROM announcements ORDER BY id DESC LIMIT 5').fetchall()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>صالة الألعاب - التوفر والخدمات</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-dark text-light">
        <div class="bg-primary text-white text-center py-4 shadow">
            <h2>🎮 صالة الألعاب والترفيه 🎱</h2>
            <p class="m-0">مرحباً بكم! اطلع على الأجهزة المتاحة وقائمة المشروبات</p>
        </div>

        <div class="container my-4">
            {% if announcements %}
            <div class="alert alert-info bg-opacity-25 text-white border-info mb-4 shadow-sm">
                <h4>🆕 آخر التحديثات والإعلانات</h4>
                <hr>
                {% for a in announcements %}
                <div class="mb-2">
                    <span class="badge bg-warning text-dark">{{ a['title'] }}</span>
                    <small class="text-secondary">({{ a['created_at'] }})</small>
                    <p class="m-0 mt-1">{{ a['content'] }}</p>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <ul class="nav nav-pills mb-3 justify-content-center" id="pills-tab">
                <li class="nav-item"><button class="nav-link active" data-bs-toggle="pill" data-bs-target="#u-billiards">🎱 البليارد</button></li>
                <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#u-ps">🎮 البلايستيشن</button></li>
                <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#u-other">🃏 ألعاب أخرى</button></li>
                <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#u-drinks">🥤 المشروبات والخدمات</button></li>
            </ul>

            <div class="tab-content" id="pills-tabContent">
                <div class="tab-pane fade show active" id="u-billiards">
                    {{ render_user_grid(items, 'billiards') }}
                </div>
                <div class="tab-pane fade" id="u-ps">
                    {{ render_user_grid(items, 'playstation') }}
                </div>
                <div class="tab-pane fade" id="u-other">
                    {{ render_user_grid(items, 'other') }}
                </div>
                <div class="tab-pane fade" id="u-drinks">
                    <div class="row">
                        {% for p in products %}
                        <div class="col-6 col-md-3 mb-3">
                            <div class="card bg-secondary text-white text-center shadow-sm h-100">
                                {% if p['image_url'] %}
                                    <img src="{{ p['image_url'] }}" class="card-img-top" style="height: 160px; object-fit: cover;">
                                {% endif %}
                                <div class="card-body d-flex flex-column justify-content-between">
                                    <h5 class="card-title">{{ p['name'] }}</h5>
                                    <div>
                                        <span class="badge bg-light text-dark mb-2">{{ p['category'] }}</span>
                                        <h4 class="text-warning m-0">{{ p['price'] }} د.ع</h4>
                                    </div>
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>

            <div class="text-center mt-5">
                <a href="{{ url_for('admin.login') }}" class="btn btn-outline-light btn-sm">دخول الإدارة / الموظفين</a>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    ''', items=items, products=products, announcements=announcements)

@user_bp.add_app_template_global
def render_user_grid(items, cat):
    filtered = [i for i in items if i['category'] == cat]
    if not filtered:
        return Markup('<div class="text-center text-muted py-3">لا يوجد عناصر مضافة حالياً.</div>')
    
    html = '<div class="row">'
    for item in filtered:
        status_color = 'success' if 'متاح' in item['status'] else ('danger' if 'مشغول' in item['status'] else 'secondary')
        
        html += f'''
        <div class="col-6 col-md-3 mb-3">
            <div class="card bg-dark text-white border-{status_color} shadow">
                <div class="card-header border-{status_color} d-flex justify-content-between align-items-center">
                    <strong>{item['name']}</strong>
                    <span class="badge bg-{status_color}">{item['status']}</span>
                </div>
                <div class="card-body">
                    <p class="card-text"><strong>السعر:</strong> {item['price']} د.ع</p>
                </div>
            </div>
        </div>
        '''
    html += '</div>'
    return Markup(html)