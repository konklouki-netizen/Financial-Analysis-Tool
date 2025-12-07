# test_loader.py (v3.7 - Επιστροφή σε σταθερή έκδοση)
import os
import sys
import pandas as pd
import yfinance as yf
import requests
from typing import Optional, Tuple, List, Dict, Any
import re 
import io

# === === === === === === === === ===
# === v3.7: Ο ΝΕΟΣ "TURBO" ΚΙΝΗΤΗΡΑΣ ===
import fitz  # PyMuPDF
# === === === === === === === === ===

# (Προσθέτει τον γονικό φάκελο στο path για να βρει το 'modules')
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if 'modules' not in os.listdir(base_dir):
        base_dir = os.path.dirname(base_dir)
    if 'modules' not in os.listdir(base_dir):
        print("Warning: 'modules' folder not found in parent directory.")
    sys.path.append(base_dir)
    from modules.analyzer import calculate_financial_ratios
except ImportError:
    print("⚠️ Σφάλμα: Δεν βρέθηκε το 'modules/analyzer.py'.")
    def calculate_financial_ratios(*args, **kwargs):
        print("DUMMY ANALYZER: Η ανάλυση θα αποτύχει.")
        return {"ratios": pd.DataFrame(), "categories": {}, "sector": "Unknown"}
except FileNotFoundError:
    print("Warning: Δεν μπόρεσε να βρεθεί το path.")
    try:
        from modules.analyzer import calculate_financial_ratios
    except ImportError:
       def calculate_financial_ratios(*args, **kwargs):
            print("DUMMY ANALYZER: Η ανάλυση θα αποτύχει.")
            return {"ratios": pd.DataFrame(), "categories": {}, "sector": "Unknown"}


# -----------------------------
# 🔹 Column Normalization Map (Yahoo) - v1.4
# -----------------------------
YAHOO_COLUMN_MAP = {
    'Total Revenue': 'Revenue', 'Revenue': 'Revenue', 'Cost of Revenue': 'CostOfGoodsSold', 
    'Cost Of Revenue': 'CostOfGoodsSold', 'COGS': 'CostOfGoodsSold', 'Gross Profit': 'GrossProfit',
    'Operating Income': 'OperatingIncome', 'Operating Profit': 'OperatingIncome', 'Net Income': 'NetIncome',
    'Total Current Assets': 'CurrentAssets', 'Current Assets': 'CurrentAssets', 'Total Assets': 'TotalAssets',
    'Assets': 'TotalAssets', 'Cash': 'Cash', 'Cash and Cash Equivalents': 'Cash',
    'Cash And Cash Equivalents': 'Cash', 'Inventory': 'Inventory', 'Inventories': 'Inventory',
    'Total Current Liabilities': 'CurrentLiabilities', 'Current Liabilities': 'CurrentLiabilities',
    'Total Liabilities': 'TotalLiabilities', 'Total Liab': 'TotalLiabilities', 'Total Debt': 'TotalDebt', 
    'Total Equity': 'TotalEquity', 'Shareholders Equity': 'TotalEquity', 'StockholdersEquity': 'TotalEquity',
    'Stockholders Equity': 'TotalEquity', 'Stockholder Equity': 'TotalEquity', 
    'Total Stockholder Equity': 'TotalEquity', 'Total Stockholders Equity': 'TotalEquity', 
    'Common Stock Equity': 'TotalEquity',
    'Total Cash From Operating Activities': 'OperatingCashFlow', 'Operating Cash Flow': 'OperatingCashFlow',
    'Shares Outstanding': 'SharesOutstanding', 'Total Loans': 'Loans', 'Total Deposits': 'Deposits', 
    'Net Interest Income': 'NetInterestIncome', 'Average Earning Assets': 'AverageEarningAssets', 
    'Research And Development': 'R&D', 'R&D Expenses': 'R&D', 'Oil Production': 'OilProduction', 
    'Gas Production': 'GasProduction', 'Operating Expenses': 'OperatingExpenses',
}


