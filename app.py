from __future__ import annotations
import os
from decimal import Decimal
from typing import Dict, Any

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret')
database_path = os.path.join(os.path.dirname(__file__), 'store.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    def price_as_decimal(self) -> Decimal:
        return Decimal(self.price) / 100

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

def seed_data() -> None:
    if Product.query.first() is None:
        sample_products = [
            Product(name='Wireless Mouse', price=2999,
                    description='A comfortable and responsive wireless mouse.',
                    image='mouse.jpg'),
            Product(name='Mechanical Keyboard', price=8499,
                    description='A clicky, tactile mechanical keyboard with RGB backlight.',
                    image='keyboard.jpg'),
            Product(name='USB‑C Charger', price=1999,
                    description='Fast‑charging USB‑C power adapter for phones and laptops.',
                    image='charger.jpg'),
            Product(name='Noise Cancelling Headphones', price=12999,
                    description='Over‑ear headphones with active noise cancellation.',
                    image='headphones.jpg'),
        ]
        db.session.bulk_save_objects(sample_products)
        db.session.commit()

@app.before_request
def ensure_cart_exists() -> None:
    if 'cart' not in session:
        session['cart'] = {}

@app.route('/')
def index() -> str:
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id: int) -> Any:
    product = Product.query.get(product_id)
    if not product:
        return redirect(url_for('index'))
    cart: Dict[str, int] = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart() -> str:
    cart: Dict[str, int] = session.get('cart', {})
    items = []
    total_cents = 0
    for pid_str, qty in cart.items():
        product = Product.query.get(int(pid_str))
        if product:
            line_total = product.price * qty
            total_cents += line_total
            items.append({
                'product': product,
                'quantity': qty,
                'line_total': Decimal(line_total) / 100
            })
    total = Decimal(total_cents) / 100
    return render_template('cart.html', items=items, total=total)

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id: int) -> Any:
    cart: Dict[str, int] = session.get('cart', {})
    pid_str = str(product_id)
    if pid_str in cart:
        if cart[pid_str] > 1:
            cart[pid_str] -= 1
        else:
            cart.pop(pid_str)
        session['cart'] = cart
    return redirect(url_for('view_cart'))

@app.route('/checkout')
def checkout() -> str:
    cart: Dict[str, int] = session.get('cart', {})
    items = []
    total_cents = 0
    for pid_str, qty in cart.items():
        product = Product.query.get(int(pid_str))
        if product:
            line_total = product.price * qty
            total_cents += line_total
            items.append({
                'product': product,
                'quantity': qty,
                'line_total': Decimal(line_total) / 100
            })
    total = Decimal(total_cents) / 100
    session['cart'] = {}
    return render_template('checkout.html', items=items, total=total)

@app.route('/register', methods=['GET', 'POST'])
def register() -> Any:
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Username and password are required.')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login() -> Any:
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('Invalid username or password.')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout() -> Any:
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/profile')
def profile() -> Any:
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    if not user:
        session.pop('user_id', None)
        return redirect(url_for('login'))
    return render_template('profile.html', user=user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True)
