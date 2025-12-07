# test_loader.py (v6.0 - FULL RESTORATION & CFA SUPPORT)
import os
import sys
import pandas as pd
import yfinance as yf
import requests_cache
import re 
import fitz  # PyMuPDF
from typing import List, Dict, Any

# === 1. Anti-Blocking Session ===
try:
    session = requests_cache.CachedSession('yfinance.cache')
    session.headers['User-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
except ImportError:
    print("Warning: requests_cache not found. Using default session.")
    session = None

# === 2. THE MASTER MAPPING (CFA 7 Pillars) ===
# Συνδέει τα ονόματα της Yahoo με τα ονόματα που θέλει ο Analyzer
COLUMN_MAP = {
    # Income Statement
    'total revenue': 'Revenue', 'revenue': 'Revenue', 'operating revenue': 'Revenue', 'sales': 'Revenue',
    'cost of revenue': 'CostOfGoodsSold', 'cost of goods sold': 'CostOfGoodsSold', 'cogs': 'CostOfGoodsSold',
    'gross profit': 'GrossProfit',
    'operating income': 'OperatingIncome', 'ebit': 'OperatingIncome',
    'net income': 'NetIncome', 'net income common stockholders': 'NetIncome',
    'interest expense': 'InterestExpense', 'interest': 'InterestExpense',
    'ebitda': 'EBITDA', 
    'basic eps': 'BasicEPS', 'diluted eps': 'DilutedEPS',
    'reconciled depreciation': 'ReconciledDepreciation',
    
    # Balance Sheet - Assets
    'total assets': 'TotalAssets',
    'total current assets': 'CurrentAssets',
    'cash': 'Cash', 'cash and cash equivalents': 'Cash', 'cash & equivalents': 'Cash',
    'inventory': 'Inventory',
    'net receivables': 'Receivables', 'accounts receivable': 'Receivables',
    'net ppe': 'NetPPE', 'property plant equipment': 'NetPPE', 'fixed assets': 'NetPPE',
    
    # Balance Sheet - Liabilities & Equity
    'total liabilities': 'TotalLiabilities',
    'total current liabilities': 'CurrentLiabilities',
    'accounts payable': 'Payables',
    'total debt': 'TotalDebt', 'long term debt': 'TotalDebt', 'total capitalization': 'TotalDebt',
    'total equity': 'TotalEquity', 'stockholders equity': 'TotalEquity', 
    'retained earnings': 'RetainedEarnings',
    'share issued': 'ShareIssued', 'ordinary shares number': 'ShareIssued',
    
    # Cash Flow
    'operating cash flow': 'OperatingCashFlow', 'total cash from operating activities': 'OperatingCashFlow',
    'investing cash flow': 'InvestingCashFlow', 'total cashflows from investing activities': 'InvestingCashFlow',
    'financing cash flow': 'FinancingCashFlow', 'total cash from financing activities': 'FinancingCashFlow',
    'capital expenditure': 'CapitalExpenditures', 'capex': 'CapitalExpenditures',
    'free cash flow': 'FreeCashFlow',
    'cash dividends paid': 'CashDividendsPaid'
}

# === 3. CORE FUNCTIONS ===

def normalize_dataframe(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    """Καθαρίζει και μετονομάζει τις στήλες βάσει του Mapping."""
    if df.empty: return df
    
    norm_df = df.copy()
    
    # Καθαρισμός ονομάτων (lowercase, strip)
    clean_cols_map = {str(c).strip().lower().replace('  ', ' '): c for c in df.columns}
    
    # Μετονομασία
    rename_dict = {}
    for raw_key, standard_key in COLUMN_MAP.items():
        for clean_col, original_col in clean_cols_map.items():
            if raw_key == clean_col:
                rename_dict[original_col] = standard_key
    
    norm_df.rename(columns=rename_dict, inplace=True)
    
    # Δημιουργία στήλης Year αν δεν υπάρχει
    if 'Year' not in norm_df.columns and 'Date' in norm_df.columns:
        norm_df['Year'] = pd.to_datetime(norm_df['Date']).dt.year
        
    return norm_df

def get_company_df(source: str, source_type: str = "yahoo") -> List[Dict[str, Any]]:
    """Κεντρική συνάρτηση που καλεί Yahoo ή PDF."""
    if source_type == "yahoo":
        print(f"⚡ Fetching Yahoo Data for: {source}")
        df = get_yahoo_data(source)
        # Επιστρέφουμε λίστα ΜΟΝΟ αν έχουμε δεδομένα
        return [{"title": "Yahoo Data", "table": df}] if not df.empty else []
    
    elif source_type == "pdf":
        return load_data_from_pdf(source)
    
    return []

def get_yahoo_data(ticker: str) -> pd.DataFrame:
    """Κατεβάζει και ενώνει όλα τα tables από Yahoo."""
    try:
        # Χρήση του session για να μην μας μπλοκάρουν
        t = yf.Ticker(ticker, session=session)
        
        # Λήψη καταστάσεων
        try:
            inc = t.financials.T
            bal = t.balance_sheet.T
            cf = t.cashflow.T
        except Exception:
            # Fallback χωρίς Transpose αν αλλάξει το API
            inc = t.financials
            bal = t.balance_sheet
            cf = t.cashflow
        
        # Έλεγχος αν είναι κενά
        if inc.empty and bal.empty:
            print(f"❌ No financial data found for {ticker}")
            return pd.DataFrame()

        # Συνένωση
        dfs = [d for d in [inc, bal, cf] if not d.empty]
        full = pd.concat(dfs, axis=1)
        
        # Καθαρισμός διπλών στηλών
        full = full.loc[:, ~full.columns.duplicated()]
        
        # Reset Index για να γίνει το Date στήλη
        full.reset_index(inplace=True)
        if 'index' in full.columns: full.rename(columns={'index': 'Date'}, inplace=True)
        if 'Date' in full.columns:
            full['Date'] = pd.to_datetime(full['Date'])
            full['Year'] = full['Date'].dt.year
            
        print(f"✅ Data fetched successfully: {full.shape}")
        return full
        
    except Exception as e:
        print(f"❌ Critical Yahoo Error: {e}")
        return pd.DataFrame()

# === 4. PDF ENGINE (Restored) ===
def load_data_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    print(f"📄 Σάρωση PDF: {file_path}")
    packages = []
    try:
        doc = fitz.open(file_path)
    except:
        return []

    for page in doc[:20]: # Ψάχνουμε τις πρώτες 20 σελίδες
        tabs = page.find_tables(vertical_strategy="text", horizontal_strategy="text")
        for tab in tabs.tables:
            df = tab.to_pandas()
            df = df.dropna(how='all')
            if df.shape[0] < 2: continue
            
            # Έλεγχος αν είναι πίνακας με χρονολογίες
            header_idx = -1
            for i, row in df.iterrows():
                s = " ".join(row.astype(str))
                if re.search(r'20[1-3][0-9]', s):
                    header_idx = i
                    break
            
            if header_idx >= 0:
                df.columns = df.iloc[header_idx]
                df = df.iloc[header_idx+1:]
            
            packages.append({"title": "PDF Table", "table": df})
            
    return packages

# === 5. HELPERS ===
def resolve_to_ticker(query: str):
    return query.strip().upper()

def load_company_info(ticker):
    try:
        t = yf.Ticker(ticker, session=session)
        info = t.info
        return pd.DataFrame([{"Κεφαλαιοποίηση": info.get('marketCap', 0), "Όνομα": info.get('longName', ticker)}]), "General"
    except:
        return pd.DataFrame(), "General"