from flask import Flask, render_template, jsonify, request, session, redirect, url_for, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from fpdf import FPDF
from flasgger import Swagger
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from requests.auth import HTTPBasicAuth
import smtplib
import random
import csv
import io
import os
import qrcode
import shutil
import re
import urllib.parse
from google import genai
import pyotp
import requests
import psutil
import base64

# The new SDK uses a Client object instead of a global configuration
ai_client = genai.Client(api_key="AIzaSyC6HBu3kYg0P-am1HOb69Uy0yIixJjhHrQ")

app = Flask(__name__)
app.secret_key = 'super_secret_grandmark_key_123'

# --- CLOUD DATABASE CONFIGURATION (RENDER + SQLITE FALLBACK) ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///site.db')

# SQLAlchemy requires 'postgresql://' but Render sometimes gives 'postgres://'. This fixes that bug automatically.
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
swagger = Swagger(app) 

SENDER_EMAIL = "starfordomwocha2006@gmail.com" 
SENDER_PASSWORD = "nibwjhqulfygakdx" 

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    totp_secret = db.Column(db.String(32), nullable=False) 

class ClientAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)

class SupplierAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False) 
    industry = db.Column(db.String(100))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50))
    unit_cost = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)

class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(100), nullable=False)
    inquiry_type = db.Column(db.String(50), nullable=False) 
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Pending Processing') 
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.Column(db.String(50), default='System Admin')

class Ledger(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(10), nullable=False) 
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class BlacklistedIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), unique=True, nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Database Initialization
with app.app_context():
    db.create_all()
    if not User.query.first():
        hashed_pw = generate_password_hash('grandmark2026', method='pbkdf2:sha256')
        master_secret = pyotp.random_base32()
        db.session.add(User(username='admin', password_hash=hashed_pw, totp_secret=master_secret))
        db.session.add(Ledger(transaction_type='Credit', amount=2000000000.00, description='Initial Business Capital (KES)'))
        db.session.commit()

# =========================================================
# --- M-PESA DARAJA API ENGINE (DORMANT) ---
# =========================================================
MPESA_CONSUMER_KEY = "VqyldcZ1JNo46B5MJ1KZ6V9XvQ7ansAdofcvUUMpu8VRsRcL"
MPESA_CONSUMER_SECRET = "qiA0xxtz96W5HllDE4AAXZfY4Ht6K31GXs0AEuohA0LoCgWKvfnpOlIr4EnFQSWf"
MPESA_SHORTCODE = "174379" 
MPESA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919" 

