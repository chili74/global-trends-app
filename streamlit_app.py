import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io
import json
import threading
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from groq import Groq
from duckduckgo_search import DDGS
from dotenv import load_dotenv

load_dotenv()

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="Global Trends AI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS
# ============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    h1, h2, h3 {
        font-family: 'Syne', sans-serif !important;
        font-weight: 700;
    }
    .stMetric {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
        border: 1px solid #2d2d4e;
        border-radius: 12px;
        padding: 1rem;
    }
    .agent-card {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
        border: 1px solid #2d2d4e;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        position: relative;
        overflow: hidden;
    }
    .agent-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #00d4ff, #7b2fff, #ff6b35);
    }
    .agent-active { border-color: #00d4ff; }
    .agent-warning { border-color: #ffaa00; }
    .agent-error { border-color: #ff4444; }
    .status-dot {
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }
    .dot-green { background: #00ff88; }
    .dot-yellow { background: #ffaa00; }
    .dot-red { background: #ff4444; }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    .alert-box {
        background: rgba(255, 170, 0, 0.1);
        border: 1px solid #ffaa00;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .alert-box-red {
        background: rgba(255, 68, 68, 0.1);
        border: 1px solid #ff4444;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .alert-box-green {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid #00ff88;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    div[data-testid="stSidebarNav"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ============================================
# DATABASE INITIALIZATION
# ============================================
DB_PATH = os.path.join('/tmp', 'global.db')


def init_database():
    required_tables = {'suppliers', 'product', 'retailers', 'customers', 'inventory',
                       'chart_of_accounts', 'accounts_receivable', 'accounts_payable',
                       'drawings', 'transactions', 'performance_notes',
                       'agent_logs', 'agent_alerts'}
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing = {row[0] for row in cursor.fetchall()}
            conn.close()
            if required_tables.issubset(existing):
                return
            os.remove(DB_PATH)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        supplier_ID VARCHAR(10) PRIMARY KEY, supplier_Name VARCHAR(100) NOT NULL,
        Account VARCHAR(100), wechat_Contact VARCHAR(100), Website VARCHAR(255), products TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS product (
        product_ID VARCHAR(10) PRIMARY KEY, product_Categories VARCHAR(100),
        products_ID VARCHAR(100), supplier_ID VARCHAR(10), supplier_Type VARCHAR(50),
        MOQ VARCHAR(50), lead_Times VARCHAR(50), unit_Cost DECIMAL(10,2), selling_Price DECIMAL(10,2),
        FOREIGN KEY (supplier_ID) REFERENCES suppliers(supplier_ID))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS retailers (
        retailer_ID VARCHAR(10) PRIMARY KEY, retailer_Name VARCHAR(100) NOT NULL,
        status VARCHAR(20), order_Quantity VARCHAR(50), product TEXT,
        order_Status VARCHAR(50), management_Contacts VARCHAR(100), payment_Terms VARCHAR(50))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS customers (
        customer_ID VARCHAR(10) PRIMARY KEY, customer_Name VARCHAR(100) NOT NULL,
        contact_Number VARCHAR(20), email VARCHAR(100), total_orders INT DEFAULT 0,
        total_spent DECIMAL(10,2) DEFAULT 0.00, outstanding_balance DECIMAL(10,2) DEFAULT 0.00,
        last_order_date DATE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
        inventory_ID VARCHAR(10) PRIMARY KEY, product_ID VARCHAR(10), product_Name VARCHAR(100),
        stock_on_hand INT, reorder_level INT, reorder_quantity INT, location VARCHAR(50),
        last_updated DATE, FOREIGN KEY (product_ID) REFERENCES product(product_ID))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS chart_of_accounts (
        account_ID VARCHAR(10) PRIMARY KEY, account_Name VARCHAR(100),
        account_Type VARCHAR(50), balance DECIMAL(12,2))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts_receivable (
        receivable_ID VARCHAR(10) PRIMARY KEY, customer_ID VARCHAR(10),
        customer_Name VARCHAR(100), invoice_Date DATE, due_Date DATE,
        invoice_Amount DECIMAL(10,2), amount_Paid DECIMAL(10,2) DEFAULT 0.00,
        outstanding_Balance DECIMAL(10,2), status VARCHAR(20))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts_payable (
        payable_ID VARCHAR(10) PRIMARY KEY, supplier_ID VARCHAR(10),
        supplier_Name VARCHAR(100), invoice_Date DATE, due_Date DATE,
        invoice_Amount DECIMAL(10,2), amount_Paid DECIMAL(10,2) DEFAULT 0.00,
        outstanding_Balance DECIMAL(10,2), status VARCHAR(20),
        FOREIGN KEY (supplier_ID) REFERENCES suppliers(supplier_ID))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS drawings (
        drawing_ID VARCHAR(10) PRIMARY KEY, date DATE, amount DECIMAL(10,2),
        description VARCHAR(200), notes TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        transaction_ID VARCHAR(10) PRIMARY KEY, date DATE, description VARCHAR(200),
        account_Debit VARCHAR(10), account_Credit VARCHAR(10), amount DECIMAL(10,2), category VARCHAR(50))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS performance_notes (
        supplier_ID VARCHAR(10) PRIMARY KEY, supplier_Rating INT, Priority VARCHAR(20), Notes TEXT,
        FOREIGN KEY (supplier_ID) REFERENCES suppliers(supplier_ID))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS agent_logs (
        log_ID INTEGER PRIMARY KEY AUTOINCREMENT, agent_name VARCHAR(50),
        action_taken TEXT, result TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, severity VARCHAR(20))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS agent_alerts (
        alert_ID INTEGER PRIMARY KEY AUTOINCREMENT, agent_name VARCHAR(50),
        alert_type VARCHAR(50), message TEXT, is_read INTEGER DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    suppliers_data = [
        ('s001', 'Huasheng Textiles Co., Ltd.', 'Wang Wei', 'wangwei_huasheng', 'www.huashengtextiles.cn',
         'Blankets, Bedding, Curtains'),
        ('s002', 'Jiangnan Ceramics Manufacturing', 'Li Fang', 'lifang_jiangnan', 'www.jiangnanporcelain.cn',
         'Pots, Vases, Dinnerware'),
        ('s003', 'Fareast Home Furnishings', 'Chen Min', 'chenmin_fareast', 'www.fareasthome.cn',
         'Curtains, Table Linens, Cushions'),
        ('s004', 'Xinguang Plastic Products', 'Zhang Yong', 'zhangyong_xinguang', 'www.xinguangplastic.cn',
         'Storage Containers, Organizers'),
        ('s005', 'Ruixiang Textiles Import', 'Liu Na', 'liuna_ruixiang', 'www.ruixiangtextile.cn',
         'Bed Sheets, Pillowcases')
    ]
    cursor.executemany('INSERT INTO suppliers VALUES (?,?,?,?,?,?)', suppliers_data)

    product_data = [
        ('p001', 'Bedding', 'Egyptian Cotton Bed Sheet Set', 's001', 'Manufacturer', '20 units', '15 days', 187.50, 399.00),
        ('p002', 'Bedding', 'Microfleece Blanket - Queen', 's001', 'Manufacturer', '30 units', '12 days', 124.75, 279.00),
        ('p003', 'Curtains', 'Thermal Blackout Curtains', 's003', 'Wholesaler', '15 pairs', '10 days', 213.00, 449.00),
        ('p004', 'Pots', 'Glazed Ceramic Flower Pot Set', 's002', 'Manufacturer', '10 sets', '20 days', 156.25, 349.00),
        ('p005', 'Bedding', 'Organic Bamboo Pillowcase Set', 's005', 'Manufacturer', '25 units', '14 days', 94.50, 199.00),
        ('p006', 'Curtains', 'Sheer Voile Curtains - Ivory', 's003', 'Wholesaler', '20 pairs', '10 days', 114.25, 259.00),
        ('p007', 'Pots', 'Handcrafted Stoneware Vase', 's002', 'Manufacturer', '8 units', '18 days', 88.75, 189.00),
        ('p008', 'Storage', 'Airtight Food Storage Set (5pc)', 's004', 'Manufacturer', '40 units', '7 days', 47.25, 119.00),
        ('p009', 'Bedding', 'Weighted Blanket - 6.8kg', 's005', 'Manufacturer', '15 units', '21 days', 291.50, 599.00),
        ('p010', 'Storage', 'Woven Bamboo Storage Baskets', 's004', 'Distributor', '25 units', '10 days', 67.80, 159.00)
    ]
    cursor.executemany('INSERT INTO product VALUES (?,?,?,?,?,?,?,?,?)', product_data)

    retailers_data = [
        ('r001', 'Takealot', 'Active', '48 units', 'Egyptian Cotton Bed Sheet Set, Microfleece Blanket', 'Shipped',
         'Sarah van der Merwe', 'Net 30'),
        ('r002', 'Makro', 'Active', '32 units', 'Thermal Blackout Curtains, Glazed Ceramic Flower Pot Set',
         'Processing', 'James Nkosi', 'Net 30'),
        ('r003', 'Woolworths', 'Potential', '0 units', 'Organic Bamboo Pillowcase Set', 'Pending', 'Michelle Govender',
         'To be confirmed'),
        ('r004', 'Game', 'Potential', '0 units', 'Airtight Food Storage Set', 'Negotiating', 'David Ngwenya',
         'To be confirmed'),
        ('r005', 'Checkers', 'Potential', '0 units', 'Sheer Voile Curtains', 'Quotation Sent', 'Linda Petersen',
         'To be confirmed')
    ]
    cursor.executemany('INSERT INTO retailers VALUES (?,?,?,?,?,?,?,?)', retailers_data)

    customers_data = [
        ('c001', 'Nomusa Dlamini', '082 123 4567', 'nomusa.dlamini@email.com', 2, 897.00, 0.00, '2025-03-20'),
        ('c002', 'Thabo Nkosi', '083 234 5678', 'thabo.nkosi@email.com', 1, 399.00, 0.00, '2025-03-12'),
        ('c003', 'Lerato Molefe', '084 345 6789', 'lerato.molefe@email.com', 3, 1187.00, 0.00, '2025-03-25'),
        ('c004', 'Sipho Mbele', '081 456 7890', 'sipho.mbele@email.com', 1, 279.00, 279.00, '2025-03-10'),
        ('c005', 'Priya Naidoo', '082 567 8901', 'priya.naidoo@email.com', 2, 798.00, 0.00, '2025-03-22'),
        ('c006', 'Johan Pretorius', '083 678 9012', 'johan.pretorius@email.com', 1, 449.00, 449.00, '2025-03-05'),
        ('c007', 'Zanele Khumalo', '084 789 0123', 'zanele.khumalo@email.com', 2, 618.00, 0.00, '2025-02-15'),
        ('c008', 'Michael Chen', '081 890 1234', 'michael.chen@email.com', 1, 199.00, 199.00, '2025-03-10'),
        ('c009', 'Fatima Patel', '082 901 2345', 'fatima.patel@email.com', 1, 349.00, 0.00, '2025-03-23'),
        ('c010', 'David Mokoena', '083 012 3456', 'david.mokoena@email.com', 1, 189.00, 0.00, '2025-02-10')
    ]
    cursor.executemany('INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)', customers_data)

    inventory_data = [
        ('inv001', 'p001', 'Egyptian Cotton Bed Sheet Set', 12, 10, 20, 'Warehouse A', '2025-03-20'),
        ('inv002', 'p002', 'Microfleece Blanket - Queen', 8, 10, 30, 'Warehouse A', '2025-03-20'),
        ('inv003', 'p003', 'Thermal Blackout Curtains', 5, 8, 15, 'Warehouse A', '2025-03-20'),
        ('inv004', 'p004', 'Glazed Ceramic Flower Pot Set', 4, 5, 10, 'Warehouse B', '2025-03-20'),
        ('inv005', 'p005', 'Organic Bamboo Pillowcase Set', 15, 10, 25, 'Warehouse A', '2025-03-20'),
        ('inv006', 'p006', 'Sheer Voile Curtains - Ivory', 10, 8, 20, 'Warehouse A', '2025-03-20'),
        ('inv007', 'p007', 'Handcrafted Stoneware Vase', 3, 4, 8, 'Warehouse B', '2025-03-20'),
        ('inv008', 'p008', 'Airtight Food Storage Set (5pc)', 25, 15, 40, 'Warehouse B', '2025-03-20'),
        ('inv009', 'p009', 'Weighted Blanket - 6.8kg', 2, 3, 15, 'Warehouse A', '2025-03-20'),
        ('inv010', 'p010', 'Woven Bamboo Storage Baskets', 8, 10, 25, 'Warehouse B', '2025-03-20')
    ]
    cursor.executemany('INSERT INTO inventory VALUES (?,?,?,?,?,?,?,?)', inventory_data)

    performance_notes_data = [
        ('s001', 5, 'Main', 'Reliable manufacturer, excellent quality bedding. Communication with Wang Wei is prompt.'),
        ('s002', 4, 'Main', 'Beautiful ceramic products. Li Fang is very helpful. Lead times can be longer during peak season.'),
        ('s003', 4, 'Alternative', 'Good wholesale pricing. Chen Min responds quickly. Quality consistent.'),
        ('s004', 3, 'Reserve', 'Zhang Yong is professional but MOQ is high. Testing smaller orders first.'),
        ('s005', 5, 'Main', 'Liu Na provides excellent customer service. Premium bedding products. Highly recommended.')
    ]
    cursor.executemany('INSERT INTO performance_notes VALUES (?,?,?,?)', performance_notes_data)

    chart_of_accounts_data = [
        ('a001', 'Cash on Hand', 'Asset', 81025.00), ('a002', 'Bank Account', 'Asset', 44275.00),
        ('a003', 'Inventory', 'Asset', 84750.00), ('a004', 'Accounts Receivable', 'Asset', 32935.00),
        ('a005', 'Equipment & Furniture', 'Asset', 14850.00),
        ('a006', 'Loan Payable - First National Bank', 'Liability', 50000.00),
        ('a007', 'Accounts Payable', 'Liability', 20375.00),
        ('a008', "Owner's Equity - Capital", 'Equity', 150000.00),
        ('a009', 'Retained Earnings', 'Equity', 0.00), ('a010', 'Sales Revenue', 'Income', 0.00),
        ('a011', 'Cost of Goods Sold', 'Expense', 0.00), ('a012', 'Operating Expenses', 'Expense', 0.00)
    ]
    cursor.executemany('INSERT INTO chart_of_accounts VALUES (?,?,?,?)', chart_of_accounts_data)

    accounts_receivable_data = [
        ('ar001', 'c004', 'Sipho Mbele', '2025-03-01', '2025-03-31', 279.00, 0.00, 279.00, 'Overdue'),
        ('ar002', 'c006', 'Johan Pretorius', '2025-03-05', '2025-04-04', 449.00, 0.00, 449.00, 'Current'),
        ('ar003', 'c008', 'Michael Chen', '2025-03-10', '2025-04-09', 199.00, 0.00, 199.00, 'Current'),
        ('ar004', 'r001', 'Takealot', '2025-03-15', '2025-04-14', 16248.00, 0.00, 16248.00, 'Current'),
        ('ar005', 'r002', 'Makro', '2025-03-18', '2025-04-17', 12760.00, 0.00, 12760.00, 'Current'),
        ('ar006', 'c001', 'Nomusa Dlamini', '2025-03-20', '2025-04-19', 897.00, 897.00, 0.00, 'Paid'),
        ('ar007', 'c005', 'Priya Naidoo', '2025-03-22', '2025-04-21', 798.00, 0.00, 798.00, 'Current'),
        ('ar008', 'c009', 'Fatima Patel', '2025-03-23', '2025-04-22', 349.00, 349.00, 0.00, 'Paid'),
        ('ar009', 'c010', 'David Mokoena', '2025-03-24', '2025-04-23', 189.00, 189.00, 0.00, 'Paid'),
        ('ar010', 'c003', 'Lerato Molefe', '2025-03-25', '2025-04-24', 1187.00, 1187.00, 0.00, 'Paid')
    ]
    cursor.executemany('INSERT INTO accounts_receivable VALUES (?,?,?,?,?,?,?,?,?)', accounts_receivable_data)

    accounts_payable_data = [
        ('ap001', 's001', 'Huasheng Textiles', '2025-03-01', '2025-03-31', 24875.00, 24875.00, 0.00, 'Paid'),
        ('ap002', 's002', 'Jiangnan Ceramics', '2025-03-05', '2025-04-04', 8475.00, 0.00, 8475.00, 'Current'),
        ('ap003', 's003', 'Fareast Home Furnishings', '2025-03-10', '2025-04-09', 11900.00, 0.00, 11900.00, 'Current'),
        ('ap004', 's004', 'Xinguang Plastic Products', '2025-03-12', '2025-04-11', 5925.00, 5925.00, 0.00, 'Paid'),
        ('ap005', 's005', 'Ruixiang Textiles Import', '2025-03-15', '2025-04-14', 12750.00, 12750.00, 0.00, 'Paid')
    ]
    cursor.executemany('INSERT INTO accounts_payable VALUES (?,?,?,?,?,?,?,?,?)', accounts_payable_data)

    drawings_data = [
        ('d001', '2025-03-05', 5250.00, 'Owner salary - March', 'Monthly salary'),
        ('d002', '2025-03-20', 2375.00, 'Personal expenses', 'Business expenses'),
        ('d003', '2025-03-28', 1200.00, 'Family emergency withdrawal', 'Temporary draw')
    ]
    cursor.executemany('INSERT INTO drawings VALUES (?,?,?,?,?)', drawings_data)

    transactions_data = [
        ('t001', '2025-03-01', 'Initial capital deposit', 'a002', 'a008', 150000.00, 'Capital'),
        ('t002', '2025-03-01', 'Bank loan received - FNB', 'a002', 'a006', 50000.00, 'Financing'),
        ('t003', '2025-03-02', 'Initial inventory purchase', 'a003', 'a002', 84750.00, 'Purchase'),
        ('t004', '2025-03-02', 'Equipment purchase (shelving, POS)', 'a005', 'a002', 14850.00, 'Asset'),
        ('t005', '2025-03-05', 'Owner drawing - March salary', 'a008', 'a002', 5250.00, 'Drawings'),
        ('t006', '2025-03-08', 'Marketing expense - Social media ads', 'a012', 'a002', 2250.00, 'Expense'),
        ('t007', '2025-03-10', 'Sale to Sipho Mbele (c004)', 'a004', 'a010', 279.00, 'Sale'),
        ('t008', '2025-03-10', 'COGS for sale to Sipho Mbele', 'a011', 'a003', 124.75, 'Cost'),
        ('t009', '2025-03-12', 'Sale to Thabo Nkosi (c002)', 'a004', 'a010', 399.00, 'Sale'),
        ('t010', '2025-03-12', 'COGS for sale to Thabo Nkosi', 'a011', 'a003', 187.50, 'Cost'),
        ('t011', '2025-03-15', 'Sale to Takealot (r001)', 'a004', 'a010', 16248.00, 'Sale'),
        ('t012', '2025-03-15', 'COGS for Takealot sale', 'a011', 'a003', 7824.00, 'Cost'),
        ('t013', '2025-03-18', 'Sale to Makro (r002)', 'a004', 'a010', 12760.00, 'Sale'),
        ('t014', '2025-03-18', 'COGS for Makro sale', 'a011', 'a003', 6228.00, 'Cost'),
        ('t015', '2025-03-20', 'Owner drawing - Personal expenses', 'a008', 'a002', 2375.00, 'Drawings'),
        ('t016', '2025-03-20', 'Marketing expense - Influencer campaign', 'a012', 'a002', 3250.00, 'Expense'),
        ('t017', '2025-03-20', 'Sale to Nomusa Dlamini (c001)', 'a004', 'a010', 897.00, 'Sale'),
        ('t018', '2025-03-20', 'COGS for sale to Nomusa Dlamini', 'a011', 'a003', 438.25, 'Cost'),
        ('t019', '2025-03-22', 'Sale to Priya Naidoo (c005)', 'a004', 'a010', 798.00, 'Sale'),
        ('t020', '2025-03-22', 'COGS for sale to Priya Naidoo', 'a011', 'a003', 389.50, 'Cost'),
        ('t021', '2025-03-23', 'Sale to Fatima Patel (c009)', 'a004', 'a010', 349.00, 'Sale'),
        ('t022', '2025-03-23', 'COGS for sale to Fatima Patel', 'a011', 'a003', 156.25, 'Cost'),
        ('t023', '2025-03-24', 'Sale to David Mokoena (c010)', 'a004', 'a010', 189.00, 'Sale'),
        ('t024', '2025-03-24', 'COGS for sale to David Mokoena', 'a011', 'a003', 88.75, 'Cost'),
        ('t025', '2025-03-25', 'Sale to Lerato Molefe (c003)', 'a004', 'a010', 1187.00, 'Sale'),
        ('t026', '2025-03-25', 'COGS for sale to Lerato Molefe', 'a011', 'a003', 578.50, 'Cost'),
        ('t027', '2025-03-25', 'Payment to Huasheng Textiles (s001)', 'a007', 'a002', 24875.00, 'Payment'),
        ('t028', '2025-03-28', 'Owner drawing - Family emergency', 'a008', 'a002', 1200.00, 'Drawings'),
        ('t029', '2025-03-28', 'Marketing expense - Flyers & signage', 'a012', 'a002', 2000.00, 'Expense'),
        ('t030', '2025-03-30', 'Operating expense - Utilities', 'a012', 'a002', 1875.00, 'Expense')
    ]
    cursor.executemany('INSERT INTO transactions VALUES (?,?,?,?,?,?,?)', transactions_data)

    conn.commit()
    conn.close()


try:
    init_database()
except Exception as e:
    st.error(f"Database initialisation error: {e}")
    st.stop()

# ============================================
# API KEY CHECK  ← FIXED: reads st.secrets first, falls back to os.getenv
# ============================================
try:
    groq_api_key = st.secrets.get("GROQ_API_KEY")
except Exception:
    groq_api_key = None
groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
if not groq_api_key:
    st.error("🚨 GROQ_API_KEY is not set. Add it to Streamlit secrets or your .env file.")
    st.stop()

groq_client = Groq(api_key=groq_api_key)


# ============================================
# NOTIFICATION HELPERS
# ============================================
def get_email_config():
    config = {}
    try:
        config['smtp_server'] = st.secrets.get("SMTP_SERVER", "")
        config['smtp_port'] = int(st.secrets.get("SMTP_PORT", 587))
        config['sender_email'] = st.secrets.get("SENDER_EMAIL", "")
        config['sender_password'] = st.secrets.get("SENDER_PASSWORD", "")
        if config['sender_email'] and config['sender_password']:
            return config
    except Exception:
        pass
    config['smtp_server'] = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    config['smtp_port'] = int(os.getenv("SMTP_PORT", 587))
    config['sender_email'] = os.getenv("SENDER_EMAIL", "")
    config['sender_password'] = os.getenv("SENDER_PASSWORD", "")
    return config


EMAIL_CONFIG = get_email_config()


def send_email_notification(subject, body, recipient=None):
    if not EMAIL_CONFIG['sender_email'] or not EMAIL_CONFIG['sender_password']:
        return False, "Email not configured"
    try:
        to = recipient or EMAIL_CONFIG['sender_email']
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        return True, "Email sent"
    except Exception as e:
        return False, str(e)


def send_whatsapp_notification(message, phone=None):
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_whatsapp = os.getenv("TWILIO_WHATSAPP_FROM", "")
    owner_phone = phone or os.getenv("OWNER_WHATSAPP", "")
    if not all([twilio_sid, twilio_token, twilio_whatsapp, owner_phone]):
        return False, "WhatsApp (Twilio) not configured"
    try:
        from twilio.rest import Client
        client = Client(twilio_sid, twilio_token)
        client.messages.create(body=message, from_=f"whatsapp:{twilio_whatsapp}", to=f"whatsapp:{owner_phone}")
        return True, "WhatsApp sent"
    except Exception as e:
        return False, str(e)


def log_agent_action(agent_name, action, result, severity="info"):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_logs (agent_name, action_taken, result, severity) VALUES (?,?,?,?)",
                       (agent_name, action, result, severity))
        conn.commit()
        conn.close()
    except Exception:
        pass


def create_alert(agent_name, alert_type, message):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO agent_alerts (agent_name, alert_type, message) VALUES (?,?,?)",
                       (agent_name, alert_type, message))
        conn.commit()
        conn.close()
    except Exception:
        pass


def notify_all(subject, message, severity="info"):
    create_alert("System", severity, message)
    send_email_notification(f"[Global Trends AI] {subject}", message)
    send_whatsapp_notification(f"🌍 Global Trends AI\n{subject}\n\n{message}")


# ============================================
# DATABASE QUERY HELPERS
# ============================================
@st.cache_data(ttl=60, show_spinner=False)
def get_suppliers():
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query("SELECT * FROM suppliers", conn)
    finally:
        conn.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_products():
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(
            "SELECT p.*, s.supplier_Name FROM product p LEFT JOIN suppliers s ON p.supplier_ID = s.supplier_ID", conn)
    finally:
        conn.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_retailers():
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query("SELECT * FROM retailers", conn)
    finally:
        conn.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_customers():
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query("SELECT * FROM customers", conn)
    finally:
        conn.close()


@st.cache_data(ttl=30, show_spinner=False)
def get_inventory():
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query("""SELECT i.*, p.selling_Price, p.unit_Cost
                                    FROM inventory i
                                    LEFT JOIN product p ON i.product_ID = p.product_ID
                                    ORDER BY i.stock_on_hand ASC""", conn)
    finally:
        conn.close()


@st.cache_data(ttl=300, show_spinner=False)
def get_financial_summary():
    conn = sqlite3.connect(DB_PATH)
    try:
        sales = pd.read_sql_query("SELECT SUM(invoice_Amount) as v FROM accounts_receivable", conn)
        ar = pd.read_sql_query("SELECT SUM(outstanding_Balance) as v FROM accounts_receivable WHERE status != 'Paid'", conn)
        ap = pd.read_sql_query("SELECT SUM(outstanding_Balance) as v FROM accounts_payable WHERE status != 'Paid'", conn)
        drawings = pd.read_sql_query("SELECT SUM(amount) as v FROM drawings", conn)
        return {
            'total_sales': sales['v'].iloc[0] or 0,
            'total_ar': ar['v'].iloc[0] or 0,
            'total_ap': ap['v'].iloc[0] or 0,
            'total_drawings': drawings['v'].iloc[0] or 0
        }
    finally:
        conn.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_performance():
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query("""SELECT s.supplier_Name, p.supplier_Rating, p.Priority, p.Notes
                                    FROM performance_notes p
                                    JOIN suppliers s ON p.supplier_ID = s.supplier_ID
                                    ORDER BY p.supplier_Rating DESC""", conn)
    except Exception as e:
        st.error(f"Performance query error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def query_database(query):
    conn = sqlite3.connect(DB_PATH)
    try:
        if query.strip().upper().startswith('SELECT'):
            df = pd.read_sql_query(query, conn)
            return df.to_string()
        return "Only SELECT queries allowed."
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()


# ============================================
# 7 AUTONOMOUS AI AGENTS
# ============================================

def run_stock_monitor_agent():
    try:
        conn = sqlite3.connect(DB_PATH)
        low_stock = pd.read_sql_query("""
            SELECT i.product_Name, i.stock_on_hand, i.reorder_level, i.reorder_quantity,
                   p.supplier_ID, s.supplier_Name, s.Account
            FROM inventory i
            LEFT JOIN product p ON i.product_ID = p.product_ID
            LEFT JOIN suppliers s ON p.supplier_ID = s.supplier_ID
            WHERE i.stock_on_hand <= i.reorder_level
        """, conn)
        critical = pd.read_sql_query("""
            SELECT product_Name, stock_on_hand, reorder_level
            FROM inventory WHERE stock_on_hand = 0
        """, conn)
        conn.close()

        if low_stock.empty:
            log_agent_action("Stock Monitor", "Inventory check", "All stock levels healthy ✅", "info")
            return {"status": "healthy", "alerts": [], "low_stock": pd.DataFrame()}

        stock_summary = low_stock[['product_Name', 'stock_on_hand', 'reorder_level', 'reorder_quantity', 'supplier_Name']].to_string()
        reasoning = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"""You are an inventory management agent for Global Trends.
Analyze this low stock situation and provide:
1. Urgency level (CRITICAL/HIGH/MEDIUM) for each item
2. Recommended action for each
3. One sentence summary for business owner

Low stock items:
{stock_summary}

Format as: ITEM | URGENCY | ACTION
Then: SUMMARY: <one sentence>"""}],
            max_tokens=500, temperature=0.1
        ).choices[0].message.content

        actions_taken = []
        for _, row in low_stock.iterrows():
            msg = f"⚠️ LOW STOCK: {row['product_Name']} has {row['stock_on_hand']} units (reorder level: {row['reorder_level']}). Supplier: {row['supplier_Name']}. Reorder {row['reorder_quantity']} units."
            create_alert("Stock Monitor", "low_stock", msg)
            actions_taken.append(msg)

        if not critical.empty:
            for _, row in critical.iterrows():
                msg = f"🚨 CRITICAL: {row['product_Name']} is OUT OF STOCK!"
                create_alert("Stock Monitor", "critical_stock", msg)
                notify_all("CRITICAL: Out of Stock", msg, "critical")

        summary_msg = f"Stock Monitor Agent Report\n\n{len(low_stock)} products below reorder level.\n\nAI Analysis:\n{reasoning}"
        send_email_notification("⚠️ Stock Alert - Action Required", summary_msg)
        send_whatsapp_notification(f"⚠️ Stock Alert: {len(low_stock)} products need reordering. Check your dashboard.")
        log_agent_action("Stock Monitor", f"Checked inventory, found {len(low_stock)} low stock items",
                         f"Notifications sent. {reasoning[:200]}", "warning")

        return {"status": "alerts", "alerts": actions_taken, "reasoning": reasoning, "low_stock": low_stock}

    except Exception as e:
        log_agent_action("Stock Monitor", "Inventory check failed", str(e), "error")
        return {"status": "error", "error": str(e)}


def run_ar_collection_agent():
    try:
        conn = sqlite3.connect(DB_PATH)
        overdue = pd.read_sql_query("""
            SELECT receivable_ID, customer_Name, customer_ID, due_Date, outstanding_Balance, invoice_Date,
                   CAST(julianday('now') - julianday(due_Date) AS INTEGER) as days_overdue
            FROM accounts_receivable
            WHERE status != 'Paid' AND outstanding_Balance > 0 AND due_Date < date('now')
            ORDER BY days_overdue DESC
        """, conn)
        conn.close()

        if overdue.empty:
            log_agent_action("AR Collection", "Checked receivables", "No overdue invoices ✅", "info")
            return {"status": "healthy", "overdue": pd.DataFrame(), "actions": []}

        actions = []
        for _, row in overdue.iterrows():
            days = int(row['days_overdue']) if pd.notna(row['days_overdue']) else 0
            amount = float(row['outstanding_Balance'])
            customer = row['customer_Name']
            inv_id = row['receivable_ID']

            if days >= 30:
                msg = f"🚨 FINAL NOTICE [{inv_id}]: {customer} owes R{amount:,.2f} — {days} days overdue. Escalate immediately."
                create_alert("AR Collection", "final_notice", msg)
                notify_all(f"Final Notice: {customer}", msg, "critical")
                actions.append({"customer": customer, "action": "Final notice sent", "days": days, "amount": amount})
            elif days >= 14:
                msg = f"⚠️ FIRM REMINDER [{inv_id}]: {customer} owes R{amount:,.2f} — {days} days overdue."
                create_alert("AR Collection", "firm_reminder", msg)
                send_email_notification(f"Overdue Invoice Reminder - {customer}", msg)
                actions.append({"customer": customer, "action": "Firm reminder sent", "days": days, "amount": amount})
            elif days >= 7:
                msg = f"📬 REMINDER [{inv_id}]: {customer} has an outstanding balance of R{amount:,.2f} — {days} days overdue."
                create_alert("AR Collection", "gentle_reminder", msg)
                actions.append({"customer": customer, "action": "Gentle reminder logged", "days": days, "amount": amount})

        total_overdue = overdue['outstanding_Balance'].sum()
        log_agent_action("AR Collection", f"Processed {len(overdue)} overdue invoices",
                         f"Total at risk: R{total_overdue:,.2f}. Actions: {len(actions)}", "warning")

        return {"status": "overdue_found", "overdue": overdue, "actions": actions, "total": total_overdue}

    except Exception as e:
        log_agent_action("AR Collection", "Failed", str(e), "error")
        return {"status": "error", "error": str(e)}


def run_supplier_performance_agent():
    try:
        conn = sqlite3.connect(DB_PATH)
        suppliers = pd.read_sql_query("""
            SELECT s.supplier_ID, s.supplier_Name, p.supplier_Rating, p.Priority, p.Notes,
                   COUNT(ap.payable_ID) as invoice_count, SUM(ap.invoice_Amount) as total_spent
            FROM suppliers s
            LEFT JOIN performance_notes p ON s.supplier_ID = p.supplier_ID
            LEFT JOIN accounts_payable ap ON s.supplier_ID = ap.supplier_ID
            GROUP BY s.supplier_ID
        """, conn)
        conn.close()

        supplier_data = suppliers[['supplier_Name', 'supplier_Rating', 'Priority', 'total_spent']].to_string()
        analysis = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"""You are a supplier performance agent for Global Trends.
Analyze these suppliers and:
1. Identify any underperforming suppliers (rating < 4)
2. Recommend priority changes if needed
3. Flag any risks
4. Suggest one strategic action

Supplier data:
{supplier_data}

Be concise. Format as:
HEALTH: Good/At Risk/Critical
UNDERPERFORMERS: <list or None>
RISKS: <list or None>
RECOMMENDATION: <one action>"""}],
            max_tokens=400, temperature=0.1
        ).choices[0].message.content

        alerts = []
        if not suppliers.empty:
            low_rated = suppliers[pd.to_numeric(suppliers['supplier_Rating'], errors='coerce') < 4]
            for _, row in low_rated.iterrows():
                msg = f"⚠️ Supplier {row['supplier_Name']} has a low rating of {row['supplier_Rating']}⭐. Consider reviewing or finding alternatives."
                create_alert("Supplier Performance", "low_rating", msg)
                alerts.append(msg)

        log_agent_action("Supplier Performance", "Evaluated all suppliers", analysis[:300], "info")
        return {"status": "complete", "analysis": analysis, "suppliers": suppliers, "alerts": alerts}

    except Exception as e:
        log_agent_action("Supplier Performance", "Failed", str(e), "error")
        return {"status": "error", "error": str(e)}


