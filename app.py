"""Small Flask commerce demo used as a portfolio project.

The application demonstrates product browsing, session-based cart management,
account registration, password hashing, and a simple checkout summary. It does
not process real payments or send password-reset email.
"""

from __future__ import annotations

import hmac
import os
import re
import secrets
from datetime import timedelta
from decimal import Decimal
from typing import Any

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class Product(db.Model):
    """A product available in the demonstration catalogue."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)  # Stored in cents.
    description = db.Column(db.String(255))
    image = db.Column(db.String(255))

    def price_as_decimal(self) -> Decimal:
        return Decimal(self.price) / 100


class User(db.Model):
    """A local demonstration account with a hashed password."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


def seed_data() -> None:
    """Create the small product catalogue when the database is empty."""

    if db.session.execute(db.select(Product).limit(1)).scalar_one_or_none() is not None:
        return

    db.session.add_all(
        [
            Product(
                name="Wireless Mouse",
                price=2999,
                description="A comfortable and responsive wireless mouse.",
                image="mouse.jpg",
            ),
            Product(
                name="Mechanical Keyboard",
                price=8499,
                description="A tactile mechanical keyboard with RGB backlight.",
                image="keyboard.jpg",
            ),
            Product(
                name="USB-C Charger",
                price=1999,
                description="A fast-charging USB-C adapter for phones and laptops.",
                image="charger.jpg",
            ),
            Product(
                name="Noise Cancelling Headphones",
                price=12999,
                description="Over-ear headphones with active noise cancellation.",
                image="headphones.jpg",
            ),
        ]
    )
    db.session.commit()


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Create and configure the application.

    ``test_config`` lets the automated tests use an isolated temporary
    database without changing the normal local-development setup.
    """

    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=database_url
        or f"sqlite:///{os.path.join(app.instance_path, 'store.db')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        CSRF_ENABLED=True,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    def csrf_token() -> str:
        token = session.get("_csrf_token")
        if token is None:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_post_requests() -> None:
        if request.method != "POST" or not app.config["CSRF_ENABLED"]:
            return
        expected = session.get("_csrf_token", "")
        supplied = request.form.get("_csrf_token", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            abort(400, description="Invalid or missing CSRF token.")

    @app.before_request
    def ensure_cart_exists() -> None:
        session.setdefault("cart", {})

    def cart_summary() -> tuple[list[dict[str, Any]], Decimal]:
        cart: dict[str, int] = session.get("cart", {})
        items: list[dict[str, Any]] = []
        total_cents = 0
        for product_id, quantity in cart.items():
            product = db.session.get(Product, int(product_id))
            if product is None:
                continue
            line_total = product.price * quantity
            total_cents += line_total
            items.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "line_total": Decimal(line_total) / 100,
                }
            )
        return items, Decimal(total_cents) / 100

    @app.get("/")
    def index() -> str:
        products = db.session.execute(db.select(Product).order_by(Product.id)).scalars()
        return render_template("index.html", products=products)

    @app.post("/cart/items/<int:product_id>")
    def add_to_cart(product_id: int) -> Any:
        if db.session.get(Product, product_id) is None:
            abort(404)
        cart: dict[str, int] = session.get("cart", {})
        key = str(product_id)
        cart[key] = cart.get(key, 0) + 1
        session["cart"] = cart
        return redirect(url_for("view_cart"))

    @app.get("/cart")
    def view_cart() -> str:
        items, total = cart_summary()
        return render_template("cart.html", items=items, total=total)

    @app.post("/cart/items/<int:product_id>/remove")
    def remove_from_cart(product_id: int) -> Any:
        cart: dict[str, int] = session.get("cart", {})
        key = str(product_id)
        if key in cart:
            cart[key] -= 1
            if cart[key] <= 0:
                cart.pop(key)
            session["cart"] = cart
        return redirect(url_for("view_cart"))

    @app.post("/checkout")
    def checkout() -> str:
        items, total = cart_summary()
        session["cart"] = {}
        return render_template("checkout.html", items=items, total=total)

    @app.route("/register", methods=["GET", "POST"])
    def register() -> Any:
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not 3 <= len(username) <= 80:
                flash("Username must be between 3 and 80 characters.")
                return redirect(url_for("register"))
            if db.session.execute(
                db.select(User).where(User.username == username)
            ).scalar_one_or_none():
                flash("Username already exists.")
                return redirect(url_for("register"))
            if not (
                len(password) >= 8
                and re.search(r"[a-z]", password)
                and re.search(r"[A-Z]", password)
                and re.search(r"\d", password)
                and re.search(r"[^A-Za-z0-9]", password)
            ):
                flash(
                    "Password must contain at least eight characters, including "
                    "uppercase, lowercase, numeric, and special characters."
                )
                return redirect(url_for("register"))

            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            return redirect(url_for("profile"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login() -> Any:
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = db.session.execute(
                db.select(User).where(User.username == username)
            ).scalar_one_or_none()
            if user and user.check_password(password):
                session["user_id"] = user.id
                session.permanent = request.form.get("remember") == "1"
                return redirect(url_for("profile"))
            flash("Invalid username or password.")
            return redirect(url_for("login"))
        return render_template("login.html")

    @app.post("/logout")
    def logout() -> Any:
        session.pop("user_id", None)
        return redirect(url_for("index"))

    @app.get("/profile")
    def profile() -> Any:
        user_id = session.get("user_id")
        if user_id is None:
            return redirect(url_for("login"))
        user = db.session.get(User, user_id)
        if user is None:
            session.pop("user_id", None)
            return redirect(url_for("login"))
        return render_template("profile.html", user=user)

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password() -> Any:
        if request.method == "POST":
            flash("This portfolio demo does not send email. No account was changed.")
            return redirect(url_for("login"))
        return render_template("forgot_password.html")

    return app


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
