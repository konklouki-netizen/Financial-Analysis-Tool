# app.py (v1.4 - Matplotlib Fix)
import streamlit as st
import pandas as pd
import os
import sys
import matplotlib.pyplot as plt # <--- ΝΕΑ ΕΙΣΑΓΩΓΗ

# === ΣΗΜΑΝΤΙΚΟ: Εισαγωγή των "Εγκεφάλων" μας ===
try:
    from test_loader import resolve_to_ticker, load_company_info, get_company_df
    from modules.analyzer import calculate_financial_ratios
except ImportError as e:
    st.error(f"Σφάλμα Εισαγωγής: {e}")
    st.error("Βεβαιώσου ότι τα 'app.py', 'test_loader.py', και ο φάκελος 'modules' είναι στον ίδιο κατάλογο.")
    st.stop() 

# === Ρύθμιση Σελίδας ===
st.set_page_config(
    page_title="Financial Analysis Tool",
    page_icon="📊",
    layout="wide" 
)

# === 1. Η Πλαϊνή Μπάρα (Sidebar) - Τα Εργαλεία Εισόδου ===
st.sidebar.title("📊 Εργαλεία Ανάλυσης")
st.sidebar.markdown("Διάλεξε την πηγή και την εταιρεία σου.")

source_options = ["Yahoo", "CSV", "Excel"] 
source_type = st.sidebar.selectbox(
    "Επίλεξε Πηγή Δεδομένων:",
    source_options,
    key="source_type_select"
)

# Αρχικοποίηση μεταβλητών
ticker = None
company_df = None
industry = "General"
info_df = None
source_name = ""
analyze_button = False
uploaded_file = None

# --- Λογική ανάλογα με την Πηγή ---
if source_type in ["CSV", "Excel"]:
    uploaded_file = st.sidebar.file_uploader(
        "Ανέβασε το αρχείο σου", 
        type=["csv", "xlsx", "xls"],
        key="file_uploader"
    )
    
    if uploaded_file:
        source_name = uploaded_file.name
        analyze_button = st.sidebar.button("🚀 Έναρξη Ανάλυσης (από Αρχείο)", key="analyze_file")

elif source_type == "Yahoo":
    raw_input = st.sidebar.text_input("Δώσε Ticker ή Όνομα Εταιρείας:", "Microsoft", key="ticker_input")
    if raw_input:
        source_name = raw_input
    analyze_button = st.sidebar.button("🚀 Έναρξη Ανάλυσης (από Yahoo)", key="analyze_yahoo")

# === 2. Κεντρική Σελίδα - Τα Αποτελέσματα ===
st.title("📊 Financial Analysis Dashboard")

