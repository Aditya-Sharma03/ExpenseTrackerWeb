import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ---------------------------
# Categories
# ---------------------------
expense_categories = ['Food', 'Transport', 'Shopping', 'Bills', 'Entertainment', 'Other']
income_categories = ['Salary', 'Business', 'Investment', 'Gift', 'Other']

# ---------------------------
# Database Setup
# ---------------------------
conn = sqlite3.connect("transactions.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    type TEXT NOT NULL,         -- "Income" or "Expense"
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL
)
""")
conn.commit()

# ---------------------------
# Functions
# ---------------------------
def add_transaction(date, t_type, category, description, amount):
    cursor.execute(
        "INSERT INTO transactions (date, type, category, description, amount) VALUES (?, ?, ?, ?, ?)",
        (date, t_type, category, description, amount)
    )
    conn.commit()

def get_transactions(month=None, year=None):
    query = "SELECT date, type, category, description, amount FROM transactions WHERE 1=1"
    params = []

    if month:
        query += " AND strftime('%m', date) = ?"
        params.append(f"{int(month):02d}")
    if year:
        query += " AND strftime('%Y', date) = ?"
        params.append(str(year))

    cursor.execute(query, params)
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=['Date', 'Type', 'Category', 'Description', 'Amount'])
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
    return df

# ---------------------------
# Streamlit UI
# ---------------------------
st.title("💰 Expense & Income Tracker Web App")

# --- Add Transaction Section ---
st.subheader("Add New Transaction")
col1, col2 = st.columns(2)
with col1:
    date = st.date_input("Date", datetime.now())
with col2:
    t_type = st.selectbox("Type", ["Income", "Expense"])

# Dropdown category based on type
if t_type == "Income":
    category = st.selectbox("Category", income_categories)
else:
    category = st.selectbox("Category", expense_categories)

description = st.text_input("Description")
amount = st.number_input("Amount", min_value=0.0, step=0.01)

if st.button("Add Transaction"):
    if category and description and amount > 0:
        add_transaction(date.strftime("%Y-%m-%d"), t_type, category, description, amount)
        st.success(f"{t_type} added successfully!")
    else:
        st.error("Please provide valid data.")

# --- View & Filter Transactions ---
st.subheader("View Transactions")
col1, col2 = st.columns(2)
months = ["All"] + [str(i) for i in range(1,13)]
years = ["All"] + [str(y) for y in range(datetime.now().year-10, datetime.now().year+1)]
with col1:
    month_filter = st.selectbox("Filter by Month", months)
with col2:
    year_filter = st.selectbox("Filter by Year", years)

month_val = None if month_filter == "All" else month_filter
year_val = None if year_filter == "All" else year_filter

df = get_transactions(month_val, year_val)

if df.empty:
    st.info("No transactions found for the selected period.")
else:
    st.dataframe(df)

    # Totals
    total_income = df[df['Type']=="Income"]['Amount'].sum()
    total_expense = df[df['Type']=="Expense"]['Amount'].sum()
    net_balance = total_income - total_expense

    st.metric("Total Income", f"${total_income:,.2f}")
    st.metric("Total Expenses", f"${total_expense:,.2f}")
    st.metric("Net Balance", f"${net_balance:,.2f}")

    # Pie chart for expenses only
    expenses_df = df[df['Type']=="Expense"]
    if not expenses_df.empty:
        exp_summary = expenses_df.groupby('Category')['Amount'].sum()
        st.subheader("Expenses by Category")
        st.bar_chart(exp_summary)

        fig1, ax1 = plt.subplots()
        ax1.pie(exp_summary, labels=exp_summary.index, autopct='%1.1f%%')
        st.pyplot(fig1)

    # Monthly trend (income vs expenses)
    df['Month'] = df['Date'].dt.to_period('M')
    monthly_summary = df.groupby(['Month', 'Type'])['Amount'].sum().unstack(fill_value=0)
    st.subheader("Monthly Income vs Expenses")
    st.bar_chart(monthly_summary)

    # Highlight Overspending (expenses > 1000)
    overspend = exp_summary[exp_summary > 1000] if not expenses_df.empty else pd.Series()
    if not overspend.empty:
        st.warning(f"⚠ Overspending detected:\n{overspend.to_dict()}")
