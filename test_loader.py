# test_loader.py (FINAL STABLE)
import os
import pandas as pd
import yfinance as yf
import requests_cache
from typing import List, Dict, Any

session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'

COLUMN_MAP = {
    'total revenue': 'Revenue', 'revenue': 'Revenue', 'cost of revenue': 'CostOfGoodsSold', 'cost of goods sold': 'CostOfGoodsSold',
    'gross profit': 'GrossProfit', 'operating income': 'OperatingIncome', 'ebit': 'OperatingIncome',
    'net income': 'NetIncome', 'ebitda': 'EBITDA', 'basic eps': 'BasicEPS',
    'total assets': 'TotalAssets', 'total current assets': 'CurrentAssets',
    'total liabilities': 'TotalLiabilities', 'total current liabilities': 'CurrentLiabilities',
    'total equity': 'TotalEquity', 'stockholders equity': 'TotalEquity',
    'total debt': 'TotalDebt', 'long term debt': 'TotalDebt', 'cash': 'Cash', 'cash and cash equivalents': 'Cash',
    'inventory': 'Inventory', 'net receivables': 'Receivables', 'accounts payable': 'Payables',
    'net ppe': 'NetPPE', 'property plant equipment': 'NetPPE', 'interest expense': 'InterestExpense',
    'operating cash flow': 'OperatingCashFlow', 'capital expenditure': 'CapitalExpenditures', 'capex': 'CapitalExpenditures'
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
        try:
            t = yf.Ticker(source, session=session)
            inc = t.financials.T; bal = t.balance_sheet.T; cf = t.cashflow.T
            full = pd.concat([inc, bal, cf], axis=1)
            full = full.loc[:, ~full.columns.duplicated()]
            full.reset_index(inplace=True)
            if 'index' in full.columns: full.rename(columns={'index': 'Date'}, inplace=True)
            return [{"title": "Yahoo Data", "table": full}]
        except: return []
    return []

def resolve_to_ticker(query: str): return query.strip().upper()
def load_company_info(ticker):
    try:
        t = yf.Ticker(ticker, session=session)
        return pd.DataFrame([{"Κεφαλαιοποίηση": t.info.get('marketCap', 0), "Όνομα": t.info.get('longName', ticker)}]), "General"
    except: return pd.DataFrame(), "General"