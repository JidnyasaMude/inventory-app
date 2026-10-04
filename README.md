# 📦 StockPulse: Inventory Management System

A full-stack web application to manage product inventory with secure login, live stock tracking, low-stock alerts and a category chart. Built as a Backend Development mini project (Teacher Assessment).

## 📖 Description

StockPulse lets authenticated users add, search, update and delete products, adjust stock with +/- buttons, and monitor inventory health from a dashboard. The frontend talks to a Flask REST API using Fetch and JSON, so everything updates without page reloads. Data is stored in an SQLite database.

## ✨ Features

- User registration and login (passwords hashed with **bcrypt**, sessions via **JWT**)
- Full CRUD on products (Product ID, Name, Category, Quantity, Price)
- Live search by name, ID or category, plus category filter
- Stock +/- buttons; stock can never go below zero
- Low-stock and out-of-stock alerts
- Dashboard cards: total products, total units, inventory value, low-stock count
- Category-wise stock donut chart
- Input validation on both client and server
- Responsive, modern UI

## 🛠️ Technologies Used

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript (Fetch API) |
| Backend | Python, Flask |
| Database | SQLite |
| Authentication | JWT (PyJWT), bcrypt |
| Security | CORS (flask-cors), security headers, parameterized SQL queries, input sanitization, XSS escaping |
| Deployment | Gunicorn, Render |
| Tools | VS Code, Git, GitHub |

## 🔐 Security Practices

- Passwords hashed with bcrypt (never stored as plain text)
- JWT token authentication on all product APIs
- Parameterized queries to prevent SQL injection
- Input validation and sanitization; output escaping to prevent XSS
- CSRF-safe: the token is sent in the Authorization header, not in cookies
- CORS enabled and security headers (CSP, X-Frame-Options, X-Content-Type-Options)

## 🚀 How to Run the Project

**Prerequisites:** Python 3.9+ and Git installed.

1. **Clone the repository**
```
   git clone https://github.com/JidnyasaMude/inventory-app.git
   cd inventory-app
```
2. **Create and activate a virtual environment**
```
   python -m venv venv
   venv\Scripts\activate
```
   (Mac/Linux: `source venv/bin/activate`)
3. **Install dependencies**
```
   pip install -r requirements.txt
```
4. **Run the app**
```
   python app.py
```
5. **Open in browser:** http://127.0.0.1:5000
6. Click **Register**, create an account, and start managing inventory. The database is created automatically with sample products.

## 📁 Project Structure

```
inventory-app/
├── app.py              # Flask backend (API, auth, database)
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Main page
└── static/
    ├── style.css       # Styling
    └── app.js          # Frontend logic (Fetch API)
```

## 🔗 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/register` | Create account |
| POST | `/api/login` | Login and get JWT |
| GET | `/api/products` | List/search products |
| POST | `/api/products` | Add product |
| PUT | `/api/products/<id>` | Update product |
| PUT | `/api/products/<id>/stock` | Increase/decrease stock |
| DELETE | `/api/products/<id>` | Delete product |
| GET | `/api/stats` | Dashboard statistics |

## 👩‍💻 Author

**Jidnyasa Mude**
B.Tech ECE, Ramdeobaba University, Nagpur
GitHub: [@JidnyasaMude](https://github.com/JidnyasaMude)