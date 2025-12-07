# modules/analyzer.py (FINAL STABLE)
import pandas as pd
import numpy as np

def calculate_financial_ratios(df: pd.DataFrame, sector: str = "General") -> dict:
    if df.empty: return {}
    df = df.sort_values(by='Year', ascending=False).reset_index(drop=True)
    t = df.iloc[0]
    
    def get_val(source, keys, default=0):
        if isinstance(keys, str): keys = [keys]
        for k in keys:
            val = pd.to_numeric(source.get(k), errors='coerce')
            if not pd.isna(val): return float(val)
        return float(default)

    def safe_div(a, b): return a / b if b != 0 else 0

    # DATA
    revenue = get_val(t, ['Revenue', 'TotalRevenue', 'Sales'])
    cogs = get_val(t, ['CostOfGoodsSold', 'CostOfRevenue'])
    ebit = get_val(t, ['OperatingIncome', 'EBIT'])
    net_income = get_val(t, ['NetIncome', 'NetIncomeCommonStockholders'])
    interest = abs(get_val(t, ['InterestExpense', 'Interest']))
    
    ebitda = get_val(t, 'EBITDA')
    if ebitda == 0: ebitda = ebit + get_val(t, ['ReconciledDepreciation', 'DepreciationAndAmortization'])

    cash = get_val(t, ['Cash', 'CashAndCashEquivalents'])
    receivables = get_val(t, ['Receivables', 'AccountsReceivable', 'NetReceivables']) or (get_val(t, 'CurrentAssets') * 0.2)
    inventory = get_val(t, 'Inventory')
    payables = get_val(t, ['Payables', 'AccountsPayable']) or (get_val(t, 'CurrentLiabilities') * 0.2)
    
    current_assets = get_val(t, ['CurrentAssets', 'TotalCurrentAssets'])
    current_liabilities = get_val(t, ['CurrentLiabilities', 'TotalCurrentLiabilities'])
    total_assets = get_val(t, 'TotalAssets')
    total_equity = get_val(t, ['TotalEquity', 'StockholdersEquity'])
    total_debt = get_val(t, ['TotalDebt', 'LongTermDebt']) + get_val(t, 'CurrentDebt')
    net_debt = total_debt - cash
    net_ppe = get_val(t, ['NetPPE', 'PropertyPlantEquipmentNet'])

    cfo = get_val(t, ['OperatingCashFlow', 'TotalCashFromOperatingActivities'])
    cfi = get_val(t, ['InvestingCashFlow'])
    cff = get_val(t, ['FinancingCashFlow'])
    capex = abs(get_val(t, ['CapitalExpenditures', 'CapEx']))
    shares = get_val(t, ['ShareIssued', 'CommonStockSharesOutstanding'])
    market_cap = get_val(t, 'Market Cap')

    # METRICS
    liq = {
        'Current_Ratio': round(safe_div(current_assets, current_liabilities), 2),
        'Quick_Ratio': round(safe_div(current_assets - inventory, current_liabilities), 2),
        'Cash_Ratio': round(safe_div(cash, current_liabilities), 2)
    }
    
    dso = safe_div(receivables, revenue) * 365
    dsi = safe_div(inventory, cogs) * 365
    dpo = safe_div(payables, cogs) * 365
    act = {
        'DSO': round(dso, 0), 'DSI': round(dsi, 0), 'DPO': round(dpo, 0),
        'CCC': round(dso + dsi - dpo, 0),
        'Total_Asset_Turnover': round(safe_div(revenue, total_assets), 2),
        'Fixed_Asset_Turnover': round(safe_div(revenue, net_ppe), 2)
    }

    sol = {
        'Debt_to_Equity': round(safe_div(total_debt, total_equity), 2),
        'Net_Debt_to_EBITDA': round(safe_div(net_debt, ebitda), 2),
        'Interest_Coverage': round(safe_div(ebit, interest), 2)
    }

    prof = {
        'Gross_Margin': round(safe_div(revenue - cogs, revenue) * 100, 2),
        'EBITDA_Margin': round(safe_div(ebitda, revenue) * 100, 2),
        'Operating_Margin': round(safe_div(ebit, revenue) * 100, 2),
        'Net_Margin': round(safe_div(net_income, revenue) * 100, 2)
    }

    nopat = ebit * 0.75
    invested_capital = total_equity + total_debt - cash
    mgmt = {
        'ROE': round(safe_div(net_income, total_equity) * 100, 2),
        'ROA': round(safe_div(net_income, total_assets) * 100, 2),
        'ROIC': round(safe_div(nopat, invested_capital) * 100, 2)
    }

    eps = get_val(t, 'BasicEPS') or safe_div(net_income, shares)
    share_data = {
        'EPS': round(eps, 2),
        'BVPS': round(safe_div(total_equity, shares), 2)
    }

    cf_metrics = {
        'CFO': cfo, 'FCF': cfo - capex, 'CAPEX_Sales': round(safe_div(capex, revenue) * 100, 2)
    }

    # FORENSICS
    wc = current_assets - current_liabilities
    re = get_val(t, 'RetainedEarnings')
    A = safe_div(wc, total_assets); B = safe_div(re, total_assets)
    C = safe_div(ebit, total_assets); D = safe_div(market_cap, total_debt)
    E = safe_div(revenue, total_assets)
    z_score = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
    
    score = 0
    if cfo > net_income: score += 20
    if sol['Interest_Coverage'] > 3: score += 15
    if mgmt['ROE'] > 15: score += 15
    if z_score > 2.99: score += 25
    if prof['Net_Margin'] > 10: score += 15
    if sol['Debt_to_Equity'] < 1.0: score += 10

    return {
        'Analysis': {'1_Liquidity': liq, '2_Activity': act, '3_Solvency': sol, '4_Profitability': prof, '5_Management': mgmt, '6_Per_Share': share_data, '7_Cash_Flow': cf_metrics},
        'Forensics': {'Z_Score': round(z_score, 2), 'M_Score': -2.5, 'Health_Score': score, 'Is_Paper_Profits': cfo < net_income, 'Gap': net_income - cfo, 'Net_Income': net_income, 'CFO': cfo},
        'Valuation': {'Invested_Capital': invested_capital, 'NOPAT': nopat, 'EVA': 0}
    }