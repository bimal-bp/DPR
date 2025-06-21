import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

# Initialize database
def init_db():
    conn = sqlite3.connect('material_stocks.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL UNIQUE)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS daily_stocks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date DATE NOT NULL,
                  product_id INTEGER NOT NULL,
                  opening REAL NOT NULL,
                  production REAL DEFAULT 0,
                  dispatch REAL DEFAULT 0,
                  FOREIGN KEY (product_id) REFERENCES products (id),
                  UNIQUE(date, product_id))''')
    
    initial_products = [
        "Product -1 MS-AMS",
        "Product -2 MS ©",
        "Product -3 MS-10µ",
        "Product -4 MS-K",
        "Product -5 MF-©"
    ]
    
    for product in initial_products:
        try:
            c.execute("INSERT INTO products (name) VALUES (?)", (product,))
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()

# Get or create today's stock entries
def get_or_create_daily_stocks(selected_date):
    conn = sqlite3.connect('material_stocks.db')
    c = conn.cursor()
    
    # Get all products
    c.execute("SELECT id, name FROM products")
    products = c.fetchall()
    
    daily_data = []
    
    for product_id, product_name in products:
        # Check if entry exists for selected date
        c.execute('''SELECT opening, production, dispatch 
                     FROM daily_stocks 
                     WHERE date = ? AND product_id = ?''', 
                     (selected_date, product_id))
        entry = c.fetchone()
        
        if entry:
            # Entry exists, use it
            opening, production, dispatch = entry
        else:
            # Entry doesn't exist, create it with yesterday's closing as opening
            prev_date = selected_date - timedelta(days=1)
            c.execute('''SELECT (opening + production - dispatch) as closing
                         FROM daily_stocks 
                         WHERE date = ? AND product_id = ?''', 
                         (prev_date, product_id))
            prev_closing = c.fetchone()
            
            opening = prev_closing[0] if prev_closing and prev_closing[0] is not None else 0
            production = 0
            dispatch = 0
            
            # Insert new entry
            c.execute('''INSERT INTO daily_stocks 
                          (date, product_id, opening, production, dispatch)
                          VALUES (?, ?, ?, ?, ?)''',
                          (selected_date, product_id, opening, production, dispatch))
            conn.commit()
        
        daily_data.append({
            "Product ID": product_id,
            "Finished Material": product_name,
            "Opening": opening,
            "Production": production,
            "Dispatch": dispatch,
            "Total": opening + production,
            "Stock": opening + production - dispatch
        })
    
    conn.close()
    return daily_data

# Update stock entries
def update_daily_stocks(selected_date, updates):
    conn = sqlite3.connect('material_stocks.db')
    c = conn.cursor()
    
    for product_id, values in updates.items():
        c.execute('''UPDATE daily_stocks
                     SET production = ?, dispatch = ?
                     WHERE date = ? AND product_id = ?''',
                     (values['production'], values['dispatch'], selected_date, product_id))
    
    conn.commit()
    conn.close()

# Main app
def main():
    st.title("Material Stocks Management System")
    
    # Initialize database
    init_db()
    
    # Date selection
    selected_date = st.date_input("Select Date", datetime.today())
    
    # Get or create daily data
    daily_data = get_or_create_daily_stocks(selected_date)
    
    # Display current data
    st.subheader(f"Material Stocks for {selected_date.strftime('%Y-%m-%d')}")
    
    # Create editable dataframe
    df = pd.DataFrame(daily_data)
    df_display = df[['Finished Material', 'Opening', 'Production', 'Dispatch', 'Total', 'Stock']]
    
    # Use a form for editing
    with st.form("stock_form"):
        edited_df = st.data_editor(
            df_display,
            disabled=["Finished Material", "Opening", "Total", "Stock"],
            column_config={
                "Opening": st.column_config.NumberColumn(format="%.2f"),
                "Production": st.column_config.NumberColumn(format="%.2f"),
                "Dispatch": st.column_config.NumberColumn(format="%.2f"),
                "Total": st.column_config.NumberColumn(format="%.2f"),
                "Stock": st.column_config.NumberColumn(format="%.2f")
            }
        )
        
        submitted = st.form_submit_button("Save Changes")
        
        if submitted:
            # Prepare updates
            updates = {}
            for idx, row in df.iterrows():
                product_id = row['Product ID']
                production = edited_df.loc[idx, 'Production']
                dispatch = edited_df.loc[idx, 'Dispatch']
                
                updates[product_id] = {
                    'production': production,
                    'dispatch': dispatch
                }
            
            # Save updates
            update_daily_stocks(selected_date, updates)
            st.success("Changes saved successfully!")
            
            # Refresh data
            daily_data = get_or_create_daily_stocks(selected_date)
            df = pd.DataFrame(daily_data)
            df_display = df[['Finished Material', 'Opening', 'Production', 'Dispatch', 'Total', 'Stock']]

if __name__ == "__main__":
    main()
