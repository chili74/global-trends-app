import sqlite3

# Create connection
connection = sqlite3.connect('global.db')
cursor = connection.cursor()

# ============================================
# TABLE 1: SUPPLIERS
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_ID VARCHAR(10) PRIMARY KEY,
    supplier_Name VARCHAR(100) NOT NULL,
    Account VARCHAR(100),
    wechat_Contact VARCHAR(100),
    Website VARCHAR(255),
    products TEXT
)
''')

# ============================================
# TABLE 2: PRODUCT
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS product (
    product_ID VARCHAR(10) PRIMARY KEY,
    product_Categories VARCHAR(100),
    products_ID VARCHAR(100),
    supplier_ID VARCHAR(10),
    supplier_Type VARCHAR(50),
    MOQ VARCHAR(50),
    lead_Times VARCHAR(50),
    unit_Cost DECIMAL(10,2),
    selling_Price DECIMAL(10,2),
    FOREIGN KEY (supplier_ID) REFERENCES suppliers(supplier_ID)
)
''')

# ============================================
# TABLE 3: RETAILERS
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS retailers (
    retailer_ID VARCHAR(10) PRIMARY KEY,
    retailer_Name VARCHAR(100) NOT NULL,
    status VARCHAR(20),
    order_Quantity VARCHAR(50),
    product TEXT,
    order_Status VARCHAR(50),
    management_Contacts VARCHAR(100),
    payment_Terms VARCHAR(50)
)
''')

# ============================================
# TABLE 4: INDEPENDENT CUSTOMERS
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS customers (
    customer_ID VARCHAR(10) PRIMARY KEY,
    customer_Name VARCHAR(100) NOT NULL,
    contact_Number VARCHAR(20),
    email VARCHAR(100),
    total_orders INT DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0.00,
    outstanding_balance DECIMAL(10,2) DEFAULT 0.00
)
''')

# ============================================
# TABLE 5: INVENTORY
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS inventory (
    inventory_ID VARCHAR(10) PRIMARY KEY,
    product_ID VARCHAR(10),
    product_Name VARCHAR(100),
    stock_on_hand INT,
    reorder_level INT,
    reorder_quantity INT,
    location VARCHAR(50),
    last_updated DATE,
    FOREIGN KEY (product_ID) REFERENCES product(product_ID)
)
''')

# ============================================
# TABLE 6a: CHART OF ACCOUNTS
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS chart_of_accounts (
    account_ID VARCHAR(10) PRIMARY KEY,
    account_Name VARCHAR(100),
    account_Type VARCHAR(50),
    balance DECIMAL(12,2)
)
''')

# ============================================
# TABLE 6b: ACCOUNTS RECEIVABLE
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS accounts_receivable (
    receivable_ID VARCHAR(10) PRIMARY KEY,
    customer_ID VARCHAR(10),
    customer_Name VARCHAR(100),
    invoice_Date DATE,
    due_Date DATE,
    invoice_Amount DECIMAL(10,2),
    amount_Paid DECIMAL(10,2) DEFAULT 0.00,
    outstanding_Balance DECIMAL(10,2),
    status VARCHAR(20)
)
''')

# ============================================
# TABLE 6c: ACCOUNTS PAYABLE
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS accounts_payable (
    payable_ID VARCHAR(10) PRIMARY KEY,
    supplier_ID VARCHAR(10),
    supplier_Name VARCHAR(100),
    invoice_Date DATE,
    due_Date DATE,
    invoice_Amount DECIMAL(10,2),
    amount_Paid DECIMAL(10,2) DEFAULT 0.00,
    outstanding_Balance DECIMAL(10,2),
    status VARCHAR(20),
    FOREIGN KEY (supplier_ID) REFERENCES suppliers(supplier_ID)
)
''')

# ============================================
# TABLE 6d: DRAWINGS
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS drawings (
    drawing_ID VARCHAR(10) PRIMARY KEY,
    date DATE,
    amount DECIMAL(10,2),
    description VARCHAR(200),
    notes TEXT
)
''')

# ============================================
# TABLE 6e: TRANSACTIONS
# ============================================
cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    transaction_ID VARCHAR(10) PRIMARY KEY,
    date DATE,
    description VARCHAR(200),
    account_Debit VARCHAR(10),
    account_Credit VARCHAR(10),
    amount DECIMAL(10,2),
    category VARCHAR(50)
)
''')

# ============================================
# INSERT SAMPLE DATA - SUPPLIERS
# ============================================
suppliers_data = [
    ('s001', 'Huasheng Textiles Co., Ltd.', 'Wang Wei', 'wangwei_huasheng', 'www.huashengtextiles.cn', 'Blankets, Bedding, Curtains'),
    ('s002', 'Jiangnan Ceramics Manufacturing', 'Li Fang', 'lifang_jiangnan', 'www.jiangnanporcelain.cn', 'Pots, Vases, Dinnerware'),
    ('s003', 'Fareast Home Furnishings', 'Chen Min', 'chenmin_fareast', 'www.fareasthome.cn', 'Curtains, Table Linens, Cushions'),
    ('s004', 'Xinguang Plastic Products', 'Zhang Yong', 'zhangyong_xinguang', 'www.xinguangplastic.cn', 'Storage Containers, Organizers'),
    ('s005', 'Ruixiang Textiles Import', 'Liu Na', 'liuna_ruixiang', 'www.ruixiangtextile.cn', 'Bed Sheets, Pillowcases')
]

cursor.executemany('''
INSERT INTO suppliers (supplier_ID, supplier_Name, Account, wechat_Contact, Website, products)
VALUES (?, ?, ?, ?, ?, ?)
''', suppliers_data)

