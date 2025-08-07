"""Simple E-commerce web application.

This module defines a minimal Flask application that implements the core
functionality of a small online store. Users can browse a catalogue of
products, add items to a session-based shopping cart, view the cart and
proceed to a checkout summary. For clarity and brevity the example omits
many production concerns such as authentication, payment integration,
security hardening and input validation. You can build on this scaffold
to implement a full-featured online shop.

Usage:
    python app.py

Access the application in your browser at http://127.0.0.1:5000/ after
running the script.
"""

from __future__ import annotations
import os
import re
from decimal import Decimal
from typing import Dict, Any
from datetime import timedelta

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

# Create the Flask app and configure it.
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

# Configure how long "remember me" logins persist (30 days).
app.permanent_session_lifetime = timedelta(days=30)

# Configure the SQLite database.
database_path = os.path.join(os.path.dirname(__file__), "store.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{database_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Product(db.Model):
    """Database model representing a product available for sale."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)  # price in cents
    description = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(255), nullable=True)

    def price_as_decimal(self) -> Decimal:
        """Return price expressed in dollars instead of cents."""
        return Decimal(self.price) / 100


class User(db.Model):
    """User account for authentication."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


def seed_data() -> None:
    """Populate the database with sample products if it's empty."""
    if Product.query.first() is None:
        sample_products = [
            Product(
                name="Wireless Mouse",
                price=2999,
                description="A comfortable and responsive wireless mouse.",
                image="mouse.jpg",
            ),
            Product(
                name="Mechanical Keyboard",
                price=8499,
                description="A clicky, tactile mechanical keyboard with RGB backlight.",
                image="keyboard.jpg",
            ),
            Product(
                name="USB-C Charger",
                price=1999,
                description="Fast-charging USB-C power adapter for phones and laptops.",
                image="charger.jpg",
            ),
            Product(
                name="Noise Cancelling Headphones",
                price=12999,
                description="Over-ear headphones with active noise cancellation.",
                image="headphones.jpg",
            ),
        ]
        db.session.bulk_save_objects(sample_products)
        db.session.commit()


@app.before_request
def ensure_cart_exists() -> None:
    """Ensure the user session has a cart structure."""
    if "cart" not in session:
        session["cart"] = {}


@app.route("/")
def index() -> str:
    """Display the home page with a list of available products."""
    products = Product.query.all()
    return render_template("index.html", products=products)


@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id: int) -> Any:
    """Add a product to the shopping cart."""
    product = Product.query.get(product_id)
    if not product:
        return redirect(url_for("index"))
    cart: Dict[str, int] = session.get("cart", {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session["cart"] = cart
    return redirect(url_for("index"))


@app.route("/cart")
def view_cart() -> str:
    """Show the contents of the shopping cart."""
    cart: Dict[str, int] = session.get("cart", {})
    items = []
    total_cents = 0
    for pid_str, qty in cart.items():
        product = Product.query.get(int(pid_str))
        if product:
            line_total = product.price * qty
            total_cents += line_total
            items.append({
                "product": product,
                "quantity": qty,
                "line_total": Decimal(line_total) / 100,
            })
    total = Decimal(total_cents) / 100
    return render_template("cart.html", items=items, total=total)


@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id: int) -> Any:
    """Remove one unit of the given product from the cart."""
    cart: Dict[str, int] = session.get("cart", {})
    pid_str = str(product_id)
    if pid_str in cart:
        if cart[pid_str] > 1:
            cart[pid_str] -= 1
        else:
            cart.pop(pid_str)
        session["cart"] = cart
    return redirect(url_for("view_cart"))


@app.route("/checkout")
def checkout() -> str:
    """Display a summary of the order and clear the cart."""
    cart: Dict[str, int] = session.get("cart", {})
    items = []
    total_cents = 0
    for pid_str, qty in cart.items():
        product = Product.query.get(int(pid_str))
        if product:
            line_total = product.price * qty
            total_cents += line_total
            items.append({
                "product": product,
                "quantity": qty,
                "line_total": Decimal(line_total) / 100,
            })
    total = Decimal(total_cents) / 100
    session["cart"] = {}
    return render_template("checkout.html", items=items, total=total)


@app.route("/register", methods=["GET", "POST"])
def register() -> Any:
    """Allow a new user to create an account with password complexity rules."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for("register"))

        # Enforce password complexity
        def is_password_valid(pwd: str) -> bool:
            return (
                len(pwd) >= 8
                and re.search(r"[a-z]", pwd)
                and re.search(r"[A-Z]", pwd)
                and re.search(r"\d", pwd)
                and re.search(r"[^A-Za-z0-9]", pwd)
            )

        if not is_password_valid(password):
            flash(
                "Password must be at least 8 characters long and include "
                "uppercase, lowercase, numeric and special characters."
            )
            return redirect(url_for("register"))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """Authenticate an existing user and start a session, with 'remember me'."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session.permanent = bool(remember)
            return redirect(url_for("index"))

        flash("Invalid username or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout() -> Any:
    """Log the user out by clearing their session."""
    session.pop("user_id", None)
    return redirect(url_for("index"))


@app.route("/profile")
def profile() -> Any:
    """Display the logged-in user’s profile."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    user = User.query.get(user_id)
    if not user:
        session.pop("user_id", None)
        return redirect(url_for("login"))
    return render_template("profile.html", user=user)


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password() -> Any:
    """Placeholder for a password reset flow."""
    if request.method == "POST":
        flash("If the account exists, reset instructions have been sent.")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True)
