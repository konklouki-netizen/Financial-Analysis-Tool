# test_loader.py (v4.0 - Clean & Stable)
import os
import sys
import pandas as pd
import yfinance as yf
import requests
from typing import Optional, Tuple, List, Dict, Any
import re 
import io
import fitz  # PyMuPDF

# === Imports από modules ===
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(base_dir)
    from modules.analyzer import calculate_financial_ratios
except ImportError:
    pass # Θα το χειριστεί το app.py

# -----------------------------
# 🔹 Column Normalization Maps
# -----------------------------
YAHOO_COLUMN_MAP = {
    'Total Revenue': 'Revenue', 'Revenue': 'Revenue', 
    'Cost of Revenue': 'CostOfGoodsSold', 'Cost Of Revenue': 'CostOfGoodsSold', 'COGS': 'CostOfGoodsSold',
    'Gross Profit': 'GrossProfit', 'Operating Income': 'OperatingIncome', 
    'Net Income': 'NetIncome', 'Total Assets': 'TotalAssets',
    'Total Current Assets': 'CurrentAssets', 'Total Current Liabilities': 'CurrentLiabilities',
    'Total Liabilities': 'TotalLiabilities', 'Total Debt': 'TotalDebt', 
    'Total Equity': 'TotalEquity', 'Stockholders Equity': 'TotalEquity',
    'Operating Cash Flow': 'OperatingCashFlow', 'Total Cash From Operating Activities': 'OperatingCashFlow',
    'Cash': 'Cash', 'Cash And Cash Equivalents': 'Cash', 
    'Inventory': 'Inventory', 'Interest Expense': 'InterestExpense'
}

GENERIC_FILE_MAP = {
    'Revenue': 'Revenue', 'Sales': 'Revenue', 'Total Revenue': 'Revenue',
    'Cost of Sales': 'CostOfGoodsSold', 'Cost of Revenue': 'CostOfGoodsSold',
    'Gross Profit': 'GrossProfit', 'Operating Income': 'OperatingIncome',
    'Net Income': 'NetIncome', 'Profit/Loss': 'NetIncome',
    'Total Assets': 'TotalAssets', 'Total Liabilities': 'TotalLiabilities',
    'Total Equity': 'TotalEquity', 'Shareholders Equity': 'TotalEquity',
    'Cash': 'Cash', 'Cash & Equivalents': 'Cash',
    'Inventory': 'Inventory', 'Total Debt': 'TotalDebt',
    'Operating Cash Flow': 'OperatingCashFlow'
}

# -----------------------------
# 🔹 Utility Functions
# -----------------------------
def clean_value_unstructured(val):
    if val is None: return pd.NA
    s = str(val).strip()
    s = s.replace('$', '').replace(',', '').replace('—', '0').replace('€', '').replace('£', '')
    if s.startswith('(') and s.endswith(')'): s = '-' + s[1:-1]
    if s == "" or s == "-": return pd.NA
    return s

def sanitize_columns(df):
    new_cols = []
    counts = {}
    for col in df.columns:
        c_str = str(col).strip()
        if c_str in counts:
            counts[c_str] += 1
            c_str = f"{c_str}_{counts[c_str]}"
        else:
            counts[c_str] = 0
        new_cols.append(c_str)
    df.columns = new_cols
    return df

def normalize_dataframe(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    if df.empty: return df
    
    mapping = YAHOO_COLUMN_MAP if source_type == "yahoo" else GENERIC_FILE_MAP
    norm_df = pd.DataFrame()

    # 1. Handling Transpose logic for certain files
    # (Simplified for stability)
    if 'Year' not in df.columns:
        # Try to find Year in index or columns
        pass 

    # 2. Copy Year/Date
    for c in ['Year', 'Date']:
        if c in df.columns: norm_df[c] = df[c]

    # 3. Map Columns
    df_cols_lower = {str(c).strip().lower(): c for c in df.columns}
    
    for std_col, map_target in mapping.items(): # std_col is key in map, map_target is value (Standard)
        # Reverse check: mapping key is the RAW name, value is the STANDARD name
        pass 
    
    # Re-loop correctly
    for raw_name, std_name in mapping.items():
        raw_lower = raw_name.lower()
        if raw_lower in df_cols_lower:
            real_col = df_cols_lower[raw_lower]
            norm_df[std_name] = pd.to_numeric(df[real_col].astype(str).map(clean_value_unstructured), errors='coerce')

    return norm_df

# -----------------------------
# 🔹 Data Loaders
# -----------------------------
def get_company_df(source: str, source_type: str = "yahoo") -> List[Dict[str, Any]]:
    if source_type == "yahoo":
        print(f"⚡ Λήψη δεδομένων από Yahoo Finance: {source}")
        df = get_yahoo_data(source)
        return [{"title": "Yahoo Data", "table": df}] if not df.empty else []
    
    elif source_type == "pdf":
        return load_data_from_pdf(source)
    
    return []

def get_yahoo_data(ticker: str) -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker)
        # Fetch annuals
        fin = t.financials.T
        bs = t.balance_sheet.T
        cf = t.cashflow.T
        
        dfs = [d for d in [fin, bs, cf] if not d.empty]
        if not dfs: return pd.DataFrame()
        
        # Merge
        full = pd.concat(dfs, axis=1)
        full = full.loc[:, ~full.columns.duplicated()]
        
        # Reset index to get Year
        full.reset_index(inplace=True)
        full.rename(columns={'index': 'Date'}, inplace=True)
        full['Year'] = pd.to_datetime(full['Date']).dt.year
        return full
    except Exception as e:
        print(f"Error Yahoo: {e}")
        return pd.DataFrame()

# -----------------------------
# 🔹 PDF ENGINE (v3.9 - Text Strategy)
# -----------------------------
def load_data_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    print(f"📄 Σάρωση PDF: {file_path}")
    packages = []
    try:
        doc = fitz.open(file_path)
    except:
        return []

    for page in doc[:20]: # First 20 pages
        # Text Strategy: Καλύτερη για 10-Q χωρίς γραμμές
        tabs = page.find_tables(vertical_strategy="text", horizontal_strategy="text")
        for tab in tabs.tables:
            df = tab.to_pandas()
            # Basic cleanup
            df = df.dropna(how='all')
            if df.shape[0] < 2: continue
            
            # Try to find header with years
            header_idx = -1
            for i, row in df.iterrows():
                s = " ".join(row.astype(str))
                if re.search(r'20[1-3][0-9]', s):
                    header_idx = i
                    break
            
            if header_idx >= 0:
                df.columns = df.iloc[header_idx]
                df = df.iloc[header_idx+1:]
            
            df = sanitize_columns(df)
            packages.append({"title": "PDF Table", "table": df})
            
    return packages

# -----------------------------
# 🔹 Helpers
# -----------------------------
def resolve_to_ticker(query: str):
    # Απλή αναζήτηση ή επιστροφή του ίδιου αν μοιάζει με ticker
    if query.upper().endswith(".AT") or len(query) < 5:
        return query.upper()
    # (Εδώ θα μπορούσε να μπει search API, για τώρα επιστρέφει το query)
    return query.upper()

def load_company_info(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return pd.DataFrame([{"Κεφαλαιοποίηση": info.get('marketCap', 0), "Όνομα": info.get('longName', ticker)}]), "General"
    except:
        return pd.DataFrame(), "General"