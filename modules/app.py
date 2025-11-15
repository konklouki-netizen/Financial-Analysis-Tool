# app.py (v1.25 - Η ΤΕΛΙΚΗ Διόρθωση Path)
import streamlit as st
import pandas as pd
import os
import sys

# === v1.25 FIX: Η "Αλεξίσφαιρη" Διόρθωση Path ===
# Αυτό εξασφαλίζει ότι η Python βλέπει τον φάκελο 'modules'
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)
# === === === === === === === === === ===

import unicodedata 
import datetime 
import plotly.graph_objects as go 
from typing import Tuple, List, Dict, Any, Optional

# === Εισαγωγή PDF Exporter ===
try:
    from modules.pdf_exporter import create_pdf_report
except ImportError:
    st.error("ΚΡΙΣΙΜΟ ΣΦΑΛΜΑ: ΔΕΝ ΒΡΕΘΗΚΕ το 'modules/pdf_exporter.py'. Βεβαιώσου ότι το αρχείο υπάρχει στον φάκελο 'modules'.")
    st.stop()
# === === === === === === === === ===

# === Εισαγωγή των "Εγκεφάλων" μας ===
try:
    from test_loader import resolve_to_ticker, load_company_info, get_company_df, normalize_dataframe
    from modules.analyzer import calculate_financial_ratios
except ImportError as e:
    st.error(f"ΚΡΙΣΙΜΟ ΣΦΑΛΜΑ: {e}")
    st.error("Βεβαιώσου ότι τα 'app.py', 'test_loader.py', και ο φάκελος 'modules' είναι στον ίδιο κατάλογο.")
    st.stop() 

# === Ρύθμιση Σελίδας ===
st.set_page_config(
    page_title="Financial Analysis Tool v1.25", # <--- Νέα έκδοση
    page_icon="📊",
    layout="wide" 
)

# === v1.22: Αρχικοποίηση "Μνήμης" (Session State) ===
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'analysis_inputs' not in st.session_state:
    st.session_state.analysis_inputs = {}
# === === === === === === === === === ===

