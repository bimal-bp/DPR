import streamlit as st
import psycopg2
from datetime import datetime, timedelta
import pandas as pd

# Database connection
def get_connection():
    return psycopg2.connect(
        dbname=st.secrets["neon"]["dbname"],
        user=st.secrets["neon"]["user"],
        password=st.secrets["neon"]["password"],
        host=st.secrets["neon"]["host"]
    )

# Initialize database
def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Create tables if not exists (simplified for example)
            pass

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

# Main application
def main():
    st.title("Stock Management System")
    
    # Date selection
    today = st.date_input("Select Date", datetime.today())
    
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
        
        for _, product in finished_products.iterrows():
            st.subheader(product['product_name'])
            
            # Get previous closing as today's opening
            opening = get_previous_closing(product['product_id'], today, 'daily_stocks')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.number_input(
                    f"Opening Stock ({product['unit']})", 
                    key=f"opening_{product['product_id']}",
                    value=float(opening),
                    disabled=True
                )
            with col2:
                production = st.number_input(
                    "Production", 
                    key=f"prod_{product['product_id']}",
                    min_value=0.0
                )
            with col3:
                dispatch = st.number_input(
                    "Dispatch", 
                    key=f"dispatch_{product['product_id']}",
                    min_value=0.0
                )
            
            # Calculate and show closing
            closing = opening + production - dispatch
            st.metric("Closing Stock", f"{closing} {product['unit']}")
    
    # Similar implementation for Raw Materials and Bags tabs
    
    if st.button("Save Today's Data"):
        save_data(today)
        st.success("Data saved successfully!")

def save_data(date):
    # Implementation to save all entered data to database
    pass

if __name__ == "__main__":
    init_db()
    main()
