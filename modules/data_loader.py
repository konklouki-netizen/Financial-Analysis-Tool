import os
import pandas as pd
import yfinance as yf
import requests

# -----------------------------------------
# 📦 Κεντρική συνάρτηση
# -----------------------------------------
def get_company_df(source, source_type="auto", api_key=None):
    """
    Επιστρέφει DataFrame με οικονομικά δεδομένα εταιρείας από διάφορες πηγές:
    - Yahoo Finance
    - CSV / Excel / PDF
    - AlphaVantage / Finnhub / Polygon / Investing
    Αν source_type='auto', το πρόγραμμα αναγνωρίζει μόνο του την πηγή.
    """

    # 🔹 Αυτόματη αναγνώριση τύπου πηγής
    if source_type == "auto":
        if isinstance(source, str):
            ext = os.path.splitext(source)[1].lower()
            if ext == ".csv":
                source_type = "csv"
            elif ext in [".xlsx", ".xls"]:
                source_type = "excel"
            elif ext == ".pdf":
                source_type = "pdf"
            elif len(source) <= 6:
                source_type = "yahoo"
            else:
                print("⚠️ Δεν αναγνωρίστηκε η πηγή, χρησιμοποιούμε Yahoo ως προεπιλογή.")
                source_type = "yahoo"
        else:
            raise TypeError("❌ Το 'source' πρέπει να είναι string.")

    # -----------------------------------------
    # 🔹 Επιλογή πηγής
    # -----------------------------------------
    if source_type == "yahoo":
        print("⚡ Λήψη δεδομένων από Yahoo Finance...")
        return get_yahoo_data(source)

    elif source_type == "csv":
        print("📂 Φόρτωση δεδομένων από CSV...")
        return load_csv(source)

    elif source_type == "excel":
        print("📘 Φόρτωση δεδομένων από Excel...")
        return load_excel(source)

    elif source_type == "pdf":
        print("📄 Ανάγνωση δεδομένων από PDF...")
        return load_pdf(source)

    elif source_type == "alphavantage":
        print("⚡ Λήψη δεδομένων από Alpha Vantage...")
        return get_alpha_vantage_data(source, api_key)

    elif source_type == "finnhub":
        print("⚡ Λήψη δεδομένων από Finnhub...")
        return get_finnhub_data(source, api_key)

    elif source_type == "polygon":
        print("⚡ Λήψη δεδομένων από Polygon.io...")
        return get_polygon_data(source, api_key)

    elif source_type == "investing":
        print("⚡ Λήψη δεδομένων από Investing.com (υπό ανάπτυξη)...")
        return get_investing_data(source, api_key)

    else:
        raise ValueError(f"❌ Μη υποστηριζόμενη πηγή: {source_type}")


# -----------------------------------------
# 🔹 Τοπικές πηγές (CSV, Excel, PDF)
# -----------------------------------------
def load_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        if 'Year' not in df.columns:
            df['Year'] = range(1, len(df) + 1)
        return df
    except Exception as e:
        print("⚠️ Σφάλμα στη φόρτωση CSV:", e)
        return pd.DataFrame()


def load_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        if 'Year' not in df.columns:
            df['Year'] = range(1, len(df) + 1)
        return df
    except Exception as e:
        print("⚠️ Σφάλμα στη φόρτωση Excel:", e)
        return pd.DataFrame()


def load_pdf(file_path):
    try:
        import tabula
        dfs = tabula.read_pdf(file_path, pages='all', multiple_tables=True)
        df = pd.concat(dfs, ignore_index=True)
        if 'Year' not in df.columns:
            df['Year'] = range(1, len(df) + 1)
        return df
    except Exception as e:
        print("⚠️ Σφάλμα στην ανάγνωση PDF:", e)
        return pd.DataFrame()


# -----------------------------------------
# 🔹 Πηγές API
# -----------------------------------------
def get_yahoo_data(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        fin = ticker_obj.financials.T
        bs = ticker_obj.balance_sheet.T
        cf = ticker_obj.cashflow.T
        df = pd.concat([fin, bs, cf], axis=1)
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'Date'}, inplace=True)
        df['Year'] = pd.to_datetime(df['Date']).dt.year
        return df
    except Exception as e:
        print("⚠️ Σφάλμα στη λήψη δεδομένων από Yahoo:", e)
        return pd.DataFrame()


def get_alpha_vantage_data(symbol, api_key):
    if not api_key:
        print("⚠️ Απαιτείται API key για Alpha Vantage.")
        return pd.DataFrame()
    try:
        url = f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={symbol}&apikey={api_key}"
        r = requests.get(url)
        data = r.json()
        df = pd.DataFrame(data.get("annualReports", []))
        return df
    except Exception as e:
        print("⚠️ Σφάλμα από Alpha Vantage:", e)
        return pd.DataFrame()


def get_finnhub_data(symbol, api_key):
    if not api_key:
        print("⚠️ Απαιτείται API key για Finnhub.")
        return pd.DataFrame()
    try:
        url = f"https://finnhub.io/api/v1/stock/financials-reported?symbol={symbol}&token={api_key}"
        r = requests.get(url)
        data = r.json()
        df = pd.json_normalize(data.get('data', []))
        return df
    except Exception as e:
        print("⚠️ Σφάλμα από Finnhub:", e)
        return pd.DataFrame()


def get_polygon_data(symbol, api_key):
    if not api_key:
        print("⚠️ Απαιτείται API key για Polygon.io.")
        return pd.DataFrame()
    try:
        url = f"https://api.polygon.io/v2/reference/financials/{symbol}?apiKey={api_key}"
        r = requests.get(url)
        data = r.json()
        df = pd.json_normalize(data.get("results", []))
        return df
    except Exception as e:
        print("⚠️ Σφάλμα από Polygon:", e)
        return pd.DataFrame()


def get_investing_data(symbol, api_key=None):
    print("⚠️ Το Investing API απαιτεί web scraping ή εμπορικό API — υπό ανάπτυξη.")
    return pd.DataFrame()


# -----------------------------------------
# 🔹 Μελλοντική επέκταση: Δείκτες Κλάδου
# -----------------------------------------
def get_sector_data(sector_name, source_type="yahoo", api_key=None):
    """
    Λήψη μέσων οικονομικών δεικτών για έναν κλάδο (π.χ. Banking, Energy).
    Μπορεί να υπολογιστεί δυναμικά με βάση πολλές εταιρείες του ίδιου κλάδου.
    """
    print(f"🌍 Λήψη δεδομένων για κλάδο: {sector_name}... (υπό ανάπτυξη)")
    return pd.DataFrame()
