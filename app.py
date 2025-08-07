"""Simple E‑commerce web application.

This module defines a minimal Flask application that implements the core
functionality of a small online store.  Users can browse a catalogue of
products, add items to a session‑based shopping cart, view the cart and
proceed to a checkout summary.  For clarity and brevity the example omits
many production concerns such as authentication, payment integration,
security hardening and input validation.  You can build on this scaffold
to implement a full‑featured online shop.

Usage:
    python app.py

Access the application in your browser at http://127.0.0.1:5000/ after
running the script.
"""

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
)
from flask_sqlalchemy import SQLAlchemy


# Create the Flask app and configure it.  For simplicity we're using a
# SQLite database stored in a local file.  In a production system you
# should consider using a more robust database (e.g. PostgreSQL) and
# storing credentials securely.
app = Flask(__name__)
# A secret key is required for session handling.  In production set this
# via an environment variable or configuration file, never commit real
# secrets to version control.
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret')

# Configure the SQLite database.  It will be created automatically if it
# doesn't exist.
database_path = os.path.join(os.path.dirname(__file__), 'store.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy extension
db = SQLAlchemy(app)


class Product(db.Model):
    """Database model representing a product available for sale.

    Attributes
    ----------
    id: int
        Primary key identifier for the product.
    name: str
        The human‑readable name of the product.
    price: int
        Price in cents to avoid floating point errors when dealing with money.
    description: str
        A brief textual description of the product.
    image: str
        Path to an image representing the product.  This example stores
        filenames relative to the ``static`` directory.  In a real
        application you might store URLs or integrate with a CDN.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(255), nullable=True)

    def price_as_decimal(self) -> Decimal:
        """Return price as a Decimal expressed in dollars instead of cents."""
        return Decimal(self.price) / 100


def seed_data() -> None:
    """Populate the database with some sample products if it's empty.

    This function checks whether any products exist in the database and, if
    none do, inserts a handful of example items.  Running this on each
    start allows the application to function out of the box without
    manual database preparation.
    """
    if Product.query.first() is None:
        sample_products = [
            Product(
                name='Wireless Mouse',
                price=2999,
                description='A comfortable and responsive wireless mouse.',
                image='mouse.jpg',
            ),
            Product(
                name='Mechanical Keyboard',
                price=8499,
                description='A clicky, tactile mechanical keyboard with RGB backlight.',
                image='keyboard.jpg',
            ),
            Product(
                name='USB‑C Charger',
                price=1999,
                description='Fast‑charging USB‑C power adapter for phones and laptops.',
                image='charger.jpg',
            ),
            Product(
                name='Noise Cancelling Headphones',
                price=12999,
                description='Over‑ear headphones with active noise cancellation.',
                image='headphones.jpg',
            ),
        ]
        db.session.bulk_save_objects(sample_products)
        db.session.commit()


@app.before_request
def ensure_cart_exists() -> None:
    """Ensure the user session has a cart structure.

    The cart is stored in the session as a dictionary mapping product IDs
    (as strings) to quantity integers.  Flask stores the session on the
    client as a signed cookie, so you should keep the stored data small
    and avoid sensitive information.
    """
    if 'cart' not in session:
        session['cart'] = {}


@app.route('/')
def index() -> str:
    """Display the home page with a list of available products."""
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id: int) -> Any:
    """Add a product to the shopping cart.

    Increments the quantity of the given product in the cart stored in
    the session.  If the product ID is not recognised, the user is
    redirected back to the home page.
    """
    product = Product.query.get(product_id)
    if not product:
        return redirect(url_for('index'))
    cart: Dict[str, int] = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    return redirect(url_for('index'))


@app.route('/cart')
def view_cart() -> str:
    """Show the contents of the shopping cart."""
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
    """Remove one unit of the given product from the cart."""
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
    """Display a summary of the order.

    In a complete implementation this is where you would collect shipping
    details and integrate with a payment gateway.  Here we simply show
    the final total and clear the cart after checkout.
    """
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
    # After checkout we clear the cart.  In a real application you would
    # persist the order and only clear the cart after successful payment.
    session['cart'] = {}
    return render_template('checkout.html', items=items, total=total)


if __name__ == '__main__':
    # Create the database tables if they don't exist
    with app.app_context():
        db.create_all()
        seed_data()
    # Run the application in debug mode for development convenience
    app.run(debug=True)