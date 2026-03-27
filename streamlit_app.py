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
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun

# ============================================
# DATABASE INITIALIZATION (STEP 1.4)
# ============================================

def init_database():
    """Initialize the database with all tables and sample data if it doesn't exist"""

    # Check if database already exists
    if os.path.exists('global.db'):
        # Verify tables exist
        conn = sqlite3.connect('global.db')
        cursor = conn.cursor()

        # Check if suppliers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='suppliers'")
        if cursor.fetchone():
            conn.close()
            return  # Database exists and has tables

    # Create new database
    st.warning("Creating new database with sample data...")
    conn = sqlite3.connect('global.db')
    cursor = conn.cursor()

    # ============================================
    # TABLE 1: SUPPLIERS
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS suppliers
                   (
                       supplier_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       supplier_Name VARCHAR
                   (
                       100
                   ) NOT NULL,
                       Account VARCHAR
                   (
                       100
                   ),
                       wechat_Contact VARCHAR
                   (
                       100
                   ),
                       Website VARCHAR
                   (
                       255
                   ),
                       products TEXT
                       )
                   ''')

    # ============================================
    # TABLE 2: PRODUCT
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS product
                   (
                       product_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       product_Categories VARCHAR
                   (
                       100
                   ),
                       products_ID VARCHAR
                   (
                       100
                   ),
                       supplier_ID VARCHAR
                   (
                       10
                   ),
                       supplier_Type VARCHAR
                   (
                       50
                   ),
                       MOQ VARCHAR
                   (
                       50
                   ),
                       lead_Times VARCHAR
                   (
                       50
                   ),
                       unit_Cost DECIMAL
                   (
                       10,
                       2
                   ),
                       selling_Price DECIMAL
                   (
                       10,
                       2
                   ),
                       FOREIGN KEY
                   (
                       supplier_ID
                   ) REFERENCES suppliers
                   (
                       supplier_ID
                   )
                       )
                   ''')

    # ============================================
    # TABLE 3: RETAILERS
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS retailers
                   (
                       retailer_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       retailer_Name VARCHAR
                   (
                       100
                   ) NOT NULL,
                       status VARCHAR
                   (
                       20
                   ),
                       order_Quantity VARCHAR
                   (
                       50
                   ),
                       product TEXT,
                       order_Status VARCHAR
                   (
                       50
                   ),
                       management_Contacts VARCHAR
                   (
                       100
                   ),
                       payment_Terms VARCHAR
                   (
                       50
                   )
                       )
                   ''')

    # ============================================
    # TABLE 4: INDEPENDENT CUSTOMERS
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS customers
                   (
                       customer_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       customer_Name VARCHAR
                   (
                       100
                   ) NOT NULL,
                       contact_Number VARCHAR
                   (
                       20
                   ),
                       email VARCHAR
                   (
                       100
                   ),
                       total_orders INT DEFAULT 0,
                       total_spent DECIMAL
                   (
                       10,
                       2
                   ) DEFAULT 0.00,
                       outstanding_balance DECIMAL
                   (
                       10,
                       2
                   ) DEFAULT 0.00
                       )
                   ''')

    # ============================================
    # TABLE 5: INVENTORY
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS inventory
                   (
                       inventory_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       product_ID VARCHAR
                   (
                       10
                   ),
                       product_Name VARCHAR
                   (
                       100
                   ),
                       stock_on_hand INT,
                       reorder_level INT,
                       reorder_quantity INT,
                       location VARCHAR
                   (
                       50
                   ),
                       last_updated DATE,
                       FOREIGN KEY
                   (
                       product_ID
                   ) REFERENCES product
                   (
                       product_ID
                   )
                       )
                   ''')

    # ============================================
    # TABLE 6a: CHART OF ACCOUNTS
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS chart_of_accounts
                   (
                       account_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       account_Name VARCHAR
                   (
                       100
                   ),
                       account_Type VARCHAR
                   (
                       50
                   ),
                       balance DECIMAL
                   (
                       12,
                       2
                   )
                       )
                   ''')

    # ============================================
    # TABLE 6b: ACCOUNTS RECEIVABLE
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS accounts_receivable
                   (
                       receivable_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       customer_ID VARCHAR
                   (
                       10
                   ),
                       customer_Name VARCHAR
                   (
                       100
                   ),
                       invoice_Date DATE,
                       due_Date DATE,
                       invoice_Amount DECIMAL
                   (
                       10,
                       2
                   ),
                       amount_Paid DECIMAL
                   (
                       10,
                       2
                   ) DEFAULT 0.00,
                       outstanding_Balance DECIMAL
                   (
                       10,
                       2
                   ),
                       status VARCHAR
                   (
                       20
                   )
                       )
                   ''')

    # ============================================
    # TABLE 6c: ACCOUNTS PAYABLE
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS accounts_payable
                   (
                       payable_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       supplier_ID VARCHAR
                   (
                       10
                   ),
                       supplier_Name VARCHAR
                   (
                       100
                   ),
                       invoice_Date DATE,
                       due_Date DATE,
                       invoice_Amount DECIMAL
                   (
                       10,
                       2
                   ),
                       amount_Paid DECIMAL
                   (
                       10,
                       2
                   ) DEFAULT 0.00,
                       outstanding_Balance DECIMAL
                   (
                       10,
                       2
                   ),
                       status VARCHAR
                   (
                       20
                   ),
                       FOREIGN KEY
                   (
                       supplier_ID
                   ) REFERENCES suppliers
                   (
                       supplier_ID
                   )
                       )
                   ''')

    # ============================================
    # TABLE 6d: DRAWINGS
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS drawings
                   (
                       drawing_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       date DATE,
                       amount DECIMAL
                   (
                       10,
                       2
                   ),
                       description VARCHAR
                   (
                       200
                   ),
                       notes TEXT
                       )
                   ''')

    # ============================================
    # TABLE 6e: TRANSACTIONS
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS transactions
                   (
                       transaction_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       date DATE,
                       description VARCHAR
                   (
                       200
                   ),
                       account_Debit VARCHAR
                   (
                       10
                   ),
                       account_Credit VARCHAR
                   (
                       10
                   ),
                       amount DECIMAL
                   (
                       10,
                       2
                   ),
                       category VARCHAR
                   (
                       50
                   )
                       )
                   ''')

    # ============================================
    # TABLE: PERFORMANCE NOTES
    # ============================================
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS performance_notes
                   (
                       supplier_ID
                       VARCHAR
                   (
                       10
                   ) PRIMARY KEY,
                       supplier_Rating INT,
                       Priority VARCHAR
                   (
                       20
                   ),
                       Notes TEXT,
                       FOREIGN KEY
                   (
                       supplier_ID
                   ) REFERENCES suppliers
                   (
                       supplier_ID
                   )
                       )
                   ''')

    # ============================================
    # INSERT SAMPLE DATA
    # ============================================

    # Insert Suppliers
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

    cursor.executemany('''
                       INSERT INTO suppliers (supplier_ID, supplier_Name, Account, wechat_Contact, Website, products)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ''', suppliers_data)

    # Insert Product
    product_data = [
        ('p001', 'Bedding', 'Egyptian Cotton Bed Sheet Set', 's001', 'Manufacturer', '20 units', '15 days', 187.50,
         399.00),
        ('p002', 'Bedding', 'Microfleece Blanket - Queen', 's001', 'Manufacturer', '30 units', '12 days', 124.75,
         279.00),
        ('p003', 'Curtains', 'Thermal Blackout Curtains', 's003', 'Wholesaler', '15 pairs', '10 days', 213.00, 449.00),
        ('p004', 'Pots', 'Glazed Ceramic Flower Pot Set', 's002', 'Manufacturer', '10 sets', '20 days', 156.25, 349.00),
        ('p005', 'Bedding', 'Organic Bamboo Pillowcase Set', 's005', 'Manufacturer', '25 units', '14 days', 94.50,
         199.00),
        ('p006', 'Curtains', 'Sheer Voile Curtains - Ivory', 's003', 'Wholesaler', '20 pairs', '10 days', 114.25,
         259.00),
        ('p007', 'Pots', 'Handcrafted Stoneware Vase', 's002', 'Manufacturer', '8 units', '18 days', 88.75, 189.00),
        ('p008', 'Storage', 'Airtight Food Storage Set (5pc)', 's004', 'Manufacturer', '40 units', '7 days', 47.25,
         119.00),
        ('p009', 'Bedding', 'Weighted Blanket - 6.8kg', 's005', 'Manufacturer', '15 units', '21 days', 291.50, 599.00),
        ('p010', 'Storage', 'Woven Bamboo Storage Baskets', 's004', 'Distributor', '25 units', '10 days', 67.80, 159.00)
    ]

    cursor.executemany('''
                       INSERT INTO product (product_ID, product_Categories, products_ID, supplier_ID, supplier_Type,
                                            MOQ, lead_Times, unit_Cost, selling_Price)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ''', product_data)

    # Insert Retailers
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

    cursor.executemany('''
                       INSERT INTO retailers (retailer_ID, retailer_Name, status, order_Quantity, product, order_Status,
                                              management_Contacts, payment_Terms)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ''', retailers_data)

    # Insert Customers
    customers_data = [
        ('c001', 'Nomusa Dlamini', '082 123 4567', 'nomusa.dlamini@email.com', 2, 897.00, 0.00),
        ('c002', 'Thabo Nkosi', '083 234 5678', 'thabo.nkosi@email.com', 1, 399.00, 0.00),
        ('c003', 'Lerato Molefe', '084 345 6789', 'lerato.molefe@email.com', 3, 1187.00, 0.00),
        ('c004', 'Sipho Mbele', '081 456 7890', 'sipho.mbele@email.com', 1, 279.00, 279.00),
        ('c005', 'Priya Naidoo', '082 567 8901', 'priya.naidoo@email.com', 2, 798.00, 0.00),
        ('c006', 'Johan Pretorius', '083 678 9012', 'johan.pretorius@email.com', 1, 449.00, 449.00),
        ('c007', 'Zanele Khumalo', '084 789 0123', 'zanele.khumalo@email.com', 2, 618.00, 0.00),
        ('c008', 'Michael Chen', '081 890 1234', 'michael.chen@email.com', 1, 199.00, 199.00),
        ('c009', 'Fatima Patel', '082 901 2345', 'fatima.patel@email.com', 1, 349.00, 0.00),
        ('c010', 'David Mokoena', '083 012 3456', 'david.mokoena@email.com', 1, 189.00, 0.00)
    ]

    cursor.executemany('''
                       INSERT INTO customers (customer_ID, customer_Name, contact_Number, email, total_orders,
                                              total_spent, outstanding_balance)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ''', customers_data)

    # Insert Inventory
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

    cursor.executemany('''
                       INSERT INTO inventory (inventory_ID, product_ID, product_Name, stock_on_hand, reorder_level,
                                              reorder_quantity, location, last_updated)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ''', inventory_data)

    # Insert Performance Notes
    performance_notes_data = [
        ('s001', 5, 'Main', 'Reliable manufacturer, excellent quality bedding. Communication with Wang Wei is prompt.'),
        ('s002', 4, 'Main',
         'Beautiful ceramic products. Li Fang is very helpful. Lead times can be longer during peak season.'),
        ('s003', 4, 'Alternative', 'Good wholesale pricing. Chen Min responds quickly. Quality consistent.'),
        ('s004', 3, 'Reserve', 'Zhang Yong is professional but MOQ is high. Testing smaller orders first.'),
        ('s005', 5, 'Main', 'Liu Na provides excellent customer service. Premium bedding products. Highly recommended.')
    ]

    cursor.executemany('''
                       INSERT INTO performance_notes (supplier_ID, supplier_Rating, Priority, Notes)
                       VALUES (?, ?, ?, ?)
                       ''', performance_notes_data)

    # Insert Chart of Accounts
    chart_of_accounts_data = [
        ('a001', 'Cash on Hand', 'Asset', 81025.00),
        ('a002', 'Bank Account', 'Asset', 44275.00),
        ('a003', 'Inventory', 'Asset', 84750.00),
        ('a004', 'Accounts Receivable', 'Asset', 32935.00),
        ('a005', 'Equipment & Furniture', 'Asset', 14850.00),
        ('a006', 'Loan Payable - First National Bank', 'Liability', 50000.00),
        ('a007', 'Accounts Payable', 'Liability', 20375.00),
        ('a008', 'Owner\'s Equity - Capital', 'Equity', 150000.00),
        ('a009', 'Retained Earnings', 'Equity', 0.00),
        ('a010', 'Sales Revenue', 'Income', 0.00),
        ('a011', 'Cost of Goods Sold', 'Expense', 0.00),
        ('a012', 'Operating Expenses', 'Expense', 0.00)
    ]

    cursor.executemany('''
                       INSERT INTO chart_of_accounts (account_ID, account_Name, account_Type, balance)
                       VALUES (?, ?, ?, ?)
                       ''', chart_of_accounts_data)

    # Insert Accounts Receivable
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

    cursor.executemany('''
                       INSERT INTO accounts_receivable (receivable_ID, customer_ID, customer_Name, invoice_Date,
                                                        due_Date, invoice_Amount, amount_Paid, outstanding_Balance,
                                                        status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ''', accounts_receivable_data)

    # Insert Accounts Payable
    accounts_payable_data = [
        ('ap001', 's001', 'Huasheng Textiles', '2025-03-01', '2025-03-31', 24875.00, 24875.00, 0.00, 'Paid'),
        ('ap002', 's002', 'Jiangnan Ceramics', '2025-03-05', '2025-04-04', 8475.00, 0.00, 8475.00, 'Current'),
        ('ap003', 's003', 'Fareast Home Furnishings', '2025-03-10', '2025-04-09', 11900.00, 0.00, 11900.00, 'Current'),
        ('ap004', 's004', 'Xinguang Plastic Products', '2025-03-12', '2025-04-11', 5925.00, 5925.00, 0.00, 'Paid'),
        ('ap005', 's005', 'Ruixiang Textiles Import', '2025-03-15', '2025-04-14', 12750.00, 12750.00, 0.00, 'Paid')
    ]

    cursor.executemany('''
                       INSERT INTO accounts_payable (payable_ID, supplier_ID, supplier_Name, invoice_Date, due_Date,
                                                     invoice_Amount, amount_Paid, outstanding_Balance, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ''', accounts_payable_data)

    # Insert Drawings
    drawings_data = [
        ('d001', '2025-03-05', 5250.00, 'Owner salary - March', 'Monthly salary'),
        ('d002', '2025-03-20', 2375.00, 'Personal expenses', 'Business expenses'),
        ('d003', '2025-03-28', 1200.00, 'Family emergency withdrawal', 'Temporary draw')
    ]

    cursor.executemany('''
                       INSERT INTO drawings (drawing_ID, date, amount, description, notes)
                       VALUES (?, ?, ?, ?, ?)
                       ''', drawings_data)

    # Insert Transactions
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

    cursor.executemany('''
                       INSERT INTO transactions (transaction_ID, date, description, account_Debit, account_Credit,
                                                 amount, category)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ''', transactions_data)

    conn.commit()
    conn.close()

    st.success("✅ Database created successfully with sample data!")
    return True


# ============================================
# CHECK AND INITIALIZE DATABASE ON STARTUP
# ============================================

# Call this function at the beginning of your app
if not os.path.exists('global.db'):
    init_database()
else:
    # Verify tables exist
    try:
        conn = sqlite3.connect('global.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='suppliers'")
        if not cursor.fetchone():
            st.warning("Database found but tables missing. Recreating database...")
            conn.close()
            os.remove('global.db')
            init_database()
        else:
            conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")
        st.info("Attempting to recreate database...")
        if os.path.exists('global.db'):
            os.remove('global.db')
        init_database()

# ============================================
# END OF DATABASE INITIALIZATION
# ============================================

# -----------------------
# CHECK GROQ API KEY
# -----------------------
if not os.getenv("GROQ_API_KEY"):
    st.error("🚨 GROQ_API_KEY is not set. Please set it in your environment variables.")
    st.stop()


# -----------------------
# EMAIL CONFIGURATION
# -----------------------
def get_email_config():
    """Securely get email configuration"""
    config = {}

    # Try Streamlit Secrets first
    try:
        config['smtp_server'] = st.secrets.get("SMTP_SERVER", "")
        config['smtp_port'] = int(st.secrets.get("SMTP_PORT", 587))
        config['sender_email'] = st.secrets.get("SENDER_EMAIL", "")
        config['sender_password'] = st.secrets.get("SENDER_PASSWORD", "")

        if config['sender_email'] and config['sender_password']:
            return config
    except Exception:
        pass

    # Fall back to environment variables
    config['smtp_server'] = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    config['smtp_port'] = int(os.getenv("SMTP_PORT", 587))
    config['sender_email'] = os.getenv("SENDER_EMAIL", "")
    config['sender_password'] = os.getenv("SENDER_PASSWORD", "")

    return config


EMAIL_CONFIG = get_email_config()


# -----------------------
# DATABASE FUNCTIONS WITH CACHING (STEP 1.5)
# -----------------------

@st.cache_data(ttl=60, show_spinner=False)
def get_suppliers():
    """Get all suppliers with caching"""
    connection = sqlite3.connect("global.db")
    try:
        df = pd.read_sql_query("SELECT * FROM suppliers", connection)
        if df.empty:
            return pd.DataFrame()  # Return empty DataFrame instead of None
        return df
    except Exception as e:
        st.error(f"Error loading suppliers: {str(e)}")
        return pd.DataFrame()
    finally:
        connection.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_products():
    """Get all products with caching"""
    connection = sqlite3.connect("global.db")
    try:
        df = pd.read_sql_query("""
                               SELECT p.*, s.supplier_Name
                               FROM product p
                                        LEFT JOIN suppliers s ON p.supplier_ID = s.supplier_ID
                               """, connection)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error loading products: {str(e)}")
        return pd.DataFrame()
    finally:
        connection.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_retailers():
    """Get all retailers with caching"""
    connection = sqlite3.connect("global.db")
    try:
        df = pd.read_sql_query("SELECT * FROM retailers", connection)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error loading retailers: {str(e)}")
        return pd.DataFrame()
    finally:
        connection.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_customers():
    """Get all independent customers with caching"""
    connection = sqlite3.connect("global.db")
    try:
        df = pd.read_sql_query("SELECT * FROM customers", connection)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error loading customers: {str(e)}")
        return pd.DataFrame()
    finally:
        connection.close()


@st.cache_data(ttl=30, show_spinner=False)  # Shorter TTL for inventory
def get_inventory():
    """Get inventory levels with caching"""
    connection = sqlite3.connect("global.db")
    try:
        # Check if supplier_ID exists in inventory table
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(inventory)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'supplier_ID' in columns:
            query = """
                    SELECT i.*, p.selling_Price, p.unit_Cost, p.supplier_ID
                    FROM inventory i
                             LEFT JOIN product p ON i.product_ID = p.product_ID
                    ORDER BY i.stock_on_hand ASC \
                    """
        else:
            query = """
                    SELECT i.*, p.selling_Price, p.unit_Cost
                    FROM inventory i
                             LEFT JOIN product p ON i.product_ID = p.product_ID
                    ORDER BY i.stock_on_hand ASC \
                    """
        df = pd.read_sql_query(query, connection)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error loading inventory: {str(e)}")
        return pd.DataFrame()
    finally:
        connection.close()


@st.cache_data(ttl=300, show_spinner=False)  # Longer TTL for financial data
def get_financial_summary():
    """Get financial summary with caching"""
    connection = sqlite3.connect("global.db")
    try:
        sales = pd.read_sql_query("SELECT SUM(invoice_Amount) as total_sales FROM accounts_receivable", connection)
        ar = pd.read_sql_query(
            "SELECT SUM(outstanding_Balance) as total_ar FROM accounts_receivable WHERE status != 'Paid'", connection)
        ap = pd.read_sql_query(
            "SELECT SUM(outstanding_Balance) as total_ap FROM accounts_payable WHERE status != 'Paid'", connection)
        drawings = pd.read_sql_query("SELECT SUM(amount) as total_drawings FROM drawings", connection)

        return {
            'total_sales': sales['total_sales'].iloc[0] if sales['total_sales'].iloc[0] else 0,
            'total_ar': ar['total_ar'].iloc[0] if ar['total_ar'].iloc[0] else 0,
            'total_ap': ap['total_ap'].iloc[0] if ap['total_ap'].iloc[0] else 0,
            'total_drawings': drawings['total_drawings'].iloc[0] if drawings['total_drawings'].iloc[0] else 0
        }
    except Exception as e:
        st.error(f"Error loading financial summary: {str(e)}")
        return {
            'total_sales': 0,
            'total_ar': 0,
            'total_ap': 0,
            'total_drawings': 0
        }
    finally:
        connection.close()


@st.cache_data(ttl=60, show_spinner=False)
def get_performance():
    """Get supplier performance with caching"""
    connection = sqlite3.connect("global.db")
    try:
        # Check if performance_notes table exists
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance_notes'")
        table_exists = cursor.fetchone()

        if table_exists:
            df = pd.read_sql_query("""
                                   SELECT s.supplier_Name, p.supplier_Rating, p.Priority, p.Notes
                                   FROM performance_notes p
                                            JOIN suppliers s ON p.supplier_ID = s.supplier_ID
                                   ORDER BY p.supplier_Rating DESC
                                   """, connection)
            if df.empty:
                return pd.DataFrame()
            return df
        else:
            # Create a default performance dataframe if table doesn't exist
            suppliers_df = pd.read_sql_query("SELECT supplier_ID, supplier_Name FROM suppliers", connection)
            if suppliers_df.empty:
                return pd.DataFrame()

            default_data = []
            for _, row in suppliers_df.iterrows():
                default_data.append({
                    'supplier_Name': row['supplier_Name'],
                    'supplier_Rating': 3,
                    'Priority': 'Alternative',
                    'Notes': 'No performance data available yet'
                })
            return pd.DataFrame(default_data)
    except Exception as e:
        st.error(f"Error loading performance data: {str(e)}")
        return pd.DataFrame()
    finally:
        connection.close()


def check_low_stock():
    """Check all products for low stock levels"""
    connection = sqlite3.connect("global.db")
    try:
        # First check if supplier_ID exists in inventory
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(inventory)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'supplier_ID' in columns:
            df = pd.read_sql_query("""
                                   SELECT product_Name, stock_on_hand, reorder_level, reorder_quantity, supplier_ID
                                   FROM inventory
                                   WHERE stock_on_hand <= reorder_level
                                   ORDER BY stock_on_hand ASC
                                   """, connection)
        else:
            df = pd.read_sql_query("""
                                   SELECT product_Name, stock_on_hand, reorder_level, reorder_quantity
                                   FROM inventory
                                   WHERE stock_on_hand <= reorder_level
                                   ORDER BY stock_on_hand ASC
                                   """, connection)

        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error checking low stock: {str(e)}")
        return pd.DataFrame()
    finally:
        connection.close()


def get_reorder_recommendations():
    """Get reorder recommendations based on current stock levels"""
    connection = sqlite3.connect("global.db")
    try:
        # Check columns in inventory table
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(inventory)")
        inventory_columns = [col[1] for col in cursor.fetchall()]

        # Check if supplier_ID exists in inventory
        if 'supplier_ID' in inventory_columns:
            df = pd.read_sql_query("""
                                   SELECT i.product_Name,
                                          i.stock_on_hand,
                                          i.reorder_level,
                                          i.reorder_quantity,
                                          i.supplier_ID,
                                          s.supplier_Name
                                   FROM inventory i
                                            LEFT JOIN suppliers s ON i.supplier_ID = s.supplier_ID
                                   WHERE i.stock_on_hand <= i.reorder_level
                                   ORDER BY (i.reorder_level - i.stock_on_hand) DESC
                                   """, connection)
        else:
            # If supplier_ID not in inventory, get from product table
            df = pd.read_sql_query("""
                                   SELECT i.product_Name,
                                          i.stock_on_hand,
                                          i.reorder_level,
                                          i.reorder_quantity,
                                          p.supplier_ID,
                                          s.supplier_Name
                                   FROM inventory i
                                            LEFT JOIN product p ON i.product_ID = p.product_ID
                                            LEFT JOIN suppliers s ON p.supplier_ID = s.supplier_ID
                                   WHERE i.stock_on_hand <= i.reorder_level
                                   ORDER BY (i.reorder_level - i.stock_on_hand) DESC
                                   """, connection)

        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error getting reorder recommendations: {str(e)}")
        return pd.DataFrame()
    finally:
        connection.close()


# -----------------------
# INVENTORY UPDATE FUNCTIONS (No caching needed for updates)
# -----------------------
def update_inventory(product_id, quantity_sold):
    """Automatically update inventory when a sale is made"""
    connection = sqlite3.connect("global.db")
    cursor = connection.cursor()

    try:
        # Get current stock
        cursor.execute("SELECT stock_on_hand, product_Name FROM inventory WHERE product_ID = ?", (product_id,))
        result = cursor.fetchone()

        if result:
            current_stock, product_name = result
            new_stock = current_stock - quantity_sold

            if new_stock < 0:
                return False, f"Insufficient stock for {product_name}. Only {current_stock} units available."

            # Update inventory
            cursor.execute("""
                           UPDATE inventory
                           SET stock_on_hand = ?,
                               last_updated  = ?
                           WHERE product_ID = ?
                           """, (new_stock, datetime.now().strftime("%Y-%m-%d"), product_id))

            connection.commit()

            # Clear cache to refresh data
            st.cache_data.clear()

            # Check if reorder is needed
            cursor.execute("""
                           SELECT reorder_level, reorder_quantity
                           FROM inventory
                           WHERE product_ID = ?
                           """, (product_id,))
            reorder_info = cursor.fetchone()

            if reorder_info and new_stock <= reorder_info[0]:
                return True, f"Stock updated. {product_name} is below reorder level! Consider reordering {reorder_info[1]} units."

            return True, f"Stock updated successfully. {product_name} now has {new_stock} units."

        return False, f"Product {product_id} not found in inventory."

    except Exception as e:
        return False, f"Error updating inventory: {str(e)}"
    finally:
        connection.close()


# -----------------------
# INVOICE GENERATION FUNCTIONS
# -----------------------
def generate_invoice_pdf(invoice_data):
    """Generate PDF invoice using ReportLab"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Company Header
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        alignment=1
    )

    story.append(Paragraph("Global Trends", title_style))
    story.append(Paragraph("Invoice", styles['Heading2']))
    story.append(Spacer(1, 0.2 * inch))

    # Invoice Details
    invoice_details = [
        ["Invoice Number:", invoice_data.get('invoice_number', 'INV-001')],
        ["Invoice Date:", invoice_data.get('invoice_date', datetime.now().strftime("%Y-%m-%d"))],
        ["Due Date:", invoice_data.get('due_date', (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"))],
        ["Customer:", invoice_data.get('customer_name', '')],
        ["Customer Type:", invoice_data.get('customer_type', 'Individual')]
    ]

    details_table = Table(invoice_details, colWidths=[2 * inch, 4 * inch])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 0.2 * inch))

    # Items Table
    items_data = [["Item", "Description", "Quantity", "Unit Price (R)", "Total (R)"]]

    for item in invoice_data.get('items', []):
        items_data.append([
            item.get('item_code', ''),
            item.get('description', ''),
            item.get('quantity', 0),
            f"{item.get('unit_price', 0):,.2f}",
            f"{item.get('total', 0):,.2f}"
        ])

    # Add subtotal and total
    items_data.append(["", "", "", "Subtotal:", f"{invoice_data.get('subtotal', 0):,.2f}"])
    items_data.append(["", "", "", "VAT (15%):", f"{invoice_data.get('vat', 0):,.2f}"])
    items_data.append(["", "", "", "Total:", f"{invoice_data.get('total', 0):,.2f}"])

    items_table = Table(items_data, colWidths=[1.2 * inch, 2.5 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch])
    items_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (4, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -3), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#ecf0f1')),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.3 * inch))

    # Payment Instructions
    payment_instructions = [
        ["Payment Instructions"],
        ["Bank: First National Bank (FNB)"],
        ["Account Name: Global Trends"],
        ["Account Number: 628 123 456 78"],
        ["Branch Code: 250655"],
        ["Reference: " + invoice_data.get('invoice_number', 'INV-001')]
    ]

    payment_table = Table(payment_instructions, colWidths=[5.5 * inch])
    payment_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(payment_table)

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def save_invoice_to_database(invoice_data):
    """Save invoice record to database"""
    connection = sqlite3.connect("global.db")
    cursor = connection.cursor()

    try:
        cursor.execute("""
                       INSERT INTO accounts_receivable
                       (receivable_ID, customer_ID, customer_Name, invoice_Date, due_Date,
                        invoice_Amount, amount_Paid, outstanding_Balance, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                       """, (
                           invoice_data.get('invoice_number', ''),
                           invoice_data.get('customer_id', ''),
                           invoice_data.get('customer_name', ''),
                           invoice_data.get('invoice_date', datetime.now().strftime("%Y-%m-%d")),
                           invoice_data.get('due_date', (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")),
                           invoice_data.get('total', 0),
                           0,
                           invoice_data.get('total', 0),
                           'Current'
                       ))
        connection.commit()

        # Clear cache for financial data
        st.cache_data.clear()

        return True
    except Exception as e:
        print(f"Error saving invoice: {e}")
        return False
    finally:
        connection.close()


def send_invoice_email(invoice_pdf, invoice_data, recipient_email):
    """Send invoice via email"""
    if not EMAIL_CONFIG['sender_email'] or not EMAIL_CONFIG['sender_password']:
        return False, "Email credentials not configured. Please set SENDER_EMAIL and SENDER_PASSWORD."

    try:
        # Create email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = recipient_email
        msg['Subject'] = f"Invoice {invoice_data['invoice_number']} from Global Trends"

        # Email body
        body = f"""
        Dear {invoice_data['customer_name']},

        Please find attached invoice {invoice_data['invoice_number']} for your recent purchase from Global Trends.

        Invoice Details:
        - Invoice Date: {invoice_data['invoice_date']}
        - Due Date: {invoice_data['due_date']}
        - Total Amount: R{invoice_data['total']:,.2f}

        Payment can be made via EFT using the banking details provided in the invoice.

        If you have any questions, please don't hesitate to contact us.

        Thank you for your business!

        Regards,
        Global Trends Team
        """

        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        attachment = MIMEBase('application', 'pdf')
        attachment.set_payload(invoice_pdf.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition',
                              f'attachment; filename=invoice_{invoice_data["invoice_number"]}.pdf')
        msg.attach(attachment)

        # Send email
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()

        return True, "Invoice sent successfully!"

    except Exception as e:
        return False, f"Error sending email: {str(e)}"


# -----------------------
# SALE PROCESSING FUNCTION
# -----------------------
def process_sale(customer_id, customer_name, customer_type, items, recipient_email=None):
    """Process a sale with automatic inventory update and invoice generation"""

    # Calculate totals
    subtotal = sum(item['quantity'] * item['unit_price'] for item in items)
    vat = subtotal * 0.15
    total = subtotal + vat

    # Generate invoice number
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{customer_id}"

    # Prepare invoice data
    invoice_data = {
        'invoice_number': invoice_number,
        'invoice_date': datetime.now().strftime("%Y-%m-%d"),
        'due_date': (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        'customer_id': customer_id,
        'customer_name': customer_name,
        'customer_type': customer_type,
        'items': items,
        'subtotal': subtotal,
        'vat': vat,
        'total': total
    }

    # Update inventory for each item
    inventory_updates = []
    for item in items:
        success, message = update_inventory(item['product_id'], item['quantity'])
        inventory_updates.append({
            'product': item['description'],
            'success': success,
            'message': message
        })

    # Check if all inventory updates were successful
    all_successful = all(update['success'] for update in inventory_updates)

    if not all_successful:
        return {
            'success': False,
            'message': "Inventory update failed for some items",
            'details': inventory_updates
        }

    # Save invoice to database
    if save_invoice_to_database(invoice_data):
        # Generate PDF
        invoice_pdf = generate_invoice_pdf(invoice_data)

        # Send email if recipient provided
        email_status = None
        if recipient_email:
            email_success, email_message = send_invoice_email(invoice_pdf, invoice_data, recipient_email)
            email_status = {'success': email_success, 'message': email_message}

        return {
            'success': True,
            'invoice_data': invoice_data,
            'invoice_pdf': invoice_pdf,
            'inventory_updates': inventory_updates,
            'email_status': email_status,
            'message': f"Sale processed successfully! Invoice {invoice_number} created."
        }

    return {
        'success': False,
        'message': "Failed to save invoice to database"
    }


# -----------------------
# TOOLS
# -----------------------
def query_database(query):
    """Execute SQL queries safely"""
    connection = sqlite3.connect("global.db")
    try:
        # For safety, only allow SELECT queries
        if query.strip().upper().startswith('SELECT'):
            df = pd.read_sql_query(query, connection)
            return df.to_string()
        else:
            return "Only SELECT queries are allowed for security reasons."
    except Exception as e:
        return f"Error executing query: {str(e)}"
    finally:
        connection.close()


db_tool = Tool(
    name="Database_Query",
    func=query_database,
    description="""
    Use this tool to query the Global Trends database.
    Available tables:
    - suppliers: supplier_ID, supplier_Name, Account, wechat_Contact, Website, products
    - product: product_ID, product_Categories, products_ID, supplier_ID, supplier_Type, MOQ, lead_Times, unit_Cost, selling_Price
    - retailers: retailer_ID, retailer_Name, status, order_Quantity, product, order_Status, management_Contacts, payment_Terms
    - customers: customer_ID, customer_Name, contact_Number, email, total_orders, total_spent, outstanding_balance
    - inventory: inventory_ID, product_ID, product_Name, stock_on_hand, reorder_level, reorder_quantity, location, last_updated
    - chart_of_accounts: account_ID, account_Name, account_Type, balance
    - accounts_receivable: receivable_ID, customer_ID, customer_Name, invoice_Date, due_Date, invoice_Amount, outstanding_Balance, status
    - accounts_payable: payable_ID, supplier_ID, supplier_Name, invoice_Date, due_Date, invoice_Amount, outstanding_Balance, status
    - drawings: drawing_ID, date, amount, description
    - transactions: transaction_ID, date, description, account_Debit, account_Credit, amount, category

    You can ask questions like:
    - Show me all active suppliers
    - Which products are low on stock?
    - What are the top rated suppliers?
    - Show me retailers with pending orders
    - What is the total accounts receivable?
    - Show me customers with outstanding balances
    - What are the recent transactions?
    """
)

search = DuckDuckGoSearchRun()

tools = [db_tool, search]

# -----------------------
# AI (GROQ)
# -----------------------
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2
)

react_prompt = PromptTemplate.from_template(
    """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
)

agent = AgentExecutor(
    agent=create_react_agent(llm=llm, tools=tools, prompt=react_prompt),
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

# -----------------------
# STREAMLIT UI
# -----------------------
st.title("🌍 Global Trends AI Assistant")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [
    "💬 AI Chat Assistant",
    "🛒 Process Sale",
    "📊 Supplier Dashboard",
    "📦 Product Dashboard",
    "🏪 Retailer Dashboard",
    "👥 Customer Dashboard",
    "📦 Inventory Dashboard",
    "💰 Financial Dashboard",
    "⭐ Performance Dashboard",
    "➕ Add Data"
])

# -----------------------
# PROCESS SALE PAGE
# -----------------------
if page == "🛒 Process Sale":
    st.header("🛒 Process New Sale")
    st.markdown("Create a new sale with automatic inventory updates and invoice generation")

    # Customer Information
    st.subheader("Customer Information")
    col1, col2 = st.columns(2)

    with col1:
        customer_type = st.selectbox("Customer Type", ["Individual", "Retailer"])

        if customer_type == "Individual":
            # Get customers from database
            customers_df = get_customers()

            if not customers_df.empty:
                customer_options = {f"{row['customer_Name']} ({row['customer_ID']})": row['customer_ID']
                                    for _, row in customers_df.iterrows()}
                selected_customer = st.selectbox("Select Customer", list(customer_options.keys()))
                customer_id = customer_options[selected_customer]
                customer_name = selected_customer.split(" (")[0]

                # Get customer email
                customer_email = customers_df[customers_df['customer_ID'] == customer_id]['email'].iloc[
                    0] if not customers_df.empty else ""
                recipient_email = st.text_input("Email for Invoice", value=customer_email if customer_email else "")
            else:
                st.warning("No customers found. Please add customers first.")
                customer_id = st.text_input("Customer ID", "c011")
                customer_name = st.text_input("Customer Name")
                recipient_email = st.text_input("Email for Invoice")
        else:
            # Get retailers from database
            retailers_df = get_retailers()

            if not retailers_df.empty:
                active_retailers = retailers_df[retailers_df['status'] == 'Active']
                if not active_retailers.empty:
                    retailer_options = {f"{row['retailer_Name']} ({row['retailer_ID']})": row['retailer_ID']
                                        for _, row in active_retailers.iterrows()}
                    selected_retailer = st.selectbox("Select Retailer", list(retailer_options.keys()))
                    customer_id = retailer_options[selected_retailer]
                    customer_name = selected_retailer.split(" (")[0]

                    # Get retailer contact
                    retailer_contact = \
                    active_retailers[active_retailers['retailer_ID'] == customer_id]['management_Contacts'].iloc[0]
                    recipient_email = st.text_input("Email for Invoice",
                                                    value=retailer_contact if "@" in str(retailer_contact) else "")
                else:
                    st.warning("No active retailers found.")
                    customer_id = st.text_input("Customer ID", "r006")
                    customer_name = st.text_input("Customer Name")
                    recipient_email = st.text_input("Email for Invoice")
            else:
                st.warning("No retailers found.")
                customer_id = st.text_input("Customer ID", "r006")
                customer_name = st.text_input("Customer Name")
                recipient_email = st.text_input("Email for Invoice")

    # Order Items
    st.subheader("Order Items")

    # Get products for dropdown
    products_df = get_products()

    if 'sale_items' not in st.session_state:
        st.session_state.sale_items = []

    # Add item form
    with st.form("add_item"):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if not products_df.empty:
                product_options = {f"{row['products_ID']} ({row['product_ID']})": row['product_ID']
                                   for _, row in products_df.iterrows()}
                selected_product = st.selectbox("Product", list(product_options.keys()))
                product_id = product_options[selected_product]
            else:
                st.warning("No products available. Please add products first.")
                product_id = ""

        if not products_df.empty and product_id:
            # Get product details
            product_row = products_df[products_df['product_ID'] == product_id].iloc[0]
            product_name = product_row['products_ID']
            unit_price = float(product_row['selling_Price']) if pd.notna(product_row['selling_Price']) else 0.0

            # Get inventory for stock check
            inventory_df = get_inventory()
            stock_available = 0
            if not inventory_df.empty:
                inv_row = inventory_df[inventory_df['product_ID'] == product_id]
                if not inv_row.empty:
                    stock_available = inv_row['stock_on_hand'].iloc[0]

            with col2:
                st.write(f"**Unit Price:** R{unit_price:,.2f}")
                st.write(f"**Stock Available:** {stock_available} units")

            with col3:
                quantity = st.number_input("Quantity", min_value=1,
                                           max_value=stock_available if stock_available > 0 else 100, value=1)

            with col4:
                item_total = quantity * unit_price
                st.write(f"**Item Total:** R{item_total:,.2f}")

        add_item = st.form_submit_button("Add Item")

        if not products_df.empty and product_id:
            if add_item and quantity > 0:
                if quantity <= stock_available:
                    st.session_state.sale_items.append({
                        'product_id': product_id,
                        'item_code': product_id,
                        'description': product_name,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total': item_total
                    })
                    st.success(f"Added {quantity}x {product_name}")
                    st.rerun()
                else:
                    st.error(f"Insufficient stock. Only {stock_available} units available.")

    # Display current items
    if st.session_state.sale_items:
        st.subheader("Current Order Items")
        items_df = pd.DataFrame(st.session_state.sale_items)
        st.dataframe(items_df[['description', 'quantity', 'unit_price', 'total']])

        # Calculate totals
        subtotal = sum(item['total'] for item in st.session_state.sale_items)
        vat = subtotal * 0.15
        total = subtotal + vat

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Subtotal", f"R{subtotal:,.2f}")
        with col2:
            st.metric("VAT (15%)", f"R{vat:,.2f}")
        with col3:
            st.metric("Total", f"R{total:,.2f}")

        # Clear items button
        if st.button("Clear All Items"):
            st.session_state.sale_items = []
            st.rerun()

        # Process Sale button
        if st.button("✅ Process Sale & Generate Invoice", type="primary"):
            with st.spinner("Processing sale..."):
                result = process_sale(
                    customer_id=customer_id,
                    customer_name=customer_name,
                    customer_type=customer_type,
                    items=st.session_state.sale_items,
                    recipient_email=recipient_email if recipient_email else None
                )

                if result['success']:
                    st.success(result['message'])

                    # Show inventory updates
                    with st.expander("Inventory Updates"):
                        for update in result['inventory_updates']:
                            if update['success']:
                                st.success(update['message'])
                            else:
                                st.error(update['message'])

                    # Show invoice details
                    with st.expander("Invoice Details"):
                        invoice = result['invoice_data']
                        st.write(f"**Invoice Number:** {invoice['invoice_number']}")
                        st.write(f"**Invoice Date:** {invoice['invoice_date']}")
                        st.write(f"**Due Date:** {invoice['due_date']}")
                        st.write(f"**Total Amount:** R{invoice['total']:,.2f}")

                        # Download invoice button
                        st.download_button(
                            label="📄 Download Invoice PDF",
                            data=result['invoice_pdf'],
                            file_name=f"invoice_{invoice['invoice_number']}.pdf",
                            mime="application/pdf"
                        )

                    # Show email status
                    if result.get('email_status'):
                        if result['email_status']['success']:
                            st.success(result['email_status']['message'])
                        else:
                            st.warning(result['email_status']['message'])

                    # Clear items after successful sale
                    if st.button("Start New Sale"):
                        st.session_state.sale_items = []
                        st.rerun()
                else:
                    st.error(result['message'])
                    if 'details' in result:
                        for detail in result['details']:
                            st.error(detail['message'])

# -----------------------
# CHAT ASSISTANT PAGE
# -----------------------
elif page == "💬 AI Chat Assistant":
    st.header("🤖 AI Assistant")
    st.markdown("Ask me anything about your suppliers, products, retailers, customers, inventory, or finances!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # User input
    user_input = st.chat_input("Ask about your suppliers, products, or orders...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        try:
            with st.spinner("Thinking..."):
                response = agent.invoke({"input": user_input})["output"]
        except Exception as e:
            response = f"⚠️ Error: {str(e)}"

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)

# -----------------------
# SUPPLIER DASHBOARD
# -----------------------
elif page == "📊 Supplier Dashboard":
    st.header("🏭 Supplier Management")

    try:
        df_suppliers = get_suppliers()

        if not df_suppliers.empty:
            st.subheader("📋 All Suppliers")
            st.dataframe(df_suppliers)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Suppliers", len(df_suppliers))

            with col2:
                products_df = get_products()
                st.metric("Total Products", len(products_df) if not products_df.empty else 0)

            with col3:
                perf_df = get_performance()
                if not perf_df.empty and 'supplier_Rating' in perf_df.columns:
                    # Convert to numeric safely
                    perf_df['supplier_Rating_num'] = pd.to_numeric(perf_df['supplier_Rating'], errors='coerce')
                    top_rated = len(perf_df[perf_df['supplier_Rating_num'] >= 4])
                    st.metric("Top Rated Suppliers (4+⭐)", top_rated)
                else:
                    st.metric("Top Rated Suppliers (4+⭐)", "N/A")

        else:
            st.info("No supplier data available. Please add suppliers using the 'Add Data' page.")

    except Exception as e:
        st.error(f"Error loading supplier dashboard: {str(e)}")
        import traceback

        st.error(traceback.format_exc())

# -----------------------
# PRODUCT DASHBOARD
# -----------------------
elif page == "📦 Product Dashboard":
    st.header("📦 Product Catalog")

    try:
        df_products = get_products()

        if not df_products.empty and len(df_products) > 0:
            st.subheader("📋 All Products")

            # Create a copy for display to avoid modifying original
            display_df = df_products.copy()

            if 'unit_Cost' in display_df.columns:
                display_df['unit_Cost'] = display_df['unit_Cost'].apply(lambda x: f"R{x:,.2f}" if pd.notna(x) else x)
            if 'selling_Price' in display_df.columns:
                display_df['selling_Price'] = display_df['selling_Price'].apply(
                    lambda x: f"R{x:,.2f}" if pd.notna(x) else x)

            st.dataframe(display_df)

            st.subheader("📊 Products by Category")
            if 'product_Categories' in df_products.columns:
                # Check if column has data before counting
                if not df_products['product_Categories'].isna().all():
                    category_counts = df_products['product_Categories'].value_counts()
                    if not category_counts.empty:
                        st.bar_chart(category_counts)
                else:
                    st.info("No category data available")

            st.subheader("💰 Profit Margin by Product")
            if 'unit_Cost' in df_products.columns and 'selling_Price' in df_products.columns:
                # Convert to numeric safely
                df_products['unit_Cost_num'] = pd.to_numeric(df_products['unit_Cost'], errors='coerce')
                df_products['selling_Price_num'] = pd.to_numeric(df_products['selling_Price'], errors='coerce')

                # Create a copy to avoid SettingWithCopyWarning
                df_margins = df_products.copy()

                # Calculate profit margin only where we have valid data
                valid_mask = (df_margins['selling_Price_num'] > 0) & (df_margins['unit_Cost_num'].notna())

                # Initialize column with 0
                df_margins['profit_margin'] = 0.0

                # Calculate margins only for valid rows
                if valid_mask.any():  # Check if any valid rows exist
                    df_margins.loc[valid_mask, 'profit_margin'] = (
                            (df_margins.loc[valid_mask, 'selling_Price_num'] - df_margins.loc[
                                valid_mask, 'unit_Cost_num']) /
                            df_margins.loc[valid_mask, 'selling_Price_num'] * 100
                    ).round(2)

                # Only show chart if we have valid data
                if (df_margins['profit_margin'] != 0).any():
                    margin_df = df_margins[['products_ID', 'profit_margin']].set_index('products_ID')
                    if not margin_df.empty:
                        st.bar_chart(margin_df)
                else:
                    st.info("No valid profit margin data available")

            st.subheader("⏱️ Lead Times by Product")
            if 'lead_Times' in df_products.columns and 'products_ID' in df_products.columns:
                # Drop duplicates and handle NaN values
                lead_times_df = df_products[['products_ID', 'lead_Times']].drop_duplicates()
                lead_times_df = lead_times_df.dropna(subset=['lead_Times'])
                if not lead_times_df.empty:
                    st.dataframe(lead_times_df)
                else:
                    st.info("No lead time data available")

        else:
            st.info("No product data available. Please add products using the 'Add Data' page.")

    except Exception as e:
        st.error(f"Error loading product dashboard: {str(e)}")
        import traceback

        st.error(traceback.format_exc())

# -----------------------
# RETAILER DASHBOARD
# -----------------------
elif page == "🏪 Retailer Dashboard":
    st.header("🏪 Retailer Management")

    try:
        df_retailers = get_retailers()

        if not df_retailers.empty:
            st.subheader("📋 All Retailers")
            st.dataframe(df_retailers)

            st.subheader("📊 Order Status Distribution")
            if 'order_Status' in df_retailers.columns:
                status_counts = df_retailers['order_Status'].value_counts()
                if not status_counts.empty:
                    st.bar_chart(status_counts)

            st.subheader("🏷️ Retailer Status")
            if 'status' in df_retailers.columns:
                retailer_status = df_retailers['status'].value_counts()
                if not retailer_status.empty:
                    st.bar_chart(retailer_status)

        else:
            st.info("No retailer data available. Please add retailers using the 'Add Data' page.")

    except Exception as e:
        st.error(f"Error loading retailer dashboard: {str(e)}")
        import traceback

        st.error(traceback.format_exc())

# -----------------------
# CUSTOMER DASHBOARD
# -----------------------
elif page == "👥 Customer Dashboard":
    st.header("👥 Independent Customer Management")

    try:
        df_customers = get_customers()

        if not df_customers.empty:
            st.subheader("📋 All Customers")

            display_df = df_customers.copy()
            if 'total_spent' in display_df.columns:
                display_df['total_spent'] = display_df['total_spent'].apply(
                    lambda x: f"R{x:,.2f}" if pd.notna(x) else x)
            if 'outstanding_balance' in display_df.columns:
                display_df['outstanding_balance'] = display_df['outstanding_balance'].apply(
                    lambda x: f"R{x:,.2f}" if pd.notna(x) else x)
            st.dataframe(display_df)

            # Create numeric versions for calculations
            df_customers['total_spent_num'] = pd.to_numeric(df_customers['total_spent'], errors='coerce')
            df_customers['outstanding_balance_num'] = pd.to_numeric(df_customers['outstanding_balance'],
                                                                    errors='coerce')

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Customers", len(df_customers))

            with col2:
                total_spent = df_customers['total_spent_num'].sum()
                st.metric("Total Sales to Customers", f"R{total_spent:,.2f}" if pd.notna(total_spent) else "R0.00")

            with col3:
                outstanding = df_customers['outstanding_balance_num'].sum()
                st.metric("Outstanding Balances", f"R{outstanding:,.2f}" if pd.notna(outstanding) else "R0.00")

            st.subheader("⚠️ Customers with Outstanding Balances")
            outstanding_customers = df_customers[df_customers['outstanding_balance_num'] > 0]
            if not outstanding_customers.empty:
                st.dataframe(outstanding_customers[['customer_Name', 'outstanding_balance']])
            else:
                st.success("All customers have paid their balances!")

            st.subheader("🏆 Top Customers by Spending")
            top_customers = df_customers.nlargest(5, 'total_spent_num')[['customer_Name', 'total_spent']]
            if not top_customers.empty:
                st.dataframe(top_customers)
            else:
                st.info("No customer spending data available")

        else:
            st.info("No customer data available. Please add customers using the 'Add Data' page.")

    except Exception as e:
        st.error(f"Error loading customer dashboard: {str(e)}")
        import traceback

        st.error(traceback.format_exc())

# -----------------------
# INVENTORY DASHBOARD
# -----------------------
elif page == "📦 Inventory Dashboard":
    st.header("📦 Inventory Management")

    try:
        # Show low stock alerts at the top
        low_stock_df = check_low_stock()
        if not low_stock_df.empty:
            st.warning(f"⚠️ {len(low_stock_df)} products are below reorder level!")

            # Reorder recommendations
            st.subheader("🔄 Reorder Recommendations")
            reorder_df = get_reorder_recommendations()
            if not reorder_df.empty:
                for _, row in reorder_df.iterrows():
                    supplier_info = f" from {row['supplier_Name']}" if 'supplier_Name' in row and pd.notna(
                        row['supplier_Name']) else ""
                    st.info(
                        f"**{row['product_Name']}**: {row['stock_on_hand']} units left (Reorder level: {row['reorder_level']}). "
                        f"Recommended reorder: {row['reorder_quantity']} units{supplier_info}")

        df_inventory = get_inventory()

        if not df_inventory.empty:
            st.subheader("📋 Current Inventory Levels")

            display_df = df_inventory.copy()
            if 'unit_Cost' in display_df.columns:
                display_df['unit_Cost'] = display_df['unit_Cost'].apply(lambda x: f"R{x:,.2f}" if pd.notna(x) else x)
            if 'selling_Price' in display_df.columns:
                display_df['selling_Price'] = display_df['selling_Price'].apply(
                    lambda x: f"R{x:,.2f}" if pd.notna(x) else x)
            st.dataframe(display_df)

            st.subheader("📊 Stock Levels by Product")
            if 'product_Name' in df_inventory.columns and 'stock_on_hand' in df_inventory.columns:
                # Create a copy to avoid issues
                stock_df = df_inventory.copy()
                stock_df = stock_df.set_index('product_Name')['stock_on_hand'].dropna()
                if not stock_df.empty:
                    st.bar_chart(stock_df)
                else:
                    st.info("No stock data available")

            # Inventory value
            st.subheader("💰 Inventory Value")
            if 'unit_Cost' in df_inventory.columns and 'stock_on_hand' in df_inventory.columns:
                df_inventory['unit_Cost_num'] = pd.to_numeric(df_inventory['unit_Cost'], errors='coerce')
                df_inventory['stock_on_hand_num'] = pd.to_numeric(df_inventory['stock_on_hand'], errors='coerce')

                # Use .sum() which handles NaN correctly
                total_value = (df_inventory['stock_on_hand_num'] * df_inventory['unit_Cost_num']).sum()
                st.metric("Total Inventory Value", f"R{total_value:,.2f}" if pd.notna(total_value) else "R0.00")

        else:
            st.info("No inventory data available. Please add products to inventory.")

    except Exception as e:
        st.error(f"Error loading inventory dashboard: {str(e)}")
        import traceback

        st.error(traceback.format_exc())

# -----------------------
# FINANCIAL DASHBOARD
# -----------------------
elif page == "💰 Financial Dashboard":
    st.header("💰 Financial Management")

    try:
        finances = get_financial_summary()

        st.subheader("📊 Key Financial Metrics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_sales = finances['total_sales'] if finances['total_sales'] is not None else 0
            st.metric("Total Sales (March)", f"R{total_sales:,.2f}")

        with col2:
            total_ar = finances['total_ar'] if finances['total_ar'] is not None else 0
            st.metric("Accounts Receivable", f"R{total_ar:,.2f}")

        with col3:
            total_ap = finances['total_ap'] if finances['total_ap'] is not None else 0
            st.metric("Accounts Payable", f"R{total_ap:,.2f}")

        with col4:
            total_drawings = finances['total_drawings'] if finances['total_drawings'] is not None else 0
            st.metric("Owner Drawings (March)", f"R{total_drawings:,.2f}")

        st.subheader("📋 Accounts Receivable Details")
        conn = sqlite3.connect("global.db")
        ar_details = pd.read_sql_query("""
                                       SELECT receivable_ID,
                                              customer_Name,
                                              invoice_Date,
                                              due_Date,
                                              invoice_Amount,
                                              outstanding_Balance,
                                              status
                                       FROM accounts_receivable
                                       WHERE status != 'Paid'
                                       ORDER BY due_Date ASC
                                       """, conn)
        if not ar_details.empty:
            ar_details['invoice_Amount'] = ar_details['invoice_Amount'].apply(
                lambda x: f"R{x:,.2f}" if pd.notna(x) else "R0.00")
            ar_details['outstanding_Balance'] = ar_details['outstanding_Balance'].apply(
                lambda x: f"R{x:,.2f}" if pd.notna(x) else "R0.00")
            st.dataframe(ar_details)
        else:
            st.success("No outstanding accounts receivable!")
        conn.close()

        st.subheader("📋 Accounts Payable Details")
        conn = sqlite3.connect("global.db")
        ap_details = pd.read_sql_query("""
                                       SELECT payable_ID,
                                              supplier_Name,
                                              invoice_Date,
                                              due_Date,
                                              invoice_Amount,
                                              outstanding_Balance,
                                              status
                                       FROM accounts_payable
                                       WHERE status != 'Paid'
                                       ORDER BY due_Date ASC
                                       """, conn)
        if not ap_details.empty:
            ap_details['invoice_Amount'] = ap_details['invoice_Amount'].apply(
                lambda x: f"R{x:,.2f}" if pd.notna(x) else "R0.00")
            ap_details['outstanding_Balance'] = ap_details['outstanding_Balance'].apply(
                lambda x: f"R{x:,.2f}" if pd.notna(x) else "R0.00")
            st.dataframe(ap_details)
        else:
            st.success("No outstanding accounts payable!")
        conn.close()

        st.subheader("🔄 Recent Transactions")
        conn = sqlite3.connect("global.db")
        transactions = pd.read_sql_query("""
                                         SELECT transaction_ID, date, description, account_Debit, account_Credit, amount, category
                                         FROM transactions
                                         ORDER BY date DESC
                                             LIMIT 15
                                         """, conn)
        if not transactions.empty:
            transactions['amount'] = transactions['amount'].apply(lambda x: f"R{x:,.2f}" if pd.notna(x) else "R0.00")
            st.dataframe(transactions)
        else:
            st.info("No transaction data available")
        conn.close()

    except Exception as e:
        st.error(f"Error loading financial dashboard: {str(e)}")
        import traceback

        st.error(traceback.format_exc())

# -----------------------
# PERFORMANCE DASHBOARD
# -----------------------
elif page == "⭐ Performance Dashboard":
    st.header("⭐ Supplier Performance")

    try:
        df_performance = get_performance()

        if not df_performance.empty:
            st.subheader("📊 Supplier Ratings")

            col1, col2 = st.columns(2)

            with col1:
                st.dataframe(df_performance)

            with col2:
                if 'supplier_Rating' in df_performance.columns:
                    # Convert to numeric safely
                    df_performance['supplier_Rating_num'] = pd.to_numeric(df_performance['supplier_Rating'],
                                                                          errors='coerce')
                    rating_counts = df_performance['supplier_Rating_num'].value_counts().sort_index()
                    if not rating_counts.empty:
                        st.subheader("Rating Distribution")
                        st.bar_chart(rating_counts)
                    else:
                        st.info("No rating data available")

            if 'Priority' in df_performance.columns:
                st.subheader("🎯 Supplier Priority")
                priority_counts = df_performance['Priority'].value_counts()
                if not priority_counts.empty:
                    st.bar_chart(priority_counts)
                else:
                    st.info("No priority data available")

            if 'supplier_Rating' in df_performance.columns and 'Notes' in df_performance.columns:
                st.subheader("📝 Notes from Top Suppliers")
                df_performance['supplier_Rating_num'] = pd.to_numeric(df_performance['supplier_Rating'],
                                                                      errors='coerce')
                top_suppliers = df_performance[df_performance['supplier_Rating_num'] >= 4]
                if not top_suppliers.empty:
                    for _, row in top_suppliers.iterrows():
                        st.info(
                            f"**{row['supplier_Name']}** (Rating: {row['supplier_Rating']}⭐ - {row['Priority']})\n\n{row['Notes']}")
                else:
                    st.info("No top-rated suppliers found")

        else:
            st.info("No performance data available.")

    except Exception as e:
        st.error(f"Error loading performance dashboard: {str(e)}")
        import traceback

        st.error(traceback.format_exc())

# -----------------------
# ADD DATA PAGE
# -----------------------
elif page == "➕ Add Data":
    st.header("➕ Add New Data")

    tab1, tab2, tab3, tab4 = st.tabs(["Add Supplier", "Add Product", "Add Retailer", "Add Customer"])

    # Tab 1: Add Supplier
    with tab1:
        st.subheader("Add New Supplier")
        with st.form("add_supplier"):
            supplier_id = st.text_input("Supplier ID (e.g., s006)")
            supplier_name = st.text_input("Supplier Name")
            account = st.text_input("Primary Contact Person")
            wechat = st.text_input("WeChat Contact")
            website = st.text_input("Website")
            products_supplied = st.text_input("Products Supplied")

            submitted_supplier = st.form_submit_button("Add Supplier")

            if submitted_supplier:
                try:
                    conn = sqlite3.connect("global.db")
                    cur = conn.cursor()

                    cur.execute("""
                                INSERT INTO suppliers (supplier_ID, supplier_Name, Account, wechat_Contact, Website,
                                                       products)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """, (supplier_id, supplier_name, account, wechat, website, products_supplied))

                    # Check if performance_notes table exists before inserting
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance_notes'")
                    if cur.fetchone():
                        cur.execute("""
                                    INSERT INTO performance_notes (supplier_ID, supplier_Rating, Priority, Notes)
                                    VALUES (?, ?, ?, ?)
                                    """, (supplier_id, 3, 'Alternative', 'New supplier - awaiting evaluation'))

                    conn.commit()
                    conn.close()

                    # Clear cache to refresh data
                    st.cache_data.clear()

                    st.success(f"✅ Supplier {supplier_name} added successfully!")

                except Exception as e:
                    st.error(f"❌ Error adding supplier: {str(e)}")

    # Tab 2: Add Product
    with tab2:
        st.subheader("Add New Product")
        with st.form("add_product"):
            product_id = st.text_input("Product ID (e.g., p011)")
            product_categories = st.text_input("Product Category (e.g., Bedding, Curtains, Pots)")
            products_id = st.text_input("Product Name")
            supplier_id = st.text_input("Supplier ID (e.g., s001)")
            supplier_type = st.selectbox("Supplier Type", ["Manufacturer", "Distributor", "Importer", "Wholesaler"])
            moq = st.text_input("Minimum Order Quantity")
            lead_times = st.text_input("Lead Times")
            unit_cost = st.number_input("Unit Cost (R)", min_value=0.0, format="%.2f")
            selling_price = st.number_input("Selling Price (R)", min_value=0.0, format="%.2f")

            submitted_product = st.form_submit_button("Add Product")

            if submitted_product:
                try:
                    conn = sqlite3.connect("global.db")
                    cur = conn.cursor()

                    cur.execute("""
                                INSERT INTO product (product_ID, product_Categories, products_ID, supplier_ID,
                                                     supplier_Type, MOQ, lead_Times, unit_Cost, selling_Price)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (product_id, product_categories, products_id, supplier_id, supplier_type, moq,
                                      lead_times, unit_cost, selling_price))

                    # Also add to inventory
                    cur.execute("""
                                INSERT INTO inventory (inventory_ID, product_ID, product_Name, stock_on_hand,
                                                       reorder_level, reorder_quantity, location, last_updated)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (f"inv{product_id}", product_id, products_id, 0, 10, 20, 'Warehouse A',
                                      datetime.now().strftime("%Y-%m-%d")))

                    conn.commit()
                    conn.close()

                    # Clear cache to refresh data
                    st.cache_data.clear()

                    st.success(f"✅ Product {products_id} added successfully!")

                except Exception as e:
                    st.error(f"❌ Error adding product: {str(e)}")

    # Tab 3: Add Retailer
    with tab3:
        st.subheader("Add New Retailer")
        with st.form("add_retailer"):
            retailer_id = st.text_input("Retailer ID (e.g., r006)")
            retailer_name = st.text_input("Retailer Name")
            status = st.selectbox("Status", ["Active", "Potential", "On Hold", "Blacklist"])
            order_quantity = st.text_input("Order Quantity")
            product = st.text_input("Product")
            order_status = st.selectbox("Order Status", ["Processing", "Shipped", "Pending Approval", "Delivered"])
            management_contacts = st.text_input("Management Contact")
            payment_terms = st.selectbox("Payment Terms",
                                         ["Net 30", "Net 45", "100% Prepayment", "30 Days Deferred", "To be confirmed"])

            submitted_retailer = st.form_submit_button("Add Retailer")

            if submitted_retailer:
                try:
                    conn = sqlite3.connect("global.db")
                    cur = conn.cursor()

                    cur.execute("""
                                INSERT INTO retailers (retailer_ID, retailer_Name, status, order_Quantity, product,
                                                       order_Status, management_Contacts, payment_Terms)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (retailer_id, retailer_name, status, order_quantity, product, order_status,
                                      management_contacts, payment_terms))

                    conn.commit()
                    conn.close()

                    # Clear cache to refresh data
                    st.cache_data.clear()

                    st.success(f"✅ Retailer {retailer_name} added successfully!")

                except Exception as e:
                    st.error(f"❌ Error adding retailer: {str(e)}")

    # Tab 4: Add Customer
    with tab4:
        st.subheader("Add New Independent Customer")
        with st.form("add_customer"):
            customer_id = st.text_input("Customer ID (e.g., c011)")
            customer_name = st.text_input("Customer Name")
            contact_number = st.text_input("Contact Number")
            email = st.text_input("Email")

            submitted_customer = st.form_submit_button("Add Customer")

            if submitted_customer:
                try:
                    conn = sqlite3.connect("global.db")
                    cur = conn.cursor()

                    cur.execute("""
                                INSERT INTO customers (customer_ID, customer_Name, contact_Number, email,
                                                       total_orders, total_spent, outstanding_balance)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (customer_id, customer_name, contact_number, email, 0, 0.00, 0.00))

                    conn.commit()
                    conn.close()

                    # Clear cache to refresh data
                    st.cache_data.clear()

                    st.success(f"✅ Customer {customer_name} added successfully!")

                except Exception as e:
                    st.error(f"❌ Error adding customer: {str(e)}")