def run_sales_forecasting_agent():
    try:
        conn = sqlite3.connect(DB_PATH)
        sales = pd.read_sql_query("""
            SELECT t.date, t.description, t.amount, t.category
            FROM transactions t
            WHERE t.category IN ('Sale', 'Cost')
            ORDER BY t.date
        """, conn)
        inventory = pd.read_sql_query("""
            SELECT i.product_Name, i.stock_on_hand, i.reorder_quantity, p.selling_Price, p.unit_Cost
            FROM inventory i JOIN product p ON i.product_ID = p.product_ID
        """, conn)
        conn.close()

        sales_summary = f"Total transactions: {len(sales)}\nTotal sales value: R{sales[sales['category'] == 'Sale']['amount'].sum():,.2f}"
        inv_summary = inventory[['product_Name', 'stock_on_hand', 'reorder_quantity']].to_string()

        forecast = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"""You are a sales forecasting agent for Global Trends, a home goods trading company.
Based on the sales data and inventory below, provide:
1. Top performing product categories (infer from descriptions)
2. Demand trend (growing/stable/declining)
3. Stock recommendations — which products to increase reorder quantities for
4. Revenue forecast for next 30 days
5. One strategic insight

Sales data:
{sales_summary}

Current inventory:
{inv_summary}

Be specific and actionable. Keep it concise."""}],
            max_tokens=500, temperature=0.2
        ).choices[0].message.content

        create_alert("Sales Forecasting", "forecast_ready", f"📈 New forecast generated: {forecast[:150]}...")
        log_agent_action("Sales Forecasting", "Generated demand forecast", forecast[:300], "info")

        return {"status": "complete", "forecast": forecast, "sales": sales, "inventory": inventory}

    except Exception as e:
        log_agent_action("Sales Forecasting", "Failed", str(e), "error")
        return {"status": "error", "error": str(e)}


