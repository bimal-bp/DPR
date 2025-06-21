import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import os

# Initialize database with better error handling
def init_db():
    try:
        conn = sqlite3.connect('material_stocks.db')
        c = conn.cursor()
        
        # Create products table
        c.execute('''CREATE TABLE IF NOT EXISTS products
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL UNIQUE)''')
        
        # Create daily_stocks table
        c.execute('''CREATE TABLE IF NOT EXISTS daily_stocks
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      date TEXT NOT NULL,  # Changed to TEXT for better compatibility
                      product_id INTEGER NOT NULL,
                      opening REAL NOT NULL,
                      production REAL DEFAULT 0,
                      dispatch REAL DEFAULT 0,
                      FOREIGN KEY (product_id) REFERENCES products (id),
                      UNIQUE(date, product_id))''')
        
        # Insert initial products
        initial_products = [
            "Product -1 MS-AMS",
            "Product -2 MS ©",
            "Product -3 MS-10µ",
            "Product -4 MS-K",
            "Product -5 MF-©"
        ]
        
        for product in initial_products:
            try:
                c.execute("INSERT OR IGNORE INTO products (name) VALUES (?)", (product,))
            except Exception as e:
                st.error(f"Error inserting product {product}: {e}")
        
        conn.commit()
        
        # DEBUG: Show tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        st.sidebar.write("Database Tables:", tables)
        
        # DEBUG: Show products
        c.execute("SELECT * FROM products")
        products = c.fetchall()
        st.sidebar.write("Products:", products)
        
    except Exception as e:
        st.error(f"Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

# Improved get_or_create_daily_stocks with better date handling
def get_or_create_daily_stocks(selected_date):
    try:
        conn = sqlite3.connect('material_stocks.db')
        c = conn.cursor()
        
        # Format date as string for database
        date_str = selected_date.strftime('%Y-%m-%d')
        
        # Get all products
        c.execute("SELECT id, name FROM products")
        products = c.fetchall()
        
        if not products:
            st.warning("No products found in database!")
            return []
        
        daily_data = []
        
        for product_id, product_name in products:
            # Check if entry exists for selected date
            c.execute('''SELECT opening, production, dispatch 
                         FROM daily_stocks 
                         WHERE date = ? AND product_id = ?''', 
                         (date_str, product_id))
            entry = c.fetchone()
            
            if entry:
                opening, production, dispatch = entry
            else:
                # Get previous day's closing stock
                prev_date = (selected_date - timedelta(days=1)).strftime('%Y-%m-%d')
                c.execute('''SELECT (opening + production - dispatch) as closing
                             FROM daily_stocks 
                             WHERE date = ? AND product_id = ?''', 
                             (prev_date, product_id))
                prev_closing = c.fetchone()
                
                opening = prev_closing[0] if prev_closing and prev_closing[0] is not None else 0.0
                production = 0.0
                dispatch = 0.0
                
                # Insert new entry
                c.execute('''INSERT INTO daily_stocks 
                              (date, product_id, opening, production, dispatch)
                              VALUES (?, ?, ?, ?, ?)''',
                              (date_str, product_id, opening, production, dispatch))
                conn.commit()
            
            daily_data.append({
                "Product ID": product_id,
                "Finished Material": product_name,
                "Opening": float(opening),
                "Production": float(production),
                "Dispatch": float(dispatch),
                "Total": float(opening) + float(production),
                "Stock": float(opening) + float(production) - float(dispatch)
            })
        
        # DEBUG: Show daily data
        st.sidebar.write("Daily Data:", daily_data)
        
        return daily_data
    
    except Exception as e:
        st.error(f"Error getting daily stocks: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Main app with better layout
def main():
    st.title("📦 Material Stocks Management System")
    
    # Initialize database with visual feedback
    with st.spinner("Initializing database..."):
        init_db()
    st.success("Database ready!")
    
    # Date selection
    selected_date = st.date_input("Select Date", datetime.today())
    
    # Get daily data with loading indicator
    with st.spinner("Loading stock data..."):
        daily_data = get_or_create_daily_stocks(selected_date)
    
    if not daily_data:
        st.warning("No stock data available!")
        return
    
    # Display current data
    st.subheader(f"Material Stocks for {selected_date.strftime('%Y-%m-%d')}")
    
    # Create editable dataframe
    df = pd.DataFrame(daily_data)
    df_display = df[['Finished Material', 'Opening', 'Production', 'Dispatch', 'Total', 'Stock']]
    
    # Display the table before editing
    st.write("Current Stock Data:")
    st.dataframe(df_display)
    
    # Use a form for editing
    with st.form("stock_form"):
        st.write("Edit Production and Dispatch values:")
        edited_df = st.data_editor(
            df_display,
            disabled=["Finished Material", "Opening", "Total", "Stock"],
            column_config={
                "Opening": st.column_config.NumberColumn(format="%.2f MT"),
                "Production": st.column_config.NumberColumn(format="%.2f MT"),
                "Dispatch": st.column_config.NumberColumn(format="%.2f MT"),
                "Total": st.column_config.NumberColumn(format="%.2f MT"),
                "Stock": st.column_config.NumberColumn(format="%.2f MT")
            },
            key="stock_editor"
        )
        
        submitted = st.form_submit_button("💾 Save Changes")
        
        if submitted:
            try:
                # Prepare updates
                updates = {}
                for idx, row in df.iterrows():
                    product_id = row['Product ID']
                    production = float(edited_df.loc[idx, 'Production'])
                    dispatch = float(edited_df.loc[idx, 'Dispatch'])
                    
                    updates[product_id] = {
                        'production': production,
                        'dispatch': dispatch
                    }
                
                # Save updates
                date_str = selected_date.strftime('%Y-%m-%d')
                conn = sqlite3.connect('material_stocks.db')
                c = conn.cursor()
                
                for product_id, values in updates.items():
                    c.execute('''UPDATE daily_stocks
                                 SET production = ?, dispatch = ?
                                 WHERE date = ? AND product_id = ?''',
                                 (values['production'], values['dispatch'], date_str, product_id))
                
                conn.commit()
                st.success("✅ Changes saved successfully!")
                
                # Refresh data
                daily_data = get_or_create_daily_stocks(selected_date)
                df = pd.DataFrame(daily_data)
                df_display = df[['Finished Material', 'Opening', 'Production', 'Dispatch', 'Total', 'Stock']]
                
                # Show updated data
                st.write("Updated Stock Data:")
                st.dataframe(df_display)
                
            except Exception as e:
                st.error(f"Error saving changes: {e}")
            finally:
                if conn:
                    conn.close()

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    main()
