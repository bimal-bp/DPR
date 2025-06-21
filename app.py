import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

# Initialize database with your specific products
def init_db():
    conn = sqlite3.connect('material_stocks.db')
    c = conn.cursor()
    
    # Create daily_stocks table
    c.execute('''CREATE TABLE IF NOT EXISTS material_stocks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  product_name TEXT NOT NULL,
                  opening REAL NOT NULL,
                  production REAL DEFAULT 0,
                  dispatch REAL DEFAULT 0,
                  UNIQUE(date, product_name))''')
    
    # Insert initial data if table is empty
    c.execute("SELECT COUNT(*) FROM material_stocks")
    if c.fetchone()[0] == 0:
        initial_data = [
            ('2025-06-20', 'Product -1 MS-AMS', 176.45, 42.55, 0),
            ('2025-06-20', 'Product -2 MS ©', 64, 0, 0),
            ('2025-06-20', 'Product -3 MS-10µ', 108.72, 0, 0),
            ('2025-06-20', 'Product -4 MS-K', 33, 0, 0),
            ('2025-06-20', 'Product -5 MF-©', 25.4, 0, 0)
        ]
        c.executemany('''INSERT INTO material_stocks 
                      (date, product_name, opening, production, dispatch)
                      VALUES (?, ?, ?, ?, ?)''', initial_data)
        conn.commit()
    conn.close()

# Get or create daily stocks
def get_daily_stocks(date):
    conn = sqlite3.connect('material_stocks.db')
    c = conn.cursor()
    date_str = date.strftime('%Y-%m-%d')
    
    # Check if data exists for this date
    c.execute("SELECT * FROM material_stocks WHERE date = ?", (date_str,))
    existing_data = c.fetchall()
    
    if existing_data:
        # Return existing data
        data = []
        for row in existing_data:
            _, _, product, opening, production, dispatch = row
            total = opening + production
            stock = total - dispatch
            data.append({
                'Finished Material': product,
                'Opening': opening,
                'Production': production,
                'Total': total,
                'Dispatch': dispatch,
                'Stock': stock
            })
        return data
    else:
        # Get yesterday's closing stocks for today's opening
        prev_date = date - timedelta(days=1)
        prev_date_str = prev_date.strftime('%Y-%m-%d')
        
        c.execute("SELECT product_name, (opening + production - dispatch) as closing FROM material_stocks WHERE date = ?", (prev_date_str,))
        prev_data = c.fetchall()
        
        if not prev_data:
            st.error("No previous data found. Please ensure you have initial data.")
            return None
        
        # Create new entries with yesterday's closing as today's opening
        new_data = []
        for product, closing in prev_data:
            opening = closing if closing else 0
            c.execute('''INSERT INTO material_stocks 
                      (date, product_name, opening, production, dispatch)
                      VALUES (?, ?, ?, ?, ?)''',
                      (date_str, product, opening, 0, 0))
            new_data.append({
                'Finished Material': product,
                'Opening': opening,
                'Production': 0,
                'Total': opening,
                'Dispatch': 0,
                'Stock': opening
            })
        conn.commit()
        return new_data

# Update stocks
def update_stocks(date, updated_data):
    conn = sqlite3.connect('material_stocks.db')
    c = conn.cursor()
    date_str = date.strftime('%Y-%m-%d')
    
    for item in updated_data:
        product = item['Finished Material']
        production = item['Production']
        dispatch = item['Dispatch']
        
        c.execute('''UPDATE material_stocks 
                     SET production = ?, dispatch = ?
                     WHERE date = ? AND product_name = ?''',
                     (production, dispatch, date_str, product))
    
    conn.commit()
    conn.close()

# Main app
def main():
    st.title("Material Stocks Management")
    
    # Initialize database
    init_db()
    
    # Date selection
    selected_date = st.date_input("Select Date", datetime.today())
    
    # Get data for selected date
    daily_data = get_daily_stocks(selected_date)
    
    if not daily_data:
        st.warning("No data available for this date")
        return
    
    # Display table
    st.subheader(f"Material Stocks (In MT) - {selected_date.strftime('%Y-%m-%d')}")
    
    # Create editable dataframe
    df = pd.DataFrame(daily_data)
    df_display = df[['Finished Material', 'Opening', 'Production', 'Total', 'Dispatch', 'Stock']]
    
    # Edit form
    with st.form("stock_form"):
        edited_df = st.data_editor(
            df_display,
            disabled=['Finished Material', 'Opening', 'Total', 'Stock'],
            column_config={
                "Opening": st.column_config.NumberColumn(format="%.2f MT"),
                "Production": st.column_config.NumberColumn(format="%.2f MT"),
                "Total": st.column_config.NumberColumn(format="%.2f MT"),
                "Dispatch": st.column_config.NumberColumn(format="%.2f MT"),
                "Stock": st.column_config.NumberColumn(format="%.2f MT")
            }
        )
        
        if st.form_submit_button("Save Data"):
            # Prepare updates
            updated_data = []
            for idx, row in df.iterrows():
                updated_data.append({
                    'Finished Material': row['Finished Material'],
                    'Production': edited_df.loc[idx, 'Production'],
                    'Dispatch': edited_df.loc[idx, 'Dispatch']
                })
            
            # Save updates
            update_stocks(selected_date, updated_data)
            st.success("Data saved successfully!")
            
            # Refresh data
            daily_data = get_daily_stocks(selected_date)
            df = pd.DataFrame(daily_data)
            df_display = df[['Finished Material', 'Opening', 'Production', 'Total', 'Dispatch', 'Stock']]

if __name__ == "__main__":
    main()
