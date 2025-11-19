import streamlit as st
import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import calendar
import io

# --- Google Sheets Configuration ---
# NOTE: This ID MUST match the ID in your st.secrets structure.
GOOGLE_SHEET_ID = "1gaFzfZOCKhrEklluRiyzdlJ7im5_BSnBrVjE3PHWQlI"
WORKSHEET_TITLE = "Sheet2"

# --- UI Setup and Styling (Omitted for brevity) ---
st.set_page_config(
    page_title="Financial Tracker 🧾💲🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Custom CSS for dark, eye-catchy theme and to remove borders/grid lines
# ... (CSS omitted) ...
st.markdown(
    """
    <style>
    /* ... (CSS styles) ... */
    </style>
    """,
    unsafe_allow_html=True
)

# Set the main title
st.markdown('<h1 class="stTitle">Financial Tracker 🧾💲🛒</h1>', unsafe_allow_html=True)


# ----------------------------------------------------------------------
# --- Google Sheets Functions (INTEGRATED & RECTIFIED) ---
# ----------------------------------------------------------------------

@st.cache_resource(ttl=3600)
def get_connection():
    """
    Authenticates, opens the spreadsheet, and returns the specific gspread 
    Worksheet object (Sheet2), mirroring the structure of app.py.
    """
    try:
        # Load credentials from st.secrets under the 'google' key
        creds_dict = st.secrets["google"]["credentials"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        client = gspread.authorize(creds)
        sheet_id = st.secrets["google"]["sheet_id"]
        
        # Access the SECOND sheet (index 1) directly, as Sheet2 is implied for data
        worksheet = client.open_by_key(sheet_id).get_worksheet(1)
        return worksheet
        
    except Exception as e:
        st.error(f"Authentication Error: Could not connect to Google Sheets. Check st.secrets. Details: {e}")
        return None

def load_data_from_gsheet(worksheet, month_name, year):
    """Loads a single month's record from the Google Sheet using the passed worksheet object."""
    # Check the passed worksheet object, not a global 'client'
    if not worksheet:
        return {}
    
    try:
        # Use the worksheet object directly
        records = worksheet.get_all_records()
        # Search for the specific month and year
        for record in records:
            # Ensure consistent type comparison for Year
            sheet_year = str(record.get("Year")) 
            
            if record.get("Month") == month_name and sheet_year == str(year):
                # Return the matching record as a dictionary
                return record
        
        # If no record found
        return {}

    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {e}")
        return {}

def save_to_gsheet(worksheet, data_row):
    """Saves/appends a row of data to the Google Sheet using the passed worksheet object."""
    if not worksheet:
        return False
    
    try:
        # Use the passed-in worksheet object directly, removing unnecessary open_by_key calls
        df_existing = pd.DataFrame(worksheet.get_all_records())
        
        # Convert the input data_row (dict) into a DataFrame for easier handling
        df_new = pd.DataFrame([data_row])
        
        # Determine the final list of columns (headers) that should be in the sheet
        if df_existing.empty:
            final_columns = df_new.columns.tolist()
            # If sheet is empty, write headers first
            worksheet.append_row(final_columns, value_input_option='USER_ENTERED')
            st.success("Sheet headers initialized.")
        else:
            # Combine columns from existing data and new data to ensure all columns are present
            existing_cols = df_existing.columns.tolist()
            new_cols = df_new.columns.tolist()
            # New columns are added at the end (useful for new grocery items)
            final_columns = existing_cols
            for col in new_cols:
                if col not in final_columns:
                    final_columns.append(col)

        # Re-index the new data row to match the final column order, filling missing with 0.0
        df_to_save = df_new.reindex(columns=final_columns, fill_value=0.0)
        
        # Convert the DataFrame row to a list of values for gspread
        values = df_to_save.iloc[0].tolist()

        # Check for existing entry for the same Month/Year
        # Ensure consistent type comparison
        month_year_check = (df_existing['Month'] == data_row['Month']) & (df_existing['Year'].astype(str) == str(data_row['Year']))
        
        if month_year_check.any():
            # Update existing row
            # +2: +1 for 1-based indexing of gspread, +1 for the header row
            row_index = df_existing[month_year_check].index[0] + 2 
            worksheet.update(f'A{row_index}', [values])
            st.success(f"Data for {data_row['Month']} {data_row['Year']} successfully UPDATED in Google Sheet (Row {row_index}).")
        else:
            # Append new row
            worksheet.append_row(values, value_input_option='USER_ENTERED')
            st.success("Data successfully SAVED/APPENDED to Google Sheet.")
        
        return True

    except Exception as e:
        st.error(f"Error saving to Google Sheet: {e}")
        st.error("Please ensure the Sheet ID is correct and the Service Account has 'Editor' access to the spreadsheet.")
        return False

# ----------------------------------------------------------------------
# --- Main Application Logic ---
# ----------------------------------------------------------------------

# --- State Initialization (Omitted for brevity) ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    now = datetime.datetime.now()
    
    st.session_state.input_month = calendar.month_name[now.month]
    st.session_state.input_year = now.year
    st.session_state.income = 0.0
    st.session_state.savings = 0.0
    
    # Fixed expense initialization
    fixed_expenses = {
        'House_Tax_A': 0.0, 'Water_Tax': 0.0, 'Drainage_Tax': 0.0, 'House_Tax_B': 0.0,
        'Electricity_House_A': 0.0, 'Electricity_House_B': 0.0, 'RD': 0.0, 'GAS': 0.0,
        'Telephone_Phone1': 0.0, 'Telephone_Phone2': 0.0, 'Telephone_Phone3': 0.0, 'Telephone_Landline': 0.0,
        'Rice': 0.0, 'Milk': 0.0, 'Other_Expenses': 0.0
    }
    for k, v in fixed_expenses.items():
        if k not in st.session_state:
            st.session_state[k] = v
            
    # Groceries initialization (20 slots with default names)
    st.session_state.grocery_items = {}
    for i in range(1, 21):
        # Format: Item Name, Amount
        st.session_state.grocery_items[f"Grocery_Item_{i}"] = {"name": f"Item {i}", "amount": 0.0}

# --- Data Loading Logic (Omitted for brevity) ---
def update_session_state(data):
    """Updates session state with loaded data."""
    # ... (function body omitted) ...
    if not data:
        st.warning(f"No existing data found for {st.session_state.input_month} {st.session_state.input_year}. Resetting amounts.")
        for key in st.session_state.keys():
            if isinstance(st.session_state.get(key), (float, int)) and key not in ['input_year']:
                st.session_state[key] = 0.0
            if key in st.session_state.grocery_items:
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

# Call get_connection() once and store the WORKSHEET object
worksheet = get_connection()
months = list(calendar.month_name)[1:]

# Top Row for Month/Year/Load
col_m, col_y, col_load = st.columns([1, 1, 1])

with col_m:
    st.selectbox("Month:", options=months, key='input_month', index=months.index(st.session_state.input_month))

with col_y:
    st.number_input("Year:", min_value=2000, max_value=2100, step=1, key='input_year')

with col_load:
    st.write("---") # Spacer
    load_button = st.button("LOAD EXISTING DATA", use_container_width=True)
    # Use 'worksheet' instead of 'client'
    if load_button and worksheet:
        with st.spinner(f"Loading data for {st.session_state.input_month} {st.session_state.input_year}..."):
            # Pass the worksheet object
            loaded_data = load_data_from_gsheet(worksheet, st.session_state.input_month, st.session_state.input_year)
            update_session_state(loaded_data)
            st.experimental_rerun() # Rerun to refresh all inputs

# ... (Income, Savings, Expenses, Metrics UI blocks omitted for brevity) ...

# --- Income and Savings ---
st.header("Income & Savings")
col_inc, col_sav = st.columns(2)
with col_inc:
    st.number_input("Input Monthly Income (₹):", min_value=0.0, format="%.2f", key='income', value=st.session_state.income)
with col_sav:
    st.number_input("Input Monthly Savings (₹):", min_value=0.0, format="%.2f", key='savings', value=st.session_state.savings)

# --- EXPENSE INPUTS ---
st.header("Monthly Expenses")
# ... (Groceries and Other Expenses UI blocks omitted) ...

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
    # Use 'worksheet' instead of 'client'
    if not worksheet:
        st.error("Cannot save: Google Sheets client is not connected. Check st.secrets configuration.")
    else:
        # Build the data dictionary for saving
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

        # Pass the worksheet object
        save_to_gsheet(worksheet, data_to_save)


# --- VISUALIZATION (Omitted for brevity) ---
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
    col_bar, col_pie = st.columns(2)
    # ... (Plotly charts code omitted) ...
    with col_bar:
        st.subheader("Expense Breakdown (Bar)")
        fig_bar = px.bar(
            df_chart, 
            x='Category', 
            y='Amount', 
            title='Major Expense Categories',
            template='plotly_dark'
        )
        fig_bar.update_traces(marker_color='#00ffff')
        fig_bar.update_xaxes(showgrid=False)
        fig_bar.update_yaxes(showgrid=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_pie:
        st.subheader("Expense Distribution (Donut)")
        fig_pie = px.pie(
            df_chart, 
            values='Amount', 
            names='Category', 
            hole=0.4, 
            title='Expense Percentage',
            template='plotly_dark'
        )
        fig_pie.update_xaxes(showgrid=False)
        fig_pie.update_yaxes(showgrid=False)
        st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("Enter some expenses to view the charts!")