# === v1.15: "Υπέρ-Έξυπνος Διαχωριστής" PDF ===
def _find_and_merge_pdf_tables(raw_data_list: list) -> Tuple[pd.DataFrame, dict]:
    """
    Αυτός είναι ο "Υπέρ-Έξυπνος Διαχωριστής" (v1.15).
    Καλείται **ΜΟΝΟ** για πηγές PDF.
    """
    st.info("🔎 Εκτέλεση 'Υπέρ-Έξυπνου Διαχωριστή' PDF (v1.15)...")
    
    INCOME_KEYS = ['income statement', 'κατασταση αποτελεσματων', 'results of operations', 'revenue', 'net income', 'έσοδα', 'κέρδη']
    BALANCE_KEYS = ['balance sheet', 'ισολογισμοσ', 'financial position', 'total assets', 'total liabilities', 'ενεργητικό', 'υποχρεώσεις']
    CASH_KEYS = ['cash flow', 'ταμειακεσ ροεσ', 'operating activities', 'investing activities', 'financing activities', 'operating cash flow']

    found_tables = {
        "income": pd.DataFrame(),
        "balance": pd.DataFrame(),
        "cashflow": pd.DataFrame()
    }
    
    debug_log = {} 

    # 1. Βρες τους 3 πίνακες
    for item in raw_data_list:
        title = item.get("title", "").lower()
        table_df = item.get("table")
        
        if table_df is None or table_df.empty:
            continue
            
        try:
            if table_df.shape[1] > 0:
                first_col_content = " ".join(table_df.iloc[:, 0].astype(str)).lower()
            else:
                first_col_content = ""
        except Exception:
            first_col_content = "" 

        search_corpus = title + " " + first_col_content

        if any(key in search_corpus for key in INCOME_KEYS) and found_tables["income"].empty:
            st.write(f"✅ Βρέθηκε ο Πίνακας 'Income' (Τίτλος: {title})")
            found_tables["income"] = table_df
            debug_log["Income Statement (Raw)"] = table_df
            
        elif any(key in search_corpus for key in BALANCE_KEYS) and found_tables["balance"].empty:
            st.write(f"✅ Βρέθηκε ο Πίνακας 'Balance' (Τίτλος: {title})")
            found_tables["balance"] = table_df
            debug_log["Balance Sheet (Raw)"] = table_df

        elif any(key in search_corpus for key in CASH_KEYS) and found_tables["cashflow"].empty:
            st.write(f"✅ Βρέθηκε ο Πίνακας 'CashFlow' (Τίτλος: {title})")
            found_tables["cashflow"] = table_df
            debug_log["Cash Flow (Raw)"] = table_df

    # 2. "Μετάφρασε" (Pivot/Normalize) τους 3 πίνακες
    final_dfs = []

    if not found_tables["income"].empty:
        st.write("...Μεταφράζεται ο Πίνακας 'Income'...")
        df = normalize_dataframe(found_tables["income"], source_type="pdf") 
        if not df.empty:
            final_dfs.append(df)
            debug_log["Income Statement (Normalized)"] = df
        else:
             st.warning("  > Η 'Μετάφραση' του Income απέτυχε (π.χ. δεν βρήκε χρονιές).")

            
    if not found_tables["balance"].empty:
        st.write("...Μεταφράζεται ο Πίνακας 'Balance'...")
        df = normalize_dataframe(found_tables["balance"], source_type="pdf")
        if not df.empty:
            final_dfs.append(df)
            debug_log["Balance Sheet (Normalized)"] = df
        else:
             st.warning("  > Η 'Μετάφραση' του Balance απέτυχε (π.χ. δεν βρήκε χρονιές).")

    if not found_tables["cashflow"].empty:
        st.write("...Μεταφράζεται ο Πίνακας 'CashFlow'...")
        df = normalize_dataframe(found_tables["cashflow"], source_type="pdf")
        if not df.empty:
            final_dfs.append(df)
            debug_log["Cash Flow (Normalized)"] = df
        else:
             st.warning("  > Η 'Μετάφραση' του CashFlow απέτυχε (π.χ. δεν βρήκε χρονιές).")

    # 3. Τελική Ένωση (Merge)
    if not final_dfs:
        st.error("❌ Ο 'Υπέρ-Έξυπνος Διαχωριστής' απέτυχε. Δεν βρέθηκε ή δεν μεταφράστηκε κανένας χρήσιμος πίνακας.")
        return pd.DataFrame(), debug_log

    st.write("...Τελική ένωση (merge) των πινάκων...")
    
    final_golden_df = pd.DataFrame()
    try:
        final_golden_df = final_dfs[0]
        if len(final_dfs) > 1:
            for i in range(1, len(final_dfs)):
                if 'Year' in final_golden_df.columns and 'Year' in final_dfs[i].columns:
                    final_golden_df = pd.merge(final_golden_df, final_dfs[i], on="Year", how="outer")
                else:
                     st.warning(f"  > Αποτυχία 'Merge': Ένας πίνακας αγνοήθηκε (έλειπε το 'Year').")
                     
    except Exception as e:
        st.error(f"Αποτυχία 'Merge': {e}")
        return pd.DataFrame(), debug_log

    final_golden_df = final_golden_df.loc[:, ~final_golden_df.columns.duplicated()]

    return final_golden_df, debug_log
# === === === === === === === === === ===


# === 1. Η Πλαϊνή Μπάρα (Sidebar) - Τα Εργαλεία Εισόδου ===
st.sidebar.title("📊 Εργαλεία Ανάλυσης (v1.25)") # <--- Νέα έκδοση
st.sidebar.markdown("Διάλεξε την πηγή και την εταιρεία σου.")