def run_crm_agent():
    try:
        conn = sqlite3.connect(DB_PATH)
        customers = pd.read_sql_query("""
            SELECT customer_ID, customer_Name, email, contact_Number, total_orders, total_spent,
                   outstanding_balance, last_order_date,
                   CAST(julianday('now') - julianday(COALESCE(last_order_date, '2025-01-01')) AS INTEGER) as days_since_order
            FROM customers ORDER BY total_spent DESC
        """, conn)
        conn.close()

        actions = []
        if 'days_since_order' in customers.columns:
            at_risk = customers[customers['days_since_order'] >= 30]
            for _, row in at_risk.iterrows():
                days = int(row['days_since_order']) if pd.notna(row['days_since_order']) else 0
                msg = f"👤 AT RISK: {row['customer_Name']} hasn't ordered in {days} days. Last spent R{row['total_spent']:,.2f} total."
                create_alert("CRM Agent", "churn_risk", msg)
                actions.append({"customer": row['customer_Name'], "issue": "churn_risk", "days": days})

        top = customers.nlargest(3, 'total_spent')
        top_names = ", ".join(top['customer_Name'].tolist())

        customer_data = customers[['customer_Name', 'total_orders', 'total_spent', 'days_since_order']].to_string()
        strategy = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"""You are a customer relationship agent for Global Trends.
Analyze these customers and:
1. Identify the top 3 VIP customers worth nurturing
2. List customers at churn risk and why
3. Suggest one retention promotion or offer
4. Recommend one upsell opportunity

Customer data:
{customer_data}

Be concise and specific."""}],
            max_tokens=400, temperature=0.2
        ).choices[0].message.content

        log_agent_action("CRM Agent",
                         f"Analyzed {len(customers)} customers, {len(at_risk) if 'days_since_order' in customers.columns else 0} at churn risk",
                         strategy[:300], "info")

        return {"status": "complete", "strategy": strategy, "customers": customers, "actions": actions,
                "top_customers": top_names}

    except Exception as e:
        log_agent_action("CRM Agent", "Failed", str(e), "error")
        return {"status": "error", "error": str(e)}


