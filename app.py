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

from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun

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
# DATABASE FUNCTIONS
# -----------------------
def query_database(query: str):
    """Execute SQL query on global_trends database"""
    connection = sqlite3.connect("global.db")
    cursor = connection.cursor()

    try:
        cursor.execute(query)
        results = cursor.fetchall()
        column_names = [description[0] for description in cursor.description] if cursor.description else []

        if results:
            if column_names:
                return f"Columns: {', '.join(column_names)}\nData: {str(results)}"
            return str(results)
        return "No results found."
    except Exception as e:
        return f"Database Error: {str(e)}"
    finally:
        connection.close()


def get_suppliers():
    """Get all suppliers"""
    connection = sqlite3.connect("global.db")
    try:
        return pd.read_sql_query("SELECT * FROM suppliers", connection)
    finally:
        connection.close()


def get_products():
    """Get all products"""
    connection = sqlite3.connect("global.db")
    try:
        return pd.read_sql_query("""
                                 SELECT p.*, s.supplier_Name, p.unit_Cost, p.selling_Price
                                 FROM product p
                                          LEFT JOIN suppliers s ON p.supplier_ID = s.supplier_ID
                                 """, connection)
    finally:
        connection.close()


def get_retailers():
    """Get all retailers"""
    connection = sqlite3.connect("global.db")
    try:
        return pd.read_sql_query("SELECT * FROM retailers", connection)
    finally:
        connection.close()


def get_customers():
    """Get all independent customers"""
    connection = sqlite3.connect("global.db")
    try:
        return pd.read_sql_query("SELECT * FROM customers", connection)
    finally:
        connection.close()


def get_inventory():
    """Get inventory levels"""
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
        return pd.read_sql_query(query, connection)
    finally:
        connection.close()


def get_financial_summary():
    """Get financial summary"""
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
    finally:
        connection.close()


def get_performance():
    """Get supplier performance - Fixed for missing table"""
    connection = sqlite3.connect("global.db")
    try:
        # Check if performance_notes table exists
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance_notes'")
        table_exists = cursor.fetchone()

        if table_exists:
            return pd.read_sql_query("""
                                     SELECT s.supplier_Name, p.supplier_Rating, p.Priority, p.Notes
                                     FROM performance_notes p
                                              JOIN suppliers s ON p.supplier_ID = s.supplier_ID
                                     ORDER BY p.supplier_Rating DESC
                                     """, connection)
        else:
            # Create a default performance dataframe if table doesn't exist
            st.warning("Performance notes table not found. Creating default data...")
            suppliers_df = pd.read_sql_query("SELECT supplier_ID, supplier_Name FROM suppliers", connection)

            # Create default performance data
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
        st.error(f"Error in get_performance: {e}")
        return pd.DataFrame()
    finally:
        connection.close()


def check_low_stock():
    """Check all products for low stock levels - Fixed for missing column"""
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
        return df
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
        return df
    finally:
        connection.close()


# -----------------------
# INVENTORY UPDATE FUNCTIONS
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
        return True
    except Exception as e:
        print(f"Error saving invoice: {e}")
        return False
    finally:
        connection.close()


