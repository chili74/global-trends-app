import streamlit as st
import sqlite3
import pandas as pd
import os

# Check if database exists
if not os.path.exists('global.db'):
    st.error("Database not found. Please ensure global.db exists.")
    st.stop()

# Simple page config
st.set_page_config(page_title="Global Trends", layout="wide")

# Title
st.title("🌍 Global Trends")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Suppliers"])

# Simple database function
def query_db(query):
    conn = sqlite3.connect("global.db")
    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# Dashboard Page
if page == "Dashboard":
    st.header("📊 Dashboard")
    
    try:
        # Try to load suppliers
        suppliers = query_db("SELECT * FROM suppliers LIMIT 5")
        if not suppliers.empty:
            st.subheader("Suppliers (Sample)")
            st.dataframe(suppliers)
        else:
            st.info("No suppliers found")
    except Exception as e:
        st.error(f"Error loading data: {e}")

# Suppliers Page
elif page == "Suppliers":
    st.header("🏭 Suppliers")
    
    try:
        suppliers = query_db("SELECT * FROM suppliers")
        if not suppliers.empty:
            st.dataframe(suppliers)
        else:
            st.info("No supplier data available")
    except Exception as e:
        st.error(f"Error: {e}")

st.success("✅ App is running!")
