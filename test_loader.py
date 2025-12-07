# test_loader.py (v5.1 - Robust Cloud Loader)
import os
import sys
import pandas as pd
import yfinance as yf
import requests_cache
import re 
import fitz  # PyMuPDF
from typing import List, Dict, Any

# === Anti-Blocking Session ===
# Δημιουργούμε ένα session για να ξεγελάσουμε την Yahoo ότι είμαστε browser
session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'

# -----------------------------
# 🔹 COLUMN MAPPING (CFA Compatible)
# -----------------------------
COLUMN_MAP = {
    # P&L
    'total revenue': 'Revenue', 'revenue': 'Revenue', 'operating revenue': 'Revenue',
    'cost of revenue': 'CostOfGoodsSold', 'cost of goods sold': 'CostOfGoodsSold',
    'gross profit': 'GrossProfit',
    'operating income': 'OperatingIncome', 'ebit': 'OperatingIncome',
    'net income': 'NetIncome', 'net income common stockholders': 'NetIncome',
    'interest expense': 'InterestExpense',
    'ebitda': 'EBITDA',
    'basic eps': 'BasicEPS',
    
    # Balance Sheet
    'total assets': 'TotalAssets',
    'total current assets': 'CurrentAssets',
    'total liabilities': 'TotalLiabilities', 'total current liabilities': 'CurrentLiabilities',
    'total equity': 'TotalEquity', 'stockholders equity': 'TotalEquity', 'total capitalization': 'TotalEquity',
    'total debt': 'TotalDebt', 'long term debt': 'TotalDebt',
    'cash': 'Cash', 'cash and cash equivalents': 'Cash',
    'inventory': 'Inventory',
    'net receivables': 'Receivables', 'accounts receivable': 'Receivables',
    'accounts payable': 'Payables',
    'net ppe': 'NetPPE', 'property plant equipment': 'NetPPE',
    'retained earnings': 'RetainedEarnings',
    'ordinary shares number': 'ShareIssued', 'share issued': 'ShareIssued',
    
    # Cash Flow
    'operating cash flow': 'OperatingCashFlow', 'total cash from operating activities': 'OperatingCashFlow',
    'investing cash flow': 'InvestingCashFlow', 'total cashflows from investing activities': 'InvestingCashFlow',
    'financing cash flow': 'FinancingCashFlow', 'total cash from financing activities': 'FinancingCashFlow',
    'capital expenditure': 'CapitalExpenditures', 'capex': 'CapitalExpenditures',
    'free cash flow': 'FreeCashFlow',
    'cash dividends paid': 'CashDividendsPaid'
}

def normalize_dataframe(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    if df.empty: return df
    norm_df = df.copy()
    
    # Καθαρισμός ονομάτων (lowercase, strip)
    clean_cols_map = {str(c).strip().lower().replace('  ', ' '): c for c in df.columns}
    
    # Rename
    rename_dict = {}
    for raw_key, standard_key in COLUMN_MAP.items():
        # Ψάχνουμε αν το κλειδί υπάρχει στα καθαρισμένα ονόματα
        for clean_col, original_col in clean_cols_map.items():
            if raw_key == clean_col:
                rename_dict[original_col] = standard_key
    
    norm_df.rename(columns=rename_dict, inplace=True)
    
    # Ensure Year
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
        # Χρήση του session για να αποφύγουμε το 403 Forbidden
        t = yf.Ticker(ticker, session=session)
        
        inc = t.financials.T
        bal = t.balance_sheet.T
        cf = t.cashflow.T
        
        dfs = [d for d in [inc, bal, cf] if not d.empty]
        if not dfs: return pd.DataFrame()
        
        full = pd.concat(dfs, axis=1)
        full = full.loc[:, ~full.columns.duplicated()]
        
        full.reset_index(inplace=True)
        if 'index' in full.columns: full.rename(columns={'index': 'Date'}, inplace=True)
        
        if 'Date' in full.columns:
            full['Date'] = pd.to_datetime(full['Date'])
            full['Year'] = full['Date'].dt.year
            
        return full
    except Exception as e:
        print(f"❌ Error fetching Yahoo data: {e}")
        return pd.DataFrame()

def load_data_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    # Placeholder για το PDF logic που έχεις ήδη
    try:
        doc = fitz.open(file_path)
        return [] # Εδώ θα μπει ο κώδικας του PDF αν χρειαστεί
    except: return []

def resolve_to_ticker(query: str):
    return query.strip().upper()

def load_company_info(ticker):
    try:
        t = yf.Ticker(ticker, session=session)
        info = t.info
        return pd.DataFrame([{"Κεφαλαιοποίηση": info.get('marketCap', 0), "Όνομα": info.get('longName', ticker)}]), "General"
    except:
        return pd.DataFrame(), "General"