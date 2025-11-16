# app.py (v2.3 - Προσθήκη Μέσου Όρου Κλάδου (Industry Average))
import streamlit as st
import pandas as pd
import os
import sys
import unicodedata 
import datetime 
import plotly.graph_objects as go 
from typing import Tuple, List, Dict, Any, Optional

# === v2.0: ΝΕΑ ΕΙΣΑΓΩΓΗ ===
from finvizfinance.quote import finvizfinance
# === === === === === === ===

# === v1.25 FIX: Η "Αλεξίσφαιρη" Διόρθωση Path ===
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)
# === === === === === === === === === ===

# === Εισαγωγή PDF Exporter ===
try:
    from modules.pdf_exporter import create_pdf_report
except ImportError:
    st.error("ΚΡΙΣΙΜΟ ΣΦΑΛΜΑ: ΔΕΝ ΒΡΕΘΗΚΕ το 'modules/pdf_exporter.py'. Βεβαιώσου ότι το αρχείο υπάρχει στον φάκελο 'modules'.")
    st.stop()
# === === === === === === === === ===

# === Εισαγωγή των "Εγκεφάλων" μας (v2.3) ===
try:
    # ΤΩΡΑ ΕΙΣΑΓΟΥΜΕ ΚΑΙ ΤΗ ΝΕΑ ΣΥΝΑΡΤΗΣΗ
    from test_loader import resolve_to_ticker, load_company_info, get_company_df, normalize_dataframe, get_industry_tickers 
    from modules.analyzer import calculate_financial_ratios
except ImportError as e:
    st.error(f"ΚΡΙΣΙΜΟ ΣΦΑΛΜΑ: {e}")
    st.error("Βεβαιώσου ότι τα 'app.py', 'test_loader.py', και ο φάκελος 'modules' είναι στον ίδιο κατάλογο.")
    st.stop() 
# === === === === === === === === ===

# === Ρύθμιση Σελίδας ===
st.set_page_config(
    page_title="Financial Analysis Tool v2.3", # <--- Νέα έκδοση
    page_icon="📊",
    layout="wide" 
)

# === v2.0: Αρχικοποίηση "Μνήμης" (Session State) ===
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'analysis_inputs' not in st.session_state:
    st.session_state.analysis_inputs = {}
if 'company_info_loaded' not in st.session_state:
    st.session_state.company_info_loaded = False
if 'company_info_data' not in st.session_state:
    st.session_state.company_info_data = {}
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
             st.warning("   > Η 'Μετάφραση' του Income απέτυχε (π.χ. δεν βρήκε χρονιές).")

            
    if not found_tables["balance"].empty:
        st.write("...Μεταφράζεται ο Πίνακας 'Balance'...")
        df = normalize_dataframe(found_tables["balance"], source_type="pdf")
        if not df.empty:
            final_dfs.append(df)
            debug_log["Balance Sheet (Normalized)"] = df
        else:
             st.warning("   > Η 'Μετάφραση' του Balance απέτυχε (π.χ. δεν βρήκε χρονιές).")

    if not found_tables["cashflow"].empty:
        st.write("...Μεταφράζεται ο Πίνακας 'CashFlow'...")
        df = normalize_dataframe(found_tables["cashflow"], source_type="pdf")
        if not df.empty:
            final_dfs.append(df)
            debug_log["Cash Flow (Normalized)"] = df
        else:
             st.warning("   > Η 'Μετάφραση' του CashFlow απέτυχε (π.χ. δεν βρήκε χρονιές).")

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
                     st.warning(f"   > Αποτυχία 'Merge': Ένας πίνακας αγνοήθηκε (έλειπε το 'Year').")
                    
    except Exception as e:
        st.error(f"Αποτυχία 'Merge': {e}")
        return pd.DataFrame(), debug_log

    final_golden_df = final_golden_df.loc[:, ~final_golden_df.columns.duplicated()]
    
    if 'Year' in final_golden_df.columns:
        final_golden_df['Year'] = pd.to_numeric(final_golden_df['Year'], errors='coerce').fillna(0).astype(int)

    return final_golden_df, debug_log