def get_mpesa_token():
    api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        r = requests.get(api_URL, auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
        return r.json()['access_token']
    except Exception as e:
        print(f"Error getting M-PESA token: {e}")
        return None

def initiate_stk_push(phone_number, amount, account_reference):
    access_token = get_mpesa_token()
    if not access_token: return False

    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = MPESA_SHORTCODE + MPESA_PASSKEY + timestamp
    password_b64 = base64.b64encode(password_str.encode()).decode('utf-8')

    formatted_phone = str(phone_number).strip()
    if formatted_phone.startswith('0'): formatted_phone = '254' + formatted_phone[1:]
    elif formatted_phone.startswith('+'): formatted_phone = formatted_phone[1:]

    test_amount = 1 

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password_b64,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": test_amount,
        "PartyA": formatted_phone, 
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": formatted_phone,
        "CallBackURL": "https://unknotty-edward-footed.ngrok-free.dev/", 
        "AccountReference": f"GMK-{account_reference}",
        "TransactionDesc": "GrandMark Logistics Freight Payment"
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        print("M-PESA Response:", response.json())
        return True
    except Exception as e:
        print(f"M-PESA Push Failed: {e}")
        return False
    
@app.before_request
def block_blacklisted_ips():
    client_ip = request.remote_addr
    if BlacklistedIP.query.filter_by(ip_address=client_ip).first():
        return "ERROR 403: Your IP address has been permanently blacklisted.", 403

# --- PUBLIC ROUTES ---
@app.route('/')
def home(): 
    return render_template('index.html')

@app.route('/catalog')
def catalog(): 
    available_products = Product.query.filter(Product.stock_quantity > 0).all()
    return render_template('catalog.html', products=available_products)

@app.route('/checkout')
def checkout(): 
    return render_template('checkout.html')

@app.route('/services')
def services(): 
    return render_template('services.html')

@app.route('/about')
def about(): 
    return render_template('about.html')

@app.route('/secret-seed-database-123')
def secret_seed():
    try:
        import os
        # This tells the server to run your seed file in the background
        os.system("python seed.py")
        return "<h1>✅ Database Seeded Successfully!</h1><p>Go check your catalog.</p>"
    except Exception as e:
        return f"<h1>❌ Error:</h1><p>{e}</p>"

# --- SUPPLIER PORTAL ROUTING ---
@app.route('/supplier_portal')
def supplier_portal():
    if session.get('supplier_logged_in'):
        all_products = Product.query.all()
        return render_template('supplier_dashboard.html', products=all_products, company=session.get('supplier_company'))
    return render_template('supplier_portal.html')

@app.route('/supplier/auth', methods=['POST'])
def supplier_auth():
    data = request.json
    action = data.get('action')
    email = data.get('email')

    if action == 'register':
        company = data.get('company_name')
        password = data.get('password')
        
        if Supplier.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists in network."}), 400
            
        otp_code = str(random.randint(100000, 999999))
        hashed_pw = generate_password_hash(password)
        new_supplier = Supplier(
            company_name=company, 
            email=email, 
            password_hash=hashed_pw,
            is_verified=False,
            verification_code=otp_code
        )
        db.session.add(new_supplier)
        db.session.commit()
        send_otp_email(email, otp_code)
        
        return jsonify({"message": "Verification email dispatched.", "status": "pending_verification"})

    elif action == 'verify':
        code_entered = data.get('code')
        user = Supplier.query.filter_by(email=email).first()
        
        if user and user.verification_code == code_entered:
            user.is_verified = True
            user.verification_code = None
            db.session.commit()
            return jsonify({"message": "Account verified successfully!"})
        else:
            return jsonify({"error": "Invalid or expired verification code."}), 400

    elif action == 'login':
        password = data.get('password')
        user = Supplier.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_verified:
                return jsonify({"error": "Account is locked. Please complete email verification."}), 403
            
            session['supplier_logged_in'] = True
            session['supplier_id'] = user.id
            session['supplier_email'] = user.email
            session['supplier_company'] = user.company_name
            return jsonify({"message": "Login successful!"})
            
        return jsonify({"error": "Invalid credentials."}), 401

@app.route('/api/restock/<int:product_id>', methods=['POST'])
def b2b_restock(product_id):
    if not session.get('supplier_logged_in'): 
        return jsonify({"error": "Unauthorized"}), 403
    
    qty = int(request.json.get('qty', 0))
    if qty <= 0: return jsonify({"error": "Invalid quantity"}), 400
    
    prod = Product.query.get(product_id)
    if prod:
        prod.stock_quantity += qty
        total_cost = prod.unit_cost * qty
        
        db.session.add(Ledger(transaction_type='Debit', amount=total_cost, description=f"Automated B2B Restock: {qty}x {prod.name} (Supplier: {session.get('supplier_company', 'Network Node')})"))
        db.session.commit()
        return jsonify({"message": f"Successfully shipped {qty} units! KES {total_cost:,.2f} has been billed to GrandMark."})
    return jsonify({"error": "Product not found"}), 404

# --- CLIENT PORTAL ---
@app.route('/client_portal')
def client_portal():
    if not session.get('client_logged_in'):
        return render_template('client_portal.html')
        
    client_email = session.get('client_email')
    
    if not client_email:
        session.clear()
        return redirect('/client_portal')

    client_orders = Inquiry.query.filter_by(contact_email=client_email).order_by(Inquiry.date_submitted.desc()).all()
    
    return render_template('client_dashboard.html', orders=client_orders) 

@app.route('/client/auth', methods=['POST'])
def client_auth():
    data = request.json
    action = data.get('action')
    email = data.get('email')

    if action == 'register':
        company = data.get('company_name')
        password = data.get('password')
        
        if Client.query.filter_by(email=email).first():
            return jsonify({"error": "Email already registered."}), 400
            
        otp_code = str(random.randint(100000, 999999))
        hashed_pw = generate_password_hash(password)
        new_client = Client(
            company_name=company, 
            email=email, 
            password_hash=hashed_pw,
            is_verified=False,
            verification_code=otp_code
        )
        db.session.add(new_client)
        db.session.commit()
        send_otp_email(email, otp_code)
        
        return jsonify({"message": "Verification email dispatched.", "status": "pending_verification"})

    elif action == 'verify':
        code_entered = data.get('code')
        user = Client.query.filter_by(email=email).first()
        
        if user and user.verification_code == code_entered:
            user.is_verified = True
            user.verification_code = None
            db.session.commit()
            return jsonify({"message": "Account verified successfully!"})
        else:
            return jsonify({"error": "Invalid or expired verification code."}), 400

    elif action == 'login':
        password = data.get('password')
        user = Client.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_verified:
                return jsonify({"error": "Account is locked. Please complete email verification."}), 403
            
            session['client_logged_in'] = True
            session['client_id'] = user.id
            session['client_email'] = user.email 
            return jsonify({"message": "Login successful!"})
            
        return jsonify({"error": "Invalid credentials."}), 401

# --- 2FA ADMIN AUTHENTICATION ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            session['pending_admin'] = user.username
            return redirect(url_for('verify_2fa'))
        return render_template('login.html', error='Invalid credentials.')
    return render_template('login.html')

@app.route('/2fa', methods=['GET', 'POST'])
def verify_2fa():
    if 'pending_admin' not in session: return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['pending_admin']).first()
    totp = pyotp.TOTP(user.totp_secret)
    
    uri = totp.provisioning_uri(name=user.username, issuer_name="GrandMark_Exec")
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(uri)}"

    if request.method == 'POST':
        otp_code = request.form.get('otp')
        if totp.verify(otp_code):
            session['logged_in'] = True
            session['username'] = user.username
            session.pop('pending_admin', None)
            return redirect(url_for('admin_dashboard'))
        return render_template('2fa.html', qr_url=qr_url, error="Invalid Authenticator Code. Try again.")

    return render_template('2fa.html', qr_url=qr_url)

