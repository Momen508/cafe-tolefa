import os
from flask import Flask, request, jsonify
from models import Category, db, Product, Visit, Order, ProductSize
from flask import session, redirect, url_for, render_template, request
from functools import wraps
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__) 
app.secret_key = 'my_super_secret_key_coffee_shop' # يقدر يتبدل بأي نص سري

# قراءة البيانات السرية للاتصال بـ Turso
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

import os

# التحقق التلقائي: هل نحن نعمل على سحابي (Vercel) أم محلياً على جهازك؟
if os.environ.get('VERCEL'):
    # إعدادات Turso أونلاين على Vercel فقط
    TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
    TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")
    
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        host = TURSO_DATABASE_URL.replace("libsql://", "").replace("https://", "").strip()
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite+libsql://{host}?secure=true"
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            "connect_args": {"auth_token": TURSO_AUTH_TOKEN.strip()}
        }
else:
    # محلياً على جهازك: استخدم SQLite العادية (بدون برامج أو درايفرات معقدة)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


# ----------------------------------------------------
#login and logout for admin
# ----------------------------------------------------
# ديكوراتور (Decorator) لحماية صفحات الآدمن
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# صفحة تسجيل الدخول
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # تقدر تغير اليوزرنيم والباسورد زي ما تحب هنا
        if username == 'admin' and password == 'lefa215@#':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'اسم المستخدم أو كلمة المرور غير صحيحة!'
            
    return render_template('login.html', error=error)

# تسجيل الخروج
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

#----------------------------------------------------
from flask import render_template # تأكد من استيرادها
@app.route('/cart')
def cart_page():
    # بنجيب السلة من الـ session (ولو مش موجودة ترجع مصفوفة فاضية)
    cart = session.get('cart', [])
    
    # حساب الإجمالي الكلي لكل المنتجات بالكميات والأحجام بتاعتها
    total_price = sum(item['price'] * item['quantity'] for item in cart)
    
    return render_template('cart.html', cart=cart, total_price=total_price)

@app.route('/')
def home():
    new_visit = Visit()
    db.session.add(new_visit)
    db.session.commit()

    products = Product.query.all()
    categories = Category.query.all()
    return render_template('index.html', products=products, categories=categories)

# إعداد قاعدة البيانات SQLite
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ربط قاعدة البيانات بالتطبيق
#db.init_app(app)

# إنشاء الجدول تلقائياً عند تشغيل التطبيق لأول مرة
#with app.app_context():
   # db.create_all()

# ----------------------------------------------------
# 1. API تسجيل زيارة جديدة عند فتح المنيو
# ----------------------------------------------------
@app.route('/api/visit', methods=['POST'])
def record_visit():
    new_visit = Visit()
    db.session.add(new_visit)
    db.session.commit()
    return jsonify({"message": "تم تسجيل الزيارة بنجاح"}), 201

# ----------------------------------------------------
# 2. API جلب جميع المنتجات لعرضها في المنيو
# ----------------------------------------------------
@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    products_list = []
    for p in products:
        # جلب الأحجام والأسعار المرتبطة بكل منتج من جدول ProductSize
     sizes_list = [{"id": s.id, "name": s.name, "price": s.price} for s in p.sizes]
        
     products_list.append({
            "id": p.id,
            "name": p.name,
            "price": p.price, # السعر الأساسي (لو حبينا نخليه احتياطي)
            "description": p.description,
            "image_url": p.image_url,
            "category_id": p.category_id,
            "sizes": sizes_list # دي اللي الجافاسكريبت هتاخدها وترسم بيها صفوف المقاسات
        })
    return jsonify(products_list), 200

# ----------------------------------------------------
# 3. API تسجيل طلب جديد (قبل التحويل للواتساب)
# ----------------------------------------------------
@app.route('/api/order', methods=['POST'])
def create_order():
    # دعم استقبال البيانات سواء JSON أو Form Data لضمان عدم حدوث خطأ
    data = request.get_json(silent=True) or request.form
    
    if not data:
        return jsonify({"message": "لا توجد بيانات للطلب"}), 400
    
    new_order = Order(
        customer_name=data.get('name'),
        customer_phone=data.get('phone'),
        customer_address=data.get('address'),
        items_details=data.get('items'),
        total_price=float(data.get('total')) if data.get('total') else 0.0
    )
    
    db.session.add(new_order)
    db.session.commit()
    
    return jsonify({"message": "تم حفظ الطلب بنجاح", "order_id": new_order.id}), 201