# === === === === === === === === === ===


# === 1. Η Πλαϊνή Μπάρα (Sidebar) - Τα Εργαλεία Εισόδου ===
st.sidebar.title("📊 Εργαλεία Ανάλυσης (v2.3)") # <--- Νέα έκδοση
st.sidebar.markdown("Διάλεξε την πηγή και την εταιρεία σου.")

def reset_analysis_state():
    """v2.0: Κάνει reset τα πάντα όταν αλλάζει η πηγή."""
    st.session_state.analysis_results = None
    st.session_state.analysis_inputs = {}
    st.session_state.company_info_loaded = False
    st.session_state.company_info_data = {}

source_options = ["Yahoo", "CSV", "Excel", "PDF"] 
source_type = st.sidebar.selectbox(
    "Επίλεξε Πηγή Δεδομένων:",
    source_options,
    key="source_type_select",
    on_change=reset_analysis_state
)

# Αρχικοποίηση μεταβλητών
raw_input: Optional[str] = None 
uploaded_file: Optional[Any] = None
selected_peers: List[str] = []

# --- Λογική ανάλογα με την Πηγή ---
if source_type in ["CSV", "Excel", "PDF"]: 
    st.sidebar.warning("Η αυτόματη εύρεση ανταγωνιστών υποστηρίζεται μόνο με την πηγή 'Yahoo'.")
    
    file_types: List[str] = []
    if source_type == "CSV": file_types = ["csv"]
    elif source_type == "Excel": file_types = ["xlsx", "xls"]
    elif source_type == "PDF": file_types = ["pdf"]

    uploaded_file = st.sidebar.file_uploader(
        f"Ανέβασε το αρχείο σου ({source_type})", 
        type=file_types,
        key="file_uploader",
        on_change=reset_analysis_state
    )
    if uploaded_file:
        st.session_state.company_info_loaded = True
        st.session_state.company_info_data = {
            "ticker": "File",
            "source_name": uploaded_file.name,
            "industry": "General",
            "country": "N/A (from file)",
            "info_df": pd.DataFrame([{"Όνομα": uploaded_file.name, "Κλάδος": "General", "Χώρα": "N/A (from file)", "Σημείωση": "Ανάλυση από τοπικό αρχείο"}]),
            "peer_list": [] 
        }


elif source_type == "Yahoo":
    raw_input = st.sidebar.text_input(
        "Ticker ή Όνομα Κύριας Εταιρείας:", 
        "MSFT", 
        key="ticker_input",
        on_change=reset_analysis_state
    )
    
    if st.sidebar.button("Εύρεση Πληροφοριών & Ανταγωνιστών", key="find_peers"):
        if raw_input:
            with st.spinner(f"Αναζήτηση για '{raw_input}'..."):
                ticker = resolve_to_ticker(raw_input, source_type="yahoo")
            if ticker:
                st.success(f"Βρέθηκε το Ticker: **{ticker}**")
                with st.spinner(f"Λήψη Πληροφοριών & Ανταγωνιστών για {ticker}..."):
                    try:
                        info_df, industry = load_company_info(ticker)
                        country = info_df['Χώρα'].iloc[0]
                        
                        stock_finviz = finvizfinance(ticker)
                        peer_list = stock_finviz.ticker_peer()
                        
                        st.session_state.company_info_loaded = True
                        st.session_state.company_info_data = {
                            "ticker": ticker,
                            "source_name": info_df['Όνομα'].iloc[0] or ticker,
                            "info_df": info_df,
                            "industry": industry,
                            "country": country,
                            "peer_list": peer_list
                        }
                        
                    except Exception as e:
                        st.error(f"Αποτυχία λήψης ανταγωνιστών (Ίσως το Finviz απέκλεισε την IP): {e}")
                        info_df, industry = load_company_info(ticker)
                        country = info_df['Χώρα'].iloc[0]
                        st.session_state.company_info_loaded = True
                        st.session_state.company_info_data = {
                            "ticker": ticker,
                            "source_name": info_df['Όνομα'].iloc[0] or ticker,
                            "info_df": info_df,
                            "industry": industry,
                            "country": country,
                            "peer_list": [] # Άδεια λίστα
                        }
            else:
                st.error(f"Δεν βρέθηκε έγκυρο Ticker για το '{raw_input}'.")
        else:
            st.warning("Παρακαλώ εισάγετε ένα Ticker ή Όνομα.")


