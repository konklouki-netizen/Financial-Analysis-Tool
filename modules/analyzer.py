# modules/analyzer.py (v4.6 - With Health Score Algorithm)
import pandas as pd
import numpy as np

def calculate_financial_ratios(df: pd.DataFrame, sector: str = "General") -> dict:
    if df.empty:
        return {}

    # Sort & Get Latest
    df = df.sort_values(by='Year', ascending=False).reset_index(drop=True)
    latest = df.iloc[0]
    try:
        prev = df.iloc[1]
    except IndexError:
        prev = latest 

    def safe_div(a, b):
        try:
            val_a = float(a)
            val_b = float(b)
            return val_a / val_b if val_b != 0 else 0
        except (ValueError, TypeError):
            return 0

    results = {}

    # === PILLAR 1: QUALITY ===
    net_income = pd.to_numeric(latest.get('NetIncome', 0), errors='coerce')
    cfo = pd.to_numeric(latest.get('OperatingCashFlow', 0), errors='coerce')
    if pd.isna(net_income): net_income = 0
    if pd.isna(cfo): cfo = 0

    earnings_gap = net_income - cfo
    is_paper_profits = cfo < net_income
    
    results['Pillar_1'] = {
        'Net_Income': net_income,
        'CFO': cfo,
        'Gap': earnings_gap,
        'Is_Paper_Profits': is_paper_profits,
        'Flag': "🔴 RED FLAG" if is_paper_profits else "🟢 OK"
    }

    # === PILLAR 2: LIQUIDITY ===
    revenue = pd.to_numeric(latest.get('Revenue', 0), errors='coerce')
    receivables = pd.to_numeric(latest.get('CurrentAssets', 0), errors='coerce') 
    inventory = pd.to_numeric(latest.get('Inventory', 0), errors='coerce')
    cogs = pd.to_numeric(latest.get('CostOfGoodsSold', 0), errors='coerce')
    payables = pd.to_numeric(latest.get('CurrentLiabilities', 0), errors='coerce') 

    dso = safe_div(receivables, revenue) * 365
    ccc = (safe_div(receivables, revenue) * 365) + \
          (safe_div(inventory, cogs) * 365) - \
          (safe_div(payables, cogs) * 365)
    
    ebit = pd.to_numeric(latest.get('OperatingIncome', 0), errors='coerce')
    interest = abs(pd.to_numeric(latest.get('InterestExpense', 0), errors='coerce'))
    int_coverage = safe_div(ebit, interest)

    results['Pillar_2'] = {
        'DSO': round(dso, 1),
        'CCC': round(ccc, 1),
        'Current_Ratio': round(safe_div(latest.get('CurrentAssets',0), latest.get('CurrentLiabilities',0)), 2),
        'Interest_Coverage': round(int_coverage, 2),
        'Flag_Solvency': "🔴 ZOMBIE FIRM?" if (int_coverage < 1.5 and int_coverage > 0) else "🟢 SOLVENT"
    }

    # === PILLAR 3: DUPONT ===
    total_assets = pd.to_numeric(latest.get('TotalAssets', 0), errors='coerce')
    total_equity = pd.to_numeric(latest.get('TotalEquity', 0), errors='coerce')
    gross_profit = pd.to_numeric(latest.get('GrossProfit', 0), errors='coerce')
    
    net_margin = safe_div(net_income, revenue)
    gross_margin = safe_div(gross_profit, revenue)
    asset_turnover = safe_div(revenue, total_assets)
    equity_multiplier = safe_div(total_assets, total_equity)
    roe = net_margin * asset_turnover * equity_multiplier

    results['Pillar_3'] = {
        'Net_Margin': round(net_margin * 100, 2),
        'Gross_Margin': round(gross_margin * 100, 2),
        'Asset_Turnover': round(asset_turnover, 3),
        'Leverage': round(equity_multiplier, 2),
        'ROE': round(roe * 100, 2),
    }

    # === PILLAR 4: GROWTH ===
    sgr = roe 
    prev_revenue = pd.to_numeric(prev.get('Revenue', 0), errors='coerce')
    sales_growth = safe_div((revenue - prev_revenue), prev_revenue)
    overtrading = sales_growth > (sgr * 1.5)

    results['Pillar_4'] = {
        'SGR': round(sgr * 100, 2),
        'Actual_Growth': round(sales_growth * 100, 2),
        'Overtrading': overtrading
    }

    # === PILLAR 5: VALUATION ===
    market_cap = pd.to_numeric(latest.get('Market Cap', 0), errors='coerce')
    pe_ratio = safe_div(market_cap, net_income) if market_cap > 0 else 0
    total_debt = pd.to_numeric(latest.get('TotalDebt', 0), errors='coerce')
    
    wacc_default = 0.10
    invested_capital = total_equity + total_debt - pd.to_numeric(latest.get('Cash', 0), errors='coerce')
    tax_rate = 0.25 
    nopat = pd.to_numeric(latest.get('OperatingIncome', 0), errors='coerce') * (1 - tax_rate)
    eva = nopat - (invested_capital * wacc_default)

    results['Pillar_5'] = {
        'PE_Ratio': round(pe_ratio, 2),
        'EVA': round(eva / 1_000_000, 2),
        'Invested_Capital': invested_capital,
        'NOPAT': nopat,
        'Value_Creation': "🟢 CREATING" if eva > 0 else "🔴 DESTROYING"
    }

    # === NEW: HEALTH SCORE ALGORITHM (0-100) ===
    score = 0
    # 1. Quality (Max 30)
    if not is_paper_profits: score += 30
    # 2. Solvency (Max 20)
    if int_coverage > 3: score += 20
    elif int_coverage > 1.5: score += 10
    # 3. ROE (Max 20)
    if roe * 100 > 15: score += 20
    elif roe * 100 > 5: score += 10
    # 4. Value Creation (Max 30)
    if eva > 0: score += 30
    
    results['Health_Score'] = score

    return results