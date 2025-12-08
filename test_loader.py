# test_loader.py (Final Working Version)
import pandas as pd
import yfinance as yf
import fitz  # PyMuPDF
from typing import List, Dict, Any

# === CFA MAPPING ===
COLUMN_MAP = {
    'total revenue': 'Revenue', 'revenue': 'Revenue', 'operating revenue': 'Revenue',
    'cost of revenue': 'CostOfGoodsSold', 'cost of goods sold': 'CostOfGoodsSold',
    'gross profit': 'GrossProfit', 'operating income': 'OperatingIncome', 'ebit': 'OperatingIncome',
    'net income': 'NetIncome', 'ebitda': 'EBITDA', 'basic eps': 'BasicEPS',
    'total assets': 'TotalAssets', 'total current assets': 'CurrentAssets',
    'total liabilities': 'TotalLiabilities', 'total current liabilities': 'CurrentLiabilities',
    'total equity': 'TotalEquity', 'stockholders equity': 'TotalEquity', 
    'total debt': 'TotalDebt', 'long term debt': 'TotalDebt', 'total capitalization': 'TotalDebt',
    'cash': 'Cash', 'cash and cash equivalents': 'Cash',
    'inventory': 'Inventory', 'net receivables': 'Receivables', 'accounts receivable': 'Receivables',
    'accounts payable': 'Payables', 'net ppe': 'NetPPE', 
    'operating cash flow': 'OperatingCashFlow', 'capital expenditure': 'CapitalExpenditures', 'capex': 'CapitalExpenditures',
    'free cash flow': 'FreeCashFlow', 'cash dividends paid': 'CashDividendsPaid',
    'investing cash flow': 'InvestingCashFlow', 'financing cash flow': 'FinancingCashFlow',
    'retained earnings': 'RetainedEarnings', 'share issued': 'ShareIssued'
}

def normalize_dataframe(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    if df.empty: return df
    norm_df = df.copy()
    clean_cols_map = {str(c).strip().lower().replace('  ', ' '): c for c in df.columns}
    rename_dict = {}
    for raw_key, standard_key in COLUMN_MAP.items():
        for clean_col, original_col in clean_cols_map.items():
            if raw_key == clean_col: rename_dict[original_col] = standard_key
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
        return [] # PDF logic removed for simplicity in debugging
    return []

def get_yahoo_data(ticker: str) -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker) # ΑΠΛΟ CALL
        try:
            inc = t.financials.T
            bal = t.balance_sheet.T
            cf = t.cashflow.T
        except: return pd.DataFrame()

        if inc.empty and bal.empty:
            print(f"❌ Empty data for {ticker}")
            return pd.DataFrame()

        full = pd.concat([d for d in [inc, bal, cf] if not d.empty], axis=1)
        full = full.loc[:, ~full.columns.duplicated()]
        full.reset_index(inplace=True)
        if 'index' in full.columns: full.rename(columns={'index': 'Date'}, inplace=True)
        if 'Date' in full.columns:
            full['Date'] = pd.to_datetime(full['Date'])
            full['Year'] = full['Date'].dt.year
        
        print(f"✅ Data fetched: {full.shape}")
        return full
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def resolve_to_ticker(query: str): return query.strip().upper()

def load_company_info(ticker):
    try:
        t = yf.Ticker(ticker)
        return pd.DataFrame([{"Κεφαλαιοποίηση": t.info.get('marketCap', 0), "Όνομα": t.info.get('longName', ticker)}]), "General"
    except: return pd.DataFrame(), "General"