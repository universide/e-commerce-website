# Flask Commerce Demo

A compact e-commerce demonstration built with Flask and SQLite. It shows a
complete local workflow: browse seeded products, create an account, sign in,
manage a session-based cart, and submit a simulated checkout.

> Portfolio scope: this project does not process real payments, send email, or
> provide production order fulfilment. Checkout only displays an order summary.

## Features

- Product catalogue backed by SQLAlchemy
- Registration and login with Werkzeug password hashing
- Session-based cart with add, remove, and checkout actions
- CSRF protection for every state-changing form
- Responsive Jinja templates and custom CSS
- Isolated automated tests for catalogue, authentication, cart, and CSRF flows

## Technology

- Python and Flask
- Flask-SQLAlchemy and SQLite
- Jinja templates, HTML, and CSS
- Pytest

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python app.py
```

Open <http://127.0.0.1:5000>.

For a persistent session signing key, set `FLASK_SECRET_KEY` before starting
the app. You can also set `DATABASE_URL` to use a different database connection.
The default SQLite file is created under `instance/` and is not committed.

## Test

```bash
pytest -q
```

The tests create their own temporary SQLite database and do not modify local
development data.

## Project structure

```text
app.py              Application factory, models, routes, and CSRF protection
templates/          Jinja page templates
static/             Styles and product images
tests/               Behaviour tests
instance/            Local SQLite data (generated and ignored)
```

## Security and limitations

- Passwords are stored as salted hashes, not plain text.
- Cart mutations, checkout, and logout use POST requests with CSRF tokens.
- The application is a learning/portfolio demo and has not undergone a
  production security audit.
- A real service would need payment-provider integration, verified email,
  order persistence, rate limiting, monitoring, and production deployment
  configuration.
