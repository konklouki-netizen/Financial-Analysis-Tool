# test_loader.py (v3.6 - Προσθήκη "Χώρας")
import os
import sys
import pandas as pd
import yfinance as yf
import requests
from typing import Optional, Tuple, List, Dict, Any
import re 
import io

# === === === === === === === === ===
# === Ο ΝΕΟΣ ΜΑΣ ΚΙΝΗΤΗΡΑΣ F1 ===
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Title, NarrativeText, Text, Table, Element
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

def normalize_dataframe(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    """
    "Ο Μεταφραστής"
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
    
    # === PDF SPECIAL HANDLING (v3.0) ===
    # Αυτή η λογική "Pivot" θα τρέξει μόνο για PDF (και CSV)
    # v3.5: Τώρα τρέχει ΜΟΝΟ για PDF
    if source_type == "pdf" or (source_type in ["csv", "excel"] and 'Year' not in df.columns and 'Date' not in df.columns):
        print(f"  [Normalize] -> Εντοπίστηκε {source_type}. Εκτέλεση 'Pivot'...")
        try:
            # 1. Βρίσκουμε την πρώτη στήλη που έχει τα ονόματα (π.χ. 'Total Assets')
            # (Καθαρίζουμε το όνομα από τυχόν NaN που έγιναν string)
            label_col = str(df.columns[0]).strip()
            if label_col == "" or label_col.lower() == "nan" or label_col.lower().startswith("unnamed"):
                # Αν η πρώτη στήλη είναι άχρηστη, δοκιμάζουμε τη δεύτερη
                print(f"  [Normalize] -> Warning: Η πρώτη στήλη '{label_col}' είναι άχρηστη. Δοκιμή της 2ης στήλης.")
                label_col = str(df.columns[1]).strip()
                if label_col == "" or label_col.lower() == "nan" or label_col.lower().startswith("unnamed"):
                    print("  [Normalize] -> ❌ ΑΠΟΤΥΧΙΑ 'Pivot': Δεν βρέθηκε στήλη για τα labels.")
                    return pd.DataFrame()
            
            # 2. Τη θέτουμε ως Index
            # v3.5 Fix: Χειρισμός διπλότυπων ετικετών (π.χ. 'Total', 'Total')
            if df[label_col].duplicated().any():
                # Δίνουμε μοναδικά ονόματα (π.χ. 'Total', 'Total_2')
                df[label_col] = df[label_col].astype(str).str.strip()
                
                # (v3.6) Πιο απλή προσέγγιση για μοναδικότητα
                df[label_col] = df.groupby(label_col).cumcount().astype(str) + '_' + df[label_col]
                df[label_col] = df[label_col].str.replace('0_', '', n=1) # Αντικαθιστά το πρώτο '0_Total' -> 'Total'
                
            df = df.set_index(label_col)
            
            # 3. "Γυρνάμε" (Transpose) τον πίνακα
            df = df.T
            
            # 4. Επαναφέρουμε το index (που τώρα έχει τις χρονιές/ημερομηνίες)
            df = df.reset_index()
            
            # 5. Προσπαθούμε να βρούμε το 'Year'
            year_col = str(df.columns[0]) # Υποθέτουμε ότι είναι η πρώτη στήλη
            
            # Βρίσκει 4-ψήφιο αριθμό που *δεν* είναι μέσα σε $
            df['Year'] = df[year_col].astype(str).str.extract(r'(?<!\d\s)(\d{4})(?!\d)')
            
            df = df.dropna(subset=['Year']) # Πέταξε γραμμές που δεν είναι χρονιές
            if df.empty:
                print(f"  [Normalize] -> ❌ ΑΠΟΤΥΧΙΑ 'Pivot': Δεν βρέθηκαν χρονιές στο header (στήλη '{year_col}').")
                return pd.DataFrame()

            print(f"  [Normalize] -> 'Pivot' επιτυχής.")
        except Exception as e:
            print(f"  [Normalize] -> ❌ ΑΠΟΤΥΧΙΑ 'Pivot': {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame() # Αποτυχία
    
    elif source_type == "yahoo":
         df = df # (Ο πίνακας είναι ήδη σωστός)
    
    # v3.6: Ειδικός χειρισμός για CSV/Excel που *έχουν* χρονιά
    elif source_type in ["csv", "excel"]:
        if 'Year' not in df.columns and 'Date' in df.columns:
            df['Year'] = pd.to_datetime(df['Date']).dt.year
        df = df # (Ο πίνακας είναι ήδη σωστός)


    # (Ο υπόλοιπος κώδικας είναι ο ίδιος με πριν)
    for col in ['Year', 'Date']:
        if col in df.columns and col not in normalized_df.columns:
            normalized_df[col] = df[col]

    # Καθαρίζουμε τα ονόματα στηλών (π.χ. αφαίρεση \n) *πριν* το mapping
    df.columns = [str(col).replace('\n', ' ').strip() for col in df.columns]
    df_columns_stripped = {str(col).strip(): col for col in df.columns}
        
    for source_col, standard_col in mapping.items():
        matching_source_col = None
        
        # Καθαρίζουμε το source_col (από το MAP) για σύγκριση
        source_col_clean = str(source_col).strip()
        
        # 1. Απλή αντιστοίχιση (π.χ. 'Total Assets' == 'Total Assets')
        if source_col_clean in df_columns_stripped:
            matching_source_col = df_columns_stripped[source_col_clean]
        
        # 2. Αν δεν βρεθεί, κάνουμε lower-case σύγκριση
        elif source_type in ["csv", "excel", "pdf", "yahoo"]: # v3.6: Προσθήκη Yahoo
            source_col_lower = source_col_clean.lower()
            for df_col_stripped, df_col_original in df_columns_stripped.items():
                if df_col_stripped.lower() == source_col_lower:
                    matching_source_col = df_col_original
                    break

        if matching_source_col:
            if standard_col not in normalized_df.columns:
                # Καθαρίζουμε τους αριθμούς
                # v3.4: Εφαρμογή του clean_value_unstructured ΚΑΙ εδώ
                clean_col = pd.to_numeric(df[matching_source_col].astype(str).map(clean_value_unstructured), errors='coerce')
                normalized_df[standard_col] = clean_col

    if 'TotalLiabilities' not in normalized_df.columns and 'TotalDebt' in normalized_df.columns:
        normalized_df['TotalLiabilities'] = normalized_df['TotalDebt']
        print("  [Normalize] Info: 'TotalLiabilities' not found. Using 'TotalDebt' as a proxy.")

    return normalized_df

# -----------------------------
# 🔹 Utilities: (Search, Premium, κλπ.)
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
# 🔹 PDF Data Extractor (v3.5 - Ο "Κυνηγός" Κλειδιών)
# -----------------------------

# Λέξεις-κλειδιά που ορίζουν έναν "Κύριο Τίτλο", ακόμα κι αν το AI τα μπερδέψει
# v3.5: Ο "Κυνηγός" Κλειδιών
MAIN_TITLE_KEYWORDS = [
    'balance sheet', 'ισολογισμοσ', 'financial position',
    'income statement', 'κατασταση αποτελεσματων', 'results of operations',
    'cash flow', 'ταμειακεσ ροεσ'
]

def is_subtitle(text: str) -> bool:
    """
    v3.5: Ελέγχει αν ένα κείμενο μοιάζει με "υπότιτλο" (π.χ. "(In millions)")
    αλλά ΔΕΝ είναι ένας από τους κύριους τίτλους.
    """
    text_clean = text.strip()
    if not text_clean or len(text_clean) == 0:
        return False
        
    # v3.5: Αν είναι ένας από τους ΚΥΡΙΟΥΣ τίτλους, ΔΕΝ είναι υπότιτλος
    text_lower = text_clean.lower()
    if any(key in text_lower for key in MAIN_TITLE_KEYWORDS):
        return False
        
    is_short = len(text_clean) < 100
    not_sentence = not text_clean.endswith('.')
    is_header_like = (
        text_clean.startswith(('(', '$')) or
        text_clean.endswith(':') or
        text_clean.isupper() or
        bool(re.match(r'^\(?\s*In millions', text_clean, re.IGNORECASE)) or
        bool(re.match(r'^\s*\d{4}\s*$', text_clean)) # "2023"
    )
    
    return is_short and not_sentence and is_header_like

def clean_value_unstructured(val):
    """ 
    Καθαριστής ειδικά για το output του unstructured.
    (Τώρα καλείται και από το normalize_dataframe)
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


def load_data_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    v3.5: Ο "Κυνηγός" Κλειδιών.
    Σαρώνει το PDF και επιστρέφει μια ΛΙΣΤΑ από "πακέτα" (τίτλος + πίνακας).
    """
    print(f"📄 Έναρξη έξυπνης σάρωσης PDF (v3.5 - F1 Engine): {file_path}")
    
    all_data = []
    current_main_title = "Untitled" # Ο Κύριος Τίτλος (π.χ. "INCOME STATEMENTS")
    current_subtitle = ""    # Ο Υπότιτλος (π.χ. "(In millions)")

    try:
        # 1. Ο "Κινητήρας F1" σαρώνει το PDF
        elements = partition_pdf(
            file_path, 
            strategy="hi_res", 
            infer_table_structure=True
        )

        # 2. v3.5: "Παντρεύουμε" Τίτλους και Πίνακες
        for el in elements:
            
            # v3.5: Ο "Κυνηγός" Κλειδιών
            # (Αναβαθμίζει ένα "Text" σε "Κύριο Τίτλο" αν ταιριάζει)
            is_main_title_from_text = False
            if isinstance(el, (Text, NarrativeText)):
                text_lower = el.text.strip().lower()
                if any(key in text_lower for key in MAIN_TITLE_KEYWORDS):
                    current_main_title = el.text.strip()
                    current_subtitle = "" # Κάνουμε reset τον υπότιτλο
                    print(f"  > (Debug) Βρέθηκε ΚΥΡΙΟΣ Τίτλος (από Κείμενο): '{current_main_title}'")
                    is_main_title_from_text = True
            
            # === === === === ===
            
            if isinstance(el, Title):
                current_main_title = el.text.strip()
                current_subtitle = "" # Κάνουμε reset τον υπότιτλο
                print(f"  > (Debug) Βρέθηκε ΚΥΡΙΟΣ Τίτλος: '{current_main_title}'")
            
            elif isinstance(el, Text) and not is_main_title_from_text:
                # Αν δεν είναι Κύριος Τίτλος, ίσως είναι Υπότιτλος;
                if is_subtitle(el.text):
                    current_subtitle = el.text.strip()
                    print(f"  > (Debug) Βρέθηκε Κείμενο-Υπότιτλος: '{current_subtitle}'")
            
            elif isinstance(el, Table):
                # ΒΡΗΚΑΜΕ ΠΙΝΑΚΑ! Ας τον "παντρέψουμε".
                if current_subtitle:
                    full_title = f"{current_main_title} - {current_subtitle}"
                else:
                    full_title = current_main_title
                
                print(f"  > Βρέθηκε Πίνακας (ML) (Ανήκει στον τίτλο: '{full_title}')...")
                
                html_table = getattr(el.metadata, 'text_as_html', None)
                if not html_table:
                    print("  -> Warning: Βρέθηκε πίνακας ML, αλλά λείπει το text_as_html.")
                    continue
                    
                # Το Pandas διαβάζει το HTML και το κάνει DataFrame
                dfs = pd.read_html(io.StringIO(html_table))
                if not dfs:
                    print("  -> Warning: Το Pandas απέτυχε να διαβάσει το HTML του πίνακα.")
                    continue
                
                table_df = dfs[0]

                # === Καθαρισμός του πίνακα (πριν τον στείλουμε) ===
                try:
                    # 1. Βρίσκουμε το σωστό header
                    header_idx = 0
                    # (Αν η πρώτη γραμμή είναι τελείως κενή ή γεμάτη NaN)
                    if not table_df.empty and table_df.iloc[0].isnull().all(): 
                        header_idx = 1
                    
                    if header_idx >= len(table_df):
                         print(f"  -> Warning: Παράλειψη πίνακα (τίτλος: {full_title}) - Δεν βρέθηκε header.")
                         continue

                    new_header = table_df.iloc[header_idx]
                    df_data = table_df.iloc[header_idx+1:]
                    
                    # (Έλεγχος αν τα δεδομένα είναι κενά)
                    if df_data.empty:
                        print(f"  -> Warning: Παράλειψη πίνακα (τίτλος: {full_title}) - Βρέθηκε header αλλά όχι δεδομένα.")
                        continue
                        
                    df_data.columns = new_header
                    
                    # 2. Καθαρίζουμε τους αριθμούς
                    df_clean = df_data.apply(lambda col: col.map(clean_value_unstructured))
                    
                    # 3. Εξυγίανση στηλών (πριν την ένωση)
                    df_sanitized = sanitize_columns(df_clean)
                    
                    # 4. Αποθήκευση του "πακέτου"
                    all_data.append({"title": full_title, "table": df_sanitized})

                except Exception as e:
                    print(f"  -> Warning: Αποτυχία καθαρισμού πίνακα (τίτλος: {full_title}): {e}")
                    # (Αν αποτύχει ο καθαρισμός, στέλνουμε τον "βρώμικο" πίνακα)
                    all_data.append({"title": full_title, "table": table_df})
        
        if not all_data:
            print("⚠️ Ο Κινητήρας F1 (unstructured) δεν βρήκε πίνακες.")
            return []

        print(f"  Επιτυχία! Βρέθηκαν {len(all_data)} 'πακέτα' (τίτλος/πίνακας).")
        return all_data

    except Exception as e:
        print(f"❌ Σφάλμα κατά την έξυπνη επεξεργασία του PDF (v3.5): {e}")
        import traceback
        traceback.print_exc()
        return [] # Επιστροφή κενής λίστας

# -----------------------------
# 🔹 Loader για διάφορες πηγές
# -----------------------------
def get_company_df(source: str, source_type: str = "yahoo", api_key: Optional[str] = None, period: str = "5y") -> List[Dict[str, Any]]:
    """
    v3.5: ΕΠΙΣΤΡΕΦΕΙ ΠΑΝΤΑ ΛΙΣΤΑ ΜΕ "ΠΑΚΕΤΑ" [ {"title": ..., "table": ...} ]
    """
    source_type = source_type.lower()

    if source_type == "yahoo":
        print("⚡ Λήψη δεδομένων από Yahoo Finance...")
        # v3.5: Το Yahoo ΔΕΝ επιστρέφει λίστα. Το μετατρέπουμε.
        yahoo_df = get_yahoo_data(source, period=period)
        if yahoo_df.empty:
            return []
        # Το "πακετάρουμε" για να ταιριάζει με το PDF
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
                
            # v3.5: Το "πακετάρουμε" κι αυτό
            return [{"title": f"File Data ({source_type})", "table": df}]
            
        except Exception as e:
            print(f"⚠️ Σφάλμα ανάγνωσης αρχείου: {e}")
            if "openpyxl" in str(e):
                print("--- HINT: Μήπως λείπει η βιβλιοθήκη 'openpyxl'; Τρέξε 'pip install openpyxl' ---")
            return []
    
    elif source_type == "pdf":
        print(f"📂 Φόρτωση δεδομένων από PDF (F1 Engine v3.5)...")
        # 1. Φορτώνουμε τα raw data από το PDF (με τον v3.5 F1 Engine)
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
    v3.5: Τώρα επιστρέφει ΕΝΑ DataFrame, έτοιμο για "Μετάφραση".
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
            
        # v3.3 Fix: Χειρισμός διπλότυπων στηλών από το Yahoo (π.χ. 'Cost Of Revenue')
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
        
        # v3.5: Ο "Μεταφραστής" καλείται πλέον στο app.py
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
            "Χώρα": country, # <-- v3.6: Η ΝΕΑ ΠΡΟΣΘΗΚΗ
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