if analyze_button:
    st.markdown(f"Ανάλυση για: **{source_name}** (Πηγή: {source_type})")

    # --- Βήμα Α: Φόρτωση Δεδομένων ---
    if source_type == "Yahoo":
        with st.spinner(f"Αναζήτηση για '{raw_input}'..."):
            ticker = resolve_to_ticker(raw_input, source_type=source_type.lower())
        
        if ticker is None:
            st.error(f"Δεν βρέθηκε έγκυρο Ticker για το '{raw_input}'. Δοκίμασε ξανά.")
            st.stop()
        
        st.success(f"Βρέθηκε το Ticker: **{ticker}**")
        
        with st.spinner(f"Λήψη δεδομένων για {ticker} (έως 5y)..."):
            info_df, industry = load_company_info(ticker)
            company_df = get_company_df(ticker, source_type=source_type.lower(), period="max")

    elif source_type in ["CSV", "Excel"] and uploaded_file is not None:
        st.success(f"Φορτώθηκε το αρχείο: **{uploaded_file.name}**")
        with st.spinner("Επεξεργασία αρχείου..."):
            
            temp_dir = "temp"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            file_ext = source_type.lower()
            if file_ext == "excel":
                try:
                    import openpyxl
                except ImportError:
                    st.error("Η βιβλιοθήκη 'openpyxl' λείπει. Τρέξε 'pip install openpyxl' στο terminal σου για να υποστηρίξεις αρχεία Excel.")
                    st.stop()
            
            company_df = get_company_df(temp_file_path, source_type=file_ext)
            
            industry = "General" 
            info_df = pd.DataFrame([{"Όνομα": uploaded_file.name, "Κλάδος": industry, "Σημείωση": "Ανάλυση από τοπικό αρχείο"}])

    if company_df is None or company_df.empty:
        st.error(f"Δεν βρέθηκαν ή δεν μπόρεσαν να φορτωθούν οικονομικά δεδομένα.")
        st.stop()

    st.success(f"Επιτυχής λήψη και κανονικοποίηση δεδομένων.")
    
    # --- Βήμα Β: Υπολογισμός Δεικτών ---
    with st.spinner("Υπολογισμός χρηματοοικονομικών δεικτών..."):
        result = calculate_financial_ratios(company_df, sector=industry)

    # === 3. Παρουσίαση Αποτελεσμάτων ===
    
    st.header(f"Επισκόπηση: {info_df['Όνομα'].iloc[0]}")
    st.dataframe(info_df, hide_index=True, use_container_width=True)

    st.header("Ανάλυση Χρηματοοικονομικών Δεικτών")
    
    categories = result.get("categories", {})
    if not categories:
        st.warning("Δεν υπολογίστηκαν κατηγορίες δεικτών.")
        st.stop()
        
    tab_names = list(categories.keys())
    tabs = st.tabs(tab_names)
    
    for i, tab_name in enumerate(tab_names):
        with tabs[i]:
            st.subheader(f"Δείκτες: {tab_name}")
            
            category_df = categories[tab_name]
            st.dataframe(category_df.set_index('Year'), use_container_width=True)
            
            # === ΦΑΣΗ 2 (v1.4): MATPLOTLIB FIX ===
            st.subheader(f"Εξέλιξη Δεικτών: {tab_name}")
            
            valid_cols = [col for col in category_df.columns if col not in ['Year', 'Date'] and not category_df[col].isnull().all()]
            
            if not valid_cols:
                st.info(f"Δεν υπάρχουν διαθέσιμα δεδομένα για τη δημιουργία γραφήματος για {tab_name}.")
            else:
                try:
                    # --- ΕΔΩ ΕΙΝΑΙ Η ΑΛΛΑΓΗ ---
                    # Δημιουργούμε ένα Figure και ένα Axis (plot) με το Matplotlib
                    fig, ax = plt.subplots()
                    
                    x_axis = category_df['Year']
                    
                    # Κάνουμε plot μία γραμμή για κάθε στήλη
                    for col in valid_cols:
                        ax.plot(x_axis, category_df[col], marker='o', label=col)
                    
                    # Προσθήκη legend (υπόμνημα)
                    if len(valid_cols) > 0:
                        ax.legend(loc='best') # 'best' βρίσκει το καλύτερο σημείο

                    ax.set_xlabel("Έτος (Year)")
                    ax.set_ylabel("Τιμή (Value)")
                    ax.grid(True) # Προσθήκη πλέγματος
                    
                    # Αυτό "στέλνει" το έτοιμο γράφημα στο Streamlit
                    st.pyplot(fig)
                    # --- ΤΕΛΟΣ ΑΛΛΑΓΗΣ ---
                    
                except Exception as e:
                    st.error(f"Σφάλμα κατά τη δημιουργία γραφήματος Matplotlib: {e}")
                    st.exception(e)

    st.success("✅ Η ανάλυση ολοκληρώθηκε!")
    
    with st.expander("Δες τα 'Standard' Δεδομένα που φορτώθηκαν (Raw Normalized Data)"):
        st.dataframe(company_df)
    
    with st.expander("Δες τον πλήρη πίνακα όλων των Δεικτών (Raw Ratios)"):
        st.dataframe(result.get("ratios"))

else:
    st.info("Επίλεξε πηγή και εταιρεία από την πλαϊνή μπάρα για να ξεκινήσεις.")