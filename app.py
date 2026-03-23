from flask import Flask, render_template, jsonify, request, session, redirect, url_for, Response, send_file, has_request_context
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import LegacyAPIWarning
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from fpdf import FPDF
from flasgger import Swagger
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from requests.auth import HTTPBasicAuth
from functools import wraps
import smtplib
import random
import string
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
import logging
import sys
import warnings

warnings.filterwarnings("ignore", category=LegacyAPIWarning)

# Lazy init so AI dependency issues never block core app routes (email, payments, admin).
ai_client = None

def get_ai_client():
    global ai_client
    if ai_client is not None:
        return ai_client

    api_key = (os.environ.get('GEMINI_API_KEY') or '').strip()
    if not api_key:
        return None

    try:
        ai_client = genai.Client(api_key=api_key)
        return ai_client
    except Exception:
        return None

app = Flask(__name__)
app.secret_key = 'super_secret_grandmark_key_123'

if not app.logger.handlers:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
    app.logger.addHandler(stream_handler)
app.logger.setLevel(logging.INFO)

# --- CLOUD DATABASE CONFIGURATION (RENDER + SQLITE FALLBACK) ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///grandmark.db')

# SQLAlchemy requires 'postgresql://' but Render sometimes gives 'postgres://'. This fixes that bug automatically.
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
swagger = Swagger(app)

SENDER_EMAIL = (
    os.environ.get('MAIL_USERNAME')
    or os.environ.get('SENDER_EMAIL')
    or ''
).strip()
SENDER_PASSWORD = (
    os.environ.get('MAIL_PASSWORD')
    or os.environ.get('MAIL_APP_PASSWORD')
    or os.environ.get('SENDER_PASSWORD')
    or ''
).strip()
MAIL_FROM_NAME = os.environ.get('MAIL_FROM_NAME', 'GrandMark Distributors').strip()
SMTP_HOST = (os.environ.get('SMTP_HOST') or os.environ.get('MAIL_SERVER') or 'smtp.zoho.com').strip()
SMTP_PORT = int(os.environ.get('SMTP_PORT') or os.environ.get('MAIL_PORT') or '465')
SMTP_USE_SSL = (
    os.environ.get('SMTP_USE_SSL')
    or os.environ.get('MAIL_USE_SSL')
    or 'true'
).strip().lower() in ['1', 'true', 'yes', 'on']

SMS_FALLBACK_WEBHOOK_URL = os.environ.get('SMS_FALLBACK_WEBHOOK_URL', '').strip()
WHATSAPP_FALLBACK_WEBHOOK_URL = os.environ.get('WHATSAPP_FALLBACK_WEBHOOK_URL', '').strip()

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
    buying_price = db.Column(db.Float, nullable=False, default=0.0) # <-- NEW: What GrandMark pays
    unit_cost = db.Column(db.Float, nullable=False) # <-- EXISTING: What the Client pays (Selling Price)
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

class CreditNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False)
    reference = db.Column(db.String(40), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    restock_inventory = db.Column(db.Boolean, default=False)
    issued_by = db.Column(db.String(50), default='System Admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CreditNoteEmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    credit_note_id = db.Column(db.Integer, db.ForeignKey('credit_note.id'), nullable=False)
    recipient = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='sent')  # sent or failed
    channel = db.Column(db.String(20), nullable=False, default='email')
    message = db.Column(db.String(255), nullable=True)
    sent_by = db.Column(db.String(50), default='System Admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AccountControl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_key = db.Column(db.String(160), unique=True, nullable=False)
    account_type = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    is_blocked = db.Column(db.Boolean, default=False)
    reason = db.Column(db.String(150), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AdminRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(30), nullable=False, default='Super Admin')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InquiryWorkflowEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False)
    from_status = db.Column(db.String(80), nullable=False)
    to_status = db.Column(db.String(80), nullable=False)
    actor = db.Column(db.String(50), default='System Admin')
    note = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class PaymentReminderLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False)
    stage = db.Column(db.String(10), nullable=False)  # 24h or 48h
    sent_to = db.Column(db.String(100), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_by = db.Column(db.String(50), default='System Automation')
    __table_args__ = (
        db.UniqueConstraint('inquiry_id', 'stage', name='uq_payment_reminder_inquiry_stage'),
    )

class ClientCreditControl(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_email = db.Column(db.String(100), unique=True, nullable=False)
    credit_limit = db.Column(db.Float, default=0.0)
    outstanding_balance = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ReturnRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(100), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(40), default='Pending')
    requested_amount = db.Column(db.Float, default=0.0)
    approved_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NotificationTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    channel = db.Column(db.String(20), default='email')
    subject = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DocumentRegistry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doc_type = db.Column(db.String(40), nullable=False)
    reference = db.Column(db.String(80), nullable=False)
    inquiry_id = db.Column(db.Integer, nullable=True)
    path = db.Column(db.String(255), nullable=False)
    created_by = db.Column(db.String(50), default='System Admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InventoryPolicy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), unique=True, nullable=False)
    reorder_point = db.Column(db.Integer, default=25)
    reorder_qty = db.Column(db.Integer, default=100)
    lead_time_days = db.Column(db.Integer, default=7)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DispatchTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False)
    driver_name = db.Column(db.String(80), nullable=False)
    vehicle_plate = db.Column(db.String(20), nullable=False)
    route = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(40), default='Assigned')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
        db.session.add(Ledger(transaction_type='Credit', amount=300000000.00, description='Initial Business Capital (KES)'))
        db.session.commit()
    if not AdminRole.query.filter_by(username='admin').first():
        db.session.add(AdminRole(username='admin', role='Super Admin'))
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

def parse_order_items_from_message(message):
    items = []
    if not message:
        return items

    matches = re.finditer(r'(\d+)\s+units of\s+(.*?)\.', message, re.IGNORECASE)
    for match in matches:
        qty = int(match.group(1))
        name = match.group(2).strip()
        items.append({'qty': qty, 'name': name})
    return items

def extract_order_total(inquiry):
    amount_match = re.search(r'TOTAL AMOUNT DUE: KES ([\d,]+\.\d{2})', inquiry.message or '')
    if amount_match:
        return float(amount_match.group(1).replace(',', ''))

    total = 0.0
    for item in parse_order_items_from_message(inquiry.message):
        db_prod = Product.query.filter_by(name=item['name']).first()
        if db_prod:
            total += item['qty'] * db_prod.unit_cost
    return total

def get_payment_details_from_status(status):
    raw_status = (status or '').strip()
    status_upper = raw_status.upper()

    payment_method = 'Online Payment'
    if 'M-PESA' in status_upper or 'MPESA' in status_upper:
        payment_method = 'M-PESA'
    elif 'CARD' in status_upper:
        payment_method = 'Card'
    elif 'WALLET' in status_upper:
        payment_method = 'Wallet'
    elif 'BANK' in status_upper:
        payment_method = 'Bank Transfer'

    reference_match = re.search(r'REF:\s*([A-Za-z0-9-]+)', raw_status, re.IGNORECASE)
    reference = reference_match.group(1) if reference_match else ''
    return payment_method, reference

def split_email_list(value):
    raw = (value or '').replace(';', ',')
    return [x.strip() for x in raw.split(',') if x.strip()]

def build_credit_note_email_tracking(note_ids):
    if not note_ids:
        return {}

    rows = CreditNoteEmailLog.query.filter(
        CreditNoteEmailLog.credit_note_id.in_(note_ids)
    ).order_by(CreditNoteEmailLog.created_at.desc()).all()

    latest = {}
    attempts = {}
    for row in rows:
        attempts[row.credit_note_id] = attempts.get(row.credit_note_id, 0) + 1
        if row.credit_note_id not in latest:
            latest[row.credit_note_id] = row

    return {
        note_id: {
            'email_status': latest[note_id].status,
            'email_last_message': latest[note_id].message or '',
            'email_last_sent_at': latest[note_id].created_at,
            'email_attempts': attempts.get(note_id, 0)
        }
        for note_id in latest.keys()
    }

def record_credit_note_email_attempt(credit_note_id, recipient, status, message, channel='email'):
    db.session.add(CreditNoteEmailLog(
        credit_note_id=credit_note_id,
        recipient=recipient or '-',
        status='sent' if status == 'sent' else 'failed',
        channel=channel,
        message=(message or '')[:250],
        sent_by=session.get('username', 'System Admin')
    ))

def is_account_blocked(account_type, email):
    key = f"{account_type}:{(email or '').strip().lower()}"
    rule = AccountControl.query.filter_by(account_key=key).first()
    return bool(rule and rule.is_blocked)

def build_account_key(account_type, email):
    return f"{account_type}:{(email or '').strip().lower()}"

def get_current_admin_role():
    username = session.get('username')
    if not username:
        return 'Viewer'
    role_row = AdminRole.query.filter_by(username=username).first()
    return role_row.role if role_row else 'Viewer'

def has_permission(permission):
    role = get_current_admin_role()
    role_map = {
        'Super Admin': {'finance', 'operations', 'inventory', 'support', 'security', 'reports'},
        'Finance': {'finance', 'reports'},
        'Operations': {'operations', 'inventory'},
        'Inventory': {'inventory'},
        'Support': {'support'},
        'Viewer': set()
    }
    return permission in role_map.get(role, set())

def ui_permissions_for_current_admin():
    return {
        'finance': has_permission('finance'),
        'operations': has_permission('operations'),
        'inventory': has_permission('inventory'),
        'support': has_permission('support'),
        'security': has_permission('security'),
        'reports': has_permission('reports')
    }

