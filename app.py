import os, re, math, sqlite3, datetime
from functools import wraps
from flask import Flask, request, jsonify, g, render_template
from flask_cors import CORS
import bcrypt, jwt

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-only-secret-key-change-me-in-production-123456")
CORS(app)  # UNIT IV: CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventory.db")
LOW_STOCK = 10  # quantity at or below this counts as "low stock"


# ---------------------------------------------------------------- DATABASE
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SEED = [
    ("LAP-101", "Dell Inspiron Laptop", "Electronics", 14, 54999),
    ("PHN-202", "Samsung Galaxy Phone", "Electronics", 6, 24999),
    ("HDP-303", "Wireless Headphones", "Accessories", 40, 1999),
    ("KEY-404", "Mechanical Keyboard", "Accessories", 3, 3499),
    ("CHR-505", "Ergonomic Office Chair", "Furniture", 12, 8999),
    ("DSK-606", "Standing Desk", "Furniture", 0, 15999),
    ("BTL-707", "Steel Water Bottle", "Home & Kitchen", 85, 499),
    ("NTB-808", "Spiral Notebook Pack", "Stationery", 120, 199),
]


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash BLOB NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity >= 0),
            price REAL NOT NULL CHECK (price >= 0),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    if con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO products (product_id, name, category, quantity, price) "
            "VALUES (?, ?, ?, ?, ?)", SEED)
    con.commit()
    con.close()


init_db()


# ---------------------------------------------------------------- HELPERS
def err(message, code=400):
    return jsonify({"error": message}), code


def clean(value):
    """Sanitization: trim, collapse spaces, strip < and > (XSS defence)."""
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value))
    return re.sub(r"[<>]", "", text).strip()


def validate_product(d):
    """Server-side validation. Returns (clean_data, error_message)."""
    if not isinstance(d, dict):
        return None, "Invalid request body"
    pid = clean(d.get("product_id")).upper()
    name = clean(d.get("name"))
    category = clean(d.get("category"))
    category = category[:1].upper() + category[1:]

    if not re.fullmatch(r"[A-Z0-9-]{2,20}", pid):
        return None, "Product ID must be 2-20 letters, digits or hyphens"
    if not 2 <= len(name) <= 60:
        return None, "Product name must be 2-60 characters"
    if not 2 <= len(category) <= 30:
        return None, "Category must be 2-30 characters"
    try:
        qty = int(d.get("quantity"))
    except (TypeError, ValueError):
        return None, "Quantity must be a whole number"
    try:
        price = round(float(d.get("price")), 2)
    except (TypeError, ValueError):
        return None, "Price must be a number"
    if qty < 0 or qty > 1_000_000:
        return None, "Quantity must be between 0 and 1,000,000"
    if not math.isfinite(price) or price < 0 or price > 10_000_000:
        return None, "Price must be between 0 and 10,000,000"
    return {"product_id": pid, "name": name, "category": category,
            "quantity": qty, "price": price}, None


# ---------------------------------------------------------------- SECURITY
@app.after_request
def security_headers(resp):
    """UNIT IV: security headers (the Flask equivalent of Helmet.js)."""
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:")
    return resp


