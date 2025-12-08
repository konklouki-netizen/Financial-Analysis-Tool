# test_loader.py (v11.0 - Fixed: Let yfinance handle the connection)
import pandas as pd
import yfinance as yf
import re 
import fitz  # PyMuPDF
from typing import List, Dict, Any

# === 1. THE MASTER MAPPING (CFA 7 Pillars) ===
COLUMN_MAP = {
    'total revenue': 'Revenue', 'revenue': 'Revenue', 'operating revenue': 'Revenue', 'sales': 'Revenue',
    'cost of revenue': 'CostOfGoodsSold', 'cost of goods sold': 'CostOfGoodsSold', 'cogs': 'CostOfGoodsSold',
    'gross profit': 'GrossProfit',
    'operating income': 'OperatingIncome', 'ebit': 'OperatingIncome',
    'net income': 'NetIncome', 'net income common stockholders': 'NetIncome',
    'interest expense': 'InterestExpense', 'interest': 'InterestExpense',
    'ebitda': 'EBITDA', 'basic eps': 'BasicEPS', 'diluted eps': 'DilutedEPS',
    'reconciled depreciation': 'ReconciledDepreciation',
    
    'total assets': 'TotalAssets', 'total current assets': 'CurrentAssets',
    'total liabilities': 'TotalLiabilities', 'total current liabilities': 'CurrentLiabilities',
    'accounts payable': 'Payables',
    'total debt': 'TotalDebt', 'long term debt': 'TotalDebt', 'total capitalization': 'TotalDebt',
    'total equity': 'TotalEquity', 'stockholders equity': 'TotalEquity', 
    'retained earnings': 'RetainedEarnings', 'share issued': 'ShareIssued', 'ordinary shares number': 'ShareIssued',
    'cash': 'Cash', 'cash and cash equivalents': 'Cash', 'cash & equivalents': 'Cash',
    'inventory': 'Inventory', 'net receivables': 'Receivables', 'accounts receivable': 'Receivables',
    'net ppe': 'NetPPE', 'property plant equipment': 'NetPPE', 'fixed assets': 'NetPPE',
    
    'operating cash flow': 'OperatingCashFlow', 'total cash from operating activities': 'OperatingCashFlow',
    'investing cash flow': 'InvestingCashFlow', 'total cashflows from investing activities': 'InvestingCashFlow',
    'financing cash flow': 'FinancingCashFlow', 'total cash from financing activities': 'FinancingCashFlow',
    'capital expenditure': 'CapitalExpenditures', 'capex': 'CapitalExpenditures',
    'free cash flow': 'FreeCashFlow', 'cash dividends paid': 'CashDividendsPaid'
}

# === 2. CORE FUNCTIONS ===

def normalize_dataframe(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    if df.empty: return df
    norm_df = df.copy()
    clean_cols_map = {str(c).strip().lower().replace('  ', ' '): c for c in df.columns}
    
    rename_dict = {}
    for raw_key, standard_key in COLUMN_MAP.items():
        for clean_col, original_col in clean_cols_map.items():
            if raw_key == clean_col:
                rename_dict[original_col] = standard_key
    
    norm_df.rename(columns=rename_dict, inplace=True)
    if 'Year' not in norm_df.columns and 'Date' in norm_df.columns:
        norm_df['Year'] = pd.to_datetime(norm_df['Date']).dt.year
    return norm_df

def get_company_df(source: str, source_type: str = "yahoo") -> List[Dict[str, Any]]:
    if source_type == "yahoo":
        print(f"⚡ Fetching Yahoo Data for: {source}")
        df = get_yahoo_data(source)
        return [{"title": "Yahoo Data", "table": df}] if not df.empty else []
    elif source_type == "pdf":
        return load_data_from_pdf(source)
    return []

def get_yahoo_data(ticker: str) -> pd.DataFrame:
    try:
        # ΔΙΟΡΘΩΣΗ: Σκέτο Ticker, χωρίς session!
        t = yf.Ticker(ticker)
        
        try:
            inc = t.financials.T
            bal = t.balance_sheet.T
            cf = t.cashflow.T
        except:
            return pd.DataFrame()

        if inc.empty and bal.empty:
            print(f"❌ Empty data for {ticker}")
            return pd.DataFrame()

        dfs = [d for d in [inc, bal, cf] if not d.empty]
        full = pd.concat(dfs, axis=1)
        full = full.loc[:, ~full.columns.duplicated()]
        
        full.reset_index(inplace=True)
        if 'index' in full.columns: full.rename(columns={'index': 'Date'}, inplace=True)
        if 'Date' in full.columns:
            full['Date'] = pd.to_datetime(full['Date'])
            full['Year'] = full['Date'].dt.year
            
        print(f"✅ Data fetched: {full.shape}")
        return full
    except Exception as e:
        print(f"❌ Error: {e}")
        return pd.DataFrame()

def load_data_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    try:
        doc = fitz.open(file_path)
        packages = []
        for page in doc[:20]:
            tabs = page.find_tables()
            for tab in tabs.tables:
                df = tab.to_pandas()
                packages.append({"title": "PDF Table", "table": df})
        return packages
    except: return []

def resolve_to_ticker(query: str): return query.strip().upper()

def load_company_info(ticker):
    try:
        # ΔΙΟΡΘΩΣΗ: Σκέτο Ticker και εδώ
        t = yf.Ticker(ticker)
        info = t.info
        return pd.DataFrame([{"Κεφαλαιοποίηση": info.get('marketCap', 0), "Όνομα": info.get('longName', ticker)}]), "General"
    except: return pd.DataFrame(), "General"