def reset_analysis_state():
    """v1.22: Κάνει reset τη 'μνήμη' (σβήνει τα παλιά αποτελέσματα) όταν αλλάζει η πηγή."""
    st.session_state.analysis_results = None
    st.session_state.analysis_inputs = {}

source_options = ["Yahoo", "CSV", "Excel", "PDF"] 
source_type = st.sidebar.selectbox(
    "Επίλεξε Πηγή Δεδομένων:",
    source_options,
    key="source_type_select",
    on_change=reset_analysis_state # v1.22: ΝΕΟ
)

# Αρχικοποίηση μεταβλητών
raw_input: Optional[str] = None 
uploaded_file: Optional[Any] = None
competitor_ticker_input: Optional[str] = None

# --- Λογική ανάλογα με την Πηγή ---
if source_type in ["CSV", "Excel", "PDF"]: 
    st.sidebar.warning("Η σύγκριση ανταγωνιστή υποστηρίζεται μόνο με την πηγή 'Yahoo'.")
    competitor_ticker_input = None 
    
    file_types: List[str] = []
    if source_type == "CSV": file_types = ["csv"]
    elif source_type == "Excel": file_types = ["xlsx", "xls"]
    elif source_type == "PDF": file_types = ["pdf"]

    uploaded_file = st.sidebar.file_uploader(
        f"Ανέβασε το αρχείο σου ({source_type})", 
        type=file_types,
        key="file_uploader",
        on_change=reset_analysis_state # v1.22: ΝΕΟ
    )

elif source_type == "Yahoo":
    raw_input = st.sidebar.text_input(
        "Ticker ή Όνομα Κύριας Εταιρείας:", 
        "Microsoft", 
        key="ticker_input",
        on_change=reset_analysis_state # v1.22: ΝΕΟ
    )
        
    competitor_ticker_input = st.sidebar.text_input(
        "Ticker Ανταγωνιστή (Προαιρετικά):", 
        key="competitor_ticker",
        on_change=reset_analysis_state # v1.22: ΝΕΟ
    )

# === v1.18: ΦΙΛΤΡΑ ΕΤΩΝ ===
st.sidebar.markdown("---")
st.sidebar.subheader("Επιλογή Χρονικού Διαστήματος")
current_year = datetime.datetime.now().year
start_year = st.sidebar.number_input("Από (Έτος):", 2018, current_year - 1, value=current_year-5, key="start_year", on_change=reset_analysis_state)
end_year = st.sidebar.number_input("Έως (Έτος):", 2019, current_year + 5, value=current_year, key="end_year", on_change=reset_analysis_state)

if start_year > end_year:
    st.sidebar.error("Το 'Από' δεν μπορεί να είναι μετά το 'Έως'.")
    st.stop()
# === === === === === === === === === ===

# --- v1.22: ΝΕΑ ΛΟΓΙΚΗ ΚΟΥΜΠΙΟΥ & STATE ---
analyze_button_pressed = False
inputs_are_valid = (source_type == "Yahoo" and raw_input) or (source_type in ["CSV", "Excel", "PDF"] and uploaded_file)

if inputs_are_valid:
    if st.sidebar.button("🚀 Έναρξη Ανάλυσης", key="analyze_main"):
        # 1. Καθάρισε τα παλιά αποτελέσματα
        st.session_state.analysis_results = None 
        # 2. Αποθήκευσε τις *νέες* ρυθμίσεις
        st.session_state.analysis_inputs = {
            "source_type": source_type,
            "source_name": uploaded_file.name if uploaded_file else raw_input,
            "raw_input": raw_input,
            "uploaded_file_bytes": uploaded_file.getvalue() if uploaded_file else None,
            "uploaded_file_name": uploaded_file.name if uploaded_file else None,
            "competitor_ticker_input": competitor_ticker_input,
            "start_year": start_year,
            "end_year": end_year
        }
        analyze_button_pressed = True # Σήμανε ότι ΜΟΛΙΣ πατήθηκε