def make_token(user_id, username):
    payload = {"sub": str(user_id), "username": username,
               "exp": datetime.datetime.now(datetime.timezone.utc)
               + datetime.timedelta(hours=8)}
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def login_required(fn):
    """Authorization: only requests with a valid JWT reach the route."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return err("Authentication required", 401)
        try:
            data = jwt.decode(header[7:], app.config["SECRET_KEY"],
                              algorithms=["HS256"])
            g.user_id = int(data["sub"])
        except jwt.PyJWTError:
            return err("Invalid or expired token", 401)
        return fn(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------- PAGES
@app.get("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------- AUTH API
@app.post("/api/register")
def register():
    d = request.get_json(silent=True) or {}
    username = clean(d.get("username"))
    password = str(d.get("password") or "")
    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
        return err("Username: 3-20 letters, digits or underscore")
    if len(password) < 6 or not re.search(r"[A-Za-z]", password) \
            or not re.search(r"\d", password):
        return err("Password must be 6+ characters with a letter and a digit")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())  # hashing
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hashed))
        db.commit()
    except sqlite3.IntegrityError:
        return err("Username already taken", 409)
    return jsonify({"token": make_token(cur.lastrowid, username),
                    "username": username}), 201


@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    username = clean(d.get("username"))
    password = str(d.get("password") or "")
    row = get_db().execute(
        "SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not row or not bcrypt.checkpw(password.encode(), row["password_hash"]):
        return err("Invalid username or password", 401)
    return jsonify({"token": make_token(row["id"], row["username"]),
                    "username": row["username"]})


# ---------------------------------------------------------------- PRODUCT API
@app.get("/api/products")
@login_required
def list_products():
    q = clean(request.args.get("q"))
    category = clean(request.args.get("category"))
    sql, params = "SELECT * FROM products WHERE 1=1", []
    if q:
        sql += " AND (name LIKE ? OR product_id LIKE ? OR category LIKE ?)"
        params += [f"%{q}%"] * 3
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY id DESC"
    rows = get_db().execute(sql, params).fetchall()  # parameterized = no SQLi
    return jsonify([dict(r) for r in rows])


@app.post("/api/products")
@login_required
def add_product():
    data, error = validate_product(request.get_json(silent=True))
    if error:
        return err(error)
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO products (product_id, name, category, quantity, price)"
            " VALUES (:product_id, :name, :category, :quantity, :price)", data)
        db.commit()
    except sqlite3.IntegrityError:
        return err(f"Product ID '{data['product_id']}' already exists", 409)
    row = db.execute("SELECT * FROM products WHERE id = ?",
                     (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.put("/api/products/<int:pid>")
@login_required
def update_product(pid):
    db = get_db()
    existing = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not existing:
        return err("Product not found", 404)
    body = request.get_json(silent=True) or {}
    body["product_id"] = existing["product_id"]  # ID cannot be changed
    data, error = validate_product(body)
    if error:
        return err(error)
    data["id"] = pid
    db.execute("UPDATE products SET name=:name, category=:category, "
               "quantity=:quantity, price=:price WHERE id=:id", data)
    db.commit()
    row = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    return jsonify(dict(row))


@app.put("/api/products/<int:pid>/stock")
@login_required
def change_stock(pid):
    db = get_db()
    row = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not row:
        return err("Product not found", 404)
    try:
        change = int((request.get_json(silent=True) or {}).get("change"))
    except (TypeError, ValueError):
        return err("'change' must be a whole number")
    new_qty = row["quantity"] + change
    if new_qty < 0:
        return err(f"Stock cannot go below zero (current stock: {row['quantity']})")
    db.execute("UPDATE products SET quantity = ? WHERE id = ?", (new_qty, pid))
    db.commit()
    return jsonify({"id": pid, "quantity": new_qty})


@app.delete("/api/products/<int:pid>")
@login_required
def delete_product(pid):
    db = get_db()
    cur = db.execute("DELETE FROM products WHERE id = ?", (pid,))
    db.commit()
    if cur.rowcount == 0:
        return err("Product not found", 404)
    return jsonify({"message": "Product deleted"})


@app.get("/api/stats")
@login_required
def stats():
    db = get_db()
    t = db.execute("SELECT COUNT(*) c, COALESCE(SUM(quantity),0) u, "
                   "COALESCE(SUM(quantity*price),0) v FROM products").fetchone()
    low = db.execute("SELECT COUNT(*) FROM products WHERE quantity <= ?",
                     (LOW_STOCK,)).fetchone()[0]
    cats = db.execute("SELECT category, SUM(quantity) units FROM products "
                      "GROUP BY category ORDER BY units DESC").fetchall()
    low_list = db.execute("SELECT id, product_id, name, quantity FROM products "
                          "WHERE quantity <= ? ORDER BY quantity LIMIT 6",
                          (LOW_STOCK,)).fetchall()
    return jsonify({
        "total_products": t["c"], "total_units": t["u"],
        "total_value": t["v"], "low_stock_count": low,
        "low_threshold": LOW_STOCK,
        "categories": [dict(c) for c in cats],
        "low_stock": [dict(r) for r in low_list]})


@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return err("Endpoint not found", 404)
    return render_template("index.html")


@app.errorhandler(500)
def server_error(_e):
    return err("Internal server error", 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)