def require_permission(permission):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get('logged_in'):
                return jsonify({"error": "Unauthorized"}), 403
            if not has_permission(permission):
                return jsonify({"error": f"Forbidden. {permission.title()} permission required."}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def log_admin_action(action_text):
    db.session.add(AuditLog(
        action=action_text,
        user=session.get('username', 'System Admin')
    ))

def register_document(doc_type, reference, path, inquiry_id=None):
    db.session.add(DocumentRegistry(
        doc_type=doc_type,
        reference=reference,
        inquiry_id=inquiry_id,
        path=path,
        created_by=session.get('username', 'System Admin')
    ))

def build_admin_experience_snapshot():
    income = sum(l.amount for l in Ledger.query.filter_by(transaction_type='Credit').all())
    expense = sum(l.amount for l in Ledger.query.filter_by(transaction_type='Debit').all())
    net = income - expense

    all_inquiries = Inquiry.query.all()
    unpaid_orders = []
    client_totals = {}
    for inq in all_inquiries:
        total = extract_order_total(inq)
        status_txt = (inq.status or '').lower()
        if any(k in status_txt for k in ['pending', 'awaiting payment', 'approved']) and 'paid' not in status_txt:
            unpaid_orders.append({
                'id': inq.id,
                'company': inq.company_name,
                'email': inq.contact_email,
                'status': inq.status,
                'total': round(total, 2)
            })
        if 'paid' in status_txt or 'delivered' in status_txt:
            key = (inq.company_name or 'Unknown').strip() or 'Unknown'
            client_totals[key] = client_totals.get(key, 0.0) + total

    top_clients = [
        {'company': k, 'revenue': round(v, 2)}
        for k, v in sorted(client_totals.items(), key=lambda kv: kv[1], reverse=True)[:8]
    ]

    low_stock = [p for p in Product.query.all() if p.stock_quantity < 25]
    low_stock_sorted = sorted(low_stock, key=lambda p: p.stock_quantity)

    suppliers = Supplier.query.all()
    supplier_rows = []
    for s in suppliers:
        linked_orders = Inquiry.query.filter_by(contact_email=s.email).count()
        supplier_rows.append({
            'company': s.company_name,
            'email': s.email,
            'engagement': linked_orders,
            'status': 'Blocked' if is_account_blocked('supplier', s.email) else 'Active'
        })
    supplier_rows.sort(key=lambda x: x['engagement'], reverse=True)

    credit_notes = CreditNote.query.order_by(CreditNote.created_at.desc()).all()
    avg_credit = (sum(c.amount for c in credit_notes) / len(credit_notes)) if credit_notes else 0.0
    suspicious_credit = [
        {
            'reference': c.reference,
            'amount': round(c.amount, 2),
            'reason': c.reason,
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M')
        }
        for c in credit_notes
        if c.amount >= max(500000.0, avg_credit * 2)
    ][:8]

    blocked_clients = AccountControl.query.filter_by(account_type='client', is_blocked=True).count()
    blocked_suppliers = AccountControl.query.filter_by(account_type='supplier', is_blocked=True).count()
    pending_rma = ReturnRequest.query.filter_by(status='Pending').count()
    high_value_unpaid = len([o for o in unpaid_orders if o['total'] >= 150000])
    risk_score = min(100, (len(suspicious_credit) * 18) + (pending_rma * 7) + (high_value_unpaid * 10))

    return {
        'kpis': {
            'income': round(income, 2),
            'expense': round(expense, 2),
            'net': round(net, 2),
            'unpaid_orders': len(unpaid_orders),
            'high_value_unpaid': high_value_unpaid,
            'low_stock_count': len(low_stock),
            'blocked_accounts': blocked_clients + blocked_suppliers,
            'risk_score': risk_score
        },
        'top_clients': top_clients,
        'supplier_rows': supplier_rows[:8],
        'fraud_signals': {
            'suspicious_credit_notes': suspicious_credit,
            'pending_rma': pending_rma,
            'blocked_clients': blocked_clients,
            'blocked_suppliers': blocked_suppliers
        },
        'action_feeds': {
            'high_value_unpaid': sorted(unpaid_orders, key=lambda x: x['total'], reverse=True)[:8],
            'stockout_risks': [
                {
                    'name': p.name,
                    'sku': p.sku,
                    'stock': p.stock_quantity,
                    'category': p.category
                }
                for p in low_stock_sorted[:8]
            ]
        }
    }

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

@app.route('/testimonials')
def testimonials():
    return render_template('testimonials.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/track')
def track():
    return render_template('track.html')

@app.route('/api/track/<int:order_id>')
def api_track_order(order_id):
    inq = Inquiry.query.get(order_id)
    if not inq:
        return jsonify({'error': 'Order not found. Please check the ID and try again.'}), 404

    status = inq.status
    steps = ['Submitted', 'Under Review', 'Approved', 'Paid', 'Dispatched']
    current_step = 0
    if 'Pending' in status:
        current_step = 1
    elif 'Approved' in status or 'Awaiting Payment' in status:
        current_step = 2
    elif 'Paid' in status:
        current_step = 3
    elif 'Dispatched' in status or 'Completed' in status:
        current_step = 4

    return jsonify({
        'id': inq.id,
        'company_name': inq.company_name,
        'contact_email': inq.contact_email,
        'inquiry_type': inq.inquiry_type,
        'message': inq.message,
        'status': inq.status,
        'date_submitted': inq.date_submitted.strftime('%Y-%m-%d %H:%M'),
        'current_step': current_step,
        'steps': steps
    })

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
            
        hashed_pw = generate_password_hash(password)
        new_supplier = Supplier(
            company_name=company, 
            email=email, 
            password_hash=hashed_pw,
            is_verified=True, # <--- INSTANTLY VERIFIED
            verification_code=None
        )
        db.session.add(new_supplier)
        db.session.commit()
        
        return jsonify({"message": "Registration successful! You can now log in.", "status": "success"})

    elif action == 'login':
        password = data.get('password')
        user = Supplier.query.filter_by(email=email).first()

        if is_account_blocked('supplier', email):
            return jsonify({"error": "Access denied. Supplier account is blocked by admin."}), 403

        if user and check_password_hash(user.password_hash, password):
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

@app.route('/client/payment/<int:inq_id>')
def client_payment_page(inq_id):
    if not session.get('client_logged_in'):
        return redirect('/client_portal')

    client_email = (session.get('client_email') or '').strip().lower()
    if not client_email:
        session.clear()
        return redirect('/client_portal')

    inq = Inquiry.query.get(inq_id)
    if not inq:
        return redirect('/client_portal')

    if (inq.contact_email or '').strip().lower() != client_email:
        return jsonify({'error': 'Access denied for this order.'}), 403

    amount_due = extract_order_total(inq)
    payable = ('Approved' in (inq.status or '')) or ('Awaiting Payment' in (inq.status or ''))

    return render_template(
        'client_payment.html',
        order=inq,
        amount_due=amount_due,
        payable=payable
    )

@app.route('/api/client/payment/<int:inq_id>', methods=['POST'])
def process_client_payment(inq_id):
    if not session.get('client_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 403

    client_email = (session.get('client_email') or '').strip().lower()
    inq = Inquiry.query.get(inq_id)
    if not inq:
        return jsonify({'error': 'Order not found.'}), 404

    if (inq.contact_email or '').strip().lower() != client_email:
        return jsonify({'error': 'Access denied for this order.'}), 403

    status = (inq.status or '')
    if 'Paid' in status:
        return jsonify({'message': 'Order is already marked as paid.'}), 200

    if not (('Approved' in status) or ('Awaiting Payment' in status)):
        return jsonify({'error': 'This order is not currently payable.'}), 400

    data = request.get_json(silent=True) or {}
    method = (data.get('method') or '').strip().lower()
    valid_methods = {'mpesa', 'card', 'wallet', 'bank_transfer'}
    if method not in valid_methods:
        return jsonify({'error': 'Invalid payment method.'}), 400

    previous_status = inq.status
    amount = extract_order_total(inq)
    reference = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    if method == 'bank_transfer':
        inq.status = f"Payment Submitted - Awaiting Verification (Bank Ref: {reference})"
        db.session.commit()
        notify_inquiry_status_change(inq, previous_status, note=f"Client submitted bank transfer reference {reference}.")
        return jsonify({
            'message': 'Bank transfer submitted for verification.',
            'status': inq.status,
            'reference': reference
        })

    method_label = {
        'mpesa': 'M-PESA',
        'card': 'CARD',
        'wallet': 'WALLET'
    }[method]
    inq.status = f"Paid ({method_label} Ref: {reference})"

    if amount > 0:
        db.session.add(Ledger(
            transaction_type='Credit',
            amount=amount,
            description=f"{method_label} Settlement | Order GMK-00{inq.id} | Ref: {reference}"
        ))

        credit_control = ClientCreditControl.query.filter_by(
            client_email=(inq.contact_email or '').strip().lower(),
            is_active=True
        ).first()
        if credit_control:
            credit_control.outstanding_balance = max(0.0, credit_control.outstanding_balance - amount)

    db.session.commit()
    notify_inquiry_status_change(inq, previous_status, note=f"Payment completed via {method_label}. Ref: {reference}")

    return jsonify({
        'message': f'Payment successful via {method_label}.',
        'status': inq.status,
        'reference': reference
    })

@app.route('/api/admin/payment/bank_transfer/pending')
@require_permission('finance')
def list_pending_bank_transfer_payments():
    pending = Inquiry.query.filter(
        Inquiry.status.ilike('Payment Submitted - Awaiting Verification%')
    ).order_by(Inquiry.date_submitted.desc()).all()

    rows = []
    for inq in pending:
        _, bank_ref = get_payment_details_from_status(inq.status)
        rows.append({
            'inquiry_id': inq.id,
            'company_name': inq.company_name,
            'contact_email': inq.contact_email,
            'status': inq.status,
            'bank_reference': bank_ref or '-',
            'amount_due': round(extract_order_total(inq), 2),
            'submitted_at': inq.date_submitted.strftime('%Y-%m-%d %H:%M')
        })

    return jsonify({'count': len(rows), 'rows': rows})

@app.route('/api/admin/payment/bank_transfer/verify/<int:inq_id>', methods=['POST'])
@require_permission('finance')
def verify_bank_transfer_payment(inq_id):
    inq = Inquiry.query.get(inq_id)
    if not inq:
        return jsonify({'error': 'Order not found.'}), 404

    status = (inq.status or '')
    if 'Payment Submitted - Awaiting Verification' not in status:
        return jsonify({'error': 'This order is not awaiting bank-transfer verification.'}), 400

    data = request.get_json(silent=True) or {}
    decision = (data.get('decision') or '').strip().lower()
    note = (data.get('note') or '').strip()
    if decision not in ['approve', 'reject']:
        return jsonify({'error': 'Decision must be approve or reject.'}), 400

    previous_status = inq.status
    _, bank_ref = get_payment_details_from_status(status)
    amount = extract_order_total(inq)

    if decision == 'approve':
        final_ref = bank_ref or ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        inq.status = f'Paid (Bank Transfer Ref: {final_ref})'
        if amount > 0:
            db.session.add(Ledger(
                transaction_type='Credit',
                amount=amount,
                description=f"BANK TRANSFER Settlement | Order GMK-00{inq.id} | Ref: {final_ref}"
            ))

            credit_control = ClientCreditControl.query.filter_by(
                client_email=(inq.contact_email or '').strip().lower(),
                is_active=True
            ).first()
            if credit_control:
                credit_control.outstanding_balance = max(0.0, credit_control.outstanding_balance - amount)

        log_admin_action(f"Bank transfer approved for GMK-00{inq.id} ({final_ref})")
        db.session.commit()
        notify_inquiry_status_change(
            inq,
            previous_status,
            note=note or f"Bank transfer verified by finance. Ref: {final_ref}"
        )
        return jsonify({'message': 'Bank transfer approved and payment posted.', 'status': inq.status})

    # reject
    inq.status = 'Bank Transfer Rejected - Awaiting New Payment'
    log_admin_action(f"Bank transfer rejected for GMK-00{inq.id}")
    db.session.commit()
    notify_inquiry_status_change(
        inq,
        previous_status,
        note=note or 'Submitted bank transfer was rejected. Please resubmit payment.'
    )
    return jsonify({'message': 'Bank transfer rejected.', 'status': inq.status})

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
            
        hashed_pw = generate_password_hash(password)
        new_client = Client(
            company_name=company, 
            email=email, 
            password_hash=hashed_pw,
            is_verified=True, # <--- INSTANTLY VERIFIED
            verification_code=None
        )
        db.session.add(new_client)
        db.session.commit()
        
        return jsonify({"message": "Registration successful! You can now log in.", "status": "success"})

    elif action == 'login':
        password = data.get('password')
        user = Client.query.filter_by(email=email).first()

        if is_account_blocked('client', email):
            return jsonify({"error": "Access denied. Client account is blocked by admin."}), 403
        
        if user and check_password_hash(user.password_hash, password):
            # We removed the 'is_verified' check here because everyone is verified instantly
            session['client_logged_in'] = True
            session['client_id'] = user.id
            session['client_email'] = user.email 
            return jsonify({"message": "Login successful!"})
            
        return jsonify({"error": "Invalid credentials."}), 401
            
        # Normal creation for brand new emails
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
            role_row = AdminRole.query.filter_by(username=user.username).first()
            session['admin_role'] = role_row.role if role_row else 'Viewer'
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

    base_inquiry_query = Inquiry.query
    search = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip()
    inquiry_type = (request.args.get('type') or '').strip()
    company = (request.args.get('company') or '').strip()
    contact_email = (request.args.get('email') or '').strip()
    from_date = (request.args.get('from_date') or '').strip()
    to_date = (request.args.get('to_date') or '').strip()

    if search:
        like_term = f"%{search}%"
        base_inquiry_query = base_inquiry_query.filter(
            db.or_(
                Inquiry.company_name.ilike(like_term),
                Inquiry.contact_email.ilike(like_term),
                Inquiry.message.ilike(like_term),
                Inquiry.status.ilike(like_term)
            )
        )

    if status:
        base_inquiry_query = base_inquiry_query.filter(Inquiry.status == status)

    if inquiry_type:
        base_inquiry_query = base_inquiry_query.filter(Inquiry.inquiry_type == inquiry_type)

    if company:
        base_inquiry_query = base_inquiry_query.filter(Inquiry.company_name.ilike(f"%{company}%"))

    if contact_email:
        base_inquiry_query = base_inquiry_query.filter(Inquiry.contact_email.ilike(f"%{contact_email}%"))

    if from_date:
        try:
            dt_from = datetime.strptime(from_date, '%Y-%m-%d')
            base_inquiry_query = base_inquiry_query.filter(Inquiry.date_submitted >= dt_from)
        except ValueError:
            from_date = ''

    if to_date:
        try:
            dt_to = datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            base_inquiry_query = base_inquiry_query.filter(Inquiry.date_submitted <= dt_to)
        except ValueError:
            to_date = ''

    all_inquiries = base_inquiry_query.order_by(Inquiry.date_submitted.desc()).all()
    low_stock = [p for p in all_products if p.stock_quantity < 25]

    inquiry_status_options = [
        row[0] for row in db.session.query(Inquiry.status).distinct().order_by(Inquiry.status).all() if row[0]
    ]
    inquiry_type_options = [
        row[0] for row in db.session.query(Inquiry.inquiry_type).distinct().order_by(Inquiry.inquiry_type).all() if row[0]
    ]

    credit_notes = CreditNote.query.order_by(CreditNote.created_at.desc()).limit(20).all()

    blocked_account_keys = {
        c.account_key for c in AccountControl.query.filter_by(is_blocked=True).all()
    }

    return render_template('admin.html', 
                           companies=Company.query.all(), products=all_products, 
                           inquiries=all_inquiries, logs=AuditLog.query.order_by(AuditLog.timestamp.desc()).all(), 
                           ledger=ledger_entries, total_revenue=total_revenue, 
                           total_expenses=total_expenses, current_balance=total_revenue - total_expenses,
                           inventory_value=inventory_value, blacklisted_ips=BlacklistedIP.query.all(),
                           low_stock_products=low_stock,
                           clients=Client.query.order_by(Client.id.desc()).all(),
                           suppliers=Supplier.query.order_by(Supplier.id.desc()).all(),
                           account_controls=AccountControl.query.all(),
                           blocked_account_keys=blocked_account_keys,
                           credit_notes=credit_notes,
                           inquiry_filters={
                               'q': search,
                               'status': status,
                               'type': inquiry_type,
                               'company': company,
                               'email': contact_email,
                               'from_date': from_date,
                               'to_date': to_date
                           },
                           inquiry_status_options=inquiry_status_options,
                           inquiry_type_options=inquiry_type_options,
                           admin_role=session.get('admin_role', get_current_admin_role()),
                           ui_permissions=ui_permissions_for_current_admin())

@app.route('/admin/credit_notes')
def admin_credit_notes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not (has_permission('finance') or has_permission('reports')):
        return "Forbidden", 403

    filtered_notes, filters = get_filtered_credit_notes(request.args)

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_total = sum(n.amount for n in CreditNote.query.filter(CreditNote.created_at >= month_start).all())
    total_credited = sum(n['amount'] for n in filtered_notes)

    trend_map = {}
    for n in filtered_notes:
        day_key = n['created_at'].strftime('%Y-%m-%d')
        trend_map[day_key] = trend_map.get(day_key, 0.0) + n['amount']

    chart_labels = sorted(trend_map.keys())
    chart_values = [round(trend_map[d], 2) for d in chart_labels]

    method_totals = {}
    method_counts = {}
    paid_inquiries = Inquiry.query.filter(Inquiry.status.ilike('%paid%')).all()
    for inq in paid_inquiries:
        method, _ = get_payment_details_from_status(inq.status)
        method_totals[method] = method_totals.get(method, 0.0) + extract_order_total(inq)
        method_counts[method] = method_counts.get(method, 0) + 1

    method_labels = sorted(method_totals.keys())
    method_values = [round(method_totals[k], 2) for k in method_labels]
    method_count_values = [method_counts[k] for k in method_labels]
    pending_bank_verifications = Inquiry.query.filter(
        Inquiry.status.ilike('Payment Submitted - Awaiting Verification%')
    ).count()

    return render_template(
        'credit_notes.html',
        credit_notes=filtered_notes,
        total_credited=total_credited,
        month_total=month_total,
        total_count=len(filtered_notes),
        filters=filters,
        chart_labels=chart_labels,
        chart_values=chart_values,
        method_labels=method_labels,
        method_values=method_values,
        method_count_values=method_count_values,
        pending_bank_verifications=pending_bank_verifications,
        export_query=request.query_string.decode('utf-8'),
        admin_role=session.get('admin_role', get_current_admin_role()),
        ui_permissions=ui_permissions_for_current_admin()
    )

def get_filtered_credit_notes(args):
    query = CreditNote.query.order_by(CreditNote.created_at.desc())

    reference = (args.get('reference') or '').strip()
    company = (args.get('company') or '').strip().lower()
    from_date = (args.get('from_date') or '').strip()
    to_date = (args.get('to_date') or '').strip()
    range_key = (args.get('range') or '').strip().lower()

    if range_key and not from_date and not to_date:
        now = datetime.utcnow()
        if range_key == '7d':
            from_date = (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)).strftime('%Y-%m-%d')
            to_date = now.strftime('%Y-%m-%d')
        elif range_key == '30d':
            from_date = (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=29)).strftime('%Y-%m-%d')
            to_date = now.strftime('%Y-%m-%d')
        elif range_key == 'ytd':
            from_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d')
            to_date = now.strftime('%Y-%m-%d')
        else:
            range_key = ''

    if reference:
        query = query.filter(CreditNote.reference.ilike(f"%{reference}%"))

    if from_date:
        try:
            dt_from = datetime.strptime(from_date, '%Y-%m-%d')
            query = query.filter(CreditNote.created_at >= dt_from)
        except ValueError:
            pass

    if to_date:
        try:
            dt_to = datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(CreditNote.created_at <= dt_to)
        except ValueError:
            pass

    notes = query.all()
    inquiry_map = {inq.id: inq for inq in Inquiry.query.filter(Inquiry.id.in_([n.inquiry_id for n in notes])).all()} if notes else {}
    tracking_map = build_credit_note_email_tracking([n.id for n in notes])

    filtered_notes = []
    for note in notes:
        inq = inquiry_map.get(note.inquiry_id)
        if company and (not inq or company not in (inq.company_name or '').lower()):
            continue
        filtered_notes.append({
            'id': note.id,
            'reference': note.reference,
            'amount': note.amount,
            'reason': note.reason,
            'restock_inventory': note.restock_inventory,
            'issued_by': note.issued_by,
            'created_at': note.created_at,
            'inquiry_id': note.inquiry_id,
            'company_name': inq.company_name if inq else 'Unknown Company',
            'contact_email': inq.contact_email if inq else '-',
            'email_status': tracking_map.get(note.id, {}).get('email_status', 'unknown'),
            'email_last_message': tracking_map.get(note.id, {}).get('email_last_message', ''),
            'email_last_sent_at': tracking_map.get(note.id, {}).get('email_last_sent_at'),
            'email_attempts': tracking_map.get(note.id, {}).get('email_attempts', 0)
        })

    return filtered_notes, {
        'reference': reference,
        'company': company,
        'from_date': from_date,
        'to_date': to_date,
        'range': range_key
    }