def send_invoice_email(invoice_pdf, invoice_data, recipient_email):
    """Send invoice via email"""
    if not EMAIL_CONFIG['sender_email'] or not EMAIL_CONFIG['sender_password']:
        return False, "Email credentials not configured. Please set SENDER_EMAIL and SENDER_PASSWORD in environment variables."

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

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
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
            conn = sqlite3.connect("global.db")
            customers_df = pd.read_sql_query("SELECT customer_ID, customer_Name, email FROM customers", conn)
            conn.close()

            if not customers_df.empty:
                customer_options = {f"{row['customer_Name']} ({row['customer_ID']})": row['customer_ID']
                                    for _, row in customers_df.iterrows()}
                selected_customer = st.selectbox("Select Customer", list(customer_options.keys()))
                customer_id = customer_options[selected_customer]
                customer_name = selected_customer.split(" (")[0]

                # Get customer email
                customer_email = customers_df[customers_df['customer_ID'] == customer_id]['email'].iloc[0]
                recipient_email = st.text_input("Email for Invoice", value=customer_email if customer_email else "")
            else:
                st.warning("No customers found. Please add customers first.")
                customer_id = st.text_input("Customer ID", "c011")
                customer_name = st.text_input("Customer Name")
                recipient_email = st.text_input("Email for Invoice")
        else:
            # Get retailers from database
            conn = sqlite3.connect("global.db")
            retailers_df = pd.read_sql_query(
                "SELECT retailer_ID, retailer_Name, management_Contacts FROM retailers WHERE status = 'Active'", conn)
            conn.close()

            if not retailers_df.empty:
                retailer_options = {f"{row['retailer_Name']} ({row['retailer_ID']})": row['retailer_ID']
                                    for _, row in retailers_df.iterrows()}
                selected_retailer = st.selectbox("Select Retailer", list(retailer_options.keys()))
                customer_id = retailer_options[selected_retailer]
                customer_name = selected_retailer.split(" (")[0]

                # Get retailer contact
                retailer_contact = retailers_df[retailers_df['retailer_ID'] == customer_id]['management_Contacts'].iloc[
                    0]
                recipient_email = st.text_input("Email for Invoice",
                                                value=retailer_contact if "@" in str(retailer_contact) else "")
            else:
                st.warning("No active retailers found.")
                customer_id = st.text_input("Customer ID", "r006")
                customer_name = st.text_input("Customer Name")
                recipient_email = st.text_input("Email for Invoice")

    # Order Items
    st.subheader("Order Items")

    # Get products for dropdown
    conn = sqlite3.connect("global.db")
    products_df = pd.read_sql_query("""
                                    SELECT p.product_ID, p.products_ID, p.selling_Price, i.stock_on_hand
                                    FROM product p
                                             LEFT JOIN inventory i ON p.product_ID = i.product_ID
                                    """, conn)
    conn.close()

    if 'sale_items' not in st.session_state:
        st.session_state.sale_items = []

    # Add item form
    with st.form("add_item"):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            product_options = {f"{row['products_ID']} ({row['product_ID']})": row['product_ID']
                               for _, row in products_df.iterrows()}
            selected_product = st.selectbox("Product", list(product_options.keys()))
            product_id = product_options[selected_product]

        # Get product details
        product_row = products_df[products_df['product_ID'] == product_id].iloc[0]
        product_name = product_row['products_ID']
        unit_price = product_row['selling_Price']
        stock_available = product_row['stock_on_hand'] if product_row['stock_on_hand'] else 0

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
                response = agent.run(user_input)
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
                conn = sqlite3.connect("global.db")
                active = pd.read_sql_query("SELECT COUNT(*) as count FROM suppliers", conn)
                st.metric("Total Suppliers", active['count'].iloc[0])
                conn.close()

            with col2:
                conn = sqlite3.connect("global.db")
                products = pd.read_sql_query("SELECT COUNT(*) as count FROM product", conn)
                st.metric("Total Products", products['count'].iloc[0])
                conn.close()

            with col3:
                # Check if performance_notes table exists
                conn = sqlite3.connect("global.db")
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance_notes'")
                table_exists = cursor.fetchone()

                if table_exists:
                    top_rated = pd.read_sql_query(
                        "SELECT COUNT(*) as count FROM performance_notes WHERE supplier_Rating >= 4", conn)
                    st.metric("Top Rated Suppliers (4+⭐)", top_rated['count'].iloc[0])
                else:
                    st.metric("Top Rated Suppliers (4+⭐)", "N/A")
                conn.close()

        else:
            st.info("No supplier data available.")

    except Exception as e:
        st.error(f"Error loading supplier dashboard: {str(e)}")

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
                category_counts = df_products['product_Categories'].value_counts()
                if not category_counts.empty:
                    st.bar_chart(category_counts)

            st.subheader("💰 Profit Margin by Product")
            if 'unit_Cost' in df_products.columns and 'selling_Price' in df_products.columns:
                # Convert to numeric safely
                df_products['unit_Cost_num'] = pd.to_numeric(df_products['unit_Cost'], errors='coerce')
                df_products['selling_Price_num'] = pd.to_numeric(df_products['selling_Price'], errors='coerce')

                # Calculate profit margin only where we have valid data
                valid_mask = (df_products['selling_Price_num'] > 0) & (df_products['unit_Cost_num'].notna())
                df_products['profit_margin'] = 0
                df_products.loc[valid_mask, 'profit_margin'] = (
                        (df_products.loc[valid_mask, 'selling_Price_num'] - df_products.loc[
                            valid_mask, 'unit_Cost_num']) /
                        df_products.loc[valid_mask, 'selling_Price_num'] * 100
                ).round(2)

                margin_df = df_products[['products_ID', 'profit_margin']].set_index('products_ID')
                if not margin_df.empty and len(margin_df) > 0:
                    st.bar_chart(margin_df)

            st.subheader("⏱️ Lead Times by Product")
            if 'lead_Times' in df_products.columns and 'products_ID' in df_products.columns:
                lead_times_df = df_products[['products_ID', 'lead_Times']].drop_duplicates()
                if not lead_times_df.empty:
                    st.dataframe(lead_times_df)

        else:
            st.info("No product data available.")

    except Exception as e:
        st.error(f"Error loading product dashboard: {str(e)}")

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
            st.info("No retailer data available.")

    except Exception as e:
        st.error(f"Error loading retailer dashboard: {str(e)}")

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
                st.metric("Total Sales to Customers", f"R{total_spent:,.2f}")

            with col3:
                outstanding = df_customers['outstanding_balance_num'].sum()
                st.metric("Outstanding Balances", f"R{outstanding:,.2f}")

            st.subheader("⚠️ Customers with Outstanding Balances")
            outstanding_customers = df_customers[df_customers['outstanding_balance_num'] > 0]
            if not outstanding_customers.empty:
                st.dataframe(outstanding_customers[['customer_Name', 'outstanding_balance']])
            else:
                st.success("All customers have paid their balances!")

            st.subheader("🏆 Top Customers by Spending")
            top_customers = df_customers.nlargest(5, 'total_spent_num')[['customer_Name', 'total_spent']]
            st.dataframe(top_customers)

        else:
            st.info("No customer data available.")

    except Exception as e:
        st.error(f"Error loading customer dashboard: {str(e)}")

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
                    supplier_info = f" from {row['supplier_Name']}" if 'supplier_Name' in row else ""
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
                stock_df = df_inventory.set_index('product_Name')['stock_on_hand']
                if not stock_df.empty:
                    st.bar_chart(stock_df)

            # Inventory value
            st.subheader("💰 Inventory Value")
            if 'unit_Cost' in df_inventory.columns and 'stock_on_hand' in df_inventory.columns:
                df_inventory['unit_Cost_num'] = pd.to_numeric(df_inventory['unit_Cost'], errors='coerce')
                total_value = (df_inventory['stock_on_hand'] * df_inventory['unit_Cost_num']).sum()
                st.metric("Total Inventory Value", f"R{total_value:,.2f}")

        else:
            st.info("No inventory data available.")

    except Exception as e:
        st.error(f"Error loading inventory dashboard: {str(e)}")

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
            st.metric("Total Sales (March)", f"R{finances['total_sales']:,.2f}")

        with col2:
            st.metric("Accounts Receivable", f"R{finances['total_ar']:,.2f}")

        with col3:
            st.metric("Accounts Payable", f"R{finances['total_ap']:,.2f}")

        with col4:
            st.metric("Owner Drawings (March)", f"R{finances['total_drawings']:,.2f}")

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
            ar_details['invoice_Amount'] = ar_details['invoice_Amount'].apply(lambda x: f"R{x:,.2f}")
            ar_details['outstanding_Balance'] = ar_details['outstanding_Balance'].apply(lambda x: f"R{x:,.2f}")
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
            ap_details['invoice_Amount'] = ap_details['invoice_Amount'].apply(lambda x: f"R{x:,.2f}")
            ap_details['outstanding_Balance'] = ap_details['outstanding_Balance'].apply(lambda x: f"R{x:,.2f}")
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
            transactions['amount'] = transactions['amount'].apply(lambda x: f"R{x:,.2f}")
            st.dataframe(transactions)
        conn.close()

    except Exception as e:
        st.error(f"Error loading financial dashboard: {str(e)}")

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
                    rating_counts = df_performance['supplier_Rating'].value_counts().sort_index()
                    if not rating_counts.empty:
                        st.subheader("Rating Distribution")
                        st.bar_chart(rating_counts)

            if 'Priority' in df_performance.columns:
                st.subheader("🎯 Supplier Priority")
                priority_counts = df_performance['Priority'].value_counts()
                if not priority_counts.empty:
                    st.bar_chart(priority_counts)

            if 'supplier_Rating' in df_performance.columns and 'Notes' in df_performance.columns:
                st.subheader("📝 Notes from Top Suppliers")
                top_suppliers = df_performance[df_performance['supplier_Rating'] >= 4]
                if not top_suppliers.empty:
                    for _, row in top_suppliers.iterrows():
                        st.info(
                            f"**{row['supplier_Name']}** (Rating: {row['supplier_Rating']}⭐ - {row['Priority']})\n\n{row['Notes']}")

        else:
            st.info("No performance data available.")

    except Exception as e:
        st.error(f"Error loading performance dashboard: {str(e)}")

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
                    else:
                        st.warning("Performance notes table not found. Skipping performance entry.")

                    conn.commit()
                    conn.close()

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

                    st.success(f"✅ Customer {customer_name} added successfully!")

                except Exception as e:
                    st.error(f"❌ Error adding customer: {str(e)}")