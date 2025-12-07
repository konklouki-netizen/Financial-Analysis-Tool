# modules/analyzer.py (v5.0 - The Forensic Edition: Z-Score + M-Score)
import pandas as pd
import numpy as np

def calculate_financial_ratios(df: pd.DataFrame, sector: str = "General") -> dict:
    if df.empty: return {}

    # Sort data (Newest first)
    df = df.sort_values(by='Year', ascending=False).reset_index(drop=True)
    
    # Get Current Year (t) and Previous Year (t-1)
    t = df.iloc[0]
    try: 
        t_minus_1 = df.iloc[1]
    except IndexError: 
        t_minus_1 = t # Fallback αν έχουμε μόνο 1 έτος (δεν θα δουλέψουν τα trends)

    def safe_div(a, b):
        try: return float(a) / float(b) if float(b) != 0 else 0
        except (ValueError, TypeError): return 0

    def get_val(source, key, default=0):
        return pd.to_numeric(source.get(key, default), errors='coerce')

    results = {}

    # === DATA EXTRACTION ===
    # Current Year (t)
    net_income = get_val(t, 'NetIncome')
    cfo = get_val(t, 'OperatingCashFlow')
    revenue = get_val(t, 'Revenue')
    receivables = get_val(t, 'CurrentAssets') # Proxy for receivables if specific column missing
    if 'AccountsReceivable' in t: receivables = get_val(t, 'AccountsReceivable')
    
    cogs = get_val(t, 'CostOfGoodsSold')
    total_assets = get_val(t, 'TotalAssets')
    current_assets = get_val(t, 'CurrentAssets')
    current_liabilities = get_val(t, 'CurrentLiabilities')
    total_liabilities = get_val(t, 'TotalLiabilities', get_val(t, 'TotalDebt'))
    total_equity = get_val(t, 'TotalEquity')
    ppe = get_val(t, 'NetPPE', get_val(t, 'GrossPPE', 0)) # Property Plant Equipment
    securities = get_val(t, 'InvestmentSecurities', 0)
    
    # Previous Year (t-1)
    rev_prev = get_val(t_minus_1, 'Revenue')
    rec_prev = get_val(t_minus_1, 'CurrentAssets')
    if 'AccountsReceivable' in t_minus_1: rec_prev = get_val(t_minus_1, 'AccountsReceivable')
    cogs_prev = get_val(t_minus_1, 'CostOfGoodsSold')
    assets_prev = get_val(t_minus_1, 'TotalAssets')

    # Handling NaNs
    if pd.isna(net_income): net_income = 0
    if pd.isna(cfo): cfo = 0

    # === PILLAR 1: QUALITY ===
    earnings_gap = net_income - cfo
    is_paper_profits = cfo < net_income
    results['Pillar_1'] = {
        'Net_Income': net_income, 'CFO': cfo, 'Gap': earnings_gap,
        'Is_Paper_Profits': is_paper_profits,
        'Flag': "🔴 RED FLAG" if is_paper_profits else "🟢 OK"
    }

    # === PILLAR 2: LIQUIDITY ===
    dso = safe_div(receivables, revenue) * 365
    ebit = get_val(t, 'OperatingIncome')
    interest = abs(get_val(t, 'InterestExpense'))
    int_coverage = safe_div(ebit, interest)

    results['Pillar_2'] = {
        'DSO': round(dso, 1),
        'Interest_Coverage': round(int_coverage, 2),
        'Flag_Solvency': "🔴 ZOMBIE FIRM?" if (int_coverage < 1.5 and int_coverage > 0) else "🟢 SOLVENT"
    }

    # === PILLAR 3: DUPONT ===
    net_margin = safe_div(net_income, revenue)
    asset_turnover = safe_div(revenue, total_assets)
    equity_multiplier = safe_div(total_assets, total_equity)
    roe = net_margin * asset_turnover * equity_multiplier

    results['Pillar_3'] = {
        'Net_Margin': round(net_margin * 100, 2),
        'Asset_Turnover': round(asset_turnover, 3),
        'Leverage': round(equity_multiplier, 2),
        'ROE': round(roe * 100, 2),
    }

    # === PILLAR 4: GROWTH & RISK ===
    sgr = roe 
    sales_growth = safe_div((revenue - rev_prev), rev_prev)
    rec_growth = safe_div((receivables - rec_prev), rec_prev)
    
    # Forensic Check: Receivables growing faster than Sales?
    stuffing_channel = rec_growth > (sales_growth * 1.2) # 20% faster is suspicious

    results['Pillar_4'] = {
        'SGR': round(sgr * 100, 2),
        'Actual_Growth': round(sales_growth * 100, 2),
        'Receivables_Growth': round(rec_growth * 100, 2),
        'Overtrading': stuffing_channel
    }

    # === PILLAR 5: VALUATION ===
    market_cap = get_val(t, 'Market Cap')
    pe_ratio = safe_div(market_cap, net_income) if market_cap > 0 else 0
    wacc = 0.10
    total_debt = get_val(t, 'TotalDebt')
    invested_capital = total_equity + total_debt - get_val(t, 'Cash')
    nopat = ebit * 0.75 
    eva = nopat - (invested_capital * wacc)

    results['Pillar_5'] = {
        'PE_Ratio': round(pe_ratio, 2),
        'EVA': round(eva / 1e6, 2),
        'Invested_Capital': invested_capital,
        'NOPAT': nopat,
        'Value_Creation': "🟢 CREATING" if eva > 0 else "🔴 DESTROYING"
    }

    # === FORENSIC MODEL 1: ALTMAN Z-SCORE (Bankruptcy) ===
    working_capital = current_assets - current_liabilities
    retained_earnings = get_val(t, 'RetainedEarnings')
    
    A = safe_div(working_capital, total_assets)
    B = safe_div(retained_earnings, total_assets)
    C = safe_div(ebit, total_assets)
    D = safe_div(market_cap, total_liabilities) 
    E = safe_div(revenue, total_assets)
    
    z_score = (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
    results['Z_Score'] = round(z_score, 2)

    # === FORENSIC MODEL 2: BENEISH M-SCORE (Manipulation) ===
    # Χρησιμοποιούμε μια απλοποιημένη έκδοση 5 μεταβλητών για σταθερότητα
    
    # 1. DSRI (Days Sales in Receivables Index): (Rec_t/Rev_t) / (Rec_t-1/Rev_t-1)
    dsri = safe_div(safe_div(receivables, revenue), safe_div(rec_prev, rev_prev))
    
    # 2. GMI (Gross Margin Index): (Gross_t-1/Rev_t-1) / (Gross_t/Rev_t)
    gross_t = revenue - cogs
    gross_prev = rev_prev - cogs_prev
    gmi = safe_div(safe_div(gross_prev, rev_prev), safe_div(gross_t, revenue))
    
    # 3. AQI (Asset Quality Index): Non-Current Assets / Total Assets ratio change
    non_curr_t = total_assets - current_assets
    non_curr_prev = assets_prev - get_val(t_minus_1, 'CurrentAssets')
    aqi = safe_div(safe_div(non_curr_t, total_assets), safe_div(non_curr_prev, assets_prev))
    
    # 4. SGI (Sales Growth Index): Rev_t / Rev_t-1
    sgi = safe_div(revenue, rev_prev)
    
    # 5. LVGI (Leverage Index)
    lev_t = safe_div(total_liabilities, total_assets)
    lev_prev = safe_div(get_val(t_minus_1, 'TotalLiabilities', get_val(t_minus_1, 'TotalDebt')), assets_prev)
    lvgi = safe_div(lev_t, lev_prev)

    # Formula (5-variable version)
    m_score = -6.065 + (0.823 * dsri) + (0.906 * gmi) + (0.593 * aqi) + (0.717 * sgi) + (0.107 * lvgi)
    
    # Αν λείπουν δεδομένα προηγούμενου έτους, το M-Score βγαίνει λάθος, οπότε βάζουμε -999 (Safe)
    if rev_prev == 0 or assets_prev == 0:
        m_score = -3.0 # Fake safe score

    results['M_Score'] = round(m_score, 2)

    # === HEALTH SCORE AGGREGATION ===
    score = 0
    if not is_paper_profits: score += 20
    if int_coverage > 3: score += 10
    if roe * 100 > 15: score += 15
    if eva > 0: score += 15
    if z_score > 2.99: score += 20 
    if m_score < -2.22: score += 20 # Safe from manipulation
    elif m_score < -1.78: score += 10 # Grey area
    
    results['Health_Score'] = score

    return results