# === v2.0: ΝΕΑ ΛΟΓΙΚΗ (Εμφανίζεται *μετά* την εύρεση) ===
if st.session_state.company_info_loaded:
    
    peers_info = st.session_state.company_info_data
    
    st.sidebar.success(f"Εταιρεία: {peers_info['ticker']} ({peers_info['industry']})")
    st.sidebar.caption(f"Χώρα: {peers_info.get('country', 'N/A')}")
    
    if peers_info.get("peer_list"):
        st.sidebar.subheader("Επιλογή Ανταγωνιστών")
        selected_peers = st.sidebar.multiselect(
            "Επίλεξε 0 ή περισσότερους για σύγκριση:",
            options=peers_info["peer_list"],
            key="peers_multiselect"
        )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Επιλογή Χρονικού Διαστήματος")
    current_year = datetime.datetime.now().year
    
    start_year = st.sidebar.number_input("Από (Έτος):", 2018, current_year - 1, value=current_year-5, key="start_year")
    end_year = st.sidebar.number_input("Έως (Έτος):", 2019, current_year + 5, value=current_year, key="end_year")

    if start_year > end_year:
        st.sidebar.error("Το 'Από' δεν μπορεί να είναι μετά το 'Έως'.")
        st.stop()

    if st.sidebar.button("🚀 Έναρξη Ανάλυσης", key="analyze_main"):
        st.session_state.analysis_results = None 
        st.session_state.analysis_inputs = {
            "source_type": source_type,
            "source_name": peers_info["source_name"],
            "main_ticker": peers_info["ticker"],
            "info_df_main": peers_info["info_df"],
            "industry_main": peers_info["industry"],
            "selected_peers": selected_peers, 
            "uploaded_file_bytes": uploaded_file.getvalue() if uploaded_file else None,
            "uploaded_file_name": uploaded_file.name if uploaded_file else None,
            "start_year": start_year,
            "end_year": end_year
        }
        analyze_button_pressed = True 
    else:
        analyze_button_pressed = False

else:
    analyze_button_pressed = False
# === === === === === === === === === ===


# === 2. Κεντρική Σελίδα - Τα Αποτελέσματα ===
st.title("📊 Financial Analysis Dashboard (v2.3)") # <--- Νέα έκδοση

