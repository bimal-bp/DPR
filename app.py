import streamlit as st
import psycopg2
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables (for local development)
load_dotenv()

# Database connection
def get_connection():
    try:
        # Try using Streamlit secrets first
        if 'neon' in st.secrets:
            return psycopg2.connect(
                dbname=st.secrets["neon"]["dbname"],
                user=st.secrets["neon"]["user"],
                password=st.secrets["neon"]["password"],
                host=st.secrets["neon"]["host"],
                sslmode="require"
            )
        # Fallback to direct connection string (for testing)
        return psycopg2.connect(
            "postgresql://neondb_owner:npg_rop03PxbtTZE@ep-delicate-dew-a4o2ufne-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
        )
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        st.stop()

# Initialize database
def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Create products table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id SERIAL PRIMARY KEY,
                    product_name VARCHAR(100) NOT NULL,
                    product_type VARCHAR(50) CHECK (product_type IN ('finished', 'raw', 'bag')),
                    unit VARCHAR(20) DEFAULT 'MT' CHECK (unit IN ('MT', 'bags'))
                )
            """)
            
            # Create daily stock transactions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_stocks (
                    transaction_id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(product_id),
                    date DATE NOT NULL,
                    opening NUMERIC(12,2) DEFAULT 0,
                    production NUMERIC(12,2) DEFAULT 0,
                    received NUMERIC(12,2) DEFAULT 0,
                    dispatch NUMERIC(12,2) DEFAULT 0,
                    used NUMERIC(12,2) DEFAULT 0,
                    closing NUMERIC(12,2) GENERATED ALWAYS AS (
                        opening + production + received - dispatch - used
                    ) STORED,
                    UNIQUE(product_id, date)
                )
            """)
            
            # Create daily bag transactions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_bags (
                    transaction_id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(product_id),
                    date DATE NOT NULL,
                    opening INTEGER DEFAULT 0,
                    purchase INTEGER DEFAULT 0,
                    used INTEGER DEFAULT 0,
                    closing INTEGER GENERATED ALWAYS AS (
                        opening + purchase - used
                    ) STORED,
                    UNIQUE(product_id, date)
                )
            """)
            conn.commit()

# Get previous day's closing as today's opening
def get_previous_closing(product_id, date, table_name):
    prev_date = date - timedelta(days=1)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT closing FROM {table_name} WHERE product_id = %s AND date = %s",
                (product_id, prev_date)
            )
            result = cur.fetchone()
            return result[0] if result else 0

# Save data to database
def save_data(date, product_data):
    with get_connection() as conn:
        with conn.cursor() as cur:
            for product_id, data in product_data.items():
                # Insert or update daily stock record
                cur.execute("""
                    INSERT INTO daily_stocks (
                        product_id, date, opening, production, dispatch
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (product_id, date) DO UPDATE SET
                        production = EXCLUDED.production,
                        dispatch = EXCLUDED.dispatch
                """, (
                    product_id, date, data['opening'], data['production'], data['dispatch']
                ))
            conn.commit()

# Main application
def main():
    st.title("Stock Management System")
    
    # Date selection
    today = st.date_input("Select Date", datetime.today())
    
    # Initialize product data dictionary
    product_data = {}
    
    # Tab layout
    tab1, tab2, tab3 = st.tabs(["Finished Materials", "Raw Materials", "Bags"])
    
    with tab1:
        st.header("Finished Materials")
        # Get finished products
        with get_connection() as conn:
            finished_products = pd.read_sql(
                "SELECT * FROM products WHERE product_type = 'finished'", 
                conn
            )
        
        if finished_products.empty:
            st.warning("No finished products found in database")
        else:
            for _, product in finished_products.iterrows():
                st.subheader(product['product_name'])
                product_id = product['product_id']
                
                # Get previous closing as today's opening
                opening = get_previous_closing(product_id, today, 'daily_stocks')
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.number_input(
                        f"Opening Stock ({product['unit']})", 
                        key=f"opening_{product_id}",
                        value=float(opening),
                        disabled=True
                    )
                with col2:
                    production = st.number_input(
                        "Production", 
                        key=f"prod_{product_id}",
                        min_value=0.0,
                        value=0.0
                    )
                with col3:
                    dispatch = st.number_input(
                        "Dispatch", 
                        key=f"dispatch_{product_id}",
                        min_value=0.0,
                        value=0.0
                    )
                
                # Calculate and show closing
                closing = opening + production - dispatch
                st.metric("Closing Stock", f"{closing} {product['unit']}")
                
                # Store data for saving
                product_data[product_id] = {
                    'opening': opening,
                    'production': production,
                    'dispatch': dispatch,
                    'closing': closing
                }
    
    # Similar implementation for Raw Materials and Bags tabs would go here
    
    if st.button("Save Today's Data"):
        if product_data:
            save_data(today, product_data)
            st.success("Data saved successfully!")
        else:
            st.warning("No data to save")

if __name__ == "__main__":
    init_db()
    main()