def run_financial_health_agent():
    try:
        conn = sqlite3.connect(DB_PATH)
        ar = pd.read_sql_query("SELECT SUM(outstanding_Balance) as v FROM accounts_receivable WHERE status != 'Paid'", conn)
        ap = pd.read_sql_query("SELECT SUM(outstanding_Balance) as v FROM accounts_payable WHERE status != 'Paid'", conn)
        cash = pd.read_sql_query("SELECT SUM(balance) as v FROM chart_of_accounts WHERE account_Type = 'Asset' AND account_Name LIKE '%Cash%'", conn)
        drawings = pd.read_sql_query("SELECT SUM(amount) as v FROM drawings", conn)
        revenue = pd.read_sql_query("SELECT SUM(invoice_Amount) as v FROM accounts_receivable", conn)
        expenses = pd.read_sql_query("SELECT SUM(amount) as v FROM transactions WHERE category = 'Expense'", conn)
        conn.close()

        total_ar = float(ar['v'].iloc[0] or 0)
        total_ap = float(ap['v'].iloc[0] or 0)
        total_cash = float(cash['v'].iloc[0] or 0)
        total_drawings = float(drawings['v'].iloc[0] or 0)
        total_revenue = float(revenue['v'].iloc[0] or 0)
        total_expenses = float(expenses['v'].iloc[0] or 0)

        metrics = {
            "total_ar": total_ar, "total_ap": total_ap, "total_cash": total_cash,
            "total_drawings": total_drawings, "total_revenue": total_revenue, "total_expenses": total_expenses,
            "net_cashflow": total_ar - total_ap,
            "drawings_to_revenue_pct": (total_drawings / total_revenue * 100) if total_revenue > 0 else 0
        }

        financial_summary = f"""
AR Outstanding: R{total_ar:,.2f}
AP Outstanding: R{total_ap:,.2f}
Cash on Hand: R{total_cash:,.2f}
Owner Drawings: R{total_drawings:,.2f}
Total Revenue: R{total_revenue:,.2f}
Total Expenses: R{total_expenses:,.2f}
Net Cash Position: R{total_ar - total_ap:,.2f}
"""
        analysis = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"""You are a financial health monitoring agent for Global Trends.
Analyze this financial snapshot and:
1. Rate overall financial health (Excellent/Good/At Risk/Critical)
2. Identify the top 2 financial risks
3. Flag if drawings are unsustainably high
4. Recommend one immediate action
5. Forecast cash flow risk for next 30 days

Financial data:
{financial_summary}

Be specific and direct."""}],
            max_tokens=400, temperature=0.1
        ).choices[0].message.content

        if total_ap > total_ar:
            msg = f"🚨 CASH FLOW RISK: Payables (R{total_ap:,.2f}) exceed receivables (R{total_ar:,.2f}). Immediate action needed."
            notify_all("Cash Flow Risk Detected", msg, "critical")

        if metrics['drawings_to_revenue_pct'] > 20:
            msg = f"⚠️ DRAWINGS ALERT: Owner drawings are {metrics['drawings_to_revenue_pct']:.1f}% of revenue — above the 20% threshold."
            create_alert("Financial Health", "high_drawings", msg)

        log_agent_action("Financial Health", "Financial snapshot analysis", analysis[:300], "info")
        return {"status": "complete", "analysis": analysis, "metrics": metrics}

    except Exception as e:
        log_agent_action("Financial Health", "Failed", str(e), "error")
        return {"status": "error", "error": str(e)}


