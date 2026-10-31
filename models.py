from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# تعريف كائن قاعدة البيانات
db = SQLAlchemy()

# 1. جدول المنتجات
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(200), nullable=True)
    # المفتاح الخارجي اللي بيربط المنتج بالتصنيف
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    sizes = db.relationship('ProductSize', backref='product',
                                cascade='all, delete-orphan', lazy=True)

# 2. جدول الزيارات (لتتبع عدد زيارات المنيو)
class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# 3. جدول الطلبات (الأوردرات)
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    items_details = db.Column(db.Text, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 4. جدول التصنيفات (Categories)
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # ربط المنتج بالتصنيف
    products = db.relationship('Product', backref='category_rel', lazy=True)


    # 5. جدول أحجام المنتج (صغير، وسط، كبير...)
class ProductSize(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)