else:
    # Αν δεν υπάρχουν είσοδοι, κάνουμε reset
    st.session_state.analysis_results = None
    st.session_state.analysis_inputs = {}

# === 2. Κεντρική Σελίδα - Τα Αποτελέσματα ===
st.title("📊 Financial Analysis Dashboard (v1.25)") # <--- Νέα έκδοση

# v1.22: Ελέγχουμε αν υπάρχουν είτε νέες ρυθμίσεις είτε παλιά αποτελέσματα
if st.session_state.analysis_inputs:
    
    # === v1.22: Φόρτωση ρυθμίσεων από τη "Μνήμη" ===
    inputs = st.session_state.analysis_inputs
    source_type = inputs["source_type"]
    source_name = inputs["source_name"]
    start_year = inputs["start_year"]
    end_year = inputs["end_year"]
    main_ticker = "" # Αρχικοποίηση

    st.markdown(f"Ανάλυση για: **{source_name}** (Πηγή: {source_type})")

    # === v1.22: Έλεγχος αν τα αποτελέσματα είναι ήδη στη "Μνήμη" ===
    if st.session_state.analysis_results and not analyze_button_pressed:
        # --- ΑΝ ΕΙΝΑΙ ΣΤΗ ΜΝΗΜΗ: ΑΠΛΑ ΦΟΡΤΩΣΕ ΤΑ (ΓΡΗΓΟΡΟ) ---
        st.info("Φόρτωση αποτελεσμάτων από τη μνήμη...")
        results = st.session_state.analysis_results
        
        info_df_main = results["info_df_main"]
        company_df_main_to_analyze = results["company_df_main_to_analyze"]
        result_categories_main = results["result_categories_main"]
        
        info_df_comp = results.get("info_df_comp")
        company_df_comp_to_analyze = results.get("company_df_comp_to_analyze")
        result_categories_comp = results.get("result_categories_comp", {})
        
        main_ticker = results.get("main_ticker", "Κύρια")
        competitor_ticker = results.get("competitor_ticker", "Ανταγων.")
        
        debug_tables_main = results.get("debug_tables_main", {})
        debug_tables_comp = results.get("debug_tables_comp", {})
        
        st.success("Έγινε επαναφόρτωση της ανάλυσης!")

    else:
        # --- ΑΝ ΔΕΝ ΕΙΝΑΙ ΣΤΗ ΜΝΗΜΗ: ΚΑΝΕ ΤΗΝ ΑΝΑΛΥΣΗ (ΑΡΓΟ) ---
        
        # Αρχικοποίηση μεταβλητών
        company_df_main: Optional[pd.DataFrame] = None
        info_df_main: Optional[pd.DataFrame] = None
        industry_main: str = "General"
        debug_tables_main: Dict[str, Any] = {}
        
        company_df_comp: Optional[pd.DataFrame] = None
        info_df_comp: Optional[pd.DataFrame] = None
        debug_tables_comp: Dict[str, Any] = {}
        competitor_ticker: str = ""

        if source_type == "Yahoo":
            raw_input = inputs["raw_input"]
            competitor_ticker_input = inputs["competitor_ticker_input"]
            
            with st.spinner(f"Αναζήτηση για '{raw_input}'..."):
                ticker = resolve_to_ticker(raw_input, source_type=source_type.lower())
            if ticker is None:
                st.error(f"Δεν βρέθηκε έγκυρο Ticker για το '{raw_input}'. Δοκίμασε ξανά.")
                st.session_state.analysis_inputs = {} # Reset
                st.stop()
            main_ticker = ticker 
            st.success(f"Βρέθηκε το Κύριο Ticker: **{ticker}**")
            
            with st.spinner(f"Λήψη δεδομένων για {ticker}..."):
                info_df_main, industry_main = load_company_info(ticker)
                raw_data_list = get_company_df(ticker, source_type=source_type.lower(), period="max")
                
                if not raw_data_list:
                     st.error(f"Δεν βρέθηκαν δεδομένα από το Yahoo Finance για τον {ticker}.")
                     st.session_state.analysis_inputs = {} # Reset
                     st.stop()
                
                st.info("...Μεταφράζεται ο Πίνακας 'Yahoo' (Κύρια Εταιρεία)...")
                raw_table_main = raw_data_list[0]["table"]
                company_df_main = normalize_dataframe(raw_table_main, source_type="yahoo")
                debug_tables_main = {"Yahoo Finance Data (Raw)": raw_table_main, "Yahoo Finance Data (Normalized)": company_df_main}

            if competitor_ticker_input:
                with st.spinner(f"Αναζήτηση για Ανταγωνιστή '{competitor_ticker_input}'..."):
                    competitor_ticker = resolve_to_ticker(competitor_ticker_input, source_type=source_type.lower())
                
                if competitor_ticker is None:
                    st.error(f"Δεν βρέθηκε έγκυρο Ticker για τον Ανταγωνιστή '{competitor_ticker_input}'.")
                    st.session_state.analysis_inputs = {} # Reset
                    st.stop()
                st.success(f"Βρέθηκε το Ticker Ανταγωνιστή: **{competitor_ticker}**")

                with st.spinner(f"Λήψη δεδομένων για {competitor_ticker}..."):
                    info_df_comp, _ = load_company_info(competitor_ticker) 
                    raw_data_list_comp = get_company_df(competitor_ticker, source_type=source_type.lower(), period="max")
                    
                    if not raw_data_list_comp:
                        st.error(f"Δεν βρέθηκαν δεδομένα από το Yahoo Finance για τον {competitor_ticker}.")
                        st.session_state.analysis_inputs = {} # Reset
                        st.stop()
                    
                    st.info("...Μεταφράζεται ο Πίνακας 'Yahoo' (Ανταγωνιστής)...")
                    raw_table_comp = raw_data_list_comp[0]["table"]
                    company_df_comp = normalize_dataframe(raw_table_comp, source_type="yahoo")
                    debug_tables_comp = {"Competitor Data (Raw)": raw_table_comp, "Competitor Data (Normalized)": company_df_comp}

        elif source_type in ["CSV", "Excel", "PDF"] and inputs["uploaded_file_bytes"] is not None:
            st.success(f"Φορτώθηκε το αρχείο: **{source_name}**")
            main_ticker = "File" 
            
            with st.spinner(f"Επεξεργασία αρχείου '{source_name}'... (Αυτό μπορεί να πάρει 1-2 λεπτά για μεγάλα PDF)"):
                
                temp_dir = "temp"
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                
                try:
                    normalized_name = unicodedata.normalize('NFKD', inputs["uploaded_file_name"]).encode('ascii', 'ignore').decode('ascii')
                    if not normalized_name or normalized_name.isspace():
                        normalized_name = "uploaded_file.tmp"
                except Exception:
                    normalized_name = "uploaded_file.tmp"
                    
                temp_file_path = os.path.join(temp_dir, normalized_name)
                
                with open(temp_file_path, "wb") as f:
                    f.write(inputs["uploaded_file_bytes"])
                
                file_ext = source_type.lower()
                if file_ext == "excel":
                    try:
                        import openpyxl
                    except ImportError:
                        st.error("Η βιβλιοθήκη 'openpyxl' λείπει. Τρέξε 'pip install openpyxl' στο terminal σου για να υποστηρίξεις αρχεία Excel.")
                        st.session_state.analysis_inputs = {} # Reset
                        st.stop()
                
                raw_data_list = get_company_df(temp_file_path, source_type=file_ext)
                
                if not raw_data_list or len(raw_data_list) == 0:
                    st.error(f"Δεν βρέθηκαν δεδομένα στο {file_ext} αρχείο.")
                    st.session_state.analysis_inputs = {} # Reset
                    st.stop()
                
                debug_tables_main = {"Source Type": file_ext}
                
                if file_ext == "pdf":
                    company_df_main, debug_pdf_tables_update = _find_and_merge_pdf_tables(raw_data_list)
                    debug_tables_main.update(debug_pdf_tables_update)
                else:
                    st.info(f"...Μεταφράζεται ο Πίνακας '{file_ext}'...")
                    raw_table_for_debug = raw_data_list[0]["table"]
                    company_df_main = normalize_dataframe(raw_table_for_debug, source_type=file_ext)
                    debug_tables_main.update({"File Data (Raw)": raw_table_for_debug, f"File Data ({file_ext}) (Normalized)": company_df_main})

            industry_main = "General" 
            # === v1.23 FIX: Προσθήκη "Χώρας" και για τα αρχεία ===
            info_df_main = pd.DataFrame([{"Όνομα": source_name, "Κλάδος": industry_main, "Χώρα": "N/A (from file)", "Σημείωση": "Ανάλυση από τοπικό αρχείο"}])

        # === === === === === === === ===
        # === ΒΗΜΑ Β: ΕΛΕΓΧΟΣ & ΦΙΛΤΡΑΡΙΣΜΑ ===
        # === === === === === === === ===
                
        if company_df_main is None or company_df_main.empty:
            st.error(f"Δεν βρέθηκαν ή δεν μπόρεσαν να φορτωθούν οικονομικά δεδομένα για την ΚΥΡΙΑ εταιρεία.")
            st.session_state.analysis_inputs = {} # Reset
            st.stop()
            
        st.success(f"Επιτυχής λήψη και κανονικοποίηση δεδομένων!")

        # === v1.18: ΦΙΛΤΡΑΡΙΣΜΑ ΧΡΟΝΙΚΟΥ ΔΙΑΣΤΗΜΑΤΟΣ ===
        company_df_main_to_analyze = pd.DataFrame()
        company_df_comp_to_analyze = pd.DataFrame()

        if 'Year' in company_df_main.columns:
            try:
                company_df_main['Year'] = pd.to_numeric(company_df_main['Year'], errors='coerce').fillna(0).astype(int)
                original_rows = len(company_df_main)
                company_df_main_filtered = company_df_main[
                    (company_df_main['Year'] >= start_year) & 
                    (company_df_main['Year'] <= end_year)
                ].copy()
                
                st.info(f"Φίλτρο Ετών ({main_ticker}): {start_year} - {end_year}. (Βρέθηκαν {len(company_df_main_filtered)} από {original_rows} εγγραφές).")

                if company_df_main_filtered.empty:
                    st.error("Δεν βρέθηκαν δεδομένα για την ΚΥΡΙΑ εταιρεία στο συγκεκριμένο χρονικό διάστημα.")
                    st.session_state.analysis_inputs = {} # Reset
                    st.stop()
                
                company_df_main_to_analyze = company_df_main_filtered
                    
            except Exception as e:
                st.warning(f"Αποτυχία φιλτραρίσματος ετών (Κύρια Εταιρεία): {e}")
                company_df_main_to_analyze = company_df_main
        else:
            st.warning("Δεν βρέθηκε στήλη 'Year' για φιλτράρισμα (Κύρια Εταιρεία).")
            company_df_main_to_analyze = company_df_main

        if company_df_comp is not None and 'Year' in company_df_comp.columns:
            try:
                company_df_comp['Year'] = pd.to_numeric(company_df_comp['Year'], errors='coerce').fillna(0).astype(int)
                original_rows_comp = len(company_df_comp)
                company_df_comp_filtered = company_df_comp[
                    (company_df_comp['Year'] >= start_year) & 
                    (company_df_comp['Year'] <= end_year)
                ].copy()
                
                st.info(f"Φίλτρο Ετών ({competitor_ticker}): {start_year} - {end_year}. (Βρέθηκαν {len(company_df_comp_filtered)} από {original_rows_comp} εγγραφές).")

                if company_df_comp_filtered.empty:
                    st.warning(f"Δεν βρέθηκαν δεδομένα για τον ΑΝΤΑΓΩΝΙΣΤΗ στο συγκεκριμένο χρονικό διάστημα. Η σύγκριση θα είναι ελλιπής.")
                    company_df_comp_to_analyze = pd.DataFrame() 
                else:
                    company_df_comp_to_analyze = company_df_comp_filtered
                    
            except Exception as e:
                st.warning(f"Αποτυχία φιλτραρίσματος ετών (Ανταγωνιστής): {e}")
                company_df_comp_to_analyze = company_df_comp
        
        # === === === === === === === ===
        # --- Βήμα Γ: Υπολογισμός Δεικτών ---
        # === === === === === === === ===
        
        with st.spinner("Υπολογισμός δεικτών (Κύρια Εταιρεία)..."):
            result_main = calculate_financial_ratios(company_df_main_to_analyze, sector=industry_main)
            result_categories_main = result_main.get("categories", {})

        result_categories_comp = {}
        if competitor_ticker and not company_df_comp_to_analyze.empty:
            with st.spinner(f"Υπολογισμός δεικτών ({competitor_ticker})..."):
                result_comp = calculate_financial_ratios(company_df_comp_to_analyze, sector="") 
                result_categories_comp = result_comp.get("categories", {})
        
        # === v1.22: ΑΠΟΘΗΚΕΥΣΗ ΟΛΩΝ ΤΩΝ ΑΠΟΤΕΛΕΣΜΑΤΩΝ ===
        st.session_state.analysis_results = {
            "info_df_main": info_df_main,
            "company_df_main_to_analyze": company_df_main_to_analyze,
            "result_categories_main": result_categories_main,
            "info_df_comp": info_df_comp,
            "company_df_comp_to_analyze": company_df_comp_to_analyze,
            "result_categories_comp": result_categories_comp,
            "main_ticker": main_ticker,
            "competitor_ticker": competitor_ticker,
            "debug_tables_main": debug_tables_main,
            "debug_tables_comp": debug_tables_comp
        }
    
    # === === === === === === === === === === ===
    # === 3. Παρουσίαση Αποτελεσμάτων (ΤΡΕΧΕΙ ΠΑΝΤΑ) ===
    # === === === === === === === === === === ===
    
    results = st.session_state.analysis_results
    info_df_main = results["info_df_main"]
    company_df_main_to_analyze = results["company_df_main_to_analyze"]
    result_categories_main = results["result_categories_main"]
    info_df_comp = results.get("info_df_comp")
    company_df_comp_to_analyze = results.get("company_df_comp_to_analyze")
    result_categories_comp = results.get("result_categories_comp", {})
    main_ticker = results.get("main_ticker", "Κύρια")
    competitor_ticker = results.get("competitor_ticker", "Ανταγων.")
    debug_tables_main = results.get("debug_tables_main", {})
    debug_tables_comp = results.get("debug_tables_comp", {})

    st.header(f"Επισκόπηση: {info_df_main['Όνομα'].iloc[0]}")
    st.dataframe(info_df_main, width=1200) 
    
    if info_df_comp is not None:
        st.header(f"Επισκόπηση Ανταγωνιστή: {info_df_comp['Όνομα'].iloc[0]}")
        st.dataframe(info_df_comp, width=1200) 

    with st.spinner("Δημιουργία αναφοράς PDF..."):
        pdf_data_raw = create_pdf_report(info_df_main, result_categories_main, company_df_main_to_analyze)
        pdf_bytes_fixed = bytes(pdf_data_raw)
        
        st.download_button(
            label="📥 Λήψη Αναφοράς σε PDF (Κύρια Εταιρεία)",
            data=pdf_bytes_fixed, 
            file_name=f"Report_{source_name}_{start_year}-{end_year}.pdf",
            mime="application/pdf",
            key="download_pdf_main"
        )

    st.header(f"Συγκριτική Ανάλυση Δεικτών (Για {start_year} - {end_year})")
    
    if not result_categories_main:
        st.warning("Δεν υπολογίστηκαν δείκτες για την Κύρια Εταιρεία.")
        
    else:
        tab_names = list(result_categories_main.keys())
        tabs = st.tabs(tab_names)
        
        for i, tab_name in enumerate(tab_names):
            with tabs[i]:
                st.subheader(f"Σύγκριση: {tab_name}")
                
                df_main = result_categories_main[tab_name]
                df_comp = result_categories_comp.get(tab_name) 
                
                if df_comp is None or df_comp.empty:
                    st.dataframe(df_main.set_index('Year'), width=1200)
                    valid_cols = [col for col in df_main.columns if col not in ['Year', 'Date'] and not df_main[col].isnull().all()]
                    
                    if valid_cols:
                        st.line_chart(df_main.set_index('Year')[valid_cols])
                    else:
                        st.info(f"Δεν υπάρχουν διαθέσιμα δεδομένα για τη δημιουργία γραφήματος για {tab_name}.")

                else:
                    try:
                        df_main_melt = df_main.melt(id_vars=['Year'], var_name='Ratio', value_name=main_ticker)
                        df_comp_melt = df_comp.melt(id_vars=['Year'], var_name='Ratio', value_name=competitor_ticker)
                        
                        df_merged = pd.merge(df_main_melt, df_comp_melt, on=['Year', 'Ratio'], how='outer')
                        df_merged = df_merged.sort_values(by=['Ratio', 'Year'], ascending=[True, False])
                        
                        st.dataframe(df_merged.set_index('Ratio'), width=1200)
                    except Exception as e:
                        st.error(f"Αποτυχία δημιουργίας συγκριτικού πίνακα: {e}")
                        st.dataframe(df_main.set_index('Year'), width=1200) 
                    
                    all_ratios = df_main.columns.drop('Year')
                    for ratio in all_ratios:
                        st.subheader(f"Εξέλιξη: {ratio}")
                        
                        df_main_chart = df_main[['Year', ratio]].rename(columns={ratio: main_ticker})
                        df_comp_chart = pd.DataFrame()
                        
                        if ratio in df_comp.columns:
                            df_comp_chart = df_comp[['Year', ratio]].rename(columns={ratio: competitor_ticker})
                        
                        if not df_comp_chart.empty:
                            chart_df = pd.merge(df_main_chart, df_comp_chart, on='Year', how='outer').set_index('Year')
                        else:
                            chart_df = df_main_chart.set_index('Year')
                        
                        st.line_chart(chart_df)

    st.success("✅ Η ανάλυση ολοκληρώθηκε!")
    
    with st.expander("Δες τον 'Χρυσό' Πίνακα (Κύρια Εταιρεία - ΦΙΛΤΡΑΡΙΣΜΕΝΑ)"):
        st.dataframe(company_df_main_to_analyze)
    if competitor_ticker:
        with st.expander(f"Δες τον 'Χρυσό' Πίνακα ({competitor_ticker} - ΦΙΛΤΡΑΡΙΣΜΕΝΑ)"):
            st.dataframe(company_df_comp_to_analyze)

    with st.expander("Δες την Αναφορά Εντοπισμού (Debug Report - Κύρια Εταιρεία)"):
        if debug_tables_main:
            for title, df in debug_tables_main.items():
                st.caption(f"Πίνακας: {title}")
                st.dataframe(df)
        else:
            st.info("Δεν φορτώθηκαν δεδομένα.")
            
    if debug_tables_comp:
         with st.expander(f"Δες την Αναφορά Εντοπισμού (Debug Report - {competitor_ticker})"):
            for title, df in debug_tables_comp.items():
                st.caption(f"Πίνακας: {title}")
                st.dataframe(df)

else:
    st.info("Επίλεξε πηγή και εταιρεία από την πλαϊνή μπάρα για να ξεκινήσεις.")