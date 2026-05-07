import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
conn = sqlite3.connect('cab_booking.db', check_same_thread=False)
c = conn.cursor()

def create_tables():
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY, customer_name TEXT, pickup TEXT, drop_loc TEXT, 
                 date TEXT, time TEXT, car_type TEXT, status TEXT, driver_id INTEGER, amount REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS drivers (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, status TEXT)''')
    conn.commit()

create_tables()

# --- HELPER FUNCTIONS ---
def get_drivers():
    return pd.read_sql_query("SELECT * FROM drivers", conn)

# --- UI SETUP ---
st.set_page_config(page_title="Transport Management System", layout="wide")

if 'user_role' not in st.session_state:
    st.session_state.user_role = None
    st.session_state.user_name = None

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🚖 Cab Service Pro")
if st.session_state.user_role:
    st.sidebar.write(f"Welcome, **{st.session_state.user_name}** ({st.session_state.user_role})")
    if st.sidebar.button("Logout"):
        st.session_state.user_role = None
        st.rerun()
else:
    role_choice = st.sidebar.selectbox("Login as", ["Customer", "Driver", "Admin"])
    if st.sidebar.button("Enter Panel"):
        st.session_state.user_role = role_choice
        st.session_state.user_name = role_choice # Simulating login
        st.rerun()

# --- 1. CUSTOMER PANEL ---
if st.session_state.user_role == "Customer":
    st.header("📍 Book Your Ride")
    
    col1, col2 = st.columns(2)
    with col1:
        pickup = st.text_input("Pickup Location")
        drop = st.text_input("Drop Location")
    with col2:
        date = st.date_input("Date")
        time = st.time_input("Time")
    
    car_type = st.selectbox("Select Car", ["Maruti Dzire (Sedan)", "Maruti Ertiga (7 Seater)"])
    
    # Fare logic (Simulated)
    fare = 500 if "Dzire" in car_type else 800
    st.write(f"### Estimated Fare: ₹{fare}")
    
    if st.button("Confirm Booking"):
        c.execute("INSERT INTO bookings (customer_name, pickup, drop_loc, date, time, car_type, status, amount) VALUES (?,?,?,?,?,?,?,?)",
                  (st.session_state.user_name, pickup, drop, str(date), str(time), car_type, "Pending", fare))
        conn.commit()
        st.success("Booking Request Sent Successfully!")

    st.divider()
    st.subheader("Your Booking History")
    df_cust = pd.read_sql_query(f"SELECT pickup, drop_loc, car_type, status, amount FROM bookings WHERE customer_name='{st.session_state.user_name}'", conn)
    st.table(df_cust)

# --- 2. DRIVER PANEL ---
elif st.session_state.user_role == "Driver":
    st.header("🚗 Driver Dashboard")
    
    # Driver registration (Simulated for setup)
    st.sidebar.divider()
    if st.sidebar.checkbox("Register as Driver"):
        d_name = st.text_input("Full Name")
        d_phone = st.text_input("Phone Number")
        if st.button("Register"):
            c.execute("INSERT INTO drivers (name, phone, status) VALUES (?,?,?)", (d_name, d_phone, "Available"))
            conn.commit()
            st.success("Registered!")

    # Show Assigned Bookings
    st.subheader("My Assigned Trips")
    # For demo, showing all bookings assigned or completed
    df_drv = pd.read_sql_query("SELECT id, customer_name, pickup, drop_loc, status, amount FROM bookings WHERE status != 'Pending'", conn)
    if not df_drv.empty:
        st.dataframe(df_drv, use_container_width=True)
        
        trip_id = st.number_input("Enter Booking ID to Complete", step=1, min_value=1)
        if st.button("Mark Trip Completed"):
            c.execute("UPDATE bookings SET status='Completed' WHERE id=?", (trip_id,))
            conn.commit()
            st.success(f"Trip {trip_id} finished!")
            st.rerun()
    else:
        st.info("No trips assigned yet.")

# --- 3. ADMIN PANEL ---
elif st.session_state.user_role == "Admin":
    st.header("📈 Admin Control Center")
    
    # Stats
    bookings_df = pd.read_sql_query("SELECT * FROM bookings", conn)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Bookings", len(bookings_df))
    col2.metric("Revenue", f"₹{bookings_df['amount'].sum()}")
    col3.metric("Drivers", len(get_drivers()))

    tab1, tab2, tab3 = st.tabs(["Manage Bookings", "Manage Drivers", "Financials"])

    with tab1:
        st.subheader("New Booking Requests")
        pending_bookings = pd.read_sql_query("SELECT * FROM bookings WHERE status='Pending'", conn)
        st.dataframe(pending_bookings)
        
        if not pending_bookings.empty:
            st.divider()
            b_id = st.selectbox("Select Booking ID to Assign", pending_bookings['id'])
            drivers_list = get_drivers()
            d_choice = st.selectbox("Assign Driver", drivers_list['name'])
            
            if st.button("Confirm Assignment"):
                c.execute("UPDATE bookings SET status='Assigned', driver_id=(SELECT id FROM drivers WHERE name=?) WHERE id=?", (d_choice, b_id))
                conn.commit()
                st.success("Driver Assigned!")
                st.rerun()

    with tab2:
        st.subheader("Driver Fleet")
        st.table(get_drivers())

    with tab3:
        st.subheader("Profit & Earnings")
        # Logic: 80% to driver, 20% to admin/company
        if not bookings_df.empty:
            bookings_df['Driver Share'] = bookings_df['amount'] * 0.8
            bookings_df['Profit'] = bookings_df['amount'] * 0.2
            st.dataframe(bookings_df[['id', 'customer_name', 'amount', 'Driver Share', 'Profit']])
