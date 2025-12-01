import streamlit as st
import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import calendar
import os
from datetime import datetime
import json


# --- Google Sheets Configuration ---
GOOGLE_SHEET_ID = st.secrets["google"]["sheet_id"]
WORKSHEET_TITLE = "Sheet2"  # Change to "Sheet2" if needed

# --- UI Setup and Styling ---
st.set_page_config(
    page_title="Financial Tracker 🧾💲🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark, eye-catchy theme
st.markdown(
    """
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    .stTitle { color: #00ffff; font-weight: 700; text-align: center; }
    .stTextInput label, .stNumberInput label, .stSelectbox label, h1, h2, h3, h4, h5, h6 { color: #e6e6e6; }
    .streamlit-expanderHeader { background-color: #161b22; color: #00ffff; font-weight: bold; border-radius: 8px; margin-top: 10px; border: 1px solid #00ffff50; }
    .column-header { font-size: 1.1em; font-weight: 600; color: #00ffff; margin-bottom: 10px; padding-top: 10px; }
    .stButton>button { background-color: #00ffff; color: #0d1117; font-weight: bold; border-radius: 8px; transition: 0.2s; border: none; padding: 10px 20px; }
    .stButton>button:hover { background-color: #00caca; color: #0d1117; }
    div[data-testid="stMetricValue"] { color: #90ee90; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<h1 class="stTitle">Financial Tracker 🧾💲🛒</h1>', unsafe_allow_html=True)

# ----------------------------------------------------------------------
# --- Google Sheets Functions ---
# ----------------------------------------------------------------------

@st.cache_resource(ttl=3600)

def get_connection():
  """Authenticate and connect to Google Sheets."""
  try:
    creds_dict = {
        "type": st.secrets["google"]["type"],
        "project_id": st.secrets["google"]["project_id"],
        "private_key_id": st.secrets["google"]["private_key_id"],
        "private_key": st.secrets["google"]["private_key"],
        "client_email": st.secrets["google"]["client_email"],
        "client_id": st.secrets["google"]["client_id"],
        "auth_uri": st.secrets["google"]["auth_uri"],
        "token_uri": st.secrets["google"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["google"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["google"]["client_x509_cert_url"],
        "universe_domain": st.secrets["google"]["universe_domain"]
    }
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    sheet_id = st.secrets["google"]["sheet_id"]
    sheet = client.open_by_key(sheet_id).sheet2  # Access the first sheet
    return sheet
  except Exception as e:
    st.error(f"Connection error: {e}. Verify your Google service account and sheet permissions.")
    return None

def load_data_from_gsheet(worksheet, month, year):
    """Load data for a specific month/year."""
    try:
        records = worksheet.get_all_records()
        for record in records:
            if record.get("Month") == month and int(record.get("Year", 0)) == year:
                return record
        return {}
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return {}

def save_to_gsheet(worksheet, data_row):
    """Save data row to Google Sheet."""
    if not worksheet:
        return False
    try:
        # Find existing row or append
        records = worksheet.get_all_records()
        row_index = None
        for i, record in enumerate(records, start=2):  # Start from row 2 (after header)
            if record.get("Month") == data_row["Month"] and int(record.get("Year", 0)) == data_row["Year"]:
                row_index = i
                break
        if row_index:
            # Update existing row
            values = list(data_row.values())
            worksheet.update(f"A{row_index}:Z{row_index}", [values])
        else:
            # Append new row
            worksheet.append_row(list(data_row.values()))
        return True
    except Exception as e:
        st.error(f"Error saving to Google Sheet: {e}")
        return False

# ----------------------------------------------------------------------
# --- Main Application Logic ---
# ----------------------------------------------------------------------

worksheet = get_connection()
if worksheet is None:
    st.error("🚨 App stopped. Please resolve the Google Sheets connection error displayed above.")
    st.stop()

# --- State Initialization ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    now = datetime.datetime.now()
    
    st.session_state.input_month = calendar.month_name[now.month]
    st.session_state.input_year = now.year
    st.session_state.income = 0.0
    st.session_state.savings = 0.0
    
    fixed_expenses = {
        'House_Tax_A': 0.0, 'Water_Tax': 0.0, 'Drainage_Tax': 0.0, 'House_Tax_B': 0.0,
        'Electricity_House_A': 0.0, 'Electricity_House_B': 0.0, 'RD': 0.0, 'GAS': 0.0,
        'Telephone_Phone1': 0.0, 'Telephone_Phone2': 0.0, 'Telephone_Phone3': 0.0, 'Telephone_Landline': 0.0,
        'Rice': 0.0, 'Milk': 0.0, 'Other_Expenses': 0.0
    }
    for k, v in fixed_expenses.items():
        st.session_state[k] = v
            
    st.session_state.grocery_items = {}
    for i in range(1, 21):
        st.session_state.grocery_items[f"Grocery_Item_{i}"] = {"name": f"Item {i}", "amount": 0.0}

def update_session_state(data):
    """Updates session state with loaded data."""
    if not data:
        st.warning(f"No existing data found for {st.session_state.input_month} {st.session_state.input_year}. Resetting amounts.")
        
        st.session_state.income = 0.0
        st.session_state.savings = 0.0
        
        fixed_keys = ['House_Tax_A', 'Water_Tax', 'Drainage_Tax', 'House_Tax_B', 
                      'Electricity_House_A', 'Electricity_House_B', 'RD', 'GAS', 
                      'Telephone_Phone1', 'Telephone_Phone2', 'Telephone_Phone3', 'Telephone_Landline',
                      'Rice', 'Milk', 'Other_Expenses']
        for k in fixed_keys:
            st.session_state[k] = 0.0
        
        for key in st.session_state.grocery_items.keys():
            st.session_state.grocery_items[key]['amount'] = 0.0
            
        return
    
    st.session_state.income = float(data.get('Income', 0.0))
    st.session_state.savings = float(data.get('Savings', 0.0))
    
    for k in ['House_Tax_A', 'Water_Tax', 'Drainage_Tax', 'House_Tax_B', 
              'Electricity_House_A', 'Electricity_House_B', 'RD', 'GAS', 
              'Telephone_Phone1', 'Telephone_Phone2', 'Telephone_Phone3', 'Telephone_Landline',
              'Rice', 'Milk', 'Other_Expenses']:
        st.session_state[k] = float(data.get(k, 0.0))
        
    for key in st.session_state.grocery_items.keys():
        st.session_state.grocery_items[key]['amount'] = float(data.get(key, 0.0))

# --- Input / UI Layout ---
months = list(calendar.month_name)[1:]

col_m, col_y, col_load = st.columns([1, 1, 1])

with col_m:
    st.selectbox("Month:", options=months, key='input_month', index=months.index(st.session_state.input_month))

with col_y:
    st.number_input("Year:", min_value=2000, max_value=2100, step=1, key='input_year')

with col_load:
    load_button = st.button("LOAD EXISTING DATA", use_container_width=True)
    if load_button:
        with st.spinner(f"Loading data for {st.session_state.input_month} {st.session_state.input_year}..."):
            loaded_data = load_data_from_gsheet(worksheet, st.session_state.input_month, st.session_state.input_year)
            update_session_state(loaded_data)
            st.rerun()

# --- Income and Savings ---
st.header("Income & Savings")
col_inc, col_sav = st.columns(2)
with col_inc:
    st.number_input("Input Monthly Income (₹):", min_value=0.0, format="%.2f", key='income', value=st.session_state.income)
with col_sav:
    st.number_input("Input Monthly Savings (₹):", min_value=0.0, format="%.2f", key='savings', value=st.session_state.savings)

# --- EXPENSE INPUTS ---
st.header("Monthly Expenses")

with st.expander("🛒 Groceries (20 Custom Slots)", expanded=True):
    st.markdown("Enter Item Name and Amount for up to 20 grocery items.")
    
    item_keys = list(st.session_state.grocery_items.keys())
    
    for i, item_key in enumerate(item_keys):
        cols = st.columns([2, 1])
        with cols[0]:
            name = st.text_input(f"Item {i+1} Name:", value=st.session_state.grocery_items[item_key]['name'], key=f"{item_key}_name_input")
            st.session_state.grocery_items[item_key]['name'] = name
        with cols[1]:
            amount = st.number_input(f"Amount (₹) {i+1}:", min_value=0.0, format="%.2f", key=f"{item_key}_amount_input", value=st.session_state.grocery_items[item_key]['amount'], label_visibility="collapsed")
            st.session_state.grocery_items[item_key]['amount'] = amount

with st.expander("🧾 Other Expenses", expanded=False):
    st.markdown('### TAX', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<p class="column-header">A) Tax Components</p>', unsafe_allow_html=True)
        st.number_input("1) House Tax A (₹):", min_value=0.0, format="%.2f", key='House_Tax_A', value=st.session_state.House_Tax_A)
        st.number_input("2) Water Tax (₹):", min_value=0.0, format="%.2f", key='Water_Tax', value=st.session_state.Water_Tax)
        st.number_input("3) Drainage Tax (₹):", min_value=0.0, format="%.2f", key='Drainage_Tax', value=st.session_state.Drainage_Tax)
    with col_b:
        st.markdown('<p class="column-header">B) Separate Tax</p>', unsafe_allow_html=True)
        st.number_input("House Tax B (₹):", min_value=0.0, format="%.2f", key='House_Tax_B', value=st.session_state.House_Tax_B)

    st.markdown("---")
    
    st.markdown('### Utilities & Financials', unsafe_allow_html=True)
    col_e1, col_e2, col_rd, col_gas = st.columns(4)
    with col_e1:
        st.number_input("Electricity House A (₹):", min_value=0.0, format="%.2f", key='Electricity_House_A', value=st.session_state.Electricity_House_A)
    with col_e2:
        st.number_input("Electricity House B (₹):", min_value=0.0, format="%.2f", key='Electricity_House_B', value=st.session_state.Electricity_House_B)
    with col_rd:
        st.number_input("RD (₹):", min_value=0.0, format="%.2f", key='RD', value=st.session_state.RD)
    with col_gas:
        st.number_input("GAS (₹):", min_value=0.0, format="%.2f", key='GAS', value=st.session_state.GAS)
    
    st.markdown("---")
    
    st.markdown('### Telephone', unsafe_allow_html=True)
    col_t1, col_t2, col_t3, col_tl = st.columns(4)
    with col_t1:
        st.number_input("Phone 1 (944...7) (₹):", min_value=0.0, format="%.2f", key='Telephone_Phone1', value=st.session_state.Telephone_Phone1)
    with col_t2:
        st.number_input("Phone 2 (900...6) (₹):", min_value=0.0, format="%.2f", key='Telephone_Phone2', value=st.session_state.Telephone_Phone2)
    with col_t3:
        st.number_input("Phone 3 (900...5) (₹):", min_value=0.0, format="%.2f", key='Telephone_Phone3', value=st.session_state.Telephone_Phone3)
    with col_tl:
        st.number_input("Landline (₹):", min_value=0.0, format="%.2f", key='Telephone_Landline', value=st.session_state.Telephone_Landline)
        
    st.markdown("---")
    
    st.markdown('### Essential Food & Miscellaneous', unsafe_allow_html=True)
    col_rice, col_milk, col_other = st.columns(3)
    with col_rice:
        st.number_input("Rice (₹):", min_value=0.0, format="%.2f", key='Rice', value=st.session_state.Rice)
    with col_milk:
        st.number_input("Milk (₹):", min_value=0.0, format="%.2f", key='Milk', value=st.session_state.Milk)
    with col_other:
        st.number_input("Other Expenses (₹):", min_value=0.0, format="%.2f", key='Other_Expenses', value=st.session_state.Other_Expenses)

# --- Calculation and Save ---
fixed_expense_keys = ['House_Tax_A', 'Water_Tax', 'Drainage_Tax', 'House_Tax_B', 
                      'Electricity_House_A', 'Electricity_House_B', 'RD', 'GAS', 
                      'Telephone_Phone1', 'Telephone_Phone2', 'Telephone_Phone3', 'Telephone_Landline',
                      'Rice', 'Milk', 'Other_Expenses']

total_fixed_expenses = sum(st.session_state.get(k, 0.0) for k in fixed_expense_keys)
total_groceries = sum(item['amount'] for item in st.session_state.grocery_items.values())
total_expenses = total_fixed_expenses + total_groceries

st.header("Summary")
col_e, col_i, col_r = st.columns(3)

col_e.metric("Total Expenses (₹)", f"{total_expenses:,.2f}")
col_i.metric("Total Income (₹)", f"{st.session_state.income:,.2f}")

remaining = st.session_state.income - total_expenses - st.session_state.savings
col_r.metric("Remaining Balance (₹)", f"{remaining:,.2f}", delta=f"{remaining:,.2f}")

st.markdown("---")

if st.button("SAVE EXPENSES TO GOOGLE SHEET", use_container_width=True):
    if not worksheet:
        st.error("Cannot save: Google Sheets connection failed.")
    else:
        data_to_save = {
            "Month": st.session_state.input_month,
            "Year": st.session_state.input_year,
            "Income": st.session_state.income,
            "Savings": st.session_state.savings,
            "Total_Expenses": total_expenses,
        }
        
        for k in fixed_expense_keys:
            data_to_save[k] = st.session_state.get(k, 0.0)
            
        for k, v in st.session_state.grocery_items.items():
            data_to_save[k] = v['amount']

        success = save_to_gsheet(worksheet, data_to_save)
        if success:
            st.success("Data saved successfully!")
        else:
            st.error("Failed to save data.")

# --- VISUALIZATION ---
st.header("Expense Visualization")
chart_data = {
    "TAX": st.session_state.House_Tax_A + st.session_state.Water_Tax + st.session_state.Drainage_Tax + st.session_state.House_Tax_B,
    "Electricity": st.session_state.Electricity_House_A + st.session_state.Electricity_House_B,
    "Telephone": st.session_state.Telephone_Phone1 + st.session_state.Telephone_Phone2 + st.session_state.Telephone_Phone3 + st.session_state.Telephone_Landline,
    "Groceries": total_groceries,
    "RD": st.session_state.RD,
    "GAS": st.session_state.GAS,
    "Rice": st.session_state.Rice,
    "Milk": st.session_state.Milk,
    "Other_Expenses": st.session_state.Other_Expenses,
}

df_chart = pd.DataFrame(list(chart_data.items()), columns=['Category', 'Amount'])
df_chart = df_chart[df_chart['Amount'] > 0]

if not df_chart.empty:
    col_bar,