# --- ADMIN DASHBOARD ---
@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    ledger_entries = Ledger.query.order_by(Ledger.timestamp.desc()).all()
    total_revenue = sum(l.amount for l in ledger_entries if l.transaction_type == 'Credit')
    total_expenses = sum(l.amount for l in ledger_entries if l.transaction_type == 'Debit')
    
    inventory_value = {}
    all_products = Product.query.all()
    for p in all_products:
        inventory_value[p.category] = inventory_value.get(p.category, 0) + (p.unit_cost * p.stock_quantity)

    all_inquiries = Inquiry.query.order_by(Inquiry.date_submitted.desc()).all()
    low_stock = [p for p in all_products if p.stock_quantity < 25]

    return render_template('admin.html', 
                           companies=Company.query.all(), products=all_products, 
                           inquiries=all_inquiries, logs=AuditLog.query.order_by(AuditLog.timestamp.desc()).all(), 
                           ledger=ledger_entries, total_revenue=total_revenue, 
                           total_expenses=total_expenses, current_balance=total_revenue - total_expenses,
                           inventory_value=inventory_value, blacklisted_ips=BlacklistedIP.query.all(),
                           low_stock_products=low_stock)

@app.route('/export/inventory')
def export_inventory():
    if not session.get('logged_in'): 
        return redirect(url_for('login'))
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['SKU Code', 'Product Name', 'Category', 'Unit Cost (KES)', 'Stock Quantity', 'Total Asset Value (KES)'])
    
    products = Product.query.all()
    for p in products:
        total_value = p.unit_cost * p.stock_quantity
        cw.writerow([p.sku, p.name, p.category, f"{p.unit_cost:.2f}", p.stock_quantity, f"{total_value:.2f}"])
    
    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=GrandMark_Live_Inventory.csv"}
    )

@app.route('/api/telemetry')
def get_telemetry(): 
    return jsonify({"cpu": psutil.cpu_percent(interval=0.1), "ram": psutil.virtual_memory().percent})

@app.route('/api/forex')
def get_forex():
    try: return jsonify({"usd_to_kes": requests.get('https://open.er-api.com/v6/latest/USD').json()['rates']['KES']})
    except: return jsonify({"usd_to_kes": "API Offline"})

@app.route('/api/submit_inquiry', methods=['POST'])
def submit_inquiry():
    data = request.json
    
    try:
        new_order = Inquiry(
            company_name=data.get('company_name'),
            contact_email=data.get('email'),
            inquiry_type=data.get('type'), 
            message=data.get('message'),
            status='Pending Approval'
        )
        
        db.session.add(new_order)
        db.session.commit()
        
        print(f"[+] NEW ORDER RECEIVED: {data.get('company_name')}")
        return jsonify({"message": "Order successfully submitted to the ledger."}), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to save order: {e}")
        db.session.rollback()
        return jsonify({"error": "Database rejection. Could not save order."}), 500

