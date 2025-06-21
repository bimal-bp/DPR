import streamlit as st
import psycopg2
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
def get_connection():
    try:
        if 'neon' in st.secrets:
            return psycopg2.connect(
                dbname=st.secrets["neon"]["dbname"],
                user=st.secrets["neon"]["user"],
                password=st.secrets["neon"]["password"],
                host=st.secrets["neon"]["host"],
                sslmode="require"
            )
        return psycopg2.connect(
            "postgresql://neondb_owner:npg_rop03PxbtTZE@ep-delicate-dew-a4o2ufne-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
        )
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        st.stop()

# Initialize database with sample data
def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Create tables if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id SERIAL PRIMARY KEY,
                    product_name VARCHAR(100) NOT NULL,
                    product_type VARCHAR(50) CHECK (product_type IN ('finished', 'raw', 'bag')),
                    unit VARCHAR(20) DEFAULT 'MT' CHECK (unit IN ('MT', 'bags'))
                )
            """)
            
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
            
            # Insert sample products if they don't exist
            products = [
                # Finished Materials
                ('Product -1 MS-AMS', 'finished', 'MT'),
                ('Product -2 MS ©', 'finished', 'MT'),
                ('Product -3 MS-10µ', 'finished', 'MT'),
                ('Product -4 MS-K', 'finished', 'MT'),
                ('Product -5 MF-©', 'finished', 'MT'),
                
                # Raw Materials
                ('SGX Slurry', 'raw', 'MT'),
                ('RWM-1 RH', 'raw', 'MT'),
                ('RWM-2 OPC', 'raw', 'MT'),
                ('RWM-3', 'raw', 'MT'),
                ('Others', 'raw', 'MT'),
                ('ACCLEATOR', 'raw', 'MT'),
                
                # Bags
                ('MS - AMS', 'bag', 'bags'),
                ('MS', 'bag', 'bags'),
                ('MF', 'bag', 'bags'),
                ('MS _jumbo', 'bag', 'bags'),
                ('Plain jumbo', 'bag', 'bags'),
                ('SGX - AMS', 'bag', 'bags'),
                ('SGX - Silica', 'bag', 'bags')
            ]
            
            for product in products:
                cur.execute(
                    "INSERT INTO products (product_name, product_type, unit) "
                    "SELECT %s, %s, %s WHERE NOT EXISTS ("
                    "SELECT 1 FROM products WHERE product_name = %s)",
                    (*product, product[0])
                )
            
            # Insert sample data for June 20th if it doesn't exist
            sample_date = datetime(2025, 6, 20).date()
            
            # Check if sample data already exists
            cur.execute("SELECT 1 FROM daily_stocks WHERE date = %s LIMIT 1", (sample_date,))
            if not cur.fetchone():
                # Sample data for June 20th
                sample_data = [
                    # Finished Materials (product_id, opening, production, dispatch)
                    (1, 176.45, 42.55, 0),  # MS-AMS
                    (2, 64, 0, 0),          # MS ©
                    (3, 108.72, 0, 0),       # MS-10µ
                    (4, 33, 0, 0),           # MS-K
                    (5, 25.4, 0, 0),         # MF-©
                    
                    # Raw Materials (product_id, opening, received, used)
                    (6, 86.39, 0, 0),        # SGX Slurry
                    (7, 17.85, 35, 12),      # RWM-1 RH
                    (8, 28.5, 0, 1.6),       # RWM-2 OPC
                    (9, 5.7, 0, 0),          # RWM-3
                    (11, 228, 0, 0)          # ACCLEATOR
                ]
                
                for data in sample_data:
                    cur.execute(
                        "INSERT INTO daily_stocks (product_id, date, opening, production, received, used, dispatch) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (data[0], sample_date, data[1], data[2], data[3] if len(data) > 3 else 0, 
                         data[4] if len(data) > 4 else 0, data[5] if len(data) > 5 else 0)
                    )
                
                # Sample bag data for June 20th
                bag_data = [
                    # Bags (product_id, opening, purchase, used)
                    (12, 5000, 0, 0),    # MS - AMS
                    (13, 75547, 0, 1702), # MS
                    (14, 32575, 0, 0),    # MF
                    (15, 982, 0, 0),      # MS _jumbo
                    (16, 246, 0, 0)       # Plain jumbo
                ]
                
                for data in bag_data:
                    cur.execute(
                        "INSERT INTO daily_bags (product_id, date, opening, purchase, used) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (data[0], sample_date, data[1], data[2], data[3])
                    )
            
            conn.commit()

# Get previous day's closing
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
def save_data(date, product_data, bag_data):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Save stock data
            for product_id, data in product_data.items():
                cur.execute("""
                    INSERT INTO daily_stocks (
                        product_id, date, opening, production, received, used, dispatch
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id, date) DO UPDATE SET
                        production = EXCLUDED.production,
                        received = EXCLUDED.received,
                        used = EXCLUDED.used,
                        dispatch = EXCLUDED.dispatch
                """, (
                    product_id, date, data['opening'], 
                    data.get('production', 0), data.get('received', 0),
                    data.get('used', 0), data.get('dispatch', 0)
                ))
            
            # Save bag data
            for product_id, data in bag_data.items():
                cur.execute("""
                    INSERT INTO daily_bags (
                        product_id, date, opening, purchase, used
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (product_id, date) DO UPDATE SET
                        purchase = EXCLUDED.purchase,
                        used = EXCLUDED.used
                """, (
                    product_id, date, data['opening'], 
                    data.get('purchase', 0), data.get('used', 0)
                ))
            
            conn.commit()

# View historical data
def view_historical_data(start_date, end_date):
    with get_connection() as conn:
        # Finished Materials
        st.header("Finished Materials History")
        finished_query = """
            SELECT p.product_name, ds.date, ds.opening, ds.production, ds.dispatch, ds.closing
            FROM daily_stocks ds
            JOIN products p ON ds.product_id = p.product_id
            WHERE p.product_type = 'finished' AND ds.date BETWEEN %s AND %s
            ORDER BY ds.date, p.product_name
        """
        finished_df = pd.read_sql(finished_query, conn, params=(start_date, end_date))
        st.dataframe(finished_df.pivot(index='date', columns='product_name', 
                                     values=['opening', 'production', 'dispatch', 'closing']))
        
        # Raw Materials
        st.header("Raw Materials History")
        raw_query = """
            SELECT p.product_name, ds.date, ds.opening, ds.received, ds.used, ds.closing
            FROM daily_stocks ds
            JOIN products p ON ds.product_id = p.product_id
            WHERE p.product_type = 'raw' AND ds.date BETWEEN %s AND %s
            ORDER BY ds.date, p.product_name
        """
        raw_df = pd.read_sql(raw_query, conn, params=(start_date, end_date))
        st.dataframe(raw_df.pivot(index='date', columns='product_name', 
                                values=['opening', 'received', 'used', 'closing']))
        
        # Bags
        st.header("Bags History")
        bags_query = """
            SELECT p.product_name, db.date, db.opening, db.purchase, db.used, db.closing
            FROM daily_bags db
            JOIN products p ON db.product_id = p.product_id
            WHERE p.product_type = 'bag' AND db.date BETWEEN %s AND %s
            ORDER BY db.date, p.product_name
        """
        bags_df = pd.read_sql(bags_query, conn, params=(start_date, end_date))
        st.dataframe(bags_df.pivot(index='date', columns='product_name', 
                                 values=['opening', 'purchase', 'used', 'closing']))

# Main application
def main():
    st.title("Stock Management System")
    
    # Initialize database
    init_db()
    
    # Navigation
    menu = st.sidebar.selectbox("Menu", ["Data Entry", "View History"])
    
    if menu == "Data Entry":
        # Date selection
        today = st.date_input("Select Date", datetime.today())
        
        # Initialize data dictionaries
        product_data = {}
        bag_data = {}
        
        # Tab layout
        tab1, tab2, tab3 = st.tabs(["Finished Materials", "Raw Materials", "Bags"])
        
        with tab1:
            st.header("Finished Materials")
            with get_connection() as conn:
                finished_products = pd.read_sql(
                    "SELECT * FROM products WHERE product_type = 'finished' ORDER BY product_name", 
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
                            value=0.0,
                            step=0.01,
                            format="%.2f"
                        )
                    with col3:
                        dispatch = st.number_input(
                            "Dispatch", 
                            key=f"dispatch_{product_id}",
                            min_value=0.0,
                            value=0.0,
                            step=0.01,
                            format="%.2f"
                        )
                    
                    # Calculate and show closing
                    closing = opening + production - dispatch
                    st.metric("Closing Stock", f"{closing:.2f} {product['unit']}")
                    
                    # Store data for saving
                    product_data[product_id] = {
                        'opening': opening,
                        'production': production,
                        'dispatch': dispatch,
                        'closing': closing
                    }
        
        with tab2:
            st.header("Raw Materials")
            with get_connection() as conn:
                raw_products = pd.read_sql(
                    "SELECT * FROM products WHERE product_type = 'raw' ORDER BY product_name", 
                    conn
                )
            
            if raw_products.empty:
                st.warning("No raw materials found in database")
            else:
                for _, product in raw_products.iterrows():
                    st.subheader(product['product_name'])
                    product_id = product['product_id']
                    
                    # Get previous closing as today's opening
                    opening = get_previous_closing(product_id, today, 'daily_stocks')
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.number_input(
                            f"Opening Stock ({product['unit']})", 
                            key=f"raw_opening_{product_id}",
                            value=float(opening),
                            disabled=True
                        )
                    with col2:
                        received = st.number_input(
                            "Received", 
                            key=f"received_{product_id}",
                            min_value=0.0,
                            value=0.0,
                            step=0.01,
                            format="%.2f"
                        )
                    with col3:
                        used = st.number_input(
                            "Used", 
                            key=f"used_{product_id}",
                            min_value=0.0,
                            value=0.0,
                            step=0.01,
                            format="%.2f"
                        )
                    
                    # Calculate and show closing
                    closing = opening + received - used
                    st.metric("Closing Stock", f"{closing:.2f} {product['unit']}")
                    
                    # Store data for saving
                    product_data[product_id] = {
                        'opening': opening,
                        'received': received,
                        'used': used,
                        'closing': closing
                    }
        
        with tab3:
            st.header("Bags")
            with get_connection() as conn:
                bag_products = pd.read_sql(
                    "SELECT * FROM products WHERE product_type = 'bag' ORDER BY product_name", 
                    conn
                )
            
            if bag_products.empty:
                st.warning("No bag products found in database")
            else:
                for _, product in bag_products.iterrows():
                    st.subheader(product['product_name'])
                    product_id = product['product_id']
                    
                    # Get previous closing as today's opening
                    opening = get_previous_closing(product_id, today, 'daily_bags')
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.number_input(
                            f"Opening Stock ({product['unit']})", 
                            key=f"bag_opening_{product_id}",
                            value=int(opening),
                            disabled=True
                        )
                    with col2:
                        purchase = st.number_input(
                            "Purchase", 
                            key=f"purchase_{product_id}",
                            min_value=0,
                            value=0,
                            step=1
                        )
                    with col3:
                        used = st.number_input(
                            "Used", 
                            key=f"bag_used_{product_id}",
                            min_value=0,
                            value=0,
                            step=1
                        )
                    
                    # Calculate and show closing
                    closing = opening + purchase - used
                    st.metric("Closing Stock", f"{closing} {product['unit']}")
                    
                    # Store data for saving
                    bag_data[product_id] = {
                        'opening': opening,
                        'purchase': purchase,
                        'used': used,
                        'closing': closing
                    }
        
        if st.button("Save Today's Data"):
            if product_data or bag_data:
                save_data(today, product_data, bag_data)
                st.success("Data saved successfully!")
            else:
                st.warning("No data to save")
    
    elif menu == "View History":
        st.header("View Historical Data")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.today() - timedelta(days=7))
        with col2:
            end_date = st.date_input("End Date", datetime.today())
        
        if start_date > end_date:
            st.error("End date must be after start date")
        else:
            view_historical_data(start_date, end_date)

if __name__ == "__main__":
    main()