def run_goal_planning_agent(goal):
    try:
        conn = sqlite3.connect(DB_PATH)
        inv_summary = pd.read_sql_query("SELECT product_Name, stock_on_hand, reorder_quantity FROM inventory", conn).to_string()
        fin_summary = pd.read_sql_query("SELECT account_Name, account_Type, balance FROM chart_of_accounts", conn).to_string()
        sales_summary = pd.read_sql_query("SELECT category, SUM(amount) as total FROM transactions GROUP BY category", conn).to_string()
        supplier_summary = pd.read_sql_query("SELECT supplier_Name, products FROM suppliers", conn).to_string()
        conn.close()

        plan = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"""You are a strategic planning agent for Global Trends, a home goods trading company in South Africa.

Business Goal: {goal}

Current Business Context:
INVENTORY: {inv_summary}
FINANCES: {fin_summary}
SALES: {sales_summary}
SUPPLIERS: {supplier_summary}

Create a detailed action plan with:
1. GOAL ANALYSIS: What does achieving this goal require?
2. SUB-TASKS: List 4-6 specific, actionable steps (numbered)
3. RESOURCES NEEDED: Budget, stock, people
4. TIMELINE: Realistic timeline for each step
5. SUCCESS METRICS: How will we know it's achieved?
6. RISKS: Top 2 risks and mitigations

Be specific to Global Trends' actual data above."""}],
            max_tokens=800, temperature=0.3
        ).choices[0].message.content

        data_queries = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"""Based on this business goal: {goal}
Write 2 SQL SELECT queries that would give the most useful data to support this goal.
Use these tables: inventory, product, suppliers, customers, transactions, accounts_receivable
Return ONLY the SQL, one per line, no explanation."""}],
            max_tokens=200, temperature=0.1
        ).choices[0].message.content

        query_results = []
        for line in data_queries.strip().split('\n'):
            line = line.strip()
            if line.upper().startswith('SELECT'):
                result = query_database(line)
                query_results.append(result[:500])

        create_alert("Goal Planner", "plan_ready", f"📋 New plan for: {goal[:50]}...")
        log_agent_action("Goal Planner", f"Created plan for: {goal}", plan[:300], "info")

        return {"status": "complete", "goal": goal, "plan": plan, "data": query_results}

    except Exception as e:
        log_agent_action("Goal Planner", f"Failed for goal: {goal}", str(e), "error")
        return {"status": "error", "error": str(e)}


