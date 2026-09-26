from flask import Blueprint, render_template_string, jsonify
import database as db

public_bp = Blueprint('public', __name__)

# --- API للتحديث المباشر لحالة الأجهزة ---
@public_bp.route('/api/live-status')
def live_status():
    conn = db.get_db()
    items = conn.execute('SELECT id, name, status, category FROM items').fetchall()
    
    summary = {
        'total': len(items),
        'free': sum(1 for i in items if i['status'] != 'مشغول'),
        'busy': sum(1 for i in items if i['status'] == 'مشغول')
    }
    
    return jsonify({
        'summary': summary,
        'items': [dict(i) for i in items]
    })

# --- الواجهة الرئيسية العامة ---
@public_bp.route('/')
def home():
    conn = db.get_db()
    categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
    items = conn.execute('''
        SELECT items.*, COALESCE(c.name, items.category) as category_name, c.icon as category_icon, c.color as category_color
        FROM items
        LEFT JOIN categories c ON items.category = c.key OR items.category = c.name
        ORDER BY category_name ASC, items.name ASC
    ''').fetchall()
    
    products = conn.execute('SELECT * FROM products WHERE show_to_user = 1 ORDER BY category ASC, name ASC').fetchall()
    food_categories = list(set(p['category'] or 'أخرى' for p in products))

    return render_template_string('''
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title> - LEVEL MAX</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@500;700;900&display=swap" rel="stylesheet">
        
        <style>
            :root {
                --primary-glow: #8b5cf6;
                --cyan-glow: #06b6d4;
                --free-color: #10b981;
                --busy-color: #f43f5e;
            }

            body {
                font-family: 'Tajawal', sans-serif;
                background: linear-gradient(-45deg, #05070f, #0d1222, #1a0b2e, #071728);
                background-size: 400% 400%;
                animation: gradientBG 12s ease infinite;
                color: #ffffff;
                min-height: 100vh;
                overflow-x: hidden;
            }

            @keyframes gradientBG {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            .bounce-emoji {
                display: inline-block;
                animation: floatEmoji 2.5s ease-in-out infinite;
            }
            @keyframes floatEmoji {
                0%, 100% { transform: translateY(0) rotate(0deg); }
                50% { transform: translateY(-8px) rotate(6deg); }
            }

            .pulse-icon {
                animation: pulseIcon 1.8s infinite;
            }
            @keyframes pulseIcon {
                0% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.15); opacity: 0.8; }
                100% { transform: scale(1); opacity: 1; }
            }

            /* الكروت الزجاجية متكيفة مع جميع الشاشات */
            .glass-card {
                background: rgba(18, 25, 42, 0.75);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .glass-card:hover {
                transform: translateY(-4px);
                border-color: rgba(255, 255, 255, 0.25);
                box-shadow: 0 15px 35px rgba(139, 92, 246, 0.25);
            }

            .stat-title-text {
                color: #e2e8f0 !important;
                font-weight: 700;
                font-size: 0.85rem;
            }

            .btn-login-vip {
                background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.05));
                border: 1px solid rgba(255, 255, 255, 0.25);
                color: #ffffff;
                padding: 8px 18px;
                border-radius: 50px;
                font-weight: 700;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                backdrop-filter: blur(10px);
                transition: all 0.3s ease;
                white-space: nowrap;
            }

            .btn-login-vip:hover {
                background: linear-gradient(135deg, var(--primary-glow), var(--cyan-glow));
                color: #ffffff;
                box-shadow: 0 0 20px rgba(6, 182, 212, 0.5);
                border-color: transparent;
            }

            .status-pill-free {
                background: rgba(16, 185, 129, 0.15);
                color: var(--free-color);
                border: 1.5px solid var(--free-color);
                box-shadow: 0 0 12px rgba(16, 185, 129, 0.3);
                padding: 6px 14px;
                border-radius: 50px;
                font-weight: 700;
                font-size: 0.85rem;
                white-space: nowrap;
            }

            .status-pill-busy {
                background: rgba(244, 63, 94, 0.15);
                color: var(--busy-color);
                border: 1.5px solid var(--busy-color);
                box-shadow: 0 0 12px rgba(244, 63, 94, 0.3);
                padding: 6px 14px;
                border-radius: 50px;
                font-weight: 700;
                font-size: 0.85rem;
                white-space: nowrap;
            }

            .device-title {
                font-size: 1.4rem;
                font-weight: 900;
                background: linear-gradient(90deg, #ffffff, #c084fc);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            /* تبويبات التصفح */
            .nav-pills-custom {
                gap: 8px;
            }

            .nav-pills-custom .nav-link {
                color: #94a3b8;
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 10px 20px;
                font-size: 1rem;
                font-weight: 700;
                transition: all 0.3s;
                white-space: nowrap;
            }

            .nav-pills-custom .nav-link.active {
                background: linear-gradient(135deg, #8b5cf6, #06b6d4) !important;
                color: #ffffff !important;
                box-shadow: 0 8px 25px rgba(139, 92, 246, 0.4);
                border-color: transparent;
            }

            /* شريط الأقسام السحب للهواتف */
            .filters-scroll-container {
                display: flex;
                gap: 8px;
                overflow-x: auto;
                padding-bottom: 8px;
                justify-content: center;
                -webkit-overflow-scrolling: touch;
            }

            .filters-scroll-container::-webkit-scrollbar {
                display: none;
            }

            .filter-chip {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid var(--cat-color, rgba(255, 255, 255, 0.2));
                color: var(--cat-color, #ffffff);
                padding: 8px 18px;
                border-radius: 50px;
                font-weight: 700;
                font-size: 0.9rem;
                transition: all 0.3s ease;
                backdrop-filter: blur(5px);
                white-space: nowrap;
                flex-shrink: 0;
            }

            .filter-chip:hover, .filter-chip.active {
                background: var(--cat-color, #8b5cf6) !important;
                color: #ffffff !important;
                box-shadow: 0 0 15px var(--cat-color, #8b5cf6) !important;
                border-color: var(--cat-color, #8b5cf6) !important;
            }

            /* إصلاح إظهار الصور كاملة بدون قص */
            .food-img-container {
                width: 100%;
                height: 180px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 16px;
                overflow: hidden;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 8px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }

            .food-img-container img {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain; /* إظهار الصورة كاملة دون أي قص */
            }

            /* تحسين الهواتف والشاشات الصغيرة */
            @media (max-width: 767.98px) {
                .header-container {
                    flex-direction: column;
                    text-align: center;
                    gap: 15px !important;
                }
                
                .header-actions {
                    width: 100%;
                    justify-content: center;
                    flex-wrap: wrap;
                }

                .filters-scroll-container {
                    justify-content: flex-start;
                    padding-left: 10px;
                    padding-right: 10px;
                }

                .device-title {
                    font-size: 1.25rem;
                }

                .nav-pills-custom .nav-link {
                    padding: 8px 14px;
                    font-size: 0.9rem;
                }
            }
        </style>
    </head>
    <body class="pb-5">

        <!-- Header -->
        <div class="container pt-3 pt-md-4 mb-4">
            <div class="glass-card p-3 p-md-4">
                <div class="d-flex justify-content-between align-items-center header-container">
                    
                    <!-- الاسم والسمايل -->
                    <div class="d-flex align-items-center justify-content-center gap-3">
                        <span class="fs-1 bounce-emoji">⚡</span>
                        <div>
                            <h2 class="fw-black m-0 text-white tracking-wide fs-3 fs-md-2"><span class="text-info fs-5">LEVEL MAX</span></h2>
                            <p class="text-info small m-0 fw-bold">شاشة العرض والمتابعة المباشرة 🎮</p>
                        </div>
                    </div>

                    <!-- العدادات + زر تسجيل الدخول -->
                    <div class="d-flex align-items-center gap-2 gap-md-3 header-actions">
                        <div class="glass-card px-3 py-2 text-center" style="min-width: 85px; background: rgba(16, 185, 129, 0.08);">
                            <span class="stat-title-text d-block">المتاحة</span>
                            <span class="fw-bold fs-4 text-success" id="stat-free">-</span>
                        </div>

                        <div class="glass-card px-3 py-2 text-center" style="min-width: 85px; background: rgba(244, 63, 94, 0.08);">
                            <span class="stat-title-text d-block">المشغولة</span>
                            <span class="fw-bold fs-4 text-danger" id="stat-busy">-</span>
                        </div>

                        <a href="/auth/login" class="btn-login-vip">
                            <i class="fa-solid fa-right-to-bracket pulse-icon"></i>
                            <span>دخول</span>
                        </a>
                    </div>

                </div>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="container mb-4">
            <ul class="nav nav-pills nav-pills-custom justify-content-center" id="mainTabs">
                <li class="nav-item">
                    <button class="nav-link active" data-bs-toggle="pill" data-bs-target="#tab-devices">
                        <span class="bounce-emoji me-1">🎯</span> الأجهزة والأنشطة
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" data-bs-toggle="pill" data-bs-target="#tab-menu">
                        <span class="bounce-emoji me-1">🍔</span> المأكولات والمشروبات
                    </button>
                </li>
            </ul>
        </div>

        <!-- Main Content -->
        <div class="container">
            <div class="tab-content">
                
                <!-- Devices Tab -->
                <div class="tab-pane fade show active" id="tab-devices">
                    <div class="filters-scroll-container mb-4" id="deviceFilters">
                        <button class="filter-chip active" data-filter="all" style="--cat-color: #06b6d4;">✨ الكل</button>
                        {% for cat in categories %}
                            <button class="filter-chip" data-filter="{{ cat['name'] }}" style="--cat-color: {{ cat['color'] or '#8b5cf6' }};">
                                {{ cat['icon'] }} {{ cat['name'] }}
                            </button>
                        {% endfor %}
                    </div>

                    <div class="row g-3 g-md-4" id="devicesGrid">
                        {% for item in items %}
                        <div class="col-12 col-sm-6 col-lg-4 device-card-item" data-category="{{ item['category_name'] }}">
                            <div class="glass-card p-3 p-md-4 h-100 d-flex flex-column justify-content-between">
                                <div>
                                    <div class="d-flex justify-content-between align-items-center mb-3">
                                        <span class="fs-2 bounce-emoji p-2 rounded-4" style="background: rgba(255,255,255,0.05)">
                                            {{ item['category_icon'] or '🎮' }}
                                        </span>
                                        
                                        <span class="status-badge-{{ item['id'] }} {% if item['status'] == 'مشغول' %}status-pill-busy{% else %}status-pill-free{% endif %}">
                                            <span class="status-text-{{ item['id'] }}">
                                                {% if item['status'] == 'مشغول' %}
                                                    🔴 محجوز حالياً
                                                {% else %}
                                                    🟢 متاح للعب
                                                {% endif %}
                                            </span>
                                        </span>
                                    </div>
                                    
                                    <h3 class="device-title mb-2">{{ item['name'] }}</h3>
                                    <span class="badge bg-secondary bg-opacity-25 text-info border border-info border-opacity-25 rounded-pill px-3 py-1">
                                        {{ item['category_name'] }}
                                    </span>
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <!-- Menu Tab -->
                <div class="tab-pane fade" id="tab-menu">
                    <div class="filters-scroll-container mb-4" id="menuFilters">
                        <button class="filter-chip active" data-filter-food="all" style="--cat-color: #06b6d4;">☕ الكل</button>
                        {% for cat_name in food_categories %}
                            <button class="filter-chip" data-filter-food="{{ cat_name }}" style="--cat-color: #ec4899;">🍔 {{ cat_name }}</button>
                        {% endfor %}
                    </div>

                    <div class="row g-3 g-md-4" id="menuGrid">
                        {% for p in products %}
                        <div class="col-6 col-md-4 col-lg-3 food-card-item" data-food-cat="{{ p['category'] or 'أخرى' }}">
                            <div class="glass-card p-3 h-100 text-center d-flex flex-column justify-content-between">
                                <div>
                                    <div class="food-img-container mb-3">
                                        {% if p['image_url'] %}
                                            <img src="{{ p['image_url'] }}" alt="{{ p['name'] }}">
                                        {% else %}
                                            <i class="fa-solid fa-mug-hot fs-1 bounce-emoji text-muted"></i>
                                        {% endif %}
                                    </div>
                                    <h5 class="fw-bold text-white mb-2 fs-6 fs-md-5">{{ p['name'] }}</h5>
                                </div>
                                <div>
                                    <span class="badge bg-dark text-muted border border-secondary rounded-pill px-2 py-1 fs-7">{{ p['category'] or 'عام' }}</span>
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>

            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            function updateLiveStatus() {
                fetch('/api/live-status')
                    .then(res => res.json())
                    .then(data => {
                        document.getElementById('stat-free').innerText = data.summary.free;
                        document.getElementById('stat-busy').innerText = data.summary.busy;

                        data.items.forEach(item => {
                            const badge = document.querySelector(`.status-badge-${item.id}`);
                            const text = document.querySelector(`.status-text-${item.id}`);

                            if (badge && text) {
                                if (item.status === 'مشغول') {
                                    badge.className = `status-badge-${item.id} status-pill-busy`;
                                    text.innerHTML = '🔴 محجوز حالياً';
                                } else {
                                    badge.className = `status-badge-${item.id} status-pill-free`;
                                    text.innerHTML = '🟢 متاح للعب';
                                }
                            }
                        });
                    })
                    .catch(err => console.log(err));
            }

            setInterval(updateLiveStatus, 4000);
            updateLiveStatus();

            document.querySelectorAll('#deviceFilters .filter-chip').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('#deviceFilters .filter-chip').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    const cat = this.getAttribute('data-filter');
                    
                    document.querySelectorAll('.device-card-item').forEach(item => {
                        if (cat === 'all' || item.getAttribute('data-category') === cat) {
                            item.style.display = 'block';
                        } else {
                            item.style.display = 'none';
                        }
                    });
                });
            });

            document.querySelectorAll('#menuFilters .filter-chip').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('#menuFilters .filter-chip').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    const cat = this.getAttribute('data-filter-food');
                    
                    document.querySelectorAll('.food-card-item').forEach(item => {
                        if (cat === 'all' || item.getAttribute('data-food-cat') === cat) {
                            item.style.display = 'block';
                        } else {
                            item.style.display = 'none';
                        }
                    });
                });
            });
        </script>
    </body>
    </html>
    ''', items=items, categories=categories, products=products, food_categories=food_categories)