if st.session_state.analysis_inputs:
    
    inputs = st.session_state.analysis_inputs
    source_type = inputs["source_type"]
    source_name = inputs["source_name"]
    start_year = inputs["start_year"]
    end_year = inputs["end_year"]
    main_ticker = inputs["main_ticker"] 

    st.markdown(f"Ανάλυση για: **{source_name}** (Πηγή: {source_type})")

    if st.session_state.analysis_results and not analyze_button_pressed:
        st.info("Φόρτωση αποτελεσμάτων από τη μνήμη...")
        results = st.session_state.analysis_results
    
    else:
        # --- ΑΝ ΔΕΝ ΕΙΝΑΙ ΣΤΗ ΜΝΗΜΗ: ΚΑΝΕ ΤΗΝ ΑΝΑΛΥΣΗ (ΑΡΓΟ) ---
        
        all_info_dfs = {}
        all_company_dfs_normalized = {}
        all_debug_tables = {}
        
        # NEW: Ψευδώνυμο για τον μέσο όρο
        INDUSTRY_AVG_TICKER = "INDUSTRY_AVG" 
        industry_ratios_to_save = {}
        sector_main = "General" # Αρχικοποίηση
        
        # === [ΝΕΟ ΒΗΜΑ Γ.1] Λήψη & Υπολογισμός Μέσου Όρου Κλάδου ===
        if source_type == "Yahoo":
            sector_main = inputs["info_df_main"]['Κλάδος'].iloc[0] 
            
            with st.spinner(f"Λήψη Tickers για τον κλάδο '{sector_main}'..."):
                # Χρησιμοποιούμε τη νέα συνάρτηση για να βρούμε ΟΛΟΥΣ τους πιθανούς tickers (έως 50)
                all_industry_tickers = get_industry_tickers(industry_name=sector_main, sector_name=sector_main)
            
            if all_industry_tickers:
                st.info(f"Βρέθηκαν {len(all_industry_tickers)} εταιρείες στον κλάδο. Υπολογισμός Μέσου Όρου...")
                
                all_industry_ratios = [] 
                
                # --- Κύκλος Ανάλυσης Κλάδου ---
                for ind_ticker in all_industry_tickers:
                    try:
                        # Λήψη δεδομένων
                        raw_data_list_ind = get_company_df(ind_ticker, source_type="yahoo", period="max")
                        if not raw_data_list_ind: continue
                        raw_table_ind = raw_data_list_ind[0]["table"]
                        company_df_ind = normalize_dataframe(raw_table_ind, source_type="yahoo")
                        
                        # Φιλτράρισμα ετών 
                        if 'Year' in company_df_ind.columns:
                            company_df_ind['Year'] = pd.to_numeric(company_df_ind['Year'], errors='coerce').fillna(0).astype(int)
                            company_df_ind = company_df_ind[
                                (company_df_ind['Year'] >= start_year) & 
                                (company_df_ind['Year'] <= end_year)
                            ].copy()
                        
                        # Υπολογισμός Δεικτών
                        if not company_df_ind.empty:
                            # Εδώ καλούμε την calculate_financial_ratios από το analyzer
                            ind_result = calculate_financial_ratios(company_df_ind, sector=sector_main)
                            if ind_result.get("categories"):
                                all_industry_ratios.append(ind_result["categories"])
                        
                    except Exception:
                        # Παραλείπουμε τα σφάλματα από μεμονωμένες εταιρείες
                        continue 
                
                # --- Υπολογισμός Μέσων Όρων ---
                if all_industry_ratios:
                    st.info(f"Επιτυχής ανάλυση {len(all_industry_ratios)} εταιρειών του κλάδου για υπολογισμό μέσου όρου.")
                    
                    # Υπολογίζουμε τον μέσο όρο (mean) για κάθε συνδυασμό Έτους/Δείκτη
                    sample_categories = all_industry_ratios[0].keys()
                    
                    for category in sample_categories:
                        all_dfs_for_category = []
                        for ratios_dict in all_industry_ratios:
                            if category in ratios_dict:
                                # Flatten DataFrame (Year, Ratio, Value)
                                df = ratios_dict[category].set_index('Year').stack().reset_index()
                                df.columns = ['Year', 'Ratio', 'Value']
                                all_dfs_for_category.append(df)
                        
                        if all_dfs_for_category:
                            merged_category_df = pd.concat(all_dfs_for_category)
                            
                            # Υπολογίζουμε τον μέσο όρο (mean) για κάθε συνδυασμό Έτους/Δείκτη
                            avg_df = merged_category_df.groupby(['Year', 'Ratio'])['Value'].mean().reset_index()
                            
                            # Ξαναγυρίζουμε στον αρχικό πίνακα (Year, Ratio1, Ratio2, ...)
                            avg_df_pivot = avg_df.pivot(index='Year', columns='Ratio', values='Value').reset_index()
                            
                            industry_ratios_to_save[category] = avg_df_pivot
                    
                    st.success(f"✅ Υπολογίστηκε ο Μέσος Όρος Κλάδου.")
        
        # === ΒΗΜΑ Α: ΦΟΡΤΩΣΗ ΚΥΡΙΑΣ ΕΤΑΙΡΕΙΑΣ ===
        all_info_dfs[main_ticker] = inputs["info_df_main"]
        industry_main = inputs["industry_main"]
        
        if source_type == "Yahoo":
            with st.spinner(f"Λήψη δεδομένων για {main_ticker}..."):
                raw_data_list = get_company_df(main_ticker, source_type=source_type.lower(), period="max")
                if not raw_data_list:
                    st.error(f"Δεν βρέθηκαν δεδομένα από το Yahoo Finance για τον {main_ticker}.")
                    st.session_state.analysis_inputs = {}
                    st.stop()
                
                st.info(f"...Μεταφράζεται ο Πίνακας 'Yahoo' ({main_ticker})...")
                raw_table_main = raw_data_list[0]["table"]
                company_df_main = normalize_dataframe(raw_table_main, source_type="yahoo")
                
                all_company_dfs_normalized[main_ticker] = company_df_main
                all_debug_tables[main_ticker] = {"Yahoo Finance Data (Raw)": raw_table_main, "Yahoo Finance Data (Normalized)": company_df_main}

        elif source_type in ["CSV", "Excel", "PDF"] and inputs["uploaded_file_bytes"] is not None:
            with st.spinner(f"Επεξεργασία αρχείου '{source_name}'..."):
                
                temp_dir = "temp"
                if not os.path.exists(temp_dir): os.makedirs(temp_dir)
                
                try:
                    normalized_name = unicodedata.normalize('NFKD', inputs["uploaded_file_name"]).encode('ascii', 'ignore').decode('ascii')
                    if not normalized_name or normalized_name.isspace(): normalized_name = "uploaded_file.tmp"
                except Exception:
                    normalized_name = "uploaded_file.tmp"
                    
                temp_file_path = os.path.join(temp_dir, normalized_name)
                
                with open(temp_file_path, "wb") as f: f.write(inputs["uploaded_file_bytes"])
                
                file_ext = source_type.lower()
                raw_data_list = get_company_df(temp_file_path, source_type=file_ext)
                
                if not raw_data_list:
                    st.error(f"Δεν βρέθηκαν δεδομένα στο {file_ext} αρχείο.")
                    st.session_state.analysis_inputs = {}
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

                all_company_dfs_normalized[main_ticker] = company_df_main
                all_debug_tables[main_ticker] = debug_tables_main

        # === ΒΗΜΑ Β: ΦΟΡΤΩΣΗ ΑΝΤΑΓΩΝΙΣΤΩΝ (v2.0) ===
        selected_peers = inputs["selected_peers"]
        for peer_ticker in selected_peers:
            with st.spinner(f"Λήψη δεδομένων για ανταγωνιστή: {peer_ticker}..."):
                try:
                    info_df_peer, _ = load_company_info(peer_ticker)
                    all_info_dfs[peer_ticker] = info_df_peer
                    
                    raw_data_list_peer = get_company_df(peer_ticker, source_type="yahoo", period="max")
                    if not raw_data_list_peer:
                        st.warning(f"Δεν βρέθηκαν δεδομένα για τον {peer_ticker}. Παράλειψη.")
                        continue
                    
                    raw_table_peer = raw_data_list_peer[0]["table"]
                    company_df_peer = normalize_dataframe(raw_table_peer, source_type="yahoo")
                    
                    all_company_dfs_normalized[peer_ticker] = company_df_peer
                    all_debug_tables[peer_ticker] = {"Yahoo Finance Data (Raw)": raw_table_peer, "Yahoo Finance Data (Normalized)": company_df_peer}
                    
                except Exception as e:
                    st.error(f"Αποτυχία λήψης δεδομένων για {peer_ticker}: {e}")
        
        # === ΒΗΜΑ Γ.2: ΦΙΛΤΡΑΡΙΣΜΑ & ΥΠΟΛΟΓΙΣΜΟΣ ΚΥΡΙΑΣ ΕΤΑΙΡΕΙΑΣ & ΑΝΤΑΓΩΝΙΣΤΩΝ ===
        
        # Αρχικοποίηση λίστας δεικτών
        all_ratios_categories = {}
        
        # ⚠️ ΠΡΟΣΘΕΤΟΥΜΕ ΠΡΩΤΑ ΤΟΝ ΜΕΣΟ ΟΡΟ ΚΛΑΔΟΥ
        if industry_ratios_to_save:
            all_ratios_categories[INDUSTRY_AVG_TICKER] = industry_ratios_to_save
            # Πρέπει να φτιάξουμε ένα Info DataFrame για τον κλάδο, ώστε να το αναγνωρίζει ο display
            all_info_dfs[INDUSTRY_AVG_TICKER] = pd.DataFrame([{"Όνομα": f"Μέσος Όρος Κλάδου ({sector_main})", "Κλάδος": sector_main, "Χώρα": "Industry", "Σημείωση": "Αυτόματος Υπολογισμός"}])
        
        all_company_dfs_analyzed = {}
        all_tickers_to_process = [main_ticker] + selected_peers
        
        # --- Κύκλος Ανάλυσης (Main & Peers) ---
        for ticker in all_tickers_to_process:
            if ticker not in all_company_dfs_normalized or all_company_dfs_normalized[ticker].empty:
                st.warning(f"Παράλειψη ανάλυσης για {ticker}: Δεν βρέθηκαν κανονικοποιημένα δεδομένα.")
                continue

            company_df = all_company_dfs_normalized[ticker]
            
            if 'Year' in company_df.columns:
                try:
                    company_df['Year'] = pd.to_numeric(company_df['Year'], errors='coerce').fillna(0).astype(int)
                    original_rows = len(company_df)
                    company_df_filtered = company_df[
                        (company_df['Year'] >= start_year) & 
                        (company_df['Year'] <= end_year)
                    ].copy()
                    
                    st.info(f"Φίλτρο Ετών ({ticker}): {start_year} - {end_year}. (Βρέθηκαν {len(company_df_filtered)} από {original_rows} εγγραφές).")

                    if company_df_filtered.empty:
                        st.error(f"Δεν βρέθηκαν δεδομένα για {ticker} στο συγκεκριμένο χρονικό διάστημα.")
                        continue
                    
                    company_df_to_analyze = company_df_filtered
                        
                except Exception as e:
                    st.warning(f"Αποτυχία φιλτραρίσματος ετών ({ticker}): {e}")
                    company_df_to_analyze = company_df
            else:
                st.warning(f"Δεν βρέθηκε στήλη 'Year' για φιλτράρισμα ({ticker}).")
                company_df_to_analyze = company_df
            
            # --- Υπολογισμός Δεικτών ---
            with st.spinner(f"Υπολογισμός δεικτών για {ticker}..."):
                current_industry = all_info_dfs[ticker]['Κλάδος'].iloc[0] if ticker in all_info_dfs else "General"
                result = calculate_financial_ratios(company_df_to_analyze, sector=current_industry)
                
                # Αποθήκευση αποτελεσμάτων
                all_ratios_categories[ticker] = result.get("categories", {})
                all_company_dfs_analyzed[ticker] = company_df_to_analyze

        # === v1.22: ΑΠΟΘΗΚΕΥΣΗ ΟΛΩΝ ΤΩΝ ΑΠΟΤΕΛΕΣΜΑΤΩΝ ===
        st.session_state.analysis_results = {
            "all_info_dfs": all_info_dfs,
            "all_company_dfs_analyzed": all_company_dfs_analyzed,
            "all_ratios_categories": all_ratios_categories,
            "main_ticker": main_ticker,
            "selected_peers": selected_peers,
            "all_debug_tables": all_debug_tables
        }
        
        results = st.session_state.analysis_results
    
    # === === === === === === === === === === ===
    # === 3. Παρουσίαση Αποτελεσμάτων (ΤΡΕΧΕΙ ΠΑΝΤΑ) ===
    # === === === === === === === === === === ===
    
    all_info_dfs = results["all_info_dfs"]
    all_company_dfs_analyzed = results["all_company_dfs_analyzed"]
    all_ratios_categories = results["all_ratios_categories"]
    main_ticker = results["main_ticker"]
    selected_peers = results["selected_peers"]
    all_debug_tables = results["all_debug_tables"]
    
    # v2.3: Αρχικοποίηση λίστας tickers για εμφάνιση
    all_tickers_to_display = [main_ticker] + selected_peers
    
    # v2.3: Προσθήκη του INDUSTRY_AVG στη λίστα tickers αν υπάρχει
    INDUSTRY_AVG_TICKER = "INDUSTRY_AVG"
    industry_avg_available = INDUSTRY_AVG_TICKER in all_info_dfs
    
    if industry_avg_available:
        all_tickers_to_display.append(INDUSTRY_AVG_TICKER)
    
    # Εμφάνιση Επισκοπήσεων (v2.3)
    for ticker in all_tickers_to_display:
        if ticker in all_info_dfs:
            st.header(f"Επισκόπηση: {all_info_dfs[ticker]['Όνομα'].iloc[0]}")
            st.dataframe(all_info_dfs[ticker], width=1200) 

    # --- Λήψη PDF (Μόνο για την Κύρια Εταιρεία) ---
    with st.spinner("Δημιουργία αναφοράς PDF..."):
        pdf_data_raw = create_pdf_report(
            all_info_dfs[main_ticker], 
            all_ratios_categories.get(main_ticker, {}), 
            all_company_dfs_analyzed.get(main_ticker, pd.DataFrame())
        )
        pdf_bytes_fixed = bytes(pdf_data_raw)
        
        st.download_button(
            label="📥 Λήψη Αναφοράς σε PDF (Κύρια Εταιρεία)",
            data=pdf_bytes_fixed, 
            file_name=f"Report_{source_name}_{start_year}-{end_year}.pdf",
            mime="application/pdf",
            key="download_pdf_main"
        )

    # --- Συγκριτική Ανάλυση ---
    st.header(f"Συγκριτική Ανάλυση Δεικτών (Για {start_year} - {end_year})")
    
    if not all_ratios_categories.get(main_ticker):
        st.warning("Δεν υπολογίστηκαν δείκτες για την Κύρια Εταιρεία.")
        
    else:
        tab_names = list(all_ratios_categories[main_ticker].keys())
        tabs = st.tabs(tab_names)
        
        for i, tab_name in enumerate(tab_names):
            with tabs[i]:
                st.subheader(f"Σύγκριση: {tab_name}")
                
                # v2.3: Λογική για πολλές εταιρείες + INDUSTRY_AVG
                all_tickers_in_tab = [main_ticker] + selected_peers
                if industry_avg_available:
                    all_tickers_in_tab.append(INDUSTRY_AVG_TICKER)
                
                melted_dfs = []
                valid_ratios_in_tab = set() 
                
                if main_ticker in all_ratios_categories and tab_name in all_ratios_categories[main_ticker]:
                     main_df = all_ratios_categories[main_ticker][tab_name]
                     if not main_df.empty:
                          valid_ratios_in_tab.update(main_df.columns.drop('Year'))
                
                for ticker in all_tickers_in_tab:
                    if ticker in all_ratios_categories and tab_name in all_ratios_categories[ticker]:
                        df = all_ratios_categories[ticker][tab_name]
                        if not df.empty and 'Year' in df.columns:
                            melted_dfs.append(df.melt(id_vars=['Year'], var_name='Ratio', value_name=ticker))
                
                if not melted_dfs:
                    st.warning(f"Δεν βρέθηκαν δεδομένα για {tab_name}.")
                    continue

                # Ενώνουμε όλους τους πίνακες
                try:
                    df_merged = melted_dfs[0]
                    if len(melted_dfs) > 1:
                        for j in range(1, len(melted_dfs)):
                            df_merged = pd.merge(df_merged, melted_dfs[j], on=['Year', 'Ratio'], how='outer')
                    
                    df_merged = df_merged.sort_values(by=['Ratio', 'Year'], ascending=[True, False])
                    st.dataframe(df_merged.set_index('Ratio'), width=1200)
                except Exception as e:
                    st.error(f"Αποτυχία δημιουργίας συγκριτικού πίνακα: {e}")
                
                # Δημιουργία Γραφημάτων (ένα για κάθε δείκτη)
                for ratio in valid_ratios_in_tab:
                    st.subheader(f"Εξέλιξη: {ratio}")
                    
                    chart_data_list = []
                    for ticker in all_tickers_in_tab:
                        if ticker in all_ratios_categories and tab_name in all_ratios_categories[ticker]:
                            df = all_ratios_categories[ticker][tab_name]
                            if ratio in df.columns:
                                chart_data_list.append(df[['Year', ratio]].rename(columns={ratio: ticker}))
                    
                    if not chart_data_list:
                        st.info(f"Δεν βρέθηκαν δεδομένα για το γράφημα του {ratio}.")
                        continue
                        
                    chart_df = chart_data_list[0]
                    if len(chart_data_list) > 1:
                          for j in range(1, len(chart_data_list)):
                                chart_df = pd.merge(chart_df, chart_data_list[j], on='Year', how='outer')
                    
                    st.line_chart(chart_df.set_index('Year'))

    st.success("✅ Η ανάλυση ολοκληρώθηκε!")
    
    with st.expander("Δες τον 'Χρυσό' Πίνακα (Κύρια Εταιρεία - ΦΙΛΤΡΑΡΙΣΜΕΝΑ)"):
        st.dataframe(all_company_dfs_analyzed.get(main_ticker, pd.DataFrame()))
        
    for peer_ticker in selected_peers:
        with st.expander(f"Δες τον 'Χρυσό' Πίνακα ({peer_ticker} - ΦΙΛΤΡΑΡΙΣΜΕΝΑ)"):
            st.dataframe(all_company_dfs_analyzed.get(peer_ticker, pd.DataFrame()))
    
    # v2.3: Εμφάνιση Debug για τον Μέσο Όρο
    if industry_avg_available:
        with st.expander("Δες τους 'Χρυσούς' Πίνακες (Μέσος Όρος Κλάδου)"):
            avg_ratios = all_ratios_categories.get(INDUSTRY_AVG_TICKER, {})
            if not avg_ratios:
                st.info("Δεν υπολογίστηκαν δείκτες Μέσου Όρου.")
            else:
                for category, df in avg_ratios.items():
                    st.caption(f"Πίνακας: {category} (Μ.Ο.)")
                    st.dataframe(df)

    with st.expander("Δες την Αναφορά Εντοπισμού (Debug Report - Κύρια Εταιρεία)"):
        if main_ticker in all_debug_tables:
            for title, df in all_debug_tables[main_ticker].items():
                st.caption(f"Πίνακας: {title}")
                st.dataframe(df)
        else:
            st.info("Δεν φορτώθηκαν δεδομένα.")
            
    for peer_ticker in selected_peers:
         with st.expander(f"Δες την Αναφορά Εντοπισμού (Debug Report - {peer_ticker})"):
            if peer_ticker in all_debug_tables:
                for title, df in all_debug_tables[peer_ticker].items():
                    st.caption(f"Πίνακας: {title}")
                    st.dataframe(df)

else:
    st.info("Επίλεξε πηγή και εταιρεία από την πλαϊνή μπάρα για να ξεκινήσεις.")