from flask import render_template, request, redirect, url_for, flash
from models import db, Product, Order, Visit, ProductSize # استدعاء الجداول من models.py

# 1. عرض صفحة لوحة التحكم وقائمة المنتجات
@app.route('/admin')
@admin_required
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    # 1. جلب المنتجات والطلبات
    products = Product.query.all()
    categories = Category.query.all()  # السطر الجديد الخاص بالتصنيفات
    orders = Order.query.order_by(Order.created_at.desc()).all()
    
    # 2. حساب إجمالي الزيارات والطلبات ونسبة التحويل
    total_visits = Visit.query.count()
    total_orders = Order.query.count()
    conversion_rate = (total_orders / total_visits * 100) if total_visits > 0 else 0

    # 3. إرجاع الصفحة مرة واحدة فقط في النهاية بكل البيانات والإحصائيات
    return render_template('admin.html', 
                           products=products, 
                           categories=categories,  # تمرير التصنيفات للواجهة
                           orders=orders,
                           total_visits=total_visits,
                           total_orders=total_orders,
                           conversion_rate=round(conversion_rate, 2))

# 2. إضافة منتج جديد
@app.route('/admin/product/add', methods=['POST'])
@admin_required
def add_product():
    name = request.form.get('name')
    description = request.form.get('description')
    category_id = request.form.get('category_id')
    image_url = request.form.get('image_url')

    # 1. إنشاء المنتج الأساسي (بدون حقل price القديم)
    new_product = Product(
        name=name,
        price=0,
        description=description,
        category_id=category_id,
        image_url=image_url
    )
    
    db.session.add(new_product)
    db.session.commit()  # بنعمل commit هنا عشان نحصل على الـ id الخاص بالمنتج الجديد

    # 2. استقبال وحفظ الأحجام والأسعار المتعددة المرتبطة بالمنتج
    size_names = request.form.getlist('size_name[]')
    size_prices = request.form.getlist('size_price[]')

    for s_name, s_price in zip(size_names, size_prices):
        if s_name and s_price:
            try:
                price_val = float(s_price)
                if price_val > 0:
                    new_size = ProductSize(
                        product_id=new_product.id,
                        name=s_name.strip(),
                        price=price_val
                    )
                    db.session.add(new_size)
            except ValueError:
                continue  # لو حصل خطأ في تحويل السعر يتم تخطيه بأمان

    db.session.commit()  # حفظ جميع الأحجام دفعة واحدة
    return redirect(url_for('admin_dashboard'))

# 3. حذف منتج
@app.route('/admin/product/delete/<int:id>', methods=['POST'])
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

 # تحديث منتج4 
@app.route('/api/products/<int:product_id>', methods=['PUT', 'POST'])
@admin_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json(silent=True)

    if not data:
        return jsonify({'message': 'لا توجد بيانات للتعديل'}), 400

    product.name = data.get('name', product.name)
    product.category_id = data.get('category_id', product.category_id)
    product.description = data.get('description', product.description)
    product.image_url = data.get('image_url', product.image_url)

    sizes = data.get('sizes')
    if sizes is not None:
        existing = {s.id: s for s in product.sizes}
        kept_ids = set()

        for item in sizes:
            name = (item.get('name') or '').strip()
            try:
                price = float(item.get('price'))
            except (TypeError, ValueError):
                continue
            if not name or price <= 0:
                continue

            sid = item.get('id')
            if sid in existing:                  # حجم موجود: عدّله
                existing[sid].name = name
                existing[sid].price = price
                kept_ids.add(sid)
            else:                                # حجم جديد: ضيفه
                db.session.add(ProductSize(product_id=product.id, name=name, price=price))

        for sid, size in existing.items():       # اللي اتشال من الفورم: احذفه
            if sid not in kept_ids:
                db.session.delete(size)

    db.session.commit()
    return jsonify({'message': 'تم تعديل المنتج بنجاح!'}), 200

# 5. إضافة تصنيف جديد   
@app.route('/admin/category/add', methods=['POST'])
@admin_required
def add_category():
    category_name = request.form.get('name')
    if category_name:
        new_cat = Category(name=category_name)
        db.session.add(new_cat)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# حذف تصنيف (فقط لو مفيهوش منتجات)
@app.route('/admin/category/delete/<int:id>', methods=['POST'])
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    if category.products:
        return redirect(url_for('admin_dashboard'))  # حماية: التصنيف فيه منتجات
    db.session.delete(category)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)