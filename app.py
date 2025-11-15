# app.py (v1.23 - Προσθήκη "Χώρας" & Fix Συμβατότητας)
import streamlit as st
import pandas as pd
import os
import sys
import unicodedata 
import datetime 
import plotly.graph_objects as go 

from typing import Tuple, List, Dict, Any, Optional

# === Εισαγωγή PDF Exporter ===
try:
    from modules.pdf_exporter import create_pdf_report
except ImportError:
    st.error("ΔΕΝ ΒΡΕΘΗΚΕ το 'modules/pdf_exporter.py'. Βεβαιώσου ότι το δημιούργησες.")
    st.stop()
# === === === === === === === === ===

# === Εισαγωγή των "Εγκεφάλων" μας ===
try:
    from test_loader import resolve_to_ticker, load_company_info, get_company_df, normalize_dataframe
    from modules.analyzer import calculate_financial_ratios
except ImportError as e:
    st.error(f"Σφάλμα Εισαγωγής: {e}")
    st.error("Βεβαιώσου ότι τα 'app.py', 'test_loader.py', και ο φάκελος 'modules' είναι στον ίδιο κατάλογο.")
    st.stop() 

# === Ρύθμιση Σελίδας ===
st.set_page_config(
    page_title="Financial Analysis Tool v1.23", # <--- Νέα έκδοση
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
st.sidebar.title("📊 Εργαλεία Ανάλυσης (v1.23)") # <--- Νέα