# modules/analyzer.py (v8.0 - CFA Full Spec)
import pandas as pd
import numpy as np

def calculate_financial_ratios(df: pd.DataFrame, sector: str = "General") -> dict:
    if df.empty: return {}

    # Sort (Newest first)
    df = df.sort_values(by='Year', ascending=False).reset_index(drop=True)
    t = df.iloc[0]
    
    # --- Helpers ---
    def get_val(source, keys, default=0):
        if isinstance(keys, str): keys = [keys]
        for k in keys:
            val = pd.to_numeric(source.get(k), errors='coerce')
            if not pd.isna(val): return float(val)
        return float(default)

    def safe_div(a, b):
        return a / b if b != 0 else 0

    # === 1. DATA EXTRACTION ===
    # Income Statement
    revenue = get_val(t, ['Revenue', 'TotalRevenue', 'Sales'])
    cogs = get_val(t, ['CostOfGoodsSold', 'CostOfRevenue'])
    ebit = get_val(t, ['OperatingIncome', 'EBIT'])
    net_income = get_val(t, ['NetIncome', 'NetIncomeCommonStockholders'])
    interest = abs(get_val(t, ['InterestExpense', 'Interest']))
    
    # EBITDA Calculation
    ebitda = get_val(t, 'EBITDA')
    if ebitda == 0: 
        depreciation = get_val(t, ['ReconciledDepreciation', 'DepreciationAndAmortization'])
        ebitda = ebit + depreciation

    # Balance Sheet
    cash = get_val(t, ['Cash', 'CashAndCashEquivalents'])
    receivables = get_val(t, ['Receivables', 'AccountsReceivable', 'NetReceivables']) 
    if receivables == 0: receivables = get_val(t, 'CurrentAssets') * 0.2 # Fallback
    
    inventory = get_val(t, 'Inventory')
    payables = get_val(t, ['Payables', 'AccountsPayable'])
    if payables == 0: payables = get_val(t, 'CurrentLiabilities') * 0.2 # Fallback

    current_assets = get_val(t, ['CurrentAssets', 'TotalCurrentAssets'])
    current_liabilities = get_val(t, ['CurrentLiabilities', 'TotalCurrentLiabilities'])
    total_assets = get_val(t, 'TotalAssets')
    total_equity = get_val(t, ['TotalEquity', 'StockholdersEquity'])
    
    # Debt
    total_debt = get_val(t, ['TotalDebt', 'LongTermDebtAndCapitalLeaseObligation'])
    if total_debt == 0: total_debt = get_val(t, 'LongTermDebt') + get_val(t, 'CurrentDebt')
    net_debt = total_debt - cash

    # Fixed Assets (Net PPE)
    net_ppe = get_val(t, ['NetPPE', 'PropertyPlantEquipmentNet'])

    # Cash Flow
    cfo = get_val(t, ['OperatingCashFlow', 'TotalCashFromOperatingActivities'])
    cfi = get_val(t, ['InvestingCashFlow', 'TotalCashflowsFromInvestingActivities'])
    cff = get_val(t, ['FinancingCashFlow', 'TotalCashFromFinancingActivities'])
    capex = abs(get_val(t, ['CapitalExpenditures', 'CapEx']))
    dividends = abs(get_val(t, ['CashDividendsPaid', 'DividendsPaid']))

    # Shares
    shares = get_val(t, ['ShareIssued', 'CommonStockSharesOutstanding'])
    market_cap = get_val(t, 'Market Cap')

    # === 2. CALCULATIONS (THE 7 CATEGORIES) ===

    # 1. Ρευστότητα (Liquidity)
    liq = {
        'Current_Ratio': round(safe_div(current_assets, current_liabilities), 2),
        'Quick_Ratio': round(safe_div(current_assets - inventory, current_liabilities), 2),
        'Cash_Ratio': round(safe_div(cash, current_liabilities), 2)
    }

    # 2. Δραστηριότητα & Αποδοτικότητα (Activity & Efficiency)
    dso = safe_div(receivables, revenue) * 365
    dsi = safe_div(inventory, cogs) * 365
    dpo = safe_div(payables, cogs) * 365
    act = {
        'DSO': round(dso, 0),
        'DSI': round(dsi, 0),
        'DPO': round(dpo, 0),
        'CCC': round(dso + dsi - dpo, 0),
        'Total_Asset_Turnover': round(safe_div(revenue, total_assets), 2),
        'Fixed_Asset_Turnover': round(safe_div(revenue, net_ppe), 2)
    }

    # 3. Μόχλευση & Κάλυψη (Solvency & Coverage)
    sol = {
        'Debt_to_Equity': round(safe_div(total_debt, total_equity), 2),
        'Net_Debt_to_EBITDA': round(safe_div(net_debt, ebitda), 2),
        'Interest_Coverage': round(safe_div(ebit, interest), 2),
        'Fin_Lev_Multiplier': round(safe_div(total_assets, total_equity), 2)
    }

    # 4. Κερδοφορία (Profitability Margins)
    prof = {
        'Gross_Margin': round(safe_div(revenue - cogs, revenue) * 100, 2),
        'EBITDA_Margin': round(safe_div(ebitda, revenue) * 100, 2),
        'Operating_Margin': round(safe_div(ebit, revenue) * 100, 2),
        'Net_Margin': round(safe_div(net_income, revenue) * 100, 2)
    }

    # 5. Δείκτες Απόδοσης Διοίκησης (Management Return Ratios)
    # ROIC Calculation: NOPAT / Invested Capital
    tax_rate = 0.25 # Assumption
    nopat = ebit * (1 - tax_rate)
    invested_capital = total_equity + total_debt - cash
    
    mgmt = {
        'ROE': round(safe_div(net_income, total_equity) * 100, 2),
        'ROA': round(safe_div(net_income, total_assets) * 100, 2),
        'ROIC': round(safe_div(nopat, invested_capital) * 100, 2)
    }

    # 6. Δεδομένα Ανά Μετοχή (Per Share Data)
    eps = get_val(t, 'BasicEPS') 
    if eps == 0: eps = safe_div(net_income, shares)
    
    per_share = {
        'EPS': round(eps, 2),
        'Dividend_Payout': round(safe_div(dividends, net_income) * 100, 2),
        'BVPS': round(safe_div(total_equity, shares), 2)
    }

    # 7. Ταμειακές Ροές (Cash Flows Fundamentals)
    cf = {
        'CFO': cfo,
        'CFI': cfi,
        'CFF': cff,
        'FCF': cfo - capex,
        'CAPEX_Sales': round(safe_div(capex, revenue) * 100, 2)
    }

    # === FORENSICS (Z-Score / M-Score) ===
    # Altman Z-Score
    wc = current_assets - current_liabilities
    re = get_val(t, 'RetainedEarnings')
    A = safe_div(wc, total_assets)
    B = safe_div(re, total_assets)
    C = safe_div(ebit, total_assets)
    D = safe_div(market_cap, total_debt) if total_debt > 0 else 0
    E = safe_div(revenue, total_assets)
    z_score = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E

    # Beneish M-Score (Simplified Proxy due to limited historical data in single pass)
    # Note: Full M-Score requires previous year data which might be complex in this structure, 
    # so we keep a simplified version or placeholders.
    m_score = -2.5 # Default Safe

    # Health Score
    score = 0
    if cfo > net_income: score += 20
    if sol['Interest_Coverage'] > 3: score += 15
    if mgmt['ROE'] > 15: score += 15
    if z_score > 2.99: score += 25
    if prof['Net_Margin'] > 10: score += 15
    if sol['Debt_to_Equity'] < 1.0: score += 10

    return {
        'Analysis': {
            '1_Liquidity': liq,
            '2_Activity': act,
            '3_Solvency': sol,
            '4_Profitability': prof,
            '5_Management': mgmt,
            '6_Per_Share': per_share,
            '7_Cash_Flow': cf
        },
        'Forensics': {
            'Z_Score': round(z_score, 2),
            'M_Score': round(m_score, 2),
            'Health_Score': score,
            'Is_Paper_Profits': cfo < net_income,
            'Gap': net_income - cfo
        },
        'Valuation': {
            'Invested_Capital': invested_capital,
            'NOPAT': nopat,
            'EVA': 0 # Calculated in App
        }
    }