# -----------------------------
# 🔹 Column Normalization Map (Generic) - v1.5
# -----------------------------
GENERIC_FILE_MAP = {
    # (Αυτός ο χάρτης θα χρησιμοποιηθεί *μετά* το "Pivot")
    'Total Revenue': 'Revenue', 'Revenue': 'Revenue', 'Sales': 'Revenue', 'Turnover': 'Revenue', 'Έσοδα': 'Revenue',
    'Cost of Revenue': 'CostOfGoodsSold', 'COGS': 'CostOfGoodsSold', 'Cost of Sales': 'CostOfGoodsSold',
    'Gross Profit': 'GrossProfit', 'Gross Income': 'GrossProfit',
    'Operating Income': 'OperatingIncome', 'Operating Profit': 'OperatingIncome',
    'Net Income': 'NetIncome', 'Profit After Tax': 'NetIncome', 'Καθαρά Κέρδη': 'NetIncome',
    'Total Current Assets': 'CurrentAssets', 'Current Assets': 'CurrentAssets',
    'Total Current Liabilities': 'CurrentLiabilities', 'Current Liabilities': 'CurrentLiabilities',
    'Total Assets': 'TotalAssets', 'Assets': 'TotalAssets', 'Ενεργητικό': 'TotalAssets',
    'Total Liabilities': 'TotalLiabilities', 'Total Liab': 'TotalLiabilities', 'Total Debt': 'TotalDebt', 'Debt': 'TotalDebt', 'Υποχρεώσεις': 'TotalLiabilities',
    'Total Equity': 'TotalEquity', 'Shareholders Equity': 'TotalEquity', 'StockholdersEquity': 'TotalEquity',
    'Total Stockholder Equity': 'TotalEquity', 'Stockholder Equity': 'TotalEquity', 'Total Stockholders Equity': 'TotalEquity', 
    'Common Stock Equity': 'TotalEquity', 'Stockholders Equity': 'TotalEquity', 
    'Cash': 'Cash', 'Cash and Cash Equivalents': 'Cash', 'Cash And Cash Equivalents': 'Cash',
    'Inventory': 'Inventory', 'Inventories': 'Inventory',
    'Shares Outstanding': 'SharesOutstanding', 'Basic Shares Outstanding': 'SharesOutstanding',
    'Total Cash From Operating Activities': 'OperatingCashFlow', 'Operating Cash Flow': 'OperatingCashFlow',
    'Total Loans': 'Loans', 'Loans': 'Loans', 'Total Deposits': 'Deposits', 'Deposits': 'Deposits',
    'Net Interest Income': 'NetInterestIncome', 'Average Earning Assets': 'AverageEarningAssets',
    'Research And Development': 'R&D', 'R&D Expenses': 'R&D',
}

def clean_value_unstructured(val):
    """ 
    v3.7: (Μετονομάστηκε αλλά κάνει την ίδια δουλειά)
    Καθαριστής για τιμές πινάκων.
    """
    if val is None: return pd.NA
    s = str(val).strip()
    
    # Αφαίρεση νομισμάτων, commmas, και γραμμών
    s = s.replace('$', '').replace(',', '').replace('—', '0').replace('€', '').replace('£', '')
    
    # Χειρισμός αρνητικών (π.χ. "(1,234.5)")
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
        
    # Αφαίρεση τυχόν " (1)" ή "[2]" (references)
    s = re.sub(r'\s*[\(\[]\d+[\)\]]', '', s) 
    
    # Αφαίρεση τυχόν " %"
    s = s.replace('%', '')
    
    # Αν μείνει κενό, είναι 0 (ή ΝΑ για να μην σπάσει το numeric)
    if s == "":
        return pd.NA
        
    return s

