import os

class Config:
    # 1. إعدادات التطبيق العامة وقاعدة البيانات
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'game_hall_secure_key_2026_xyz'
    DATABASE = os.environ.get('DATABASE_PATH') or 'game_hall.db'
    DEBUG = True
    
    # 2. الصلاحيات الافتراضية المتاحة للربط مع الموظفين
    PERMISSIONS_LIST = [
        ('start_session', 'بدء جلسة'),
        ('end_session', 'إنهاء جلسة وحساب'),
        ('add_product_to_session', 'إضافة مشروب/خدمة للجلسة'),
        ('manage_items', 'إنشاء وتعديل الألعاب والأجهزة'),
        ('manage_products', 'إدارة المنتجات والمخزون'),
        ('view_reports', 'مشاهدة الأرباح والتقارير'),
        ('manage_staff', 'إدارة الموظفين والصلاحيات'),
        ('manage_announcements', 'إدارة الإعلانات والتحديثات')
    ]