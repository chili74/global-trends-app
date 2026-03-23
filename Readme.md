# 🌍 Global Trends Business Management System

A comprehensive business management system built with Streamlit that helps small to medium-sized businesses manage suppliers, products, inventory, customers, sales, and finances with AI-powered assistance.

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Structure](#database-structure)
- [Usage Guide](#usage-guide)
- [AI Assistant](#ai-assistant)
- [Email Configuration](#email-configuration)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)
- [License](#license)

## 🎯 Overview

Global Trends Business Management System is an all-in-one solution for managing:
- **Supply Chain**: Suppliers, products, and inventory management
- **Sales**: Customer management, sales processing, and invoice generation
- **Finance**: Accounts receivable/payable, transaction tracking, and financial reporting
- **Retail**: Retailer relationship management and order tracking
- **AI Assistance**: Natural language queries and intelligent recommendations

## ✨ Features

### 1. 🤖 AI-Powered Chat Assistant
- Natural language queries about your business data
- Intelligent recommendations and insights
- DuckDuckGo integration for market research

### 2. 🛒 Sales Processing
- Automated inventory updates
- PDF invoice generation
- Email invoice delivery
- Support for both individual customers and retailers

### 3. 📊 Interactive Dashboards
- **Supplier Dashboard**: Track supplier performance and ratings
- **Product Dashboard**: Monitor profit margins and lead times
- **Inventory Dashboard**: Real-time stock levels and reorder alerts
- **Financial Dashboard**: Track sales, AR/AP, and transactions
- **Customer Dashboard**: Manage customer relationships and outstanding balances
- **Performance Dashboard**: Supplier ratings and notes

### 4. 📦 Inventory Management
- Real-time stock level tracking
- Automatic reorder alerts
- Low stock notifications
- Inventory value calculations

### 5. 💰 Financial Management
- Complete chart of accounts
- Accounts receivable/payable tracking
- Transaction history
- Owner drawings tracking

### 6. 📧 Automated Invoicing
- Professional PDF invoice generation
- Email delivery to customers
- Automatic database recording

## 🛠 Technology Stack

- **Frontend**: Streamlit
- **Database**: SQLite3
- **AI/ML**: LangChain, Groq (Llama 3.3 70B)
- **PDF Generation**: ReportLab
- **Email**: SMTP (Gmail support)
- **Search**: DuckDuckGo Search API
- **Data Processing**: Pandas

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/global-trends-management.git
cd global-trends-management