def sanitize_columns(df_to_fix):
    """Μετονομάζει διπλότυπες στήλες (π.χ. 'Amount', 'Amount_2')"""
    if df_to_fix.empty:
        return df_to_fix
        
    new_cols = []
    col_counts = {}
    
    # v3.4 Fix: Χειρισμός MultiIndex (πίνακες με διπλά headers)
    if df_to_fix.columns.nlevels > 1:
        print("   -> Warning: Εντοπίστηκε MultiIndex, απλοποίηση...")
        # Ενώνει τα επίπεδα, π.χ. ('Revenue', '2023') -> 'Revenue_2023'
        df_to_fix.columns = ['_'.join(map(str, col)).strip().replace(r'Unnamed: \d+_level_\d_', '', regex=True) for col in df_to_fix.columns.values]

    for col in df_to_fix.columns:
        if not isinstance(col, str):
            col = str(col) if col is not None else "Unnamed"
        
        # v3.4 Fix: Αφαίρεση "Unnamed" από headers
        col = re.sub(r'Unnamed: \d+', '', col).strip()
        
        if col in col_counts:
            col_counts[col] += 1
            new_col_name = f"{col}_{col_counts[col]}" # π.χ. "Amount_2"
        else:
            col_counts[col] = 1
            new_col_name = col
        
        # v3.4 Fix: Αν η στήλη μείνει τελείως κενή, δώσε της ένα όνομα
        if new_col_name == "":
            new_col_name = f"Unnamed_{col_counts.get('', 0)}"
            col_counts[''] = col_counts.get('', 0) + 1
            
        new_cols.append(new_col_name)
    
    df_to_fix.columns = new_cols
    return df_to_fix


