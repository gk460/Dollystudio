

from flask import Flask, render_template, request, redirect, session, send_file, flash, jsonify
import sqlite3,os,time
import webbrowser
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

app = Flask(__name__)

app.secret_key = "mysecretkey123"  # 👈 YE ADD KARO



UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)





import os
import sys
from flask import Flask

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static")
)

app.secret_key = "mysecretkey123"

# -----------------------------------------------
# DATABASE + TABLES INIT
# ----------------------------


import os

# user writable folder (VERY IMPORTANT)
db_path = os.path.join(os.environ['APPDATA'], "DollyStudio")

if not os.path.exists(db_path):
    os.makedirs(db_path)

DATABASE = os.path.join(db_path, "studio.db")

def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )""")

    c.execute("INSERT OR IGNORE INTO users (id, username, password) VALUES (1,'admin','admin123')")

    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        address TEXT,
        email TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        shoot_type TEXT,
        date TEXT,
        delivery_date TEXT,
        status TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        total REAL,
        advance REAL,
        remaining REAL,
        payment_mode TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        filename TEXT
    )""")

    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------
# GALLERY
# -----------------------------------------------
@app.route('/gallery')
def gallery():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT photos.id, photos.filename, photos.customer_id,
               COALESCE(customers.name, 'Customer') as cname
        FROM photos
        LEFT JOIN customers ON photos.customer_id = customers.id
        ORDER BY photos.id DESC
    ''')
    all_photos = c.fetchall()
    conn.close()

    photos = []
    seen = set()
    for p in all_photos:
        filepath = os.path.join(UPLOAD_FOLDER, p[1])
        if os.path.exists(filepath) and p[1] not in seen:
            seen.add(p[1])
            photos.append(p)

    return render_template('gallery.html', photos=photos)

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/about')
def about():
    return render_template('about.html')

# -----------------------------------------------
# LOGIN
# -----------------------------------------------

from flask import request, redirect, render_template, session, url_for
import sqlite3

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("studio.db")
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()

        conn.close()

        if user:
            session['user'] = username
            # return redirect(url_for('home'))
            return redirect('/')
        else:
            return "Invalid username or password"

    return render_template('login.html')


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         conn = get_db()
#         c = conn.cursor()
#         c.execute(
#             "SELECT * FROM users WHERE username=? AND password=?",
#             (request.form['username'], request.form['password'])
#         )
#         user = c.fetchone()
#         conn.close()
#         if user:
#             session['user'] = user[1]
#             return redirect('/')
#     return render_template('login.html')

# -----------------------------------------------
# LOGOUT
# -----------------------------------------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# -----------------------------------------------
# DASHBOARD
# -----------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()
    c = conn.cursor()

    # Phone search
    search = request.form.get('search')
    customer_result = None
    customer_orders = []
    customer_payments = []

    if search:
        c.execute("SELECT * FROM customers WHERE phone LIKE ?", ('%' + search + '%',))
        customer_result = c.fetchone()
        if customer_result:
            customer_id = customer_result[0]
            c.execute("SELECT * FROM orders WHERE customer_id=?", (customer_id,))
            customer_orders = c.fetchall()
            c.execute(
                "SELECT * FROM payments WHERE order_id IN (SELECT id FROM orders WHERE customer_id=?)",
                (customer_id,)
            )
            customer_payments = c.fetchall()

    # Name search
    name_search = request.form.get('name_search')
    name_customer = None
    name_orders = []
    name_payments = []

    if name_search:
        c.execute("SELECT * FROM customers WHERE name LIKE ?", ('%' + name_search + '%',))
        name_customer = c.fetchone()
        if name_customer:
            cid = name_customer[0]
            c.execute("SELECT * FROM orders WHERE customer_id=?", (cid,))
            name_orders = c.fetchall()
            c.execute(
                "SELECT * FROM payments WHERE order_id IN (SELECT id FROM orders WHERE customer_id=?)",
                (cid,)
            )
            name_payments = c.fetchall()

    c.execute("SELECT * FROM customers")
    customers = c.fetchall()
    c.execute("SELECT * FROM orders")
    orders = c.fetchall()
    c.execute("SELECT * FROM payments")
    payments = c.fetchall()

    total_income = sum([p[2] for p in payments]) if payments else 0
    pending      = sum([p[4] for p in payments]) if payments else 0

    conn.close()

    return render_template(
        'index.html',
        customers=customers, orders=orders, payments=payments,
        total_income=total_income, pending=pending,
        customer_result=customer_result,
        customer_orders=customer_orders,
        customer_payments=customer_payments,
        name_customer=name_customer,
        name_orders=name_orders,
        name_payments=name_payments
    )

# -----------------------------------------------
# ADD CUSTOMER
# -----------------------------------------------
@app.route('/add_customer', methods=['POST'])
def add_customer():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO customers (name, phone, address, email) VALUES (?, ?, ?, ?)",
            (request.form['name'], request.form['phone'], request.form['address'], request.form['email'])
        )
        conn.commit()
        conn.close()
        flash("✅ Customer added successfully!")
    except:
        flash("❌ Customer already exists!")
    return redirect('/')

# -----------------------------------------------
# ADD ORDER
# -----------------------------------------------
@app.route('/add_order', methods=['POST'])
def add_order():
    conn = get_db()
    c = conn.cursor()

    c.execute(
        "INSERT INTO orders (customer_id, shoot_type, date, delivery_date, status) VALUES (?, ?, ?, ?, ?)",
        (request.form['customer_id'], request.form['shoot_type'], request.form['date'],
         request.form['delivery_date'], request.form['status'])
    )
    order_id     = c.lastrowid
    total        = float(request.form.get('total', 0))
    advance      = float(request.form.get('advance', 0))
    remaining    = total - advance
    payment_mode = request.form.get('payment_mode', 'Cash')

    c.execute(
        "INSERT INTO payments (order_id, total, advance, remaining, payment_mode) VALUES (?, ?, ?, ?, ?)",
        (order_id, total, advance, remaining, payment_mode)
    )
    conn.commit()
    conn.close()
    flash("✅ Order added successfully!")
    return redirect('/')

# -----------------------------------------------
# GET DUE (auto-fill)
# -----------------------------------------------
@app.route('/get_due/<int:order_id>')
def get_due(order_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT total, advance, remaining FROM payments WHERE order_id=?", (order_id,))
    payment = c.fetchone()
    conn.close()
    total     = payment[0] if payment else 0
    remaining = payment[2] if payment else 0
    return jsonify({"total": total, "remaining": remaining})

# -----------------------------------------------
# ADD / UPDATE PAYMENT
# -----------------------------------------------
@app.route('/add_payment', methods=['POST'])
def add_payment():
    order_id    = request.form['order_id']
    new_payment = float(request.form['advance'])

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM payments WHERE order_id=?", (order_id,))
    payment = c.fetchone()

    if payment:
        total     = payment[2]
        new_paid  = payment[3] + new_payment
        remaining = total - new_paid

        c.execute(
            "UPDATE payments SET advance=?, remaining=? WHERE order_id=?",
            (new_paid, remaining, order_id)
        )
        if remaining <= 0:
            c.execute("UPDATE orders SET status=? WHERE id=?", ("Completed", order_id))
            flash("✅ Payment Complete! Order status → Completed")
        else:
            flash(f"Rs.{remaining:.0f} abhi baaki hai")

        conn.commit()
        conn.close()
    else:
        conn.close()
        flash("❌ Order not found!")

    return redirect('/')

# -----------------------------------------------
# CUSTOMER DETAILS (JSON)
# -----------------------------------------------
@app.route('/customer_details/<int:cid>')
def customer_details(cid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE customer_id=?", (cid,))
    orders = c.fetchall()

    result = []
    for o in orders:
        c.execute("SELECT * FROM payments WHERE order_id=?", (o[0],))
        payment = c.fetchone()
        result.append({
            "order_id":  o[0],
            "service":   o[2],
            "date":      o[3],
            "total":     payment[2] if payment else 0,
            "paid":      payment[3] if payment else 0,
            "remaining": payment[4] if payment else 0
        })

    conn.close()
    return jsonify(result)

# -----------------------------------------------
# INVOICE HTML
# -----------------------------------------------
@app.route('/invoice/<int:order_id>')
def invoice(order_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    order = c.fetchone()
    if not order:
        return "❌ Order not found!", 404

    c.execute("SELECT * FROM payments WHERE order_id=?", (order_id,))
    payment = c.fetchone()
    c.execute("SELECT * FROM customers WHERE id=?", (order[1],))
    customer = c.fetchone()
    conn.close()

    year           = datetime.now().strftime("%Y")
    invoice_number = f"INV-{year}-{order_id:03d}"
    today_date     = datetime.now().strftime("%d-%m-%Y")

    return render_template(
        'invoice.html',
        order=order, payment=payment, customer=customer,
        invoice_number=invoice_number, today_date=today_date
    )

# -----------------------------------------------
# PHOTO UPLOAD
# -----------------------------------------------
@app.route('/upload', methods=['POST'])
def upload():
    import time
    file        = request.files['photo']
    customer_id = request.form['customer_id']

    if file and file.filename:
        parts       = file.filename.rsplit('.', 1)
        ext         = parts[1].lower() if len(parts) > 1 else 'jpg'
        unique_name = f"cust{customer_id}_{int(time.time())}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(filepath)

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO photos (customer_id, filename) VALUES (?, ?)",
            (customer_id, unique_name)
        )
        conn.commit()
        conn.close()
        flash("✅ Photo uploaded successfully!")
    else:
        flash("❌ Koi file select nahi ki!")

    return redirect('/gallery')

# -----------------------------------------------
# PDF INVOICE
# -----------------------------------------------
@app.route('/invoice_pdf/<int:order_id>')
def invoice_pdf(order_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    order = c.fetchone()
    if not order:
        return "❌ Order not found!", 404

    c.execute("SELECT * FROM payments WHERE order_id=?", (order_id,))
    payment = c.fetchone()
    c.execute("SELECT * FROM customers WHERE id=?", (order[1],))
    customer = c.fetchone()
    conn.close()

    if not payment:
        return "Payment not added for this order!"

    year           = datetime.now().strftime("%Y")
    invoice_number = f"INV-{year}-{order_id:03d}"
    file_path      = f"invoice_{order_id}.pdf"
    doc            = SimpleDocTemplate(file_path)
    styles         = getSampleStyleSheet()

    content_list = [
        Paragraph(f"Invoice: {invoice_number}",     styles['Title']),
        Paragraph(f"Customer: {customer[1]}",       styles['Normal']),
        Paragraph(f"Phone: {customer[2]}",          styles['Normal']),
        Paragraph(f"Address: {customer[3]}",        styles['Normal']),
        Paragraph(f"Service: {order[2]}",           styles['Normal']),
        Paragraph(f"Date: {order[3]}",              styles['Normal']),
        Paragraph(f"Delivery Date: {order[4]}",     styles['Normal']),
        Paragraph(f"Status: {order[5]}",            styles['Normal']),
        Paragraph(f"Total: Rs.{payment[2]}",        styles['Normal']),
        Paragraph(f"Advance Paid: Rs.{payment[3]}", styles['Normal']),
        Paragraph(f"Remaining: Rs.{payment[4]}",    styles['Normal']),
        Paragraph(f"Payment Mode: {payment[5]}",    styles['Normal']),
    ]
    doc.build(content_list)
    return send_file(file_path, as_attachment=True)

# -----------------------------------------------
# CLEAN BROKEN PHOTOS
# -----------------------------------------------
@app.route('/clean_photos')
def clean_photos():
    if 'user' not in session:
        return redirect('/login')
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, filename FROM photos")
    all_photos = c.fetchall()
    deleted = 0
    for p in all_photos:
        if not os.path.exists(os.path.join('static/uploads', p[1])):
            c.execute("DELETE FROM photos WHERE id=?", (p[0],))
            deleted += 1
    conn.commit()
    conn.close()
    flash(f"✅ {deleted} broken photo entries removed!")
    return redirect('/gallery')

# -----------------------------------------------
# RUN
# -----------------------------------------------
# if __name__ == '__main__':
#     import threading
#     import webbrowser

#     def open_browser():
#         webbrowser.open("http://127.0.0.1:5000")

#     threading.Timer(1, open_browser).start()

#     app.run(debug=False, port=5000)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)










