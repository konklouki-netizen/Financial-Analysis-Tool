# modules/analyzer.py (v4.7 - Z-Score & Decomposition)
import pandas as pd
import numpy as np

def calculate_financial_ratios(df: pd.DataFrame, sector: str = "General") -> dict:
    if df.empty: return {}

    # Sort
    df = df.sort_values(by='Year', ascending=False).reset_index(drop=True)
    latest = df.iloc[0]
    try: prev = df.iloc[1]
    except IndexError: prev = latest 

    def safe_div(a, b):
        try: return float(a) / float(b) if float(b) != 0 else 0
        except (ValueError, TypeError): return 0

    results = {}

    # === DATA EXTRACTION ===
    net_income = pd.to_numeric(latest.get('NetIncome', 0), errors='coerce')
    cfo = pd.to_numeric(latest.get('OperatingCashFlow', 0), errors='coerce')
    revenue = pd.to_numeric(latest.get('Revenue', 0), errors='coerce')
    total_assets = pd.to_numeric(latest.get('TotalAssets', 0), errors='coerce')
    total_liabilities = pd.to_numeric(latest.get('TotalLiabilities', latest.get('TotalDebt', 0)), errors='coerce') # Fallback
    total_equity = pd.to_numeric(latest.get('TotalEquity', 0), errors='coerce')
    retained_earnings = pd.to_numeric(latest.get('RetainedEarnings', 0), errors='coerce')
    ebit = pd.to_numeric(latest.get('OperatingIncome', 0), errors='coerce')
    market_cap = pd.to_numeric(latest.get('Market Cap', 0), errors='coerce')
    working_capital = pd.to_numeric(latest.get('CurrentAssets', 0), errors='coerce') - pd.to_numeric(latest.get('CurrentLiabilities', 0), errors='coerce')

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
    receivables = pd.to_numeric(latest.get('CurrentAssets', 0), errors='coerce') 
    dso = safe_div(receivables, revenue) * 365
    interest = abs(pd.to_numeric(latest.get('InterestExpense', 0), errors='coerce'))
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

    # === PILLAR 4: GROWTH ===
    sgr = roe 
    prev_rev = pd.to_numeric(prev.get('Revenue', 0), errors='coerce')
    sales_growth = safe_div((revenue - prev_rev), prev_rev)
    overtrading = sales_growth > (sgr * 1.5)
    results['Pillar_4'] = {
        'SGR': round(sgr * 100, 2),
        'Actual_Growth': round(sales_growth * 100, 2),
        'Overtrading': overtrading
    }

    # === PILLAR 5: VALUATION ===
    pe_ratio = safe_div(market_cap, net_income) if market_cap > 0 else 0
    wacc = 0.10
    total_debt = pd.to_numeric(latest.get('TotalDebt', 0), errors='coerce')
    invested_capital = total_equity + total_debt - pd.to_numeric(latest.get('Cash', 0), errors='coerce')
    nopat = ebit * 0.75 # 25% Tax
    eva = nopat - (invested_capital * wacc)

    results['Pillar_5'] = {
        'PE_Ratio': round(pe_ratio, 2),
        'EVA': round(eva / 1e6, 2),
        'Invested_Capital': invested_capital,
        'NOPAT': nopat,
        'Value_Creation': "🟢 CREATING" if eva > 0 else "🔴 DESTROYING"
    }

    # === NEW: ALTMAN Z-SCORE (Bankruptcy Prediction) ===
    # Formula: 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
    A = safe_div(working_capital, total_assets)
    B = safe_div(retained_earnings, total_assets)
    C = safe_div(ebit, total_assets)
    D = safe_div(market_cap, total_liabilities) # Market Value of Equity / Total Liabilities
    E = safe_div(revenue, total_assets)
    
    z_score = (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
    results['Z_Score'] = round(z_score, 2)

    # === HEALTH SCORE ===
    score = 0
    if not is_paper_profits: score += 25
    if int_coverage > 3: score += 15
    elif int_coverage > 1.5: score += 10
    if roe * 100 > 15: score += 20
    if eva > 0: score += 20
    if z_score > 2.99: score += 20 # Safe Zone
    elif z_score > 1.81: score += 10 # Grey Zone
    
    results['Health_Score'] = score

    return results