# --- THE COMPACT ENTERPRISE PDF ENGINE ---
def create_pdf(inq):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_auto_page_break(auto=True, margin=15) 
    
    COLOR_PRIMARY = (15, 23, 42)     
    COLOR_ACCENT = (56, 189, 248)    
    COLOR_TEXT = (51, 65, 85)        
    COLOR_MUTED = (148, 163, 184)    
    COLOR_LINE = (226, 232, 240)     
    
    pdf.set_fill_color(*COLOR_ACCENT)
    pdf.rect(0, 0, 210, 5, 'F') 
    
    logo_path = os.path.join(app.root_path, 'static', 'logo.png')
    if os.path.exists(logo_path):
        try: pdf.image(logo_path, x=10, y=12, h=14)
        except: pass 
        
    is_paid = 'Paid' in inq.status
    doc_title = "TAX INVOICE"
    
    pdf.set_y(15)
    pdf.set_font("Helvetica", 'B', 28)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 10, doc_title, ln=True, align='R')
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.cell(0, 5, f"Invoice No: GMK-{inq.id:04d}", ln=True, align='R')
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 5, f"Date Issued: {inq.date_submitted.strftime('%d %B %Y')}", ln=True, align='R')
    pdf.ln(5)
    
    pdf.set_y(40)
    if is_paid:
        pdf.set_fill_color(220, 252, 231) 
        pdf.set_text_color(22, 163, 74)   
        status_msg = "STATUS: PAID IN FULL - CLEARED FOR DISPATCH"
    else:
        pdf.set_fill_color(254, 226, 226) 
        pdf.set_text_color(220, 38, 38)   
        status_msg = "STATUS: PAYMENT DUE - AWAITING M-PESA CLEARANCE"
        
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(0, 8, f"  {status_msg}", ln=True, fill=True, align='C')
    pdf.ln(5)
    
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(100, 5, "FROM:", ln=False)
    pdf.cell(90, 5, "BILLED TO:", ln=True)
    
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.set_font("Helvetica", 'B', 11)
    
    start_y = pdf.get_y()
    pdf.set_xy(10, start_y)
    pdf.cell(100, 5, "GrandMark Logistics Ltd.")
    pdf.set_xy(110, start_y)
    pdf.cell(90, 5, inq.company_name)
    pdf.ln(5)
    
    pdf.set_text_color(*COLOR_TEXT)
    pdf.set_font("Helvetica", '', 10)
    
    start_y = pdf.get_y()
    pdf.set_xy(10, start_y)
    pdf.multi_cell(90, 5, "GrandMark Industrial Park\nNairobi, Kenya\nKRA PIN: P012345678Z")
    
    pdf.set_xy(110, start_y)
    pdf.multi_cell(90, 5, f"{inq.contact_email}\nClient ID: CLI-{inq.id:04d}")
    pdf.ln(8)
    
    items = []
    matches = re.finditer(r'(\d+)\s+units of\s+(.*?)\.', inq.message, re.IGNORECASE)
    for match in matches:
        qty = int(match.group(1))
        name = match.group(2).strip()
        db_prod = Product.query.filter_by(name=name).first()
        unit_price = db_prod.unit_cost if db_prod else 0.0
        line_total = qty * unit_price
        items.append({'qty': qty, 'name': name, 'unit_price': unit_price, 'line_total': line_total})
        
    amount_match = re.search(r'TOTAL AMOUNT DUE: KES ([\d,]+\.\d{2})', inq.message)
    grand_total = float(amount_match.group(1).replace(',', '')) if amount_match else sum(i['line_total'] for i in items)
        
    subtotal = grand_total / 1.16
    vat_amount = grand_total - subtotal
    
    if not items:
        items.append({'qty': 1, 'name': 'Standard Logistics Fulfillment', 'unit_price': grand_total, 'line_total': grand_total})
    
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", 'B', 9)
    
    pdf.cell(85, 7, "  ITEM DESCRIPTION", border=0, fill=True)
    pdf.cell(20, 7, "QTY", border=0, fill=True, align='C')
    pdf.cell(40, 7, "UNIT PRICE (KES)", border=0, fill=True, align='R')
    pdf.cell(45, 7, "LINE TOTAL (KES)", border=0, fill=True, align='R')
    pdf.ln(7)
    
    pdf.set_text_color(*COLOR_TEXT)
    pdf.set_font("Helvetica", '', 9)
    pdf.set_draw_color(*COLOR_LINE)
    pdf.set_line_width(0.2)
    
    for item in items:
        short_name = item['name'][:45] + "..." if len(item['name']) > 45 else item['name']
        
        pdf.cell(85, 7, f"  {short_name}", border='B')
        pdf.cell(20, 7, str(item['qty']), border='B', align='C')
        pdf.cell(40, 7, f"{item['unit_price']:,.2f}", border='B', align='R')
        
        pdf.set_font("Helvetica", 'B', 9)
        pdf.cell(45, 7, f"{item['line_total']:,.2f}  ", border='B', align='R')
        pdf.set_font("Helvetica", '', 9)
        pdf.ln(7)
        
    pdf.ln(4)
    pdf.set_x(110)
    pdf.set_font("Helvetica", '', 9)
    pdf.set_text_color(*COLOR_TEXT)
    
    pdf.cell(40, 6, "Subtotal (Excl. VAT):", align='R')
    pdf.cell(40, 6, f"KES {subtotal:,.2f}  ", align='R', ln=True)
    
    pdf.set_x(110)
    pdf.cell(40, 6, "VAT (16%):", align='R')
    pdf.cell(40, 6, f"KES {vat_amount:,.2f}  ", align='R', ln=True)
    pdf.ln(2)
    
    pdf.set_x(110)
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(40, 10, " GRAND TOTAL", fill=True, align='L')
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.cell(40, 10, f"KES {grand_total:,.2f}  ", fill=True, align='R', ln=True)
    
    pdf.set_y(-18) 
    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.set_font("Helvetica", 'B', 8)
    pdf.cell(0, 4, "Thank you for partnering with GrandMark Logistics.", ln=True, align='C')
    
    pdf.set_text_color(*COLOR_MUTED)
    pdf.set_font("Helvetica", '', 7)
    pdf.cell(0, 3, "This is a computer-generated tax document. No physical signature is required.", ln=True, align='C')
    pdf.cell(0, 3, "GrandMark Internal Systems 2026 | Automated Enterprise Software", ln=True, align='C')
    
    instance_dir = os.path.join(app.root_path, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    filepath = os.path.join(instance_dir, f"invoice_{inq.id}.pdf")
    pdf.output(filepath)
    return filepath

def send_otp_email(target_email, code):
    sender_email = "starfordomwocha2006@gmail.com" 
    app_password = "nibwjhqulfygakdx" 
    
    msg = MIMEMultipart()
    msg['Subject'] = 'GrandMark OS - Verify Your Account'
    msg['From'] = f"GrandMark Security <{sender_email}>"
    msg['To'] = target_email

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background: #0f172a; color: #fff; padding: 40px; text-align: center;">
        <h2 style="color: #38bdf8;">GrandMark OS Security</h2>
        <p style="color: #cbd5e1; font-size: 16px;">An account registration request was initiated with this email.</p>
        <p style="color: #cbd5e1; font-size: 16px;">Your unique verification code is:</p>
        <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 12px; margin: 20px auto; max-width: 200px; font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3);">
            {code}
        </div>
        <p style="color: #64748b; font-size: 12px;">If you did not request this, please ignore this email.</p>
      </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

@app.route('/api/financial_report')
def generate_financial_report():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    ledger_entries = Ledger.query.order_by(Ledger.timestamp.asc()).all()
    total_revenue = sum(l.amount for l in ledger_entries if l.transaction_type == 'Credit')
    total_expenses = sum(l.amount for l in ledger_entries if l.transaction_type == 'Debit')
    net_profit = total_revenue - total_expenses
    
    pdf = FPDF()
    pdf.add_page()
    
    primary = (37, 99, 235)
    dark_text = (15, 23, 42)
    gray_text = (100, 116, 139)
    
    pdf.set_fill_color(*primary)
    pdf.rect(0, 0, 210, 6, 'F')
    
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 24)
    pdf.set_text_color(*primary)
    pdf.cell(0, 10, "OFFICIAL FINANCIAL AUDIT", ln=True, align='C')
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(*gray_text)
    pdf.cell(0, 6, f"GrandMark Enterprise  |  Generated: {datetime.utcnow().strftime('%B %d, %Y')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*dark_text)
    pdf.cell(0, 10, "EXECUTIVE SUMMARY", ln=True)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(*gray_text)
    pdf.cell(80, 8, "Gross Revenue (Credits):", ln=False)
    pdf.set_text_color(*dark_text)
    pdf.cell(50, 8, f"KES {total_revenue:,.2f}", ln=True)
    
    pdf.set_text_color(*gray_text)
    pdf.cell(80, 8, "Operating Expenses (Debits):", ln=False)
    pdf.set_text_color(*dark_text)
    pdf.cell(50, 8, f"KES {total_expenses:,.2f}", ln=True)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(*gray_text)
    pdf.cell(80, 10, "Net Cashbook Balance:", ln=False)
    if net_profit >= 0:
        pdf.set_text_color(34, 197, 94)
    else:
        pdf.set_text_color(239, 68, 68)
    pdf.cell(50, 10, f"KES {net_profit:,.2f}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*dark_text)
    pdf.cell(0, 10, "DOUBLE-ENTRY LEDGER", ln=True)
    
    pdf.set_fill_color(*primary)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 8, "Date", border=1, fill=True)
    pdf.cell(85, 8, "Transaction Details", border=1, fill=True)
    pdf.cell(30, 8, "Debit (Out)", border=1, fill=True, align='R')
    pdf.cell(35, 8, "Credit (In)", border=1, fill=True, align='R')
    pdf.ln()
    
    pdf.set_text_color(*dark_text)
    pdf.set_font("Arial", '', 9)
    for l in ledger_entries:
        pdf.cell(40, 8, l.timestamp.strftime('%Y-%m-%d'), border=1)
        desc = l.description[:45] + "..." if len(l.description) > 45 else l.description
        pdf.cell(85, 8, desc, border=1)
        if l.transaction_type == 'Debit':
            pdf.cell(30, 8, f"{l.amount:,.2f}", border=1, align='R')
            pdf.cell(35, 8, "-", border=1, align='R')
        else:
            pdf.cell(30, 8, "-", border=1, align='R')
            pdf.cell(35, 8, f"{l.amount:,.2f}", border=1, align='R')
        pdf.ln()
        
    pdf.set_y(-25)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(*gray_text)
    pdf.cell(0, 5, "Automated Accounting Report by GrandMark Internal Systems.", ln=True, align='C')
    
    os.makedirs('instance', exist_ok=True)
    filepath = "instance/financial_report.pdf"
    pdf.output(filepath)
    return send_file(filepath, as_attachment=True)

def send_approval_email(recipient_email, company_name, pdf_path, inq_id, is_paid):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Official Document #GMK-00{inq_id} - GrandMark Logistics"
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        
        if is_paid:
            status_color = "#10b981"
            status_text = "Fully Paid & Dispatched"
            action_message = "Your payment has been successfully verified. Your cargo is now fully paid and has been marked for immediate dispatch."
            btn_text = "View Order History"
        else:
            status_color = "#f59e0b"
            status_text = "Action Required - Pending Payment"
            action_message = "To finalize dispatch, please log into your Client Gateway and clear the pending balance via our Safaricom M-PESA integration."
            btn_text = "Access Secure Portal (Pay via M-PESA)"
        
        html_body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f1f5f9; padding: 30px; margin: 0;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 12px; border-top: 6px solid #38bdf8; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
                <h1 style="color: #0f172a; margin-top: 0; font-size: 24px; letter-spacing: -0.5px;">GrandMark Distributors</h1>
                <p style="color: #475569; font-size: 16px; margin-bottom: 25px;">Hello <strong>{company_name}</strong>,</p>
                <p style="color: #475569; font-size: 16px; line-height: 1.6;">Your logistics request has been processed by our executive team. Please find your official documentation attached to this email.</p>
                
                <div style="background: #f8fafc; padding: 20px; border-left: 4px solid {status_color}; border-radius: 0 8px 8px 0; margin: 30px 0;">
                    <p style="margin: 0; color: #0f172a; font-weight: 800; font-size: 18px;">Order Reference: #GMK-00{inq_id}</p>
                    <p style="margin: 5px 0 0 0; color: #64748b; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Status: <strong style="color: {status_color};">{status_text}</strong></p>
                </div>
                
                <p style="color: #475569; font-size: 16px; line-height: 1.6;">{action_message}</p>
                
                <div style="text-align: center; margin: 35px 0;">
                    <a href="http://127.0.0.1:5000/client_portal" style="display: inline-block; padding: 14px 30px; background: #38bdf8; color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 10px rgba(56, 189, 248, 0.3);">{btn_text}</a>
                </div>
                
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0 20px 0;">
                <p style="color: #94a3b8; font-size: 12px; text-align: center; line-height: 1.5;">This is an automated transmission from the GrandMark Enterprise Server. Please do not reply directly to this email address.</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText("Please enable HTML to view this email.", 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header('Content-Disposition', 'attachment', filename=f"GrandMark_Document_00{inq_id}.pdf")
            msg.attach(attach)
            
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True, "Sent"
    except Exception as e:
        return False, str(e)

@app.route('/api/approve_inquiry/<int:inq_id>', methods=['POST'])
def approve_inquiry(inq_id):
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 403
    inq = Inquiry.query.get(inq_id)
    if inq:
        is_paid = 'Paid' in inq.status 
        pdf_path = create_pdf(inq)
        success, msg = send_approval_email(inq.contact_email, inq.company_name, pdf_path, inq.id, is_paid)
        
        if is_paid:
            matches = re.finditer(r'(\d+)\s+units of\s+(.*?)\.', inq.message, re.IGNORECASE)
            for match in matches:
                qty_ordered = int(match.group(1))
                product_name = match.group(2).strip()
                db_product = Product.query.filter_by(name=product_name).first()
                if db_product:
                    if db_product.stock_quantity >= qty_ordered:
                        db_product.stock_quantity -= qty_ordered
                    else:
                        db_product.stock_quantity = 0 
            inq.status = 'Paid & Dispatched'
        else:
            inq.status = 'Approved - Awaiting Payment'
            
        db.session.commit()
        
        if success:
            return jsonify({"message": "Pipeline Action Authorized & Inventory Deducted!"})
        else:
            return jsonify({"message": f"Pipeline Action Authorized! (Note: Email failed - {msg})"})
            
    return jsonify({"error": "Not found"}), 404

@app.route('/api/delete_inquiry/<int:inq_id>', methods=['DELETE'])
def delete_inquiry(inq_id):
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 403
    inq = Inquiry.query.get(inq_id)
    if inq:
        inq.status = 'Rejected' 
        db.session.commit()
    return jsonify({"message": "Order Rejected"})

@app.route('/api/mpesa_pay/<int:inq_id>', methods=['POST'])
def mpesa_pay(inq_id):
    # SIMULATOR VERSION - No Safaricom Daraja API needed
    inq = Inquiry.query.get(inq_id)
    
    if inq and ('Pending' in inq.status or 'Approved' in inq.status or 'Awaiting Payment' in inq.status):
        import random
        import string
        
        # Generate a fake M-PESA receipt code (e.g., QWE123RTY)
        fake_receipt = ''.join(random.choices(string.ascii_uppercase + string.digits, k=9))
        
        # Update the database
        inq.status = f'Paid (Ref: {fake_receipt})'
        db.session.commit()
        
        print(f"[+] SIMULATION: Order GMK-00{inq.id} marked as PAID. Ref: {fake_receipt}")
        return jsonify({"message": "Payment simulation successful!"}), 200
            
    return jsonify({"error": "Order not found or already processed."}), 404

@app.route('/api/mpesa_callback', methods=['POST'])
def mpesa_callback():
    data = request.json
    print("\n" + "="*50)
    print(" 📡 M-PESA SECURE CALLBACK RECEIVED ")
    print("="*50)
    
    try:
        result_code = data['Body']['stkCallback']['ResultCode']
        
        if result_code == 0:
            callback_metadata = data['Body']['stkCallback']['CallbackMetadata']['Item']
            amount = next(item['Value'] for item in callback_metadata if item['Name'] == 'Amount')
            receipt = next(item['Value'] for item in callback_metadata if item['Name'] == 'MpesaReceiptNumber')
            
            inq = Inquiry.query.filter_by(status='Processing M-PESA...').order_by(Inquiry.id.desc()).first()
            
            if inq:
                inq.status = f'Paid (Ref: {receipt})'
                new_ledger = Ledger(
                    transaction_type='Credit',
                    amount=float(amount),
                    description=f"M-PESA Auto-Settlement | Order GMK-00{inq.id} | Ref: {receipt}"
                )
                db.session.add(new_ledger)
                db.session.commit()
                print(f"[SUCCESS] Order GMK-00{inq.id} marked as PAID. Cashbook updated with KES {amount}.")
                
        else:
            result_desc = data['Body']['stkCallback']['ResultDesc']
            print(f"[FAILED] M-PESA Transaction Failed: {result_desc}")
            
            inq = Inquiry.query.filter_by(status='Processing M-PESA...').order_by(Inquiry.id.desc()).first()
            if inq:
                inq.status = 'Awaiting Payment (M-PESA Failed/Cancelled)'
                db.session.commit()
                
    except Exception as e:
        print(f"[ERROR] Callback Processing Error: {e}")

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

@app.route('/api/add_product', methods=['POST'])
def add_product():
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    unit_cost = float(data['unit_cost'])
    stock_qty = int(data['stock_quantity'])
    total_expense = unit_cost * stock_qty
    
    db.session.add(Product(name=data['name'], sku=data['sku'], category=data['category'], unit_cost=unit_cost, stock_quantity=stock_qty))
    db.session.add(Ledger(transaction_type='Debit', amount=total_expense, description=f"Warehouse Stock Purchase: {stock_qty}x {data['name']} (SKU: {data['sku']})"))
    
    qr_dir = os.path.join(app.root_path, 'static', 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)
    img = qrcode.make(f"SKU: {data['sku']}\nProduct: {data['name']}\nCost: KES {unit_cost}")
    img.save(os.path.join(qr_dir, f"{data['sku']}.png"))
    
    db.session.commit()
    return jsonify({"message": "Product successfully registered, Expense logged to Ledger, and QR Code generated!"})

@app.route('/api/delete_product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 403
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
    return jsonify({"message": "Product deleted"})

@app.route('/api/add_revenue', methods=['POST'])
def add_revenue():
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    db.session.add(Ledger(transaction_type='Credit', amount=data['amount'], description=data['description']))
    db.session.commit()
    return jsonify({"message": "Revenue logged!"})

@app.route('/api/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    
    if not user_message:
        return jsonify({"reply": "System ready. How can I assist you with GrandMark Logistics today?"})

    try:
        products = Product.query.all()
        if products:
            inventory_data = "\n".join([f"- {p.name}: {p.stock_quantity} units available at KES {p.unit_cost:,.2f} each" for p in products])
        else:
            inventory_data = "Warehouse is currently empty. We have NO products in stock."
    except Exception:
        inventory_data = "Inventory database currently syncing."

    strict_prompt = f"""
    You are the official AI Assistant for GrandMark Distributors, a premium B2B logistics company in Nairobi, Kenya.
    
    CRITICAL RULES:
    1. Keep answers brief, professional, and under 3 sentences.
    2. DO NOT use markdown formatting (no asterisks or bold text).
    3. Only quote products and prices from the LIVE INVENTORY DATA. If not listed, say: "We do not currently stock that item."
    4. Guide users to the correct website sections based on the PLATFORM SITE MAP below.
    5. Do not invent features or pages that are not listed below.
    
    --- PLATFORM SITE MAP & CAPABILITIES ---
    - Catalog Page: Public view of our available warehouse stock.
    - Order Portal: Where clients submit bulk restock orders. Our system automatically calculates pricing and math.
    - Client Gateway: Secure portal where clients view approved orders and pay instantly via our Safaricom M-PESA STK Push integration.
    - Supplier Portal: Where global partners and manufacturers can apply to supply our warehouse.
    - Admin Dashboard: The executive console (protected by Google Authenticator 2FA) where admins authorize orders, dispatch cargo, monitor live telemetry, view the double-entry financial ledger, and generate PDF audits.
    - Automated Features: Our system autonomously generates PDF receipts, sends HTML emails, and warns admins when stock drops below 25 units.
    
    --- LIVE INVENTORY DATA ---
    {inventory_data}
    ---------------------------
    
    USER MESSAGE: {user_message}
    """
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=strict_prompt
        )
        return jsonify({"reply": response.text.strip()})
    except Exception as e:
        return jsonify({"reply": "My neural network is currently offline. Please contact the GrandMark Executive Team."})

# --- INTELLIGENT SYSTEM LOGOUT ROUTE ---
@app.route('/logout')
def logout():
    if session.get('client_logged_in'):
        session.clear() 
        return redirect('/client_portal') 
        
    elif session.get('supplier_logged_in'):
        session.clear() 
        return redirect('/supplier_portal') 
        
    else:
        session.clear()
        return redirect('/')

# --- SERVER STARTUP ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)