# ============================================
# REACT CHAT AGENT
# ============================================
def run_web_search(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "No results found."
            return "\n\n".join([f"Title: {r.get('title', '')}\nSnippet: {r.get('body', '')}" for r in results])
    except Exception as e:
        return f"Search error: {str(e)}"


def run_react_agent(user_question, max_iterations=10):
    system_prompt = """You are a helpful AI assistant for Global Trends, a trading company.
You have access to two tools:
1. Database_Query - Query the SQLite database with SELECT statements.
   Tables: suppliers, product, retailers, customers, inventory, chart_of_accounts,
   accounts_receivable, accounts_payable, drawings, transactions, performance_notes
2. Web_Search - Search the internet for market info.

Format EXACTLY like this (one action per turn):
Thought: <your reasoning>
Action: Database_Query
Action Input: SELECT ...

OR:
Thought: <your reasoning>
Action: Web_Search
Action Input: <search terms>

When you have enough info:
Thought: I now know the final answer
Final Answer: <your complete answer>

IMPORTANT: Always use Final Answer when you have the data you need."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Question: {user_question}\nThought:"}
    ]

    for _ in range(max_iterations):
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile", messages=messages,
            temperature=0.2, max_tokens=1000, stop=["Observation:"]
        )
        text = response.choices[0].message.content.strip()
        messages.append({"role": "assistant", "content": text})

        if "Final Answer:" in text:
            return text.split("Final Answer:")[-1].strip()

        action, action_input = None, None
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("Action:"):
                action = line.replace("Action:", "").strip()
            if line.startswith("Action Input:"):
                action_input = line.replace("Action Input:", "").strip()
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("Action") or lines[j].startswith("Thought") or lines[j].startswith("Final"):
                        break
                    action_input += " " + lines[j].strip()
                action_input = action_input.strip()

        if not action or not action_input:
            messages.append({"role": "user", "content": "Please respond with Thought, Action, and Action Input."})
            continue

        if any(k in action.lower() for k in ["database", "db", "query"]):
            observation = query_database(action_input)
        elif any(k in action.lower() for k in ["search", "web"]):
            observation = run_web_search(action_input)
        else:
            observation = f"Unknown tool '{action}'. Use Database_Query or Web_Search."

        messages.append({"role": "user", "content": f"Observation: {observation}\nThought:"})

    messages.append({"role": "user", "content": "Please give a Final Answer based on what you've found so far."})
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile", messages=messages,
        temperature=0.2, max_tokens=500
    )
    final = response.choices[0].message.content.strip()
    if "Final Answer:" in final:
        return final.split("Final Answer:")[-1].strip()
    return final


# ============================================
# INVOICE & SALE FUNCTIONS
# ============================================
def update_inventory(product_id, quantity_sold):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT stock_on_hand, product_Name FROM inventory WHERE product_ID = ?", (product_id,))
        result = cursor.fetchone()
        if result:
            current_stock, product_name = result
            new_stock = current_stock - quantity_sold
            if new_stock < 0:
                return False, f"Insufficient stock for {product_name}."
            cursor.execute("UPDATE inventory SET stock_on_hand=?, last_updated=? WHERE product_ID=?",
                           (new_stock, datetime.now().strftime("%Y-%m-%d"), product_id))
            conn.commit()
            st.cache_data.clear()
            return True, f"Stock updated. {product_name} now has {new_stock} units."
        return False, f"Product {product_id} not found."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def generate_invoice_pdf(invoice_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=24,
                                 textColor=colors.HexColor('#2c3e50'), alignment=1)
    story.append(Paragraph("Global Trends", title_style))
    story.append(Paragraph("Invoice", styles['Heading2']))
    story.append(Spacer(1, 0.2 * inch))
    details = [
        ["Invoice Number:", invoice_data.get('invoice_number', '')],
        ["Invoice Date:", invoice_data.get('invoice_date', '')],
        ["Due Date:", invoice_data.get('due_date', '')],
        ["Customer:", invoice_data.get('customer_name', '')],
    ]
    dt = Table(details, colWidths=[2 * inch, 4 * inch])
    dt.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), ('FONTSIZE', (0, 0), (-1, -1), 10)]))
    story.append(dt)
    story.append(Spacer(1, 0.2 * inch))
    items_data = [["Item", "Description", "Qty", "Unit Price (R)", "Total (R)"]]
    for item in invoice_data.get('items', []):
        items_data.append([item.get('item_code', ''), item.get('description', ''),
                           item.get('quantity', 0), f"{item.get('unit_price', 0):,.2f}",
                           f"{item.get('total', 0):,.2f}"])
    items_data.append(["", "", "", "Subtotal:", f"{invoice_data.get('subtotal', 0):,.2f}"])
    items_data.append(["", "", "", "VAT (15%):", f"{invoice_data.get('vat', 0):,.2f}"])
    items_data.append(["", "", "", "Total:", f"{invoice_data.get('total', 0):,.2f}"])
    it = Table(items_data, colWidths=[1.2 * inch, 2.5 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch])
    it.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -3), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ]))
    story.append(it)
    doc.build(story)
    buffer.seek(0)
    return buffer


def save_invoice_to_database(invoice_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""INSERT INTO accounts_receivable
            (receivable_ID, customer_ID, customer_Name, invoice_Date, due_Date, invoice_Amount,
             amount_Paid, outstanding_Balance, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (invoice_data.get('invoice_number', ''), invoice_data.get('customer_id', ''),
                        invoice_data.get('customer_name', ''), invoice_data.get('invoice_date', ''),
                        invoice_data.get('due_date', ''), invoice_data.get('total', 0), 0,
                        invoice_data.get('total', 0), 'Current'))
        conn.commit()
        st.cache_data.clear()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def process_sale(customer_id, customer_name, customer_type, items, recipient_email=None):
    subtotal = sum(i['quantity'] * i['unit_price'] for i in items)
    vat = subtotal * 0.15
    total = subtotal + vat
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{customer_id}"
    invoice_data = {
        'invoice_number': invoice_number, 'invoice_date': datetime.now().strftime("%Y-%m-%d"),
        'due_date': (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        'customer_id': customer_id, 'customer_name': customer_name,
        'customer_type': customer_type, 'items': items,
        'subtotal': subtotal, 'vat': vat, 'total': total
    }
    inventory_updates = []
    for item in items:
        success, message = update_inventory(item['product_id'], item['quantity'])
        inventory_updates.append({'product': item['description'], 'success': success, 'message': message})
    if not all(u['success'] for u in inventory_updates):
        return {'success': False, 'message': "Inventory update failed", 'details': inventory_updates}
    if save_invoice_to_database(invoice_data):
        invoice_pdf = generate_invoice_pdf(invoice_data)
        email_status = None
        if recipient_email:
            ok, msg = send_email_notification(
                f"Invoice {invoice_number} from Global Trends",
                f"Dear {customer_name},\n\nPlease find attached invoice {invoice_number}.\n\nTotal: R{total:,.2f}",
                recipient_email)
            email_status = {'success': ok, 'message': msg}
        return {'success': True, 'invoice_data': invoice_data, 'invoice_pdf': invoice_pdf,
                'inventory_updates': inventory_updates, 'email_status': email_status,
                'message': f"Sale processed! Invoice {invoice_number} created."}
    return {'success': False, 'message': "Failed to save invoice"}


# ============================================
# ALERT HELPERS
# ============================================
def get_unread_alerts_count():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM agent_alerts WHERE is_read = 0")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0


def get_all_alerts(limit=50):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT * FROM agent_alerts ORDER BY timestamp DESC LIMIT {limit}", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()


def mark_alerts_read():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE agent_alerts SET is_read = 1")
        conn.commit()
        conn.close()
    except:
        pass


def get_agent_logs(limit=30):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT * FROM agent_logs ORDER BY timestamp DESC LIMIT {limit}", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()


# ============================================
# STREAMLIT UI
# ============================================
unread_count = get_unread_alerts_count()
alert_badge = f" 🔴 {unread_count}" if unread_count > 0 else ""

st.sidebar.markdown("""
<div style="text-align:center; padding: 1rem 0;">
    <h2 style="font-family: Syne, sans-serif; font-size: 1.4rem; margin:0;">🌍 Global Trends</h2>
    <p style="color: #888; font-size: 0.8rem; margin:0;">AI Business Intelligence</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 Agent Control")
page = st.sidebar.radio("Navigate", [
    f"🧠 Agent Command Centre{alert_badge}",
    "💬 AI Chat Assistant",
    "🛒 Process Sale",
    "📊 Supplier ",
    "📦 Product ",
    "🏪 Retailer ",
    "👥 Customer ",
    "📦 Inventory ",
    "💰 Financial ",
    "⭐ Performance ",
    "➕ Add Data"
])

# ============================================
# AGENT COMMAND CENTRE
# ============================================
if "Agent Command Centre" in page:
    st.title("🧠 Agent Command Centre")
    st.markdown("*Autonomous AI agents monitoring, reasoning, and acting on your behalf*")

    if unread_count > 0:
        st.markdown(f'<div class="alert-box">📬 You have <strong>{unread_count} unread alerts</strong> from your agents.</div>', unsafe_allow_html=True)

    st.markdown("### 🤖 Agent Status")
    cols = st.columns(7)
    agents = [
        ("📦", "Stock Monitor"), ("💸", "AR Collection"), ("🏭", "Supplier Perf."),
        ("📈", "Sales Forecast"), ("👥", "CRM Agent"), ("💰", "Fin. Health"), ("🎯", "Goal Planner"),
    ]
    for col, (icon, name) in zip(cols, agents):
        with col:
            st.markdown(f"""<div class="agent-card" style="text-align:center; padding:0.8rem;">
                <div style="font-size:1.5rem">{icon}</div>
                <div style="font-size:0.7rem; color:#aaa; margin-top:4px">{name}</div>
                <div style="margin-top:6px"><span class="status-dot dot-green"></span><span style="font-size:0.7rem">Ready</span></div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    tabs = st.tabs(["📦 Stock", "💸 AR", "🏭 Suppliers", "📈 Forecast", "👥 CRM", "💰 Finance", "🎯 Goal Planner", "📋 Logs & Alerts"])

    with tabs[0]:
        st.subheader("📦 Proactive Stock Monitor Agent")
        st.markdown("*Autonomously checks inventory levels, reasons about urgency, and sends reorder alerts*")
        if st.button("▶ Run Stock Monitor Agent", type="primary"):
            with st.spinner("Agent scanning inventory and reasoning..."):
                result = run_stock_monitor_agent()
            if result['status'] == 'healthy':
                st.markdown('<div class="alert-box-green">✅ All stock levels are healthy. No action needed.</div>', unsafe_allow_html=True)
            elif result['status'] == 'alerts':
                st.warning(f"⚠️ {len(result['alerts'])} products need attention")
                for alert in result['alerts']:
                    st.markdown(f'<div class="alert-box">{alert}</div>', unsafe_allow_html=True)
                with st.expander("🧠 AI Reasoning"):
                    st.write(result.get('reasoning', ''))
                if not result['low_stock'].empty:
                    st.dataframe(result['low_stock'])
            else:
                st.error(f"Agent error: {result.get('error')}")

    with tabs[1]:
        st.subheader("💸 Accounts Receivable Collection Agent")
        st.markdown("*Autonomously monitors overdue invoices and escalates collection actions*")
        if st.button("▶ Run AR Collection Agent", type="primary"):
            with st.spinner("Agent scanning invoices and planning collection actions..."):
                result = run_ar_collection_agent()
            if result['status'] == 'healthy':
                st.markdown('<div class="alert-box-green">✅ No overdue invoices. All accounts current.</div>', unsafe_allow_html=True)
            elif result['status'] == 'overdue_found':
                st.warning(f"⚠️ R{result['total']:,.2f} in overdue invoices")
                for action in result['actions']:
                    color = "alert-box-red" if action['days'] >= 30 else "alert-box"
                    st.markdown(f'<div class="{color}">👤 <strong>{action["customer"]}</strong> — {action["action"]} ({action["days"]} days, R{action["amount"]:,.2f})</div>', unsafe_allow_html=True)
                st.dataframe(result['overdue'])
            else:
                st.error(f"Agent error: {result.get('error')}")

    with tabs[2]:
        st.subheader("🏭 Supplier Performance Agent")
        st.markdown("*Evaluates supplier reliability and recommends strategic changes*")
        if st.button("▶ Run Supplier Performance Agent", type="primary"):
            with st.spinner("Agent evaluating all suppliers..."):
                result = run_supplier_performance_agent()
            if result['status'] == 'complete':
                st.markdown("#### 🧠 AI Analysis")
                st.info(result['analysis'])
                for alert in result.get('alerts', []):
                    st.markdown(f'<div class="alert-box">{alert}</div>', unsafe_allow_html=True)
                if not result['suppliers'].empty:
                    st.dataframe(result['suppliers'])
            else:
                st.error(f"Agent error: {result.get('error')}")

    with tabs[3]:
        st.subheader("📈 Sales Trend & Demand Forecasting Agent")
        st.markdown("*Analyses transaction history and generates demand forecasts*")
        if st.button("▶ Run Sales Forecasting Agent", type="primary"):
            with st.spinner("Agent analysing sales trends and generating forecast..."):
                result = run_sales_forecasting_agent()
            if result['status'] == 'complete':
                st.markdown("#### 📊 AI Forecast & Recommendations")
                st.info(result['forecast'])
                col1, col2 = st.columns(2)
                with col1:
                    if not result['sales'].empty:
                        st.markdown("**Sales by Category**")
                        sale_data = result['sales'][result['sales']['category'] == 'Sale']
                        st.metric("Total Sales", f"R{sale_data['amount'].sum():,.2f}")
                with col2:
                    if not result['inventory'].empty:
                        st.markdown("**Inventory Overview**")
                        st.metric("Products Tracked", len(result['inventory']))
            else:
                st.error(f"Agent error: {result.get('error')}")

    with tabs[4]:
        st.subheader("👥 Customer Relationship Agent")
        st.markdown("*Detects churn risk, identifies VIP customers, generates outreach strategies*")
        if st.button("▶ Run CRM Agent", type="primary"):
            with st.spinner("Agent analysing customer relationships..."):
                result = run_crm_agent()
            if result['status'] == 'complete':
                st.markdown("#### 🧠 CRM Strategy")
                st.info(result['strategy'])
                if result['actions']:
                    st.markdown("#### ⚠️ Customers Requiring Attention")
                    for action in result['actions']:
                        st.markdown(f'<div class="alert-box">👤 <strong>{action["customer"]}</strong> — {action["issue"]} ({action["days"]} days since last order)</div>', unsafe_allow_html=True)
                st.markdown(f"**🏆 Top Customers:** {result.get('top_customers', 'N/A')}")
                if not result['customers'].empty:
                    display_cols = [c for c in ['customer_Name', 'total_orders', 'total_spent', 'outstanding_balance', 'days_since_order'] if c in result['customers'].columns]
                    st.dataframe(result['customers'][display_cols])
            else:
                st.error(f"Agent error: {result.get('error')}")

    with tabs[5]:
        st.subheader("💰 Financial Health Monitor Agent")
        st.markdown("*Monitors cash flow ratios, flags risks, and forecasts financial health*")
        if st.button("▶ Run Financial Health Agent", type="primary"):
            with st.spinner("Agent analysing financial health..."):
                result = run_financial_health_agent()
            if result['status'] == 'complete':
                metrics = result['metrics']
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("AR Outstanding", f"R{metrics['total_ar']:,.2f}")
                with col2:
                    st.metric("AP Outstanding", f"R{metrics['total_ap']:,.2f}")
                with col3:
                    delta = metrics['total_ar'] - metrics['total_ap']
                    st.metric("Net Cash Position", f"R{delta:,.2f}", delta=f"R{delta:,.2f}")
                with col4:
                    st.metric("Drawings / Revenue", f"{metrics['drawings_to_revenue_pct']:.1f}%")
                st.markdown("#### 🧠 Financial Health Analysis")
                st.info(result['analysis'])
            else:
                st.error(f"Agent error: {result.get('error')}")

    with tabs[6]:
        st.subheader("🎯 Multi-Step Goal Planning Agent")
        st.markdown("*Give the agent a high-level business goal — it plans and executes the steps*")
        goal_examples = [
            "Prepare for the school holiday season in December",
            "Expand our curtains product line",
            "Reduce our accounts receivable by 50% in 30 days",
            "Find 2 new supplier alternatives for bedding",
            "Increase monthly revenue by 20%"
        ]
        st.markdown("**Example goals:**")
        for ex in goal_examples:
            st.markdown(f"• *{ex}*")
        goal_input = st.text_area("Enter your business goal:", placeholder="e.g. Prepare for the school holiday season in December", height=80)
        if st.button("▶ Execute Goal Planning Agent", type="primary") and goal_input:
            with st.spinner("Agent planning and executing multi-step strategy..."):
                result = run_goal_planning_agent(goal_input)
            if result['status'] == 'complete':
                st.markdown(f"#### 📋 Strategic Plan: *{result['goal']}*")
                st.info(result['plan'])
                if result.get('data'):
                    with st.expander("📊 Data Retrieved by Agent"):
                        for i, d in enumerate(result['data']):
                            st.markdown(f"**Query {i + 1} result:**")
                            st.text(d)
            else:
                st.error(f"Agent error: {result.get('error')}")

    with tabs[7]:
        st.subheader("📋 Agent Logs & Alerts")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🔔 Recent Alerts")
            if st.button("Mark All as Read"):
                mark_alerts_read()
                st.rerun()
            alerts_df = get_all_alerts()
            if not alerts_df.empty:
                for _, row in alerts_df.iterrows():
                    is_unread = row.get('is_read', 1) == 0
                    color = "alert-box-red" if row['alert_type'] in ['critical_stock', 'final_notice'] else "alert-box"
                    badge = " 🆕" if is_unread else ""
                    st.markdown(f'<div class="{color}"><small><strong>{row["agent_name"]}</strong>{badge} — {row["timestamp"]}</small><br>{row["message"]}</div>', unsafe_allow_html=True)
            else:
                st.info("No alerts yet. Run an agent to generate alerts.")
        with col2:
            st.markdown("#### 📝 Agent Activity Log")
            logs_df = get_agent_logs()
            if not logs_df.empty:
                for _, row in logs_df.iterrows():
                    severity_color = {"critical": "alert-box-red", "warning": "alert-box", "info": "alert-box-green", "error": "alert-box-red"}.get(row.get('severity', 'info'), "alert-box")
                    st.markdown(f'<div class="{severity_color}"><small><strong>{row["agent_name"]}</strong> — {row["timestamp"]}</small><br><em>{row["action_taken"]}</em><br>{str(row["result"])[:200]}</div>', unsafe_allow_html=True)
            else:
                st.info("No agent activity yet.")

    st.markdown("---")
    st.markdown("### ⚡ Run All Agents")
    if st.button("▶▶ Run All 6 Monitoring Agents Now", type="primary"):
        with st.spinner("Running all agents simultaneously..."):
            results = {}
            results['stock'] = run_stock_monitor_agent()
            results['ar'] = run_ar_collection_agent()
            results['suppliers'] = run_supplier_performance_agent()
            results['forecast'] = run_sales_forecasting_agent()
            results['crm'] = run_crm_agent()
            results['finance'] = run_financial_health_agent()
        st.success("✅ All agents completed! Check the Logs & Alerts tab for results.")
        new_alerts = get_unread_alerts_count()
        if new_alerts > 0:
            st.warning(f"📬 {new_alerts} new alerts generated. Review the Logs & Alerts tab.")
        st.rerun()


# ============================================
# CHAT ASSISTANT
# ============================================
elif "AI Chat" in page:
    st.header("🤖 AI Chat Assistant")
    st.markdown("Ask anything about your suppliers, products, inventory, finances, or market trends.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    user_input = st.chat_input("Ask about your business...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)
        try:
            with st.spinner("Thinking..."):
                response = run_react_agent(user_input)
        except Exception as e:
            response = f"⚠️ Error: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)


# ============================================
# PROCESS SALE
# ============================================
elif "Process Sale" in page:
    st.header("🛒 Process New Sale")
    customers_df = get_customers()
    retailers_df = get_retailers()
    products_df = get_products()

    col1, col2 = st.columns(2)
    with col1:
        customer_type = st.selectbox("Customer Type", ["Individual", "Retailer"])
        if customer_type == "Individual" and not customers_df.empty:
            opts = {f"{r['customer_Name']} ({r['customer_ID']})": r['customer_ID'] for _, r in customers_df.iterrows()}
            sel = st.selectbox("Select Customer", list(opts.keys()))
            customer_id = opts[sel]
            customer_name = sel.split(" (")[0]
            email_val = customers_df[customers_df['customer_ID'] == customer_id]['email'].iloc[0]
            recipient_email = st.text_input("Email", value=email_val)
        elif not retailers_df.empty:
            active = retailers_df[retailers_df['status'] == 'Active']
            opts = {f"{r['retailer_Name']} ({r['retailer_ID']})": r['retailer_ID'] for _, r in active.iterrows()}
            sel = st.selectbox("Select Retailer", list(opts.keys()))
            customer_id = opts[sel]
            customer_name = sel.split(" (")[0]
            recipient_email = st.text_input("Email for Invoice")
        else:
            customer_id = st.text_input("Customer ID")
            customer_name = st.text_input("Customer Name")
            recipient_email = st.text_input("Email")

    if 'sale_items' not in st.session_state:
        st.session_state.sale_items = []

    st.subheader("Order Items")
    with st.form("add_item"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if not products_df.empty:
                prod_opts = {f"{r['products_ID']} ({r['product_ID']})": r['product_ID'] for _, r in products_df.iterrows()}
                sel_prod = st.selectbox("Product", list(prod_opts.keys()))
                product_id = prod_opts[sel_prod]
            else:
                product_id = ""
        if not products_df.empty and product_id:
            prod_row = products_df[products_df['product_ID'] == product_id].iloc[0]
            unit_price = float(prod_row['selling_Price']) if pd.notna(prod_row['selling_Price']) else 0.0
            inv_df = get_inventory()
            stock_available = 0
            if not inv_df.empty:
                inv_row = inv_df[inv_df['product_ID'] == product_id]
                if not inv_row.empty:
                    stock_available = inv_row['stock_on_hand'].iloc[0]
            with c2:
                st.write(f"**Price:** R{unit_price:,.2f}")
                st.write(f"**Stock:** {stock_available}")
            with c3:
                quantity = st.number_input("Qty", min_value=1, max_value=max(stock_available, 1), value=1)
            with c4:
                st.write(f"**Total:** R{quantity * unit_price:,.2f}")
        add_item = st.form_submit_button("Add Item")
        if not products_df.empty and product_id and add_item:
            if quantity <= stock_available:
                st.session_state.sale_items.append({
                    'product_id': product_id, 'item_code': product_id,
                    'description': prod_row['products_ID'], 'quantity': quantity,
                    'unit_price': unit_price, 'total': quantity * unit_price
                })
                st.rerun()
            else:
                st.error(f"Only {stock_available} units available.")

    if st.session_state.sale_items:
        st.dataframe(pd.DataFrame(st.session_state.sale_items)[['description', 'quantity', 'unit_price', 'total']])
        subtotal = sum(i['total'] for i in st.session_state.sale_items)
        vat = subtotal * 0.15
        total = subtotal + vat
        c1, c2, c3 = st.columns(3)
        c1.metric("Subtotal", f"R{subtotal:,.2f}")
        c2.metric("VAT 15%", f"R{vat:,.2f}")
        c3.metric("Total", f"R{total:,.2f}")
        if st.button("Clear Items"):
            st.session_state.sale_items = []
            st.rerun()
        if st.button("✅ Process Sale & Generate Invoice", type="primary"):
            with st.spinner("Processing..."):
                result = process_sale(customer_id, customer_name, customer_type,
                                      st.session_state.sale_items, recipient_email)
            if result['success']:
                st.success(result['message'])
                inv = result['invoice_data']
                st.download_button("📄 Download Invoice PDF", data=result['invoice_pdf'],
                                   file_name=f"invoice_{inv['invoice_number']}.pdf", mime="application/pdf")
                st.session_state.sale_items = []
            else:
                st.error(result['message'])


# ============================================
# DASHBOARDS
# ============================================
elif "Supplier" in page:
    st.header("🏭 Supplier Management")
    df = get_suppliers()
    if not df.empty:
        st.dataframe(df)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Suppliers", len(df))
        c2.metric("Total Products", len(get_products()))
        perf = get_performance()
        if not perf.empty:
            perf['r'] = pd.to_numeric(perf['supplier_Rating'], errors='coerce')
            c3.metric("Top Rated (4+⭐)", len(perf[perf['r'] >= 4]))
    else:
        st.info("No supplier data.")

elif "Product Dashboard" in page:
    st.header("📦 Product Catalog")
    df = get_products()
    if not df.empty:
        display = df.copy()
        if 'unit_Cost' in display.columns:
            display['unit_Cost'] = display['unit_Cost'].apply(lambda x: f"R{x:,.2f}" if pd.notna(x) else x)
        if 'selling_Price' in display.columns:
            display['selling_Price'] = display['selling_Price'].apply(lambda x: f"R{x:,.2f}" if pd.notna(x) else x)
        st.dataframe(display)
        if 'product_Categories' in df.columns:
            st.bar_chart(df['product_Categories'].value_counts())
    else:
        st.info("No product data.")

elif "Retailer Dashboard " in page:
    st.header("🏪 Retailer Management")
    df = get_retailers()
    if not df.empty:
        st.dataframe(df)
        if 'order_Status' in df.columns:
            st.bar_chart(df['order_Status'].value_counts())
    else:
        st.info("No retailer data.")

elif "Customer Dashboard" in page:
    st.header("👥 Customer Management")
    df = get_customers()
    if not df.empty:
        st.dataframe(df)
        df['ts'] = pd.to_numeric(df['total_spent'], errors='coerce')
        df['ob'] = pd.to_numeric(df['outstanding_balance'], errors='coerce')
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Customers", len(df))
        c2.metric("Total Revenue", f"R{df['ts'].sum():,.2f}")
        c3.metric("Outstanding", f"R{df['ob'].sum():,.2f}")
    else:
        st.info("No customer data.")

elif "Inventory Dashboard" in page:
    st.header("📦 Inventory Management")
    df = get_inventory()
    if not df.empty:
        low = df[df['stock_on_hand'] <= df['reorder_level']]
        if not low.empty:
            st.warning(f"⚠️ {len(low)} products below reorder level")
        st.dataframe(df)
        st.bar_chart(df.set_index('product_Name')['stock_on_hand'])
    else:
        st.info("No inventory data.")

elif "Financial Dashboard" in page:
    st.header("💰 Financial Management")
    fin = get_financial_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sales", f"R{fin['total_sales']:,.2f}")
    c2.metric("AR Outstanding", f"R{fin['total_ar']:,.2f}")
    c3.metric("AP Outstanding", f"R{fin['total_ap']:,.2f}")
    c4.metric("Owner Drawings", f"R{fin['total_drawings']:,.2f}")
    conn = sqlite3.connect(DB_PATH)
    ar = pd.read_sql_query(
        "SELECT receivable_ID,customer_Name,due_Date,invoice_Amount,outstanding_Balance,status FROM accounts_receivable WHERE status != 'Paid' ORDER BY due_Date", conn)
    if not ar.empty:
        st.subheader("Accounts Receivable")
        st.dataframe(ar)
    conn.close()

elif "Performance Dashboard" in page:
    st.header("⭐ Supplier Performance")
    df = get_performance()
    if not df.empty:
        st.dataframe(df)
        if 'supplier_Rating' in df.columns:
            df['r'] = pd.to_numeric(df['supplier_Rating'], errors='coerce')
            st.bar_chart(df.set_index('supplier_Name')['r'])
    else:
        st.info("No performance data.")

elif "Add Data" in page:
    st.header("➕ Add New Data")
    tab1, tab2, tab3, tab4 = st.tabs(["Add Supplier", "Add Product", "Add Retailer", "Add Customer"])

    with tab1:
        with st.form("add_supplier"):
            s_id = st.text_input("Supplier ID (e.g., s006)")
            s_name = st.text_input("Supplier Name")
            s_account = st.text_input("Primary Contact")
            s_wechat = st.text_input("WeChat")
            s_website = st.text_input("Website")
            s_products = st.text_input("Products")
            if st.form_submit_button("Add Supplier"):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("INSERT INTO suppliers VALUES (?,?,?,?,?,?)",
                                 (s_id, s_name, s_account, s_wechat, s_website, s_products))
                    conn.execute("INSERT INTO performance_notes VALUES (?,?,?,?)", (s_id, 3, 'Alternative', 'New supplier'))
                    conn.commit(); conn.close()
                    st.cache_data.clear()
                    st.success(f"✅ {s_name} added!")
                except Exception as e:
                    st.error(str(e))

    with tab2:
        with st.form("add_product"):
            p_id = st.text_input("Product ID")
            p_cat = st.text_input("Category")
            p_name = st.text_input("Product Name")
            p_sup = st.text_input("Supplier ID")
            p_type = st.selectbox("Type", ["Manufacturer", "Distributor", "Importer", "Wholesaler"])
            p_moq = st.text_input("MOQ")
            p_lead = st.text_input("Lead Time")
            p_cost = st.number_input("Unit Cost (R)", min_value=0.0, format="%.2f")
            p_price = st.number_input("Selling Price (R)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Add Product"):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("INSERT INTO product VALUES (?,?,?,?,?,?,?,?,?)",
                                 (p_id, p_cat, p_name, p_sup, p_type, p_moq, p_lead, p_cost, p_price))
                    conn.execute("INSERT INTO inventory VALUES (?,?,?,?,?,?,?,?)",
                                 (f"inv{p_id}", p_id, p_name, 0, 10, 20, 'Warehouse A', datetime.now().strftime("%Y-%m-%d")))
                    conn.commit(); conn.close()
                    st.cache_data.clear()
                    st.success(f"✅ {p_name} added!")
                except Exception as e:
                    st.error(str(e))

    with tab3:
        with st.form("add_retailer"):
            r_id = st.text_input("Retailer ID")
            r_name = st.text_input("Name")
            r_status = st.selectbox("Status", ["Active", "Potential", "On Hold"])
            r_qty = st.text_input("Order Quantity")
            r_prod = st.text_input("Product")
            r_ostatus = st.selectbox("Order Status", ["Processing", "Shipped", "Pending", "Delivered"])
            r_contact = st.text_input("Contact")
            r_terms = st.selectbox("Terms", ["Net 30", "Net 45", "100% Prepayment", "To be confirmed"])
            if st.form_submit_button("Add Retailer"):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("INSERT INTO retailers VALUES (?,?,?,?,?,?,?,?)",
                                 (r_id, r_name, r_status, r_qty, r_prod, r_ostatus, r_contact, r_terms))
                    conn.commit(); conn.close()
                    st.cache_data.clear()
                    st.success(f"✅ {r_name} added!")
                except Exception as e:
                    st.error(str(e))

    with tab4:
        with st.form("add_customer"):
            c_id = st.text_input("Customer ID")
            c_name = st.text_input("Name")
            c_phone = st.text_input("Contact Number")
            c_email = st.text_input("Email")
            if st.form_submit_button("Add Customer"):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)",
                                 (c_id, c_name, c_phone, c_email, 0, 0.00, 0.00, None))
                    conn.commit(); conn.close()
                    st.cache_data.clear()
                    st.success(f"✅ {c_name} added!")
                except Exception as e:
                    st.error(str(e))
