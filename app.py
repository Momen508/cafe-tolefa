import os
from flask import Flask, request, jsonify
from models import Category, db, Product, Visit, Order
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

# صيغة رابط الاتصال السحابي بـ Turso
if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite+{TURSO_DATABASE_URL}?authToken={TURSO_AUTH_TOKEN}"
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db' # للاختبار المحلي فقط

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
    
    return render_template('cart.html')

@app.route('/')
def home():
    new_visit = Visit()
    db.session.add(new_visit)
    db.session.commit()
        
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('index.html' , products=products, categories=categories)

# إعداد قاعدة البيانات SQLite
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ربط قاعدة البيانات بالتطبيق
#db.init_app(app)

# إنشاء الجدول تلقائياً عند تشغيل التطبيق لأول مرة
with app.app_context():
    db.create_all()

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
        products_list.append({
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "description": p.description,
            "image_url": p.image_url,
            "category_id": p.category_id,
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
from models import db, Product, Order, Visit # استدعاء الجداول من models.py

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
    price = float(request.form.get('price'))
    if price <= 0:
      return "خطأ: السعر يجب أن يكون أكبر من الصفر!", 400
    description = request.form.get('description')
    category_id = request.form.get('category_id')
    image_url = request.form.get('image_url')

    new_product = Product(
        name=name,
        price=price,
        description=description,
        category_id=category_id,
        image_url=image_url
    )
    
    db.session.add(new_product)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# 3. حذف منتج
@app.route('/admin/product/delete/<int:id>', methods=['POST'])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

 # تحديث منتج4 
@app.route('/api/products/<int:product_id>', methods=['PUT', 'POST'])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # دعم استقبال البيانات سواء JSON أو Form Data
    data = request.get_json(silent=True) or request.form

    if not data:
        return jsonify({'message': 'لا توجد بيانات للتعيدل'}), 400

    product.name = data.get('name', product.name)
    
    price = data.get('price')
    if price is not None and price != '':
        product.price = float(price)
        
    product.category = data.get('category', product.category)
    product.description = data.get('description', product.description)
    product.image_url = data.get('image_url', product.image_url)

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


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    app.run(debug=True)