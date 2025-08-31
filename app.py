import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import date

# ----------------------------
# Database setup
# ----------------------------
conn = sqlite3.connect("transactions.db", check_same_thread=False)
cursor = conn.cursor()

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# Transactions table
cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL
)
""")
conn.commit()

# Upgrade DB: add user_id if missing
cursor.execute("PRAGMA table_info(transactions)")
columns = [col[1] for col in cursor.fetchall()]
if "user_id" not in columns:
    cursor.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER DEFAULT 0")
    conn.commit()
    st.info("Database upgraded: 'user_id' column added to transactions table.")

# ----------------------------
# Password hashing
# ----------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ----------------------------
# User functions
# ----------------------------
def register_user(username, password):
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                   (username, hash_password(password)))
    return cursor.fetchone()

# ----------------------------
# Transaction functions
# ----------------------------
def add_transaction(user_id, date_val, t_type, category, description, amount):
    cursor.execute("""
    INSERT INTO transactions (user_id, date, type, category, description, amount)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, str(date_val), t_type, category, description, amount))
    conn.commit()

def get_transactions(user_id, month=None, year=None):
    query = "SELECT date, type, category, description, amount FROM transactions WHERE user_id=?"
    params = [user_id]
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

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("💰 Expense Tracker Web App")

# Session state
if "user" not in st.session_state:
    st.session_state["user"] = None
if "refresh" not in st.session_state:
    st.session_state["refresh"] = False

# ----------------------------
# Login / Sign Up
# ----------------------------
if st.session_state["user"] is None:
    st.subheader("Login / Sign Up")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            user = login_user(username, password)
            if user:
                st.session_state["user"] = username
                st.session_state["refresh"] = not st.session_state["refresh"]
            else:
                st.error("Invalid username or password")

    with tab2:
        new_username = st.text_input("Username", key="signup_username")
        new_password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Register"):
            if register_user(new_username, new_password):
                st.success("Account created! You can now log in.")
            else:
                st.error("Username already exists")

else:
    st.subheader(f"Welcome, {st.session_state['user']}!")

    # Get user_id
    cursor.execute("SELECT id FROM users WHERE username=?", (st.session_state["user"],))
    user_id = cursor.fetchone()[0]

    # Assign old transactions with user_id=0 to this user
    cursor.execute("UPDATE transactions SET user_id=? WHERE user_id=0", (user_id,))
    conn.commit()

    # ----------------------------
    # Add Transaction
    # ----------------------------
    st.markdown("### ➕ Add Transaction")
    col1, col2 = st.columns(2)
    with col1:
        t_type = st.selectbox("Type", ["Income", "Expense"])
        category = st.selectbox("Category", ["Salary", "Food", "Entertainment", "Bills", "Others"])
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    with col2:
        description = st.text_input("Description")
        date_val = st.date_input("Date", date.today())

    if st.button("Add Transaction"):
        add_transaction(user_id, date_val, t_type, category, description, amount)
        st.success("Transaction added!")

    # ----------------------------
    # Transactions Table & Filters
    # ----------------------------
    st.markdown("### 📊 Transactions")
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        filter_month = st.selectbox(
            "Month", ["All"] + list(range(1, 13))
        )
        filter_month_value = None if filter_month == "All" else int(filter_month)

    with filter_col2:
        filter_year = st.selectbox(
            "Year", ["All"] + list(range(2022, date.today().year + 1))
        )
        filter_year_value = None if filter_year == "All" else int(filter_year)

    df = get_transactions(user_id, filter_month_value, filter_year_value)
    if not df.empty:
        st.dataframe(df)
        total_income = df[df['Type'] == 'Income']['Amount'].sum()
        total_expense = df[df['Type'] == 'Expense']['Amount'].sum()
        st.metric("Total Income", f"${total_income:.2f}")
        st.metric("Total Expenses", f"${total_expense:.2f}")
    else:
        st.info("No transactions found.")

    if st.button("Logout"):
        st.session_state["user"] = None
        st.session_state["refresh"] = not st.session_state["refresh"]