def normalize_dataframe(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    """
    "Ο Μεταφραστής" (v3.6)
    Παίρνει έναν *μεμονωμένο*, σχεδόν-καθαρό πίνακα (π.χ. Ισολογισμό)
    και τον "γυρνάει" (Pivot) ώστε οι χρονιές να γίνουν στήλες.
    """
    if df.empty:
        return df

    if source_type == "yahoo":
        mapping = YAHOO_COLUMN_MAP
    elif source_type in ["csv", "excel", "pdf"]:
        mapping = GENERIC_FILE_MAP
    else:
        print(f"⚠️ Warning: Άγνωστος source_type '{source_type}'. Χρήση 'GENERIC_FILE_MAP'.")
        mapping = GENERIC_FILE_MAP

    normalized_df = pd.DataFrame()
    
    # === PIVOT LOGIC ===
    # v3.7: Το Pivot τρέχει πλέον για PDF, και για CSV/Excel *χωρίς* χρονιές
    run_pivot = False
    if source_type == "pdf":
        run_pivot = True
    elif source_type in ["csv", "excel"] and 'Year' not in df.columns and 'Date' not in df.columns:
        run_pivot = True

    if run_pivot:
        print(f"  [Normalize] -> Εντοπίστηκε {source_type}. Εκτέλεση 'Pivot'...")
        try:
            # 1. Βρίσκουμε την πρώτη στήλη που έχει τα ονόματα
            label_col = str(df.columns[0]).strip()
            if label_col == "" or label_col.lower() == "nan" or label_col.lower().startswith("unnamed"):
                print(f"  [Normalize] -> Warning: Η πρώτη στήλη '{label_col}' είναι άχρηστη. Δοκιμή της 2ης στήλης.")
                label_col = str(df.columns[1]).strip()
                if label_col == "" or label_col.lower() == "nan" or label_col.lower().startswith("unnamed"):
                    print("  [Normalize] -> ❌ ΑΠΟΤΥΧΙΑ 'Pivot': Δεν βρέθηκε στήλη για τα labels.")
                    return pd.DataFrame()
            
            # 2. Τη θέτουμε ως Index
            if df[label_col].duplicated().any():
                df[label_col] = df[label_col].astype(str).str.strip()
                df[label_col] = df.groupby(label_col).cumcount().astype(str) + '_' + df[label_col]
                df[label_col] = df[label_col].str.replace('0_', '', n=1)
                
            df = df.set_index(label_col)
            
            # 3. "Γυρνάμε" (Transpose) τον πίνακα
            df = df.T
            
            # 4. Επαναφέρουμε το index (που τώρα έχει τις χρονιές/ημερομηνίες)
            df = df.reset_index()
            
            # 5. Προσπαθούμε να βρούμε το 'Year'
            year_col = str(df.columns[0]) 
            df['Year'] = df[year_col].astype(str).str.extract(r'(?<!\d\s)(\d{4})(?!\d)')
            
            df = df.dropna(subset=['Year']) 
            if df.empty:
                print(f"  [Normalize] -> ❌ ΑΠΟΤΥΧΙΑ 'Pivot': Δεν βρέθηκαν χρονιές στο header (στήλη '{year_col}').")
                return pd.DataFrame()

            print(f"  [Normalize] -> 'Pivot' επιτυχής.")
        except Exception as e:
            print(f"  [Normalize] -> ❌ ΑΠΟΤΥΧΙΑ 'Pivot': {e}")
            return pd.DataFrame() # Αποτυχία
    
    # v3.7: Χειρισμός για Yahoo/CSV/Excel που είναι ήδη "γυρισμένα"
    elif source_type == "yahoo":
         df = df 
    elif source_type in ["csv", "excel"]:
        if 'Year' not in df.columns and 'Date' in df.columns:
            df['Year'] = pd.to_datetime(df['Date']).dt.year
        df = df

    # === MAPPING LOGIC ===
    for col in ['Year', 'Date']:
        if col in df.columns and col not in normalized_df.columns:
            normalized_df[col] = df[col]

    df.columns = [str(col).replace('\n', ' ').strip() for col in df.columns]
    df_columns_stripped = {str(col).strip(): col for col in df.columns}
        
    for source_col, standard_col in mapping.items():
        matching_source_col = None
        source_col_clean = str(source_col).strip()
        
        if source_col_clean in df_columns_stripped:
            matching_source_col = df_columns_stripped[source_col_clean]
        else: 
            source_col_lower = source_col_clean.lower()
            for df_col_stripped, df_col_original in df_columns_stripped.items():
                if df_col_stripped.lower() == source_col_lower:
                    matching_source_col = df_col_original
                    break

        if matching_source_col:
            if standard_col not in normalized_df.columns:
                clean_col = pd.to_numeric(df[matching_source_col].astype(str).map(clean_value_unstructured), errors='coerce')
                normalized_df[standard_col] = clean_col

    if 'TotalLiabilities' not in normalized_df.columns and 'TotalDebt' in normalized_df.columns:
        normalized_df['TotalLiabilities'] = normalized_df['TotalDebt']
        print("  [Normalize] Info: 'TotalLiabilities' not found. Using 'TotalDebt' as a proxy.")

    return normalized_df

# -----------------------------
# 🔹 Utilities: (Search, Premium, Industry Lookups)
# -----------------------------
YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"

def search_company_by_name(name: str, limit: int = 10):
    try:
        params = {"q": name, "quotesCount": limit, "newsCount": 0}
        r = requests.get(YAHOO_SEARCH_URL, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        results = []
        for item in data.get("quotes", []):
            results.append({
                "symbol": item.get("symbol"),
                "name": item.get("shortname") or item.get("longname") or item.get("displayName") or item.get("name"),
                "exchange": item.get("exchange"),
                "type": item.get("typeDisp")
            })
        return results
    except Exception as e:
        print(f"⚠️ Σφάλμα κατά το search: {e}")
        return []

def resolve_to_ticker(user_input: str, source_type: str = "yahoo") -> Optional[str]:
    candidate = user_input.strip()
    
    print(f"Info: Αναζήτηση για '{candidate}'...")
    matches = search_company_by_name(candidate, limit=10)
    
    is_streamlit = 'streamlit' in sys.modules
    if not matches:
        if is_streamlit:
            print("⚠️ Δεν βρέθηκαν αποτελέσματα αναζήτησης.")
            return None
        else:
            print("⚠️ Δεν βρέθηκαν αποτελέσματα αναζήτησης.")
            return None
    
    if is_streamlit:
        print(f"Info: Βρέθηκε '{matches[0]['symbol']}' για το '{candidate}'.")
        return matches[0]['symbol']
    
    print("\nΒρέθηκαν προτάσεις:")
    for i, m in enumerate(matches, start=1):
        name = m.get("name") or "—"; symbol = m.get("symbol") or "—"
        exch = m.get("exchange") or ""; typ = m.get("type") or ""
        print(f"{i}. {name} ({symbol}) {exch} {typ}")
    sel = input("Επέλεξε αριθμό της εταιρείας (ή άσε κενό για ακύρωση): ").strip()
    try:
        if sel == "": return None
        sel_i = int(sel) - 1
        if 0 <= sel_i < len(matches):
            return matches[sel_i]["symbol"]
        else:
            print("Μη έγκυρη επιλογή."); return None
    except Exception:
        print("Μη έγκυρη είσοδος (Ίσως έδωσες Ticker αντί για Αριθμό;)."); return None

def get_premium_data(ticker: str, api_key: Optional[str] = None, source: str = "premium") -> pd.DataFrame:
    # (Placeholder)
    return pd.DataFrame()

# -----------------------------
# 🔹 PDF Data Extractor (v3.7 - "Turbo Engine" PyMuPDF)
# -----------------------------

# Αντικατάστησε ΜΟΝΟ τη συνάρτηση load_data_from_pdf στο test_loader.py

# test_loader.py - load_data_from_pdf (Safe & Compatible Mode)

def load_data_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    v3.9: Turbo Engine με "Text Strategy" (Συμβατή Έκδοση).
    Χρησιμοποιεί τη διάταξη του κειμένου για να βρει πίνακες χωρίς γραμμές.
    """
    print(f"📄 Έναρξη σάρωσης PDF (v3.9 - Text Strategy): {file_path}")
    
    all_data_packages = []
    
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        print(f"❌ Σφάλμα PyMuPDF: {e}")
        return []

    # Σάρωση πρώτων 20 σελίδων
    pages_to_scan = doc[:20] if len(doc) > 20 else doc

    for page_num, page in enumerate(pages_to_scan):
        try:
            # === Η ΑΛΛΑΓΗ ΕΙΝΑΙ ΕΔΩ ===
            # Αφαιρέσαμε τα 'tolerance' που χτυπούσαν λάθος.
            # Κρατήσαμε τα strategies που βρίσκουν τους πίνακες της Microsoft.
            table_finder = page.find_tables(
                vertical_strategy="text", 
                horizontal_strategy="text"
            )
            
            tables = table_finder.tables
            
            if not tables:
                continue

            print(f"   > Σελίδα {page_num+1}: Βρέθηκαν {len(tables)} πιθανοί πίνακες...")

            for i, table in enumerate(tables):
                try:
                    df = table.to_pandas()
                    
                    # Καθαρισμός
                    df = df.dropna(how='all').fillna("")
                    
                    # Φίλτρο μεγέθους
                    if df.shape[0] < 3 or df.shape[1] < 2:
                        continue

                    # Header Detection (ψάχνουμε έτος)
                    header_idx = -1
                    for r_idx, row in df.iterrows():
                        row_str = " ".join(row.astype(str))
                        if re.search(r'20[1-3][0-9]', row_str):
                            header_idx = r_idx
                            break
                    
                    if header_idx != -1:
                        new_header = df.iloc[header_idx]
                        df_data = df.iloc[header_idx+1:]
                        df_data.columns = new_header
                    else:
                        df_data = df 

                    # Sanitize
                    df_sanitized = sanitize_columns(df_data)
                    df_clean = df_sanitized.apply(lambda col: col.map(clean_value_unstructured))

                    # Πακετάρισμα
                    all_data_packages.append({
                        "title": f"Page_{page_num+1}_Table_{i+1}",
                        "table": df_clean
                    })
                    
                except Exception as e:
                    continue 
        
        except Exception as e:
            print(f"   -> Error page {page_num+1}: {e}")
            continue

    if not all_data_packages:
        print("⚠️ Δεν βρέθηκαν πίνακες.")
        return []

    print(f"   Επιτυχία! Βρέθηκαν {len(all_data_packages)} 'πακέτα'.")
    return all_data_packages

# -----------------------------
# 🔹 Loader για διάφορες πηγές
# -----------------------------
def get_company_df(source: str, source_type: str = "yahoo", api_key: Optional[str] = None, period: str = "5y") -> List[Dict[str, Any]]:
    """
    v3.7: ΕΠΙΣΤΡΕΦΕΙ ΠΑΝΤΑ ΛΙΣΤΑ ΜΕ "ΠΑΚΕΤΑ" [ {"title": ..., "table": ...} ]
    """
    source_type = source_type.lower()

    if source_type == "yahoo":
        print("⚡ Λήψη δεδομένων από Yahoo Finance...")
        yahoo_df = get_yahoo_data(source, period=period)
        if yahoo_df.empty:
            return []
        return [{"title": "Yahoo Finance Data", "table": yahoo_df}]
        
    elif source_type in ["csv", "excel"]:
        print(f"📂 Φόρτωση δεδομένων από {source_type.upper()}: {source}")
        try:
            if source_type == "csv":
                df = pd.read_csv(source)
            else:
                df = pd.read_excel(source)
            
            if df.empty:
                return []
            return [{"title": f"File Data ({source_type})", "table": df}]
            
        except Exception as e:
            print(f"⚠️ Σφάλμα ανάγνωσης αρχείου: {e}")
            if "openpyxl" in str(e):
                print("--- HINT: Μήπως λείπει η βιβλιοθήκη 'openpyxl'; Τρέξε 'pip install openpyxl' ---")
            return []
    
    elif source_type == "pdf":
        print(f"📂 Φόρτωση δεδομένων από PDF (F1 Engine v3.7 - Turbo)...")
        # 1. Φορτώνουμε τα raw data από το PDF (με τον v3.7 Turbo Engine)
        raw_data_list = load_data_from_pdf(source) 
        
        if not raw_data_list:
            return []
            
        # 2. Επιστρέφουμε τη ΛΙΣΤΑ με τα "πακέτα"
        print(f"--- Επιστροφή ΛΙΣΤΑΣ με {len(raw_data_list)} 'πακέτα' (πριν τον Μεταφραστή) ---")
        return raw_data_list 

    # ... (rest of the placeholders) ...
    elif source_type == "alphavantage" or source_type == "premium":
        print(f"⚠️ Η πηγή '{source_type}' δεν υποστηρίζεται πλήρως σε αυτή την έκδοση.")
        return []

    else:
        print(f"❌ Μη υποστηριζόμενη πηγή: {source_type}")
        return []


def get_yahoo_data(ticker: str, period: str = "5y") -> pd.DataFrame:
    """
    v3.7: Επιστρέφει ΕΝΑ DataFrame, έτοιμο για "Μετάφραση" (αλλά "ακατέργαστο").
    """
    try:
        ticker_obj = yf.Ticker(ticker)
        fin = ticker_obj.financials.T if hasattr(ticker_obj, "financials") else pd.DataFrame()
        bs = ticker_obj.balance_sheet.T if hasattr(ticker_obj, "balance_sheet") else pd.DataFrame()
        cf = ticker_obj.cashflow.T if hasattr(ticker_obj, "cashflow") else pd.DataFrame()
        
        df_list = [df for df in [fin, bs, cf] if not df.empty]
        if not df_list:
            print(f"⚠️ $ {ticker}: Δεν βρέθηκαν καθόλου δεδομένα (financials, balance, cashflow).")
            return pd.DataFrame()
            
        clean_df_list = []
        for df in df_list:
            df = df.loc[~df.index.duplicated(keep='first')]
            clean_df_list.append(df)
            
        df = pd.concat(clean_df_list, axis=1)
        df = df.loc[:, ~df.columns.duplicated(keep='first')]
        
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'Date'}, inplace=True)
        df['Year'] = pd.to_datetime(df['Date']).dt.year
        df.columns = [str(c).strip() for c in df.columns]
        
        # Επιστρέφουμε τον "ακατέργαστο" πίνακα του Yahoo
        return df
        
    except Exception as e:
        print(f"⚠️ Σφάλμα στη λήψη δεδομένων από Yahoo ($ {ticker}):", e)
        return pd.DataFrame()

# -----------------------------
# 🔹 Company basic info & peers (Helpers for Terminal)
# -----------------------------
def load_company_info(ticker: str) -> Tuple[pd.DataFrame, str]:
    """
    v3.6: Τώρα επιστρέφει ΚΑΙ τη χώρα (Country) μέσα στο info_df
    """
    try:
        company = yf.Ticker(ticker)
        info = company.info or {}
        
        industry = info.get("industry", "General") 
        if not industry or pd.isna(industry): industry = "General"
        
        country = info.get("country", "Unknown") # <-- v3.6: Η ΝΕΑ ΠΡΟΣΘΗΚΗ

        df = pd.DataFrame([{
            "Όνομα": info.get("longName", "Άγνωστο"),
            "Κλάδος": industry,
            "Χώρα": country, # <-- v3.g: Η ΝΕΑ ΠΡΟΣΘΗΚΗ
            "Κεφαλαιοποίηση": info.get("marketCap", None),
            "P/E": info.get("trailingPE", None),
            "ROE": info.get("returnOnEquity", None),
        }])
        
        return df, industry
    except Exception as e:
        print(f"⚠️ Σφάλμα στη λήψη info εταιρείας ($ {ticker}): {e}")
        return pd.DataFrame(), "General"
# === === === === === === === === === ===

def get_industry_peers(ticker: str):
    print("Η λήψη Peers εκτελείται μόνο στο terminal.")
    return []
def calculate_industry_averages(peers: list):
    return None
def compare_company_to_industry(company_df, industry_avg):
    print("Η σύγκριση κλάδου εκτελείται μόνο στο terminal.")


# -----------------------------
# 🔹 Κύριο πρόγραμμα (Terminal flow)
# -----------------------------
def main():
    print("📊 Financial Analysis Tool — Terminal (v3.5 - Deprecated)\n")
    print("--- Αυτό είναι το Terminal mode. ---")
    print("--- Για το πλήρες GUI, τρέξε: streamlit run app.py ---")
    
    choice = "yahoo" 
    raw = input("Δώσε ticker ή όνομα εταιρείας (π.χ. AAPL ή 'JP Morgan Chase'): ").strip()
    if not raw: return

    ticker = resolve_to_ticker(raw, source_type=choice)
    if ticker is None: return

    info_df, industry = load_company_info(ticker)
    print("\n--- Πληροφορίες Εταιρείας ---")
    print(info_df.to_string(index=False))

    # v3.5: Το get_company_df επιστρέφει ΛΙΣΤΑ
    data_list = get_company_df(ticker, source_type=choice, period="max")
    if not data_list: 
        print("⚠️ Δεν βρέθηκαν δεδομένα.")
        return

    # v3.5: Πρέπει να το στείλουμε στον "Μεταφραστή" εδώ
    company_df_raw = data_list[0]["table"]
    company_df = normalize_dataframe(company_df_raw, source_type="yahoo")

    if company_df is None or company_df.empty: 
        print("⚠️ Αποτυχία 'Μετάφρασης' δεδομένων.")
        return

    result = calculate_financial_ratios(company_df, sector=industry)
    ratios_df = result.get("ratios")
    
    print("\n--- Δείκτες Εταιρείας (Σύντομη Επισκόπηση) ---")
    if isinstance(ratios_df, pd.DataFrame) and not ratios_df.empty:
        with pd.option_context('display.max_columns', None, 'display.width', 200):
            print(ratios_df.head().to_string(index=False))
    else:
        print("⚠️ Δεν υπολογίστηκαν δείκτες.")
    print("\n✅ Ολοκληρώθηκε η ανάλυση στο Terminal.")


if __name__ == "__main__":
    main()