@app.route('/admin/credit_notes/export.csv')
def export_credit_notes_csv():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not has_permission('reports'):
        return "Forbidden", 403

    filtered_notes, _ = get_filtered_credit_notes(request.args)

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow([
        'Reference', 'Order ID', 'Company', 'Email', 'Amount (KES)',
        'Reason', 'Restocked', 'Issued By', 'Issued At'
    ])

    for n in filtered_notes:
        cw.writerow([
            n['reference'],
            f"GMK-00{n['inquiry_id']}",
            n['company_name'],
            n['contact_email'],
            f"{n['amount']:.2f}",
            n['reason'],
            'Yes' if n['restock_inventory'] else 'No',
            n['issued_by'],
            n['created_at'].strftime('%Y-%m-%d %H:%M')
        ])

    return Response(
        si.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=GrandMark_Credit_Notes.csv'}
    )

@app.route('/admin/credit_notes/export.pdf')
def export_credit_notes_pdf():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not has_permission('reports'):
        return "Forbidden", 403

    filtered_notes, filters = get_filtered_credit_notes(request.args)

    pdf = ReceiptPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=35)
    content_left = (pdf.w - 180) / 2
    content_inner = content_left + 5

    # Title row aligned to invoice style
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(120, 8, 'CREDIT NOTES SUMMARY REPORT', ln=False)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*ReceiptPDF.GREY)
    pdf.cell(0, 8, f"Generated: {datetime.utcnow().strftime('%d %B %Y, %H:%M')}", align='R', ln=True)
    pdf.ln(2)

    # Filters box
    pdf.set_fill_color(*ReceiptPDF.LIGHT_BG)
    y0 = pdf.get_y()
    pdf.rect(content_left, y0, 180, 24, 'F')

    pdf.set_xy(content_inner, y0 + 3)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(28, 5, 'Reference:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(55, 5, (filters['reference'] or '-')[:25], ln=False)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(25, 5, 'Company:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(0, 5, (filters['company'] or '-')[:30], ln=True)

    pdf.set_x(content_inner)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(28, 5, 'From Date:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(55, 5, filters['from_date'] or '-', ln=False)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(25, 5, 'To Date:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(0, 5, filters['to_date'] or '-', ln=True)
    pdf.ln(14)

    total_credited = sum(n['amount'] for n in filtered_notes)
    pdf.set_fill_color(255, 248, 235)
    y1 = pdf.get_y()
    pdf.rect(content_left, y1, 180, 14, 'F')
    pdf.set_xy(content_inner, y1 + 3)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*ReceiptPDF.GOLD)
    pdf.cell(95, 6, f"Total Notes: {len(filtered_notes)}", ln=False)
    pdf.cell(0, 6, f"Total Credited: KES {total_credited:,.2f}", align='R', ln=True)
    pdf.ln(6)

    # Table header
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(*ReceiptPDF.NAVY)
    pdf.set_text_color(*ReceiptPDF.WHITE)
    pdf.cell(32, 8, 'Reference', border=0, fill=True)
    pdf.cell(20, 8, 'Order', border=0, fill=True)
    pdf.cell(46, 8, 'Company', border=0, fill=True)
    pdf.cell(23, 8, 'Amount', border=0, fill=True, align='R')
    pdf.cell(29, 8, 'Date', border=0, fill=True)
    pdf.cell(30, 8, 'Issued By', border=0, fill=True)
    pdf.ln()

    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.set_font('Helvetica', '', 8.5)
    for idx, note in enumerate(filtered_notes, 1):
        row_fill = (idx % 2 == 0)
        if row_fill:
            pdf.set_fill_color(248, 249, 252)

        company_name = (note['company_name'] or '-')[:24]
        issued_by = (note['issued_by'] or '-')[:15]
        pdf.cell(32, 7, note['reference'][:16], border=0, fill=row_fill)
        pdf.cell(20, 7, f"GMK-00{note['inquiry_id']}", border=0, fill=row_fill)
        pdf.cell(46, 7, company_name, border=0, fill=row_fill)
        pdf.cell(23, 7, f"{note['amount']:,.2f}", border=0, fill=row_fill, align='R')
        pdf.cell(29, 7, note['created_at'].strftime('%Y-%m-%d'), border=0, fill=row_fill)
        pdf.cell(30, 7, issued_by, border=0, fill=row_fill)
        pdf.ln()

    if not filtered_notes:
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(*ReceiptPDF.GREY)
        pdf.cell(0, 10, 'No credit notes match the selected filters.', ln=True)

    os.makedirs('instance', exist_ok=True)
    file_path = 'instance/credit_notes_summary.pdf'
    pdf.output(file_path)
    register_document('credit_note_summary', 'CN-SUMMARY', file_path)
    db.session.commit()
    return send_file(file_path, as_attachment=True)

@app.route('/admin/control_tower')
def admin_control_tower():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    return render_template(
        'control_tower.html',
        admin_role=session.get('admin_role', get_current_admin_role()),
        ui_permissions=ui_permissions_for_current_admin(),
        admin_users=User.query.order_by(User.username.asc()).all(),
        roles=AdminRole.query.order_by(AdminRole.username.asc()).all(),
        workflow_events=InquiryWorkflowEvent.query.order_by(InquiryWorkflowEvent.timestamp.desc()).limit(30).all(),
        credit_controls=ClientCreditControl.query.order_by(ClientCreditControl.updated_at.desc()).all(),
        returns=ReturnRequest.query.order_by(ReturnRequest.created_at.desc()).all(),
        templates=NotificationTemplate.query.order_by(NotificationTemplate.updated_at.desc()).all(),
        documents=DocumentRegistry.query.order_by(DocumentRegistry.created_at.desc()).limit(30).all(),
        policies=InventoryPolicy.query.order_by(InventoryPolicy.updated_at.desc()).all(),
        dispatch_tickets=DispatchTicket.query.order_by(DispatchTicket.created_at.desc()).all(),
        inquiries=Inquiry.query.order_by(Inquiry.date_submitted.desc()).limit(100).all(),
        clients=Client.query.order_by(Client.id.desc()).all(),
        products=Product.query.order_by(Product.name.asc()).all()
    )

@app.route('/api/admin/role/assign', methods=['POST'])
@require_permission('security')
def assign_admin_role():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    role = (data.get('role') or '').strip()
    valid_roles = ['Super Admin', 'Finance', 'Operations', 'Inventory', 'Support', 'Viewer']

    if not username or role not in valid_roles:
        return jsonify({"error": "Invalid username or role."}), 400

    row = AdminRole.query.filter_by(username=username).first()
    if not row:
        row = AdminRole(username=username, role=role)
        db.session.add(row)
    else:
        row.role = role

    log_admin_action(f"Assigned role {role} to {username}")
    db.session.commit()
    return jsonify({"message": f"Role updated: {username} -> {role}"})

@app.route('/api/admin/role/delete', methods=['POST'])
@require_permission('security')
def delete_admin_role():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    if not username:
        return jsonify({"error": "Username is required."}), 400

    if username == session.get('username'):
        return jsonify({"error": "You cannot delete your own role assignment while logged in."}), 400

    row = AdminRole.query.filter_by(username=username).first()
    if not row:
        return jsonify({"error": "Role assignment not found."}), 404

    db.session.delete(row)
    log_admin_action(f"Deleted role assignment for {username}")
    db.session.commit()
    return jsonify({"message": f"Role assignment deleted for {username}."})

@app.route('/api/admin/user/create', methods=['POST'])
@require_permission('security')
def create_admin_user():
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = (data.get('role') or 'Viewer').strip()
    valid_roles = ['Super Admin', 'Finance', 'Operations', 'Inventory', 'Support', 'Viewer']

    if not username or len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters."}), 400
    if not re.match(r'^[A-Za-z0-9_.-]+$', username):
        return jsonify({"error": "Username contains invalid characters."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    if role not in valid_roles:
        return jsonify({"error": "Invalid role."}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Admin username already exists."}), 409

    new_user = User(
        username=username,
        password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
        totp_secret=pyotp.random_base32()
    )
    db.session.add(new_user)
    db.session.add(AdminRole(username=username, role=role))

    log_admin_action(f"Created admin user {username} with role {role}")
    db.session.commit()
    return jsonify({"message": f"Admin user created: {username} ({role})"})

@app.route('/api/admin/workflow/update/<int:inq_id>', methods=['POST'])
@require_permission('operations')
def update_workflow_status(inq_id):
    inq = Inquiry.query.get(inq_id)
    if not inq:
        return jsonify({"error": "Order not found"}), 404

    data = request.json or {}
    to_status = (data.get('status') or '').strip()
    note = (data.get('note') or '').strip()
    valid_statuses = ['Pending Approval', 'Approved - Awaiting Payment', 'Paid', 'Packed', 'Dispatched', 'Delivered', 'Rejected']
    if to_status not in valid_statuses:
        return jsonify({"error": "Invalid workflow status."}), 400

    if to_status == 'Dispatched' and not (has_permission('finance') or get_current_admin_role() == 'Super Admin'):
        return jsonify({"error": "Finance approval required to dispatch."}), 403

    from_status = inq.status
    event = InquiryWorkflowEvent(
        inquiry_id=inq.id,
        from_status=from_status,
        to_status=to_status,
        actor=session.get('username', 'System Admin'),
        note=note
    )
    inq.status = to_status
    db.session.add(event)
    log_admin_action(f"Workflow update GMK-00{inq.id}: {event.from_status} -> {event.to_status}")
    db.session.commit()
    notify_inquiry_status_change(inq, from_status, note=note)
    return jsonify({"message": "Workflow status updated."})

@app.route('/api/admin/credit_control/set', methods=['POST'])
@require_permission('finance')
def set_credit_control():
    data = request.json or {}
    client_email = (data.get('client_email') or '').strip().lower()
    if not client_email:
        return jsonify({"error": "Client email is required."}), 400

    try:
        credit_limit = float(data.get('credit_limit', 0))
        outstanding = float(data.get('outstanding_balance', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric values."}), 400

    row = ClientCreditControl.query.filter_by(client_email=client_email).first()
    if not row:
        row = ClientCreditControl(client_email=client_email)
        db.session.add(row)

    row.credit_limit = max(0.0, credit_limit)
    row.outstanding_balance = max(0.0, outstanding)
    row.is_active = bool(data.get('is_active', True))

    log_admin_action(f"Updated credit control for {client_email}")
    db.session.commit()
    return jsonify({"message": "Credit control updated."})

@app.route('/api/admin/returns/create', methods=['POST'])
@require_permission('support')
def create_return_request():
    data = request.json or {}
    try:
        inquiry_id = int(data.get('inquiry_id', 0))
        requested_amount = float(data.get('requested_amount', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid return request data."}), 400

    inq = Inquiry.query.get(inquiry_id)
    if not inq:
        return jsonify({"error": "Order not found."}), 404

    reason = (data.get('reason') or '').strip()
    if not reason:
        return jsonify({"error": "Return reason is required."}), 400

    rr = ReturnRequest(
        inquiry_id=inq.id,
        company_name=inq.company_name,
        contact_email=inq.contact_email,
        reason=reason,
        requested_amount=max(0.0, requested_amount)
    )
    db.session.add(rr)
    log_admin_action(f"Created return request RR-{inq.id}-{datetime.utcnow().strftime('%H%M%S')}")
    db.session.commit()
    return jsonify({"message": "Return request created.", "return_id": rr.id})

@app.route('/api/admin/returns/<int:return_id>/resolve', methods=['POST'])
@require_permission('support')
def resolve_return_request(return_id):
    rr = ReturnRequest.query.get(return_id)
    if not rr:
        return jsonify({"error": "Return request not found."}), 404

    data = request.json or {}
    decision = (data.get('decision') or '').strip().lower()
    if decision not in ['approved', 'rejected']:
        return jsonify({"error": "Decision must be approved or rejected."}), 400

    if decision == 'rejected':
        rr.status = 'Rejected'
        log_admin_action(f"Rejected return request {rr.id}")
        db.session.commit()
        return jsonify({"message": "Return request rejected."})

    try:
        approved_amount = float(data.get('approved_amount', rr.requested_amount or 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid approved amount."}), 400

    rr.status = 'Approved'
    rr.approved_amount = max(0.0, approved_amount)

    inq = Inquiry.query.get(rr.inquiry_id)
    previous_inquiry_status = inq.status if inq else None
    if inq and rr.approved_amount > 0:
        reference = f"CN-RMA-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000,9999)}"
        while CreditNote.query.filter_by(reference=reference).first():
            reference = f"CN-RMA-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

        db.session.add(CreditNote(
            inquiry_id=inq.id,
            reference=reference,
            amount=rr.approved_amount,
            reason=f"RMA Resolution: {rr.reason}",
            restock_inventory=False,
            issued_by=session.get('username', 'System Admin')
        ))
        db.session.add(Ledger(
            transaction_type='Debit',
            amount=rr.approved_amount,
            description=f"Credit Note {reference} | RMA for Order GMK-00{inq.id}"
        ))
        if 'Credit Note Issued' not in inq.status:
            inq.status = f"{inq.status} | Credit Note Issued"

    log_admin_action(f"Approved return request {rr.id}")
    db.session.commit()
    if inq and previous_inquiry_status != inq.status:
        notify_inquiry_status_change(inq, previous_inquiry_status, note=f"RMA approved (RR-{rr.id}).")
    return jsonify({"message": "Return request approved and credit note issued."})

@app.route('/api/admin/notification_template/upsert', methods=['POST'])
@require_permission('support')
def upsert_notification_template():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    channel = (data.get('channel') or 'email').strip().lower()
    subject = (data.get('subject') or '').strip()
    body = (data.get('body') or '').strip()

    if not name or not subject or not body:
        return jsonify({"error": "Template name, subject, and body are required."}), 400

    row = NotificationTemplate.query.filter_by(name=name).first()
    if not row:
        row = NotificationTemplate(name=name)
        db.session.add(row)

    row.channel = channel
    row.subject = subject
    row.body = body
    row.is_active = bool(data.get('is_active', True))

    log_admin_action(f"Upserted notification template {name}")
    db.session.commit()
    return jsonify({"message": "Template saved."})

@app.route('/api/admin/inventory_policy/upsert', methods=['POST'])
@require_permission('inventory')
def upsert_inventory_policy():
    data = request.json or {}
    try:
        product_id = int(data.get('product_id', 0))
        reorder_point = int(data.get('reorder_point', 25))
        reorder_qty = int(data.get('reorder_qty', 100))
        lead_time_days = int(data.get('lead_time_days', 7))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid policy values."}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found."}), 404

    row = InventoryPolicy.query.filter_by(product_id=product_id).first()
    if not row:
        row = InventoryPolicy(product_id=product_id)
        db.session.add(row)

    row.reorder_point = max(0, reorder_point)
    row.reorder_qty = max(1, reorder_qty)
    row.lead_time_days = max(1, lead_time_days)
    log_admin_action(f"Updated inventory policy for {product.name}")
    db.session.commit()
    return jsonify({"message": "Inventory policy saved."})

@app.route('/api/admin/reorder_suggestions')
@require_permission('inventory')
def reorder_suggestions():
    suggestions = []
    products = Product.query.all()
    policy_map = {p.product_id: p for p in InventoryPolicy.query.all()}

    for p in products:
        policy = policy_map.get(p.id)
        reorder_point = policy.reorder_point if policy else 25
        reorder_qty = policy.reorder_qty if policy else 100
        if p.stock_quantity <= reorder_point:
            suggestions.append({
                'product_id': p.id,
                'name': p.name,
                'sku': p.sku,
                'stock': p.stock_quantity,
                'reorder_point': reorder_point,
                'suggested_qty': reorder_qty,
                'lead_time_days': policy.lead_time_days if policy else 7
            })

    return jsonify({'suggestions': suggestions, 'count': len(suggestions)})

@app.route('/api/admin/dispatch/create', methods=['POST'])
@require_permission('operations')
def create_dispatch_ticket():
    data = request.json or {}
    try:
        inquiry_id = int(data.get('inquiry_id', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid order id."}), 400

    inq = Inquiry.query.get(inquiry_id)
    if not inq:
        return jsonify({"error": "Order not found."}), 404

    driver_name = (data.get('driver_name') or '').strip()
    vehicle_plate = (data.get('vehicle_plate') or '').strip()
    route = (data.get('route') or '').strip()

    if not driver_name or not vehicle_plate or not route:
        return jsonify({"error": "Driver, vehicle plate, and route are required."}), 400

    ticket = DispatchTicket(
        inquiry_id=inq.id,
        driver_name=driver_name,
        vehicle_plate=vehicle_plate,
        route=route,
        status='Assigned'
    )
    db.session.add(ticket)

    previous_status = inq.status
    event = InquiryWorkflowEvent(
        inquiry_id=inq.id,
        from_status=previous_status,
        to_status='Dispatched',
        actor=session.get('username', 'System Admin'),
        note=f"Dispatch ticket created ({vehicle_plate})"
    )
    inq.status = 'Dispatched'
    db.session.add(event)
    log_admin_action(f"Created dispatch ticket for GMK-00{inq.id}")
    db.session.commit()
    notify_inquiry_status_change(inq, previous_status, note=f"Dispatch assigned to {driver_name} ({vehicle_plate}).")
    return jsonify({"message": "Dispatch ticket created.", "dispatch_id": ticket.id})

@app.route('/api/admin/dispatch/<int:dispatch_id>/status', methods=['POST'])
@require_permission('operations')
def update_dispatch_status(dispatch_id):
    ticket = DispatchTicket.query.get(dispatch_id)
    if not ticket:
        return jsonify({"error": "Dispatch ticket not found."}), 404

    status = (request.json or {}).get('status', '').strip()
    valid = ['Assigned', 'In Transit', 'Delivered', 'Delayed', 'Cancelled']
    if status not in valid:
        return jsonify({"error": "Invalid status."}), 400

    ticket.status = status
    inq = Inquiry.query.get(ticket.inquiry_id)
    previous_inquiry_status = inq.status if inq else None
    if inq and status == 'Delivered':
        inq.status = 'Delivered'
    log_admin_action(f"Dispatch #{ticket.id} updated to {status}")
    db.session.commit()
    if inq and previous_inquiry_status != inq.status:
        notify_inquiry_status_change(inq, previous_inquiry_status, note=f"Dispatch status is now {status}.")
    return jsonify({"message": "Dispatch status updated."})

@app.route('/api/admin/analytics/overview')
@require_permission('reports')
def admin_analytics_overview():
    income = sum(l.amount for l in Ledger.query.filter_by(transaction_type='Credit').all())
    expense = sum(l.amount for l in Ledger.query.filter_by(transaction_type='Debit').all())
    low_stock_count = len([p for p in Product.query.all() if p.stock_quantity < 25])
    credit_note_total = sum(cn.amount for cn in CreditNote.query.all())
    total_orders = Inquiry.query.count()
    delivered = Inquiry.query.filter(Inquiry.status.ilike('%Delivered%')).count()

    return jsonify({
        'income': income,
        'expense': expense,
        'net': income - expense,
        'credit_note_total': credit_note_total,
        'credit_note_ratio': (credit_note_total / income) if income > 0 else 0,
        'low_stock_count': low_stock_count,
        'orders_total': total_orders,
        'orders_delivered': delivered
    })

@app.route('/api/admin/payment_reminders/run', methods=['POST'])
@require_permission('support')
def run_payment_reminders_api():
    result = run_awaiting_payment_reminders()
    log_admin_action(
        f"Payment reminder automation executed: sent={result['sent']}, skipped={result['skipped']}, candidates={result['candidates']}"
    )
    db.session.commit()
    return jsonify({
        'message': 'Payment reminder automation completed.',
        'sent': result['sent'],
        'skipped': result['skipped'],
        'candidates': result['candidates']
    })

@app.route('/api/admin/email/test', methods=['POST'])
@require_permission('support')
def test_smtp_email_api():
    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form.to_dict()

    smtp_cfg = get_smtp_runtime_config()
    target_email = (
        data.get('target_email')
        or request.args.get('target_email')
        or smtp_cfg['sender_email']
        or ''
    ).strip()
    if not target_email:
        return jsonify({'error': 'No target email provided and sender email is not configured. Set MAIL_USERNAME or pass target_email.'}), 400

    success, msg = send_smtp_test_email(target_email)
    if not success:
        app.logger.error(
            "SMTP test failed | target=%s | sender=%s | host=%s | port=%s | ssl=%s | error=%s",
            target_email,
            smtp_cfg['sender_email'],
            smtp_cfg['smtp_host'],
            smtp_cfg['smtp_port'],
            smtp_cfg['smtp_use_ssl'],
            msg
        )
        return jsonify({'error': f'SMTP test failed: {msg}'}), 500

    log_admin_action(f"SMTP test email sent to {target_email} via {smtp_cfg['smtp_host']}:{smtp_cfg['smtp_port']}")
    db.session.commit()
    return jsonify({
        'message': f'SMTP test email sent to {target_email}.',
        'smtp_host': smtp_cfg['smtp_host'],
        'smtp_port': smtp_cfg['smtp_port'],
        'smtp_ssl': smtp_cfg['smtp_use_ssl'],
        'sender': smtp_cfg['sender_email']
    })

@app.route('/api/admin/experience/overview')
@require_permission('reports')
def admin_experience_overview():
    return jsonify(build_admin_experience_snapshot())

@app.route('/api/admin/copilot/query', methods=['POST'])
@require_permission('reports')
def admin_copilot_query():
    prompt = ((request.json or {}).get('prompt') or '').strip()
    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    snapshot = build_admin_experience_snapshot()
    text = prompt.lower()

    if 'high value' in text and 'unpaid' in text:
        rows = snapshot['action_feeds']['high_value_unpaid'][:5]
        if not rows:
            return jsonify({'reply': 'No high-value unpaid orders right now.'})
        lines = [f"GMK-00{r['id']} | {r['company']} | KES {r['total']:,.2f} | {r['status']}" for r in rows]
        return jsonify({'reply': "Top high-value unpaid orders:\n" + "\n".join(lines)})

    if 'stockout' in text or 'low stock' in text:
        rows = snapshot['action_feeds']['stockout_risks'][:6]
        if not rows:
            return jsonify({'reply': 'No stockout risks detected.'})
        lines = [f"{r['name']} ({r['sku']}) | Stock: {r['stock']}" for r in rows]
        return jsonify({'reply': "Stockout risk list:\n" + "\n".join(lines)})

    if 'credit stress' in text or 'over limit' in text:
        stressed = []
        for c in ClientCreditControl.query.filter_by(is_active=True).all():
            if c.credit_limit > 0 and c.outstanding_balance >= (0.8 * c.credit_limit):
                stressed.append(c)
        if not stressed:
            return jsonify({'reply': 'No clients are near their credit limits.'})
        lines = [f"{c.client_email} | Outstanding {c.outstanding_balance:,.2f} / Limit {c.credit_limit:,.2f}" for c in stressed[:8]]
        return jsonify({'reply': "Clients near credit limits:\n" + "\n".join(lines)})

    if 'fraud' in text or 'suspicious' in text:
        sig = snapshot['fraud_signals']
        lines = [
            f"Suspicious credit notes: {len(sig['suspicious_credit_notes'])}",
            f"Pending RMAs: {sig['pending_rma']}",
            f"Blocked clients: {sig['blocked_clients']}",
            f"Blocked suppliers: {sig['blocked_suppliers']}"
        ]
        return jsonify({'reply': "Fraud risk summary:\n" + "\n".join(lines)})

    return jsonify({'reply': 'Try one of these prompts: "show high value unpaid", "show stockout risks", "show credit stress clients", or "fraud summary".'})

@app.route('/export/inventory')
def export_inventory():
    if not session.get('logged_in'): 
        return redirect(url_for('login'))
    if not (has_permission('inventory') or has_permission('reports')):
        return "Forbidden", 403
    
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
        email = (data.get('email') or '').strip().lower()
        message = data.get('message') or ''
        amount_match = re.search(r'TOTAL AMOUNT DUE: KES ([\d,]+\.\d{2})', message)
        order_total = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0

        credit_control = ClientCreditControl.query.filter_by(client_email=email, is_active=True).first()
        if credit_control and credit_control.credit_limit > 0:
            projected = credit_control.outstanding_balance + order_total
            if projected > credit_control.credit_limit:
                return jsonify({
                    "error": f"Credit limit exceeded. Remaining available: KES {max(0.0, credit_control.credit_limit - credit_control.outstanding_balance):,.2f}"
                }), 400

        new_order = Inquiry(
            company_name=data.get('company_name'),
            contact_email=email,
            inquiry_type=data.get('type'), 
            message=message,
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

# ---------------------------------------------------------------------------
# PREMIUM PDF RECEIPT GENERATOR
# ---------------------------------------------------------------------------
class ReceiptPDF(FPDF):
    """Professional order receipt PDF."""

    NAVY = (18, 47, 82)
    GOLD = (245, 166, 35)
    HEADER_BG = (255, 255, 255)
    LOGO_BLUE = (32, 74, 132)
    DARK = (33, 37, 41)
    GREY = (108, 117, 125)
    LIGHT_BG = (245, 247, 250)
    WHITE = (255, 255, 255)

    def header(self):
        # Header bar aligned to logo background tone
        self.set_fill_color(*self.HEADER_BG)
        self.rect(0, 0, 210, 42, "F")

        # Logo at top-left (shared across all branded PDFs)
        logo_path = os.path.join(app.root_path, 'static', 'logo.png')
        if os.path.exists(logo_path):
            try:
                self.image(logo_path, x=0, y=0, h=41)
            except Exception:
                pass

        # Right: brand/details use the blue tone from the logo
        self.set_text_color(*self.LOGO_BLUE)
        self.set_xy(105, 7)
        self.set_font("Helvetica", "B", 20)
        self.cell(90, 9, "GRANDMARK", align="R", ln=True)
        self.set_xy(105, 18)
        self.set_font("Helvetica", "B", 13)
        self.cell(90, 7, "DISTRIBUTORS", align="R", ln=True)
        self.set_xy(105, 27)
        self.set_font("Helvetica", "", 8)
        self.cell(90, 5, "support@grandmarkdistributors.live  |  +254 700 123 456", align="R")

        # Gold accent line
        self.set_fill_color(*self.GOLD)
        self.rect(0, 42, 210, 2, "F")
        self.set_y(47)

    def footer(self):
        content_left = (self.w - 180) / 2
        content_right = content_left + 180
        self.set_y(-30)
        self.set_draw_color(*self.NAVY)
        self.line(content_left, self.get_y(), content_right, self.get_y())
        self.ln(4)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*self.GREY)
        self.cell(0, 4, "Grandmark Distributors Ltd  |  Industrial Area, Nairobi, Kenya  |  +254 700 123 456  |  info@grandmarkdistributors.co.ke", align="C", ln=True)
        self.cell(0, 4, "Thank you for your business! Prices include VAT where indicated. This is a computer-generated receipt.", align="C")

def create_pdf(inq):
    """Builds a professional receipt PDF using the DB Inquiry object."""
    VAT_RATE = 0.16
    DELIVERY_FEE = 250.0
    is_paid = 'Paid' in inq.status
    payment_method, payment_reference = get_payment_details_from_status(inq.status)

    pdf = ReceiptPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=35)
    content_left = (pdf.w - 180) / 2
    content_inner = content_left + 5
    content_right = content_left + 180

    # --- Title row ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(100, 8, "ORDER RECEIPT / INVOICE", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*ReceiptPDF.GREY)
    pdf.cell(0, 8, f"Date: {inq.date_submitted.strftime('%d %B %Y, %H:%M')}", align="R", ln=True)
    pdf.ln(2)

    # --- Order info box ---
    pdf.set_fill_color(*ReceiptPDF.LIGHT_BG)
    y0 = pdf.get_y()
    pdf.rect(content_left, y0, 180, 36, "F")

    pdf.set_xy(content_inner, y0 + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(45, 5, "Order Reference:", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(45, 5, f"GMK-00{inq.id}", ln=False)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(35, 5, "Status:", ln=False)
    pdf.set_font("Helvetica", "B", 9)
    
    # Status coloring
    if is_paid:
        pdf.set_text_color(34, 197, 94) # Green
        pdf.cell(0, 5, "PAID IN FULL", ln=True)
    else:
        pdf.set_text_color(239, 68, 68) # Red
        pdf.cell(0, 5, "PAYMENT DUE", ln=True)

    pdf.set_x(content_inner)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(45, 5, "Customer:", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(45, 5, inq.company_name[:25], ln=False)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(35, 5, "Email:", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(0, 5, inq.contact_email, ln=True)

    pdf.set_x(content_inner)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(45, 5, "Payment Ref:", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    if is_paid and payment_reference:
        payment_ref_text = f"{payment_reference} ({payment_method})"
    elif is_paid:
        payment_ref_text = f"Not Captured ({payment_method})"
    else:
        payment_ref_text = "Pending Payment"
    pdf.cell(0, 5, payment_ref_text[:55], ln=True)
    pdf.ln(9)

    # --- Parse Items from Database ---
    items = []
    matches = re.finditer(r'(\d+)\s+units of\s+(.*?)\.', inq.message, re.IGNORECASE)
    for match in matches:
        qty = int(match.group(1))
        name = match.group(2).strip()
        db_prod = Product.query.filter_by(name=name).first()
        unit_price = db_prod.unit_cost if db_prod else 0.0
        cat_name = db_prod.category if db_prod and db_prod.category else "-"
        items.append({'qty': qty, 'name': name, 'unit_price': unit_price, 'category': cat_name})
        
    if not items: # Fallback if empty
        items.append({'qty': 1, 'name': 'Standard Logistics Fulfillment', 'unit_price': 0.0, 'category': 'Service'})

    # --- Product table header ---
    pdf.set_fill_color(*ReceiptPDF.NAVY)
    pdf.set_text_color(*ReceiptPDF.WHITE)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(10, 8, "#", border=0, fill=True, align="C")
    pdf.cell(75, 8, "Product", border=0, fill=True)
    pdf.cell(25, 8, "Category", border=0, fill=True, align="C")
    pdf.cell(25, 8, "Qty", border=0, fill=True, align="C")
    pdf.cell(22, 8, "Price", border=0, fill=True, align="R")
    pdf.cell(23, 8, "Subtotal", border=0, fill=True, align="R")
    pdf.ln()

    # --- Product rows ---
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*ReceiptPDF.DARK)
    subtotal = 0.0
    
    for idx, item in enumerate(items, 1):
        row_sub = item['qty'] * item['unit_price']
        subtotal += row_sub
        
        # Alternate row background
        if idx % 2 == 0:
            pdf.set_fill_color(248, 249, 252)
            fill = True
        else:
            fill = False
            
        pdf.cell(10, 7, str(idx), border=0, fill=fill, align="C")
        pdf.cell(75, 7, item['name'][:42], border=0, fill=fill)
        pdf.cell(25, 7, item['category'][:12], border=0, fill=fill, align="C")
        pdf.cell(25, 7, str(item['qty']), border=0, fill=fill, align="C")
        pdf.cell(22, 7, f"{item['unit_price']:,.0f}", border=0, fill=fill, align="R")
        pdf.cell(23, 7, f"{row_sub:,.0f}", border=0, fill=fill, align="R")
        pdf.ln()

    # --- Separator ---
    pdf.set_draw_color(*ReceiptPDF.NAVY)
    pdf.line(content_left, pdf.get_y(), content_right, pdf.get_y())
    pdf.ln(4)

    # --- Totals aligned right ---
    tax = subtotal * VAT_RATE
    grand_total = subtotal + tax + DELIVERY_FEE

    x_label = content_left + 115
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*ReceiptPDF.DARK)

    pdf.set_x(x_label)
    pdf.cell(42, 6, "Subtotal:", align="R", ln=False)
    pdf.cell(23, 6, f"KES {subtotal:,.0f}", align="R", ln=True)

    pdf.set_x(x_label)
    pdf.cell(42, 6, f"VAT ({VAT_RATE*100:.0f}%):", align="R", ln=False)
    pdf.cell(23, 6, f"KES {tax:,.0f}", align="R", ln=True)

    pdf.set_x(x_label)
    pdf.cell(42, 6, "Delivery Fee:", align="R", ln=False)
    pdf.cell(23, 6, f"KES {DELIVERY_FEE:,.0f}", align="R", ln=True)

    pdf.ln(1)
    pdf.set_fill_color(*ReceiptPDF.NAVY)
    pdf.set_text_color(*ReceiptPDF.WHITE)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_x(x_label)
    pdf.cell(42, 9, "TOTAL DUE:", align="R", fill=True, ln=False)
    pdf.set_text_color(*ReceiptPDF.GOLD)
    pdf.cell(23, 9, f"KES {grand_total:,.0f}", align="R", fill=True, ln=True)

    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.ln(6)

    # --- Payment info box ---
    if is_paid:
        payment_line = f"Verified via {payment_method}."
        if payment_reference:
            payment_line += f" Reference: {payment_reference}."
        else:
            payment_line += " Transaction reference logged."

        pdf.set_fill_color(255, 248, 235)
        y0 = pdf.get_y()
        pdf.rect(content_left, y0, 180, 16, "F")
        pdf.set_xy(content_inner, y0 + 2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*ReceiptPDF.GOLD)
        pdf.cell(0, 5, "Payment Confirmation", ln=True)
        pdf.set_x(content_inner)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*ReceiptPDF.DARK)
        pdf.cell(0, 5, payment_line[:110], ln=True)

    # Save to Instance folder (required for email attachment to work)
    instance_dir = os.path.join(app.root_path, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    filepath = os.path.join(instance_dir, f"invoice_{inq.id}.pdf")
    pdf.output(filepath)
    register_document('invoice', f"INV-GMK-00{inq.id}", filepath, inquiry_id=inq.id)
    
    return filepath

def get_smtp_runtime_config():
    sender_email = (
        os.environ.get('MAIL_USERNAME')
        or os.environ.get('SENDER_EMAIL')
        or SENDER_EMAIL
        or ''
    ).strip()
    sender_password = (
        os.environ.get('MAIL_PASSWORD')
        or os.environ.get('MAIL_APP_PASSWORD')
        or os.environ.get('SENDER_PASSWORD')
        or SENDER_PASSWORD
        or ''
    ).strip()
    mail_from_name = (os.environ.get('MAIL_FROM_NAME') or MAIL_FROM_NAME or 'GrandMark Distributors').strip()
    smtp_host = (os.environ.get('SMTP_HOST') or os.environ.get('MAIL_SERVER') or SMTP_HOST or 'smtp.zoho.com').strip()
    smtp_port = int(os.environ.get('SMTP_PORT') or os.environ.get('MAIL_PORT') or str(SMTP_PORT or 465))
    smtp_use_ssl = (
        os.environ.get('SMTP_USE_SSL')
        or os.environ.get('MAIL_USE_SSL')
        or ('true' if SMTP_USE_SSL else 'false')
    ).strip().lower() in ['1', 'true', 'yes', 'on']
    return {
        'sender_email': sender_email,
        'sender_password': sender_password,
        'mail_from_name': mail_from_name,
        'smtp_host': smtp_host,
        'smtp_port': smtp_port,
        'smtp_use_ssl': smtp_use_ssl
    }

def get_billing_distribution_recipients():
    cc_list = split_email_list(os.environ.get('BILLING_CC_EMAILS', ''))
    bcc_list = split_email_list(os.environ.get('BILLING_BCC_EMAILS', ''))
    return cc_list, bcc_list

def apply_billing_distribution(msg):
    cc_list, bcc_list = get_billing_distribution_recipients()
    if cc_list:
        msg['Cc'] = ', '.join(cc_list)
    if bcc_list:
        msg['Bcc'] = ', '.join(bcc_list)
    return msg

def smtp_send_message(msg):
    smtp_cfg = get_smtp_runtime_config()
    sender_email = smtp_cfg['sender_email']
    sender_password = smtp_cfg['sender_password']
    smtp_host = smtp_cfg['smtp_host']
    smtp_port = smtp_cfg['smtp_port']
    smtp_use_ssl = smtp_cfg['smtp_use_ssl']

    if not sender_email or not sender_password:
        return False, "SMTP credentials not configured. Set MAIL_USERNAME and MAIL_PASSWORD."

    try:
        app.logger.info(
            "SMTP send attempt | from=%s | to=%s | host=%s | port=%s | ssl=%s",
            sender_email,
            msg.get('To', ''),
            smtp_host,
            smtp_port,
            smtp_use_ssl
        )
        if smtp_use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
        app.logger.info("SMTP send success | to=%s", msg.get('To', ''))
        return True, "Sent"
    except Exception as e:
        app.logger.error("SMTP send failed | to=%s | error=%s", msg.get('To', ''), str(e))
        return False, str(e)

def send_smtp_test_email(target_email):
    smtp_cfg = get_smtp_runtime_config()
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'SMTP Configuration Test - GrandMark'
    msg['From'] = f"{smtp_cfg['mail_from_name']} <{smtp_cfg['sender_email']}>"
    msg['To'] = target_email

    text_body = (
        "This is a test email from GrandMark. "
        "If you received this, SMTP is configured correctly."
    )
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f8fafc; padding:24px; color:#0f172a;">
        <div style="max-width:620px; margin:0 auto; background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:24px;">
            <h2 style="margin-top:0; color:#0ea5e9;">GrandMark SMTP Test</h2>
            <p>This is a test email sent from your configured SMTP provider.</p>
            <ul>
                <li><strong>From:</strong> {smtp_cfg['sender_email']}</li>
                <li><strong>Host:</strong> {smtp_cfg['smtp_host']}</li>
                <li><strong>Port:</strong> {smtp_cfg['smtp_port']}</li>
                <li><strong>SSL:</strong> {smtp_cfg['smtp_use_ssl']}</li>
                <li><strong>Time (UTC):</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}</li>
            </ul>
            <p style="margin-bottom:0; color:#64748b; font-size:12px;">GrandMark test utility.</p>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))
    return smtp_send_message(msg)

def send_otp_email(target_email, code):
    smtp_cfg = get_smtp_runtime_config()
    msg = MIMEMultipart()
    msg['Subject'] = 'GrandMark OS - Verify Your Account'
    msg['From'] = f"{smtp_cfg['mail_from_name']} Security <{smtp_cfg['sender_email']}>"
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

    success, smtp_msg = smtp_send_message(msg)
    if not success:
        print(f"SMTP Error: {smtp_msg}")
    return success

def send_inquiry_status_email(inquiry, from_status, to_status, note=None):
    recipient = (inquiry.contact_email or '').strip()
    if not recipient:
        return False, "Missing recipient email"

    if (from_status or '').strip() == (to_status or '').strip():
        return False, "Status unchanged"

    actor = session.get('username', 'System Admin')
    subject = f"Order GMK-00{inquiry.id} Status Update: {to_status}"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f8fafc; margin:0; padding:24px; color:#0f172a;">
        <div style="max-width:640px; margin:0 auto; background:#ffffff; border-radius:12px; border:1px solid #e2e8f0; padding:24px;">
            <h2 style="margin-top:0; color:#0ea5e9;">GrandMark Order Status Update</h2>
            <p>Hello <strong>{inquiry.company_name}</strong>,</p>
            <p>Your order status has changed. Details are below:</p>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:16px; margin:16px 0;">
                <p style="margin:0 0 8px 0;"><strong>Order:</strong> GMK-00{inquiry.id}</p>
                <p style="margin:0 0 8px 0;"><strong>Previous Status:</strong> {from_status or 'N/A'}</p>
                <p style="margin:0 0 8px 0;"><strong>Current Status:</strong> {to_status}</p>
                <p style="margin:0;"><strong>Updated By:</strong> {actor}</p>
            </div>
            {f'<p><strong>Note:</strong> {note}</p>' if note else ''}
            <p style="margin-bottom:0; color:#64748b; font-size:12px;">This is an automated email from GrandMark Distributors.</p>
        </div>
    </body>
    </html>
    """

    try:
        smtp_cfg = get_smtp_runtime_config()
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{smtp_cfg['mail_from_name']} <{smtp_cfg['sender_email']}>"
        msg['To'] = recipient
        msg.attach(MIMEText("Your order status has been updated.", 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        email_ok, email_msg = smtp_send_message(msg)
        if email_ok:
            return True, email_msg
        raise RuntimeError(email_msg)
    except Exception as e:
        fallback_text = (
            f"GrandMark status update for GMK-00{inquiry.id}: "
            f"{from_status or 'N/A'} -> {to_status}."
        )
        fallback_ok, fallback_msg = try_backup_channels(
            recipient=recipient,
            subject=subject,
            message=fallback_text,
            metadata={'inquiry_id': inquiry.id, 'type': 'status_update'}
        )
        if fallback_ok:
            return True, f"Email failed, fallback delivered ({fallback_msg})"
        return False, f"Email failed ({e}); fallback failed ({fallback_msg})"

def notify_inquiry_status_change(inquiry, from_status, note=None):
    to_status = inquiry.status or ''
    success, msg = send_inquiry_status_email(inquiry, from_status, to_status, note=note)
    if not success and msg not in ['Status unchanged', 'Missing recipient email']:
        print(f"[WARN] Status email failed for GMK-00{inquiry.id}: {msg}")
    return success, msg

def send_backup_channel_notification(channel, recipient, subject, message, metadata=None):
    webhook_url = ''
    if channel == 'sms':
        webhook_url = SMS_FALLBACK_WEBHOOK_URL
    elif channel == 'whatsapp':
        webhook_url = WHATSAPP_FALLBACK_WEBHOOK_URL

    if not webhook_url:
        return False, f"{channel} fallback webhook not configured"

    payload = {
        'channel': channel,
        'recipient': recipient,
        'subject': subject,
        'message': message,
        'metadata': metadata or {},
        'source': 'grandmark_automation'
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if 200 <= response.status_code < 300:
            return True, f"{channel} fallback sent"
        return False, f"{channel} fallback failed with {response.status_code}"
    except Exception as e:
        return False, str(e)

def try_backup_channels(recipient, subject, message, metadata=None):
    sms_ok, sms_msg = send_backup_channel_notification('sms', recipient, subject, message, metadata)
    wa_ok, wa_msg = send_backup_channel_notification('whatsapp', recipient, subject, message, metadata)
    overall_ok = sms_ok or wa_ok
    status_msg = f"sms=({sms_ok}, {sms_msg}); whatsapp=({wa_ok}, {wa_msg})"

    if overall_ok and has_request_context() and session.get('logged_in'):
        db.session.add(AuditLog(
            action=f"Fallback channel notification sent to {recipient}. {status_msg}",
            user=session.get('username', 'System Admin')
        ))
        db.session.commit()

    return overall_ok, status_msg

def send_payment_reminder_email(inquiry, stage):
    recipient = (inquiry.contact_email or '').strip()
    if not recipient:
        return False, "Missing recipient email"

    age_hours = int((datetime.utcnow() - inquiry.date_submitted).total_seconds() // 3600)
    subject = f"Payment Reminder ({stage}) | Order GMK-00{inquiry.id}"
    urgency_color = '#f59e0b' if stage == '24h' else '#ef4444'

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f8fafc; margin:0; padding:24px; color:#0f172a;">
        <div style="max-width:640px; margin:0 auto; background:#ffffff; border-radius:12px; border:1px solid #e2e8f0; padding:24px;">
            <h2 style="margin-top:0; color:{urgency_color};">GrandMark Payment Reminder</h2>
            <p>Hello <strong>{inquiry.company_name}</strong>,</p>
            <p>Your order is still awaiting payment confirmation.</p>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:16px; margin:16px 0;">
                <p style="margin:0 0 8px 0;"><strong>Order:</strong> GMK-00{inquiry.id}</p>
                <p style="margin:0 0 8px 0;"><strong>Status:</strong> {inquiry.status}</p>
                <p style="margin:0;"><strong>Age:</strong> {age_hours} hour(s) since submission</p>
            </div>
            <p>Please complete payment via your client portal to avoid fulfillment delay.</p>
            <div style="text-align:center; margin:24px 0;">
                <a href="http://127.0.0.1:5000/client_portal" style="display:inline-block; padding:12px 24px; background:#38bdf8; color:#fff; text-decoration:none; border-radius:8px; font-weight:bold;">Open Client Portal</a>
            </div>
            <p style="margin-bottom:0; color:#64748b; font-size:12px;">This is an automated reminder from GrandMark Distributors.</p>
        </div>
    </body>
    </html>
    """

    try:
        smtp_cfg = get_smtp_runtime_config()
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{smtp_cfg['mail_from_name']} <{smtp_cfg['sender_email']}>"
        msg['To'] = recipient
        msg.attach(MIMEText("Your order is awaiting payment.", 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        email_ok, email_msg = smtp_send_message(msg)
        if email_ok:
            return True, email_msg
        raise RuntimeError(email_msg)
    except Exception as e:
        fallback_text = (
            f"GrandMark payment reminder ({stage}) for GMK-00{inquiry.id}. "
            f"Status: {inquiry.status}. Please complete payment in client portal."
        )
        fallback_ok, fallback_msg = try_backup_channels(
            recipient=recipient,
            subject=subject,
            message=fallback_text,
            metadata={'inquiry_id': inquiry.id, 'type': 'payment_reminder', 'stage': stage}
        )
        if fallback_ok:
            return True, f"Email failed, fallback delivered ({fallback_msg})"
        return False, f"Email failed ({e}); fallback failed ({fallback_msg})"

def run_awaiting_payment_reminders():
    sent_count = 0
    skipped_count = 0
    now = datetime.utcnow()

    awaiting = Inquiry.query.filter(Inquiry.status.ilike('%awaiting payment%')).all()

    for inq in awaiting:
        age_hours = (now - inq.date_submitted).total_seconds() / 3600.0
        stage = None
        if age_hours >= 48:
            if not PaymentReminderLog.query.filter_by(inquiry_id=inq.id, stage='48h').first():
                stage = '48h'
        elif age_hours >= 24:
            if not PaymentReminderLog.query.filter_by(inquiry_id=inq.id, stage='24h').first():
                stage = '24h'

        if not stage:
            skipped_count += 1
            continue

        success, msg = send_payment_reminder_email(inq, stage)
        if success:
            db.session.add(PaymentReminderLog(
                inquiry_id=inq.id,
                stage=stage,
                sent_to=inq.contact_email,
                sent_by=session.get('username', 'System Automation')
            ))
            sent_count += 1
        else:
            print(f"[WARN] Payment reminder failed for GMK-00{inq.id} ({stage}): {msg}")
            skipped_count += 1

    db.session.commit()
    return {'sent': sent_count, 'skipped': skipped_count, 'candidates': len(awaiting)}

@app.route('/api/financial_report')
@require_permission('reports')
def generate_financial_report():
    ledger_entries = Ledger.query.order_by(Ledger.timestamp.asc()).all()
    total_revenue = sum(l.amount for l in ledger_entries if l.transaction_type == 'Credit')
    total_expenses = sum(l.amount for l in ledger_entries if l.transaction_type == 'Debit')
    net_profit = total_revenue - total_expenses

    pdf = ReceiptPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=35)
    content_left = (pdf.w - 180) / 2
    content_inner = content_left + 5

    # Title row in invoice style
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(120, 8, "FINANCIAL AUDIT REPORT", ln=False)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*ReceiptPDF.GREY)
    pdf.cell(0, 8, f"Generated: {datetime.utcnow().strftime('%d %B %Y, %H:%M')}", align="R", ln=True)
    pdf.ln(2)

    # Executive summary box
    pdf.set_fill_color(*ReceiptPDF.LIGHT_BG)
    y0 = pdf.get_y()
    pdf.rect(content_left, y0, 180, 28, "F")

    pdf.set_xy(content_inner, y0 + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(46, 5, "Gross Revenue (Credits):", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(44, 5, f"KES {total_revenue:,.2f}", ln=False)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(42, 5, "Operating Expense (Debits):", ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(0, 5, f"KES {total_expenses:,.2f}", ln=True)

    pdf.set_x(content_inner)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(46, 5, "Net Cashbook Balance:", ln=False)
    pdf.set_font("Helvetica", "B", 9)
    if net_profit >= 0:
        pdf.set_text_color(34, 197, 94)
    else:
        pdf.set_text_color(239, 68, 68)
    pdf.cell(44, 5, f"KES {net_profit:,.2f}", ln=False)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*ReceiptPDF.GREY)
    pdf.cell(0, 5, f"Entries: {len(ledger_entries)}", ln=True)
    pdf.ln(12)

    # Ledger table header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*ReceiptPDF.NAVY)
    pdf.set_text_color(*ReceiptPDF.WHITE)
    pdf.cell(28, 8, "Date", border=0, fill=True)
    pdf.cell(86, 8, "Transaction Details", border=0, fill=True)
    pdf.cell(28, 8, "Debit (Out)", border=0, fill=True, align="R")
    pdf.cell(28, 8, "Credit (In)", border=0, fill=True, align="R")
    pdf.cell(10, 8, "Type", border=0, fill=True, align="C")
    pdf.ln()

    # Ledger rows with alternating style
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*ReceiptPDF.DARK)
    for idx, entry in enumerate(ledger_entries, 1):
        row_fill = (idx % 2 == 0)
        if row_fill:
            pdf.set_fill_color(248, 249, 252)

        desc = entry.description[:50] + "..." if len(entry.description) > 50 else entry.description
        debit_val = f"{entry.amount:,.2f}" if entry.transaction_type == 'Debit' else "-"
        credit_val = f"{entry.amount:,.2f}" if entry.transaction_type == 'Credit' else "-"

        pdf.cell(28, 7, entry.timestamp.strftime('%Y-%m-%d'), border=0, fill=row_fill)
        pdf.cell(86, 7, desc, border=0, fill=row_fill)
        pdf.cell(28, 7, debit_val, border=0, fill=row_fill, align="R")
        pdf.cell(28, 7, credit_val, border=0, fill=row_fill, align="R")
        pdf.cell(10, 7, entry.transaction_type[:1], border=0, fill=row_fill, align="C")
        pdf.ln()

    if not ledger_entries:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*ReceiptPDF.GREY)
        pdf.cell(0, 10, "No ledger entries found for this report window.", ln=True)

    os.makedirs('instance', exist_ok=True)
    filepath = "instance/financial_report.pdf"
    pdf.output(filepath)
    register_document('financial_audit', f"AUD-{datetime.utcnow().strftime('%Y%m%d%H%M')}", filepath)
    db.session.commit()
    return send_file(filepath, as_attachment=True)

def send_approval_email(recipient_email, company_name, pdf_path, inq_id, is_paid):
    try:
        smtp_cfg = get_smtp_runtime_config()
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Official Document #GMK-00{inq_id} - GrandMark Logistics"
        msg['From'] = f"{smtp_cfg['mail_from_name']} <{smtp_cfg['sender_email']}>"
        msg['To'] = recipient_email
        apply_billing_distribution(msg)
        
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
            
        email_ok, email_msg = smtp_send_message(msg)
        if email_ok:
            return True, email_msg
        raise RuntimeError(email_msg)
    except Exception as e:
        short_status = "Paid & Dispatched" if is_paid else "Approved - Awaiting Payment"
        fallback_text = (
            f"GrandMark update for GMK-00{inq_id}: {short_status}. "
            "Please check your client portal for full document details."
        )
        fallback_ok, fallback_msg = try_backup_channels(
            recipient=recipient_email,
            subject=f"Order GMK-00{inq_id} update",
            message=fallback_text,
            metadata={'inquiry_id': inq_id, 'type': 'approval_document'}
        )
        if fallback_ok:
            return True, f"Email failed, fallback delivered ({fallback_msg})"
        return False, f"Email failed ({e}); fallback failed ({fallback_msg})"

@app.route('/api/approve_inquiry/<int:inq_id>', methods=['POST'])
@require_permission('operations')
def approve_inquiry(inq_id):
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
            total_due = extract_order_total(inq)
            credit_control = ClientCreditControl.query.filter_by(client_email=(inq.contact_email or '').lower(), is_active=True).first()
            if credit_control and total_due > 0:
                credit_control.outstanding_balance += total_due
            
        db.session.commit()
        
        if success:
            return jsonify({"message": "Pipeline Action Authorized & Inventory Deducted!"})
        else:
            return jsonify({"message": f"Pipeline Action Authorized! (Note: Email failed - {msg})"})
            
    return jsonify({"error": "Not found"}), 404

@app.route('/api/delete_inquiry/<int:inq_id>', methods=['DELETE'])
@require_permission('operations')
def delete_inquiry(inq_id):
    inq = Inquiry.query.get(inq_id)
    if inq:
        previous_status = inq.status
        inq.status = 'Rejected' 
        db.session.commit()
        notify_inquiry_status_change(inq, previous_status, note="Order rejected by operations.")
    return jsonify({"message": "Order Rejected"})

@app.route('/api/mpesa_pay/<int:inq_id>', methods=['POST'])
def mpesa_pay(inq_id):
    # SIMULATOR VERSION - No Safaricom Daraja API needed
    inq = Inquiry.query.get(inq_id)
    
    if inq and ('Pending' in inq.status or 'Approved' in inq.status or 'Awaiting Payment' in inq.status):
        import random
        import string
        import re
        previous_status = inq.status
        
        # 1. Generate a fake M-PESA receipt code (e.g., QWE123RTY)
        fake_receipt = ''.join(random.choices(string.ascii_uppercase + string.digits, k=9))
        inq.status = f'Paid (Ref: {fake_receipt})'
        
        # 2. Extract the exact amount from the invoice message
        amount_match = re.search(r'TOTAL AMOUNT DUE: KES ([\d,]+\.\d{2})', inq.message)
        exact_amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0
        
        # 3. Inject the cash directly into the Executive Ledger
        if exact_amount > 0:
            new_ledger = Ledger(
                transaction_type='Credit',
                amount=exact_amount,
                description=f"M-PESA Settlement (Simulated) | Order GMK-00{inq.id} | Ref: {fake_receipt}"
            )
            db.session.add(new_ledger)

            credit_control = ClientCreditControl.query.filter_by(client_email=(inq.contact_email or '').lower(), is_active=True).first()
            if credit_control:
                credit_control.outstanding_balance = max(0.0, credit_control.outstanding_balance - exact_amount)
        
        db.session.commit()
        notify_inquiry_status_change(inq, previous_status, note=f"Payment confirmed. Receipt: {fake_receipt}")
        
        print(f"[+] SIMULATION: Order GMK-00{inq.id} marked as PAID. Cashbook updated with KES {exact_amount}.")
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
@require_permission('inventory')
def add_product():
    data = request.json
    
    buying_price = float(data.get('buying_price', 0))
    selling_price = float(data['unit_cost'])
    stock_qty = int(data['stock_quantity'])
    
    # REAL ACCOUNTING: Expense is based on what YOU paid for it, not what you sell it for!
    total_expense = buying_price * stock_qty
    
    db.session.add(Product(
        name=data['name'], 
        sku=data['sku'], 
        category=data['category'], 
        buying_price=buying_price, 
        unit_cost=selling_price, 
        stock_quantity=stock_qty
    ))
    
    db.session.add(Ledger(
        transaction_type='Debit', 
        amount=total_expense, 
        description=f"Warehouse Stock Purchase: {stock_qty}x {data['name']} @ KES {buying_price} each"
    ))
    log_admin_action(f"Added product {data['name']} ({data['sku']}) with qty {stock_qty}")
    
    qr_dir = os.path.join(app.root_path, 'static', 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)
    img = qrcode.make(f"SKU: {data['sku']}\nProduct: {data['name']}\nCost: KES {selling_price}")
    img.save(os.path.join(qr_dir, f"{data['sku']}.png"))
    
    db.session.commit()
    return jsonify({"message": "Product registered, true expense logged, and QR Code generated!"})

@app.route('/api/update_product/<int:product_id>', methods=['PUT'])
@require_permission('inventory')
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.json or {}
    try:
        new_buying = float(data.get('buying_price', product.buying_price))
        new_selling = float(data.get('unit_cost', product.unit_cost))
        new_qty = int(data.get('stock_quantity', product.stock_quantity))
        if new_buying < 0 or new_selling < 0 or new_qty < 0:
            return jsonify({"error": "Values must be non-negative."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid numeric values supplied."}), 400

    product.name = (data.get('name') or product.name).strip()
    product.category = (data.get('category') or product.category or '').strip()
    product.buying_price = new_buying
    product.unit_cost = new_selling
    product.stock_quantity = new_qty
    log_admin_action(f"Updated product {product.name} (ID {product.id})")
    db.session.commit()
    return jsonify({"message": "Product updated successfully."})

@app.route('/api/delete_product/<int:product_id>', methods=['DELETE'])
@require_permission('inventory')
def delete_product(product_id):
    product = Product.query.get(product_id)
    if product:
        log_admin_action(f"Deleted product {product.name} (ID {product.id})")
        db.session.delete(product)
        db.session.commit()
    return jsonify({"message": "Product deleted"})

@app.route('/api/toggle_account_block/<string:account_type>/<int:account_id>', methods=['POST'])
@require_permission('security')
def toggle_account_block(account_type, account_id):
    if account_type not in ['client', 'supplier']:
        return jsonify({"error": "Invalid account type"}), 400

    model = Client if account_type == 'client' else Supplier
    account = model.query.get(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    key = build_account_key(account_type, account.email)
    control = AccountControl.query.filter_by(account_key=key).first()
    reason = (request.json or {}).get('reason', 'Administrative control')

    if control and control.is_blocked:
        control.is_blocked = False
        control.reason = None
        log_admin_action(f"Unblocked {account_type} account {account.email}")
        db.session.commit()
        return jsonify({"message": f"{account_type.title()} account unblocked."})

    if not control:
        control = AccountControl(
            account_key=key,
            account_type=account_type,
            email=account.email,
            is_blocked=True,
            reason=reason
        )
        db.session.add(control)
    else:
        control.is_blocked = True
        control.reason = reason

    log_admin_action(f"Blocked {account_type} account {account.email}")
    db.session.commit()
    return jsonify({"message": f"{account_type.title()} account blocked."})

@app.route('/api/delete_account/<string:account_type>/<int:account_id>', methods=['DELETE'])
@require_permission('security')
def delete_account(account_type, account_id):
    if account_type not in ['client', 'supplier']:
        return jsonify({"error": "Invalid account type"}), 400

    model = Client if account_type == 'client' else Supplier
    account = model.query.get(account_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404

    key = build_account_key(account_type, account.email)
    control = AccountControl.query.filter_by(account_key=key).first()
    if control:
        db.session.delete(control)

    log_admin_action(f"Deleted {account_type} account {account.email}")
    db.session.delete(account)
    db.session.commit()
    return jsonify({"message": f"{account_type.title()} account deleted."})

@app.route('/api/bulk_account_action', methods=['POST'])
@require_permission('security')
def bulk_account_action():
    data = request.json or {}
    account_type = data.get('account_type')
    action = data.get('action')
    ids = data.get('ids', [])
    reason = (data.get('reason') or 'Bulk administrative control').strip()

    if account_type not in ['client', 'supplier']:
        return jsonify({"error": "Invalid account type"}), 400
    if action not in ['block', 'unblock', 'delete']:
        return jsonify({"error": "Invalid action"}), 400
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "No account IDs provided"}), 400

    model = Client if account_type == 'client' else Supplier
    changed = 0

    for account_id in ids:
        account = model.query.get(account_id)
        if not account:
            continue

        key = build_account_key(account_type, account.email)
        control = AccountControl.query.filter_by(account_key=key).first()

        if action == 'delete':
            if control:
                db.session.delete(control)
            db.session.delete(account)
            changed += 1
            continue

        if not control:
            control = AccountControl(
                account_key=key,
                account_type=account_type,
                email=account.email,
                is_blocked=False
            )
            db.session.add(control)

        if action == 'block':
            control.is_blocked = True
            control.reason = reason
            changed += 1
        elif action == 'unblock':
            control.is_blocked = False
            control.reason = None
            changed += 1

    log_admin_action(f"Bulk {action} on {changed} {account_type} accounts")
    db.session.commit()
    return jsonify({"message": f"Bulk action complete: {changed} account(s) processed."})

@app.route('/api/bulk_price_update', methods=['POST'])
@require_permission('inventory')
def bulk_price_update():
    data = request.json or {}
    category = (data.get('category') or '').strip()
    target = data.get('target', 'category')
    product_ids = data.get('product_ids', [])

    try:
        percent = float(data.get('percent', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid percentage value."}), 400

    if percent == 0:
        return jsonify({"error": "Percentage cannot be zero."}), 400

    q = Product.query
    if target == 'selected':
        if not isinstance(product_ids, list) or not product_ids:
            return jsonify({"error": "No product IDs supplied for selected mode."}), 400
        q = q.filter(Product.id.in_(product_ids))
    elif target == 'category':
        if not category or category.lower() == 'all':
            return jsonify({"error": "Provide a valid category for category mode."}), 400
        q = q.filter_by(category=category)
    elif target == 'all':
        pass
    else:
        return jsonify({"error": "Invalid target mode."}), 400

    products = q.all()
    if not products:
        return jsonify({"error": "No matching products found."}), 404

    factor = 1 + (percent / 100.0)
    updated = 0
    for product in products:
        next_price = round(product.unit_cost * factor, 2)
        if next_price < 0:
            continue
        product.unit_cost = next_price
        updated += 1

    log_admin_action(f"Bulk price update {percent:+.2f}% on {updated} product(s)")
    db.session.commit()
    return jsonify({"message": f"Bulk price update complete: {updated} product(s) adjusted."})

def generate_credit_note_pdf_file(credit_note, inquiry):
    pdf = ReceiptPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=35)
    content_left = (pdf.w - 180) / 2
    content_inner = content_left + 5

    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(120, 8, 'CREDIT NOTE DOCUMENT', ln=False)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*ReceiptPDF.GREY)
    pdf.cell(0, 8, f"Issued: {credit_note.created_at.strftime('%d %B %Y, %H:%M')}", align='R', ln=True)
    pdf.ln(2)

    # Identity box
    pdf.set_fill_color(*ReceiptPDF.LIGHT_BG)
    y0 = pdf.get_y()
    pdf.rect(content_left, y0, 180, 28, 'F')

    pdf.set_xy(content_inner, y0 + 3)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(32, 5, 'Reference:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(55, 5, credit_note.reference, ln=False)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(26, 5, 'Issued By:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(0, 5, credit_note.issued_by, ln=True)

    pdf.set_x(content_inner)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(32, 5, 'Order:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(55, 5, f'GMK-00{inquiry.id}', ln=False)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(26, 5, 'Client:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(0, 5, inquiry.company_name[:38], ln=True)
    pdf.ln(13)

    # Amount strip
    pdf.set_fill_color(*ReceiptPDF.NAVY)
    pdf.set_text_color(*ReceiptPDF.WHITE)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_x(content_left)
    pdf.cell(65, 9, 'Credit Amount', border=0, fill=True)
    pdf.set_text_color(*ReceiptPDF.GOLD)
    pdf.cell(115, 9, f'KES {credit_note.amount:,.2f}', border=0, fill=True, align='R', ln=True)
    pdf.ln(4)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(0, 6, 'Reason', ln=True)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.multi_cell(0, 6, credit_note.reason)
    pdf.ln(2)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(48, 6, 'Inventory Restocked:', ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*ReceiptPDF.DARK)
    pdf.cell(0, 6, 'Yes' if credit_note.restock_inventory else 'No', ln=True)
    pdf.ln(4)

    # Returned items section (all parsed order items)
    returned_items = parse_order_items_from_message(inquiry.message)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*ReceiptPDF.NAVY)
    pdf.cell(0, 6, 'Returned Items', ln=True)

    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_fill_color(*ReceiptPDF.NAVY)
    pdf.set_text_color(*ReceiptPDF.WHITE)
    pdf.set_x(content_left)
    pdf.cell(12, 8, '#', border=0, fill=True, align='C')
    pdf.cell(95, 8, 'Item', border=0, fill=True)
    pdf.cell(18, 8, 'Qty', border=0, fill=True, align='C')
    pdf.cell(27, 8, 'Unit (KES)', border=0, fill=True, align='R')
    pdf.cell(28, 8, 'Subtotal', border=0, fill=True, align='R')
    pdf.ln()

    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(*ReceiptPDF.DARK)
    items_total = 0.0
    if returned_items:
        for idx, item in enumerate(returned_items, 1):
            prod = Product.query.filter_by(name=item['name']).first()
            unit_price = prod.unit_cost if prod else 0.0
            row_total = unit_price * item['qty']
            items_total += row_total

            row_fill = (idx % 2 == 0)
            if row_fill:
                pdf.set_fill_color(248, 249, 252)

            pdf.set_x(content_left)
            pdf.cell(12, 7, str(idx), border=0, fill=row_fill, align='C')
            pdf.cell(95, 7, (item['name'] or '-')[:42], border=0, fill=row_fill)
            pdf.cell(18, 7, str(item['qty']), border=0, fill=row_fill, align='C')
            pdf.cell(27, 7, f"{unit_price:,.2f}", border=0, fill=row_fill, align='R')
            pdf.cell(28, 7, f"{row_total:,.2f}", border=0, fill=row_fill, align='R')
            pdf.ln()
    else:
        pdf.set_x(content_left)
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(*ReceiptPDF.GREY)
        pdf.cell(180, 8, 'No item-level details were parsed from the original order message.', border=0, ln=True)

    if returned_items:
        pdf.ln(2)
        pdf.set_x(content_left)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*ReceiptPDF.NAVY)
        pdf.cell(152, 7, 'Parsed Items Total (Reference):', border=0, align='R')
        pdf.set_text_color(*ReceiptPDF.DARK)
        pdf.cell(28, 7, f"KES {items_total:,.2f}", border=0, align='R', ln=True)

    os.makedirs('instance', exist_ok=True)
    file_path = f"instance/credit_note_{credit_note.id}.pdf"
    pdf.output(file_path)
    return file_path

def send_credit_note_email(recipient_email, company_name, credit_note, inquiry, pdf_path):
    try:
        smtp_cfg = get_smtp_runtime_config()
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Credit Note {credit_note.reference} | Order GMK-00{inquiry.id}"
        msg['From'] = f"{smtp_cfg['mail_from_name']} <{smtp_cfg['sender_email']}>"
        msg['To'] = recipient_email
        apply_billing_distribution(msg)

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background:#f8fafc; margin:0; padding:24px; color:#0f172a;">
            <div style="max-width:640px; margin:0 auto; background:#ffffff; border-radius:12px; border:1px solid #e2e8f0; padding:24px;">
                <h2 style="margin-top:0; color:#0ea5e9;">Credit Note Issued</h2>
                <p>Hello <strong>{company_name}</strong>,</p>
                <p>A credit note has been issued for your order. Details are below:</p>
                <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:16px; margin:16px 0;">
                    <p style="margin:0 0 8px 0;"><strong>Credit Note:</strong> {credit_note.reference}</p>
                    <p style="margin:0 0 8px 0;"><strong>Order:</strong> GMK-00{inquiry.id}</p>
                    <p style="margin:0 0 8px 0;"><strong>Amount:</strong> KES {credit_note.amount:,.2f}</p>
                    <p style="margin:0;"><strong>Reason:</strong> {credit_note.reason}</p>
                </div>
                <p>The official credit note PDF is attached to this email.</p>
                <p style="margin-bottom:0; color:#64748b; font-size:12px;">This is an automated email from GrandMark Distributors.</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText("Your credit note has been issued. Please find attached document.", 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with open(pdf_path, 'rb') as f:
            attach = MIMEApplication(f.read(), _subtype='pdf')
            attach.add_header('Content-Disposition', 'attachment', filename=f"{credit_note.reference}.pdf")
            msg.attach(attach)

        email_ok, email_msg = smtp_send_message(msg)
        if email_ok:
            return True, email_msg
        raise RuntimeError(email_msg)
    except Exception as e:
        fallback_text = (
            f"GrandMark credit note issued: {credit_note.reference} for GMK-00{inquiry.id}. "
            f"Amount KES {credit_note.amount:,.2f}."
        )
        fallback_ok, fallback_msg = try_backup_channels(
            recipient=recipient_email,
            subject=f"Credit Note {credit_note.reference}",
            message=fallback_text,
            metadata={'inquiry_id': inquiry.id, 'credit_note_id': credit_note.id, 'type': 'credit_note'}
        )
        if fallback_ok:
            return True, f"Email failed, fallback delivered ({fallback_msg})"
        return False, f"Email failed ({e}); fallback failed ({fallback_msg})"

@app.route('/api/issue_credit_note/<int:inq_id>', methods=['POST'])
@require_permission('finance')
def issue_credit_note(inq_id):
    inquiry = Inquiry.query.get(inq_id)
    if not inquiry:
        return jsonify({"error": "Order not found"}), 404

    if 'Paid' not in inquiry.status and 'Dispatched' not in inquiry.status:
        return jsonify({"error": "Credit notes can only be issued for paid/dispatched orders."}), 400

    data = request.json or {}
    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid credit note amount."}), 400

    reason = (data.get('reason') or '').strip()
    restock = bool(data.get('restock_inventory', False))

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero."}), 400
    if not reason:
        return jsonify({"error": "Reason is required."}), 400

    order_total = extract_order_total(inquiry)
    existing_total = sum(cn.amount for cn in CreditNote.query.filter_by(inquiry_id=inq_id).all())
    if order_total > 0 and (existing_total + amount) > order_total:
        return jsonify({"error": f"Credit notes exceed billed amount. Remaining limit: KES {order_total - existing_total:,.2f}"}), 400

    reference = f"CN-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    while CreditNote.query.filter_by(reference=reference).first():
        reference = f"CN-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    credit = CreditNote(
        inquiry_id=inq_id,
        reference=reference,
        amount=amount,
        reason=reason,
        restock_inventory=restock,
        issued_by=session.get('username', 'System Admin')
    )
    db.session.add(credit)

    db.session.add(Ledger(
        transaction_type='Debit',
        amount=amount,
        description=f"Credit Note {reference} | Order GMK-00{inq_id} | {reason}"
    ))

    if restock:
        for item in parse_order_items_from_message(inquiry.message):
            db_product = Product.query.filter_by(name=item['name']).first()
            if db_product:
                db_product.stock_quantity += item['qty']

    previous_status = inquiry.status
    if 'Credit Note Issued' not in inquiry.status:
        inquiry.status = f"{inquiry.status} | Credit Note Issued"

    log_admin_action(f"Issued credit note {reference} for order GMK-00{inq_id}")
    db.session.commit()

    email_status = "not_sent"
    email_message = "Customer email skipped."
    recipient = (inquiry.contact_email or '').strip()
    try:
        pdf_path = generate_credit_note_pdf_file(credit, inquiry)
        email_ok, email_msg = send_credit_note_email(
            recipient_email=recipient,
            company_name=inquiry.company_name,
            credit_note=credit,
            inquiry=inquiry,
            pdf_path=pdf_path
        )
        email_status = "sent" if email_ok else "failed"
        email_message = email_msg
        record_credit_note_email_attempt(credit.id, recipient, email_status, email_message)
    except Exception as e:
        email_status = "failed"
        email_message = str(e)
        record_credit_note_email_attempt(credit.id, recipient, email_status, email_message)
        app.logger.error("Credit note email pipeline failed | reference=%s | error=%s", reference, str(e))

    if previous_status != inquiry.status:
        notify_inquiry_status_change(inquiry, previous_status, note=f"Credit note issued: {reference}")
    return jsonify({
        "message": f"Credit note {reference} issued successfully.",
        "reference": reference,
        "email_status": email_status,
        "email_message": email_message
    })

@app.route('/api/credit_note/<int:credit_note_id>/pdf')
@require_permission('reports')
def export_credit_note_pdf(credit_note_id):
    credit_note = CreditNote.query.get(credit_note_id)
    if not credit_note:
        return jsonify({"error": "Credit note not found"}), 404

    inquiry = Inquiry.query.get(credit_note.inquiry_id)
    if not inquiry:
        return jsonify({"error": "Associated order not found"}), 404

    file_path = generate_credit_note_pdf_file(credit_note, inquiry)
    register_document('credit_note', credit_note.reference, file_path, inquiry_id=credit_note.inquiry_id)
    db.session.commit()
    return send_file(file_path, as_attachment=True)

@app.route('/api/credit_note/<int:credit_note_id>/resend', methods=['POST'])
@require_permission('finance')
def resend_credit_note_email(credit_note_id):
    credit_note = CreditNote.query.get(credit_note_id)
    if not credit_note:
        return jsonify({'error': 'Credit note not found'}), 404

    inquiry = Inquiry.query.get(credit_note.inquiry_id)
    if not inquiry:
        return jsonify({'error': 'Associated order not found'}), 404

    recipient = (inquiry.contact_email or '').strip()
    if not recipient:
        return jsonify({'error': 'Customer email is missing for this order.'}), 400

    file_path = generate_credit_note_pdf_file(credit_note, inquiry)
    register_document('credit_note', credit_note.reference, file_path, inquiry_id=credit_note.inquiry_id)
    email_ok, email_msg = send_credit_note_email(
        recipient_email=recipient,
        company_name=inquiry.company_name,
        credit_note=credit_note,
        inquiry=inquiry,
        pdf_path=file_path
    )
    record_credit_note_email_attempt(
        credit_note.id,
        recipient,
        'sent' if email_ok else 'failed',
        email_msg
    )

    log_admin_action(f"Credit note email resend for {credit_note.reference} to {recipient} ({'success' if email_ok else 'failed'})")
    db.session.commit()

    if not email_ok:
        return jsonify({'error': f'Email resend failed: {email_msg}'}), 500

    return jsonify({'message': f'Credit note {credit_note.reference} resent to {recipient}.'})

@app.route('/api/add_revenue', methods=['POST'])
@require_permission('finance')
def add_revenue():
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
    You are the official AI Assistant for GrandMark Distributors, Kenya's premier wholesale sourcing and distribution enterprise based in Nairobi.
    
    CRITICAL RULES:
    1. Keep answers brief, professional, and under 3 sentences.
    2. DO NOT use markdown formatting (no asterisks or bold text).
    3. Only quote products and prices from the LIVE INVENTORY DATA. If not listed, say: "We do not currently stock that item."
    4. Emphasize our business model: We source high-quality FMCG, hardware, and electronics locally from Kenyan manufacturers and abroad, and distribute them to local retailers using our robust in-house logistics fleet.
    
    --- PLATFORM SITE MAP & CAPABILITIES ---
    - Catalog Page: Public view of our globally and locally sourced warehouse stock.
    - Order Portal: Where local businesses submit bulk wholesale procurement orders.
    - Client Gateway: Secure portal where retailers approve orders and pay instantly via Safaricom M-PESA.
    - Supplier Portal: Where global partners and local manufacturers apply to supply our Nairobi warehouse.
    - Local Logistics: We handle all last-mile delivery to businesses across Kenya.
    
    --- LIVE INVENTORY DATA ---
    {inventory_data}
    ---------------------------
    
    USER MESSAGE: {user_message}
    """
    
    try:
        client = get_ai_client()
        if not client:
            return jsonify({"reply": "AI assistant is currently offline. Please contact the GrandMark Executive Team."})

        response = client.models.generate_content(
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