# ============================================
# INSERT SAMPLE DATA - PRODUCT
# ============================================
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

cursor.executemany('''
INSERT INTO product (product_ID, product_Categories, products_ID, supplier_ID, supplier_Type, MOQ, lead_Times, unit_Cost, selling_Price)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', product_data)

# ============================================
# INSERT SAMPLE DATA - RETAILERS
# ============================================
retailers_data = [
    ('r001', 'Takealot', 'Active', '48 units', 'Egyptian Cotton Bed Sheet Set, Microfleece Blanket', 'Shipped', 'Sarah van der Merwe', 'Net 30'),
    ('r002', 'Makro', 'Active', '32 units', 'Thermal Blackout Curtains, Glazed Ceramic Flower Pot Set', 'Processing', 'James Nkosi', 'Net 30'),
    ('r003', 'Woolworths', 'Potential', '0 units', 'Organic Bamboo Pillowcase Set', 'Pending', 'Michelle Govender', 'To be confirmed'),
    ('r004', 'Game', 'Potential', '0 units', 'Airtight Food Storage Set', 'Negotiating', 'David Ngwenya', 'To be confirmed'),
    ('r005', 'Checkers', 'Potential', '0 units', 'Sheer Voile Curtains', 'Quotation Sent', 'Linda Petersen', 'To be confirmed')
]

cursor.executemany('''
INSERT INTO retailers (retailer_ID, retailer_Name, status, order_Quantity, product, order_Status, management_Contacts, payment_Terms)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', retailers_data)

# ============================================
# INSERT SAMPLE DATA - CUSTOMERS
# ============================================
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
INSERT INTO customers (customer_ID, customer_Name, contact_Number, email, total_orders, total_spent, outstanding_balance)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', customers_data)

# ============================================
# INSERT SAMPLE DATA - INVENTORY
# ============================================
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
INSERT INTO inventory (inventory_ID, product_ID, product_Name, stock_on_hand, reorder_level, reorder_quantity, location, last_updated)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', inventory_data)

# ============================================
# INSERT SAMPLE DATA - CHART OF ACCOUNTS
# ============================================
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

# ============================================
# INSERT SAMPLE DATA - ACCOUNTS RECEIVABLE
# ============================================
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
INSERT INTO accounts_receivable (receivable_ID, customer_ID, customer_Name, invoice_Date, due_Date, invoice_Amount, amount_Paid, outstanding_Balance, status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', accounts_receivable_data)

# ============================================
# INSERT SAMPLE DATA - ACCOUNTS PAYABLE
# ============================================
accounts_payable_data = [
    ('ap001', 's001', 'Huasheng Textiles', '2025-03-01', '2025-03-31', 24875.00, 24875.00, 0.00, 'Paid'),
    ('ap002', 's002', 'Jiangnan Ceramics', '2025-03-05', '2025-04-04', 8475.00, 0.00, 8475.00, 'Current'),
    ('ap003', 's003', 'Fareast Home Furnishings', '2025-03-10', '2025-04-09', 11900.00, 0.00, 11900.00, 'Current'),
    ('ap004', 's004', 'Xinguang Plastic Products', '2025-03-12', '2025-04-11', 5925.00, 5925.00, 0.00, 'Paid'),
    ('ap005', 's005', 'Ruixiang Textiles Import', '2025-03-15', '2025-04-14', 12750.00, 12750.00, 0.00, 'Paid')
]

cursor.executemany('''
INSERT INTO accounts_payable (payable_ID, supplier_ID, supplier_Name, invoice_Date, due_Date, invoice_Amount, amount_Paid, outstanding_Balance, status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', accounts_payable_data)

# ============================================
# INSERT SAMPLE DATA - DRAWINGS
# ============================================
drawings_data = [
    ('d001', '2025-03-05', 5250.00, 'Owner salary - March', 'Monthly salary'),
    ('d002', '2025-03-20', 2375.00, 'Personal expenses', 'Business expenses'),
    ('d003', '2025-03-28', 1200.00, 'Family emergency withdrawal', 'Temporary draw')
]

cursor.executemany('''
INSERT INTO drawings (drawing_ID, date, amount, description, notes)
VALUES (?, ?, ?, ?, ?)
''', drawings_data)

# ============================================
# INSERT SAMPLE DATA - TRANSACTIONS
# ============================================
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
INSERT INTO transactions (transaction_ID, date, description, account_Debit, account_Credit, amount, category)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', transactions_data)

# ============================================
# SAVE CHANGES AND CLOSE CONNECTION
# ============================================
connection.commit()
connection.close()

print("=" * 60)
print("Global Trends Database Created Successfully!")
print("=" * 60)
print("Database file: global_trends.db")
print("\nTables Created:")
print("  ✓ suppliers")
print("  ✓ product")
print("  ✓ retailers")
print("  ✓ customers")
print("  ✓ inventory")
print("  ✓ chart_of_accounts")
print("  ✓ accounts_receivable")
print("  ✓ accounts_payable")
print("  ✓ drawings")
print("  ✓ transactions")
print("\nRecords Inserted:")
print("  ✓ 5 suppliers")
print("  ✓ 10 products")
print("  ✓ 5 retailers (2 active, 3 potential)")
print("  ✓ 10 independent customers")
print("  ✓ 10 inventory records")
print("  ✓ 12 chart of accounts entries")
print("  ✓ 10 accounts receivable records")
print("  ✓ 5 accounts payable records")
print("  ✓ 3 drawings records")
print("  ✓ 30 transaction records")
print("=" * 60)
print("\nFinancial Summary:")
print(f"  Total Assets: R257,835.00")
print(f"  Total Liabilities: R70,375.00")
print(f"  Total Equity: R187,460.00")
print("=" * 60)