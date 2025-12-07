# modules/analyzer.py (v6.0 - The Core Financials Architecture)
import pandas as pd
import numpy as np

def calculate_financial_ratios(df: pd.DataFrame, sector: str = "General") -> dict:
    if df.empty: return {}

    # Ταξινόμηση (Το πιο πρόσφατο έτος πρώτο)
    df = df.sort_values(by='Year', ascending=False).reset_index(drop=True)
    
    # Τρέχον Έτος (t) και Προηγούμενο (t-1) για Growth metrics
    t = df.iloc[0]
    try: t_prev = df.iloc[1]
    except IndexError: t_prev = t 

    # --- Helper Functions ---
    def get_val(source, key, default=0):
        # Προσπάθεια εύρεσης της στήλης (αγνοεί πεζά/κεφαλαία)
        try:
            val = pd.to_numeric(source.get(key, default), errors='coerce')
            return 0 if pd.isna(val) else float(val)
        except:
            return 0

    def safe_div(a, b):
        return a / b if b != 0 else 0

    # === 1. DATA EXTRACTION (ΒΑΣΙΚΑ ΔΕΔΟΜΕΝΑ) ===
    # Income Statement
    revenue = get_val(t, 'Revenue')
    cogs = get_val(t, 'CostOfGoodsSold')
    gross_profit = get_val(t, 'GrossProfit')
    ebit = get_val(t, 'OperatingIncome')
    net_income = get_val(t, 'NetIncome')
    interest = abs(get_val(t, 'InterestExpense'))
    
    # Balance Sheet
    receivables = get_val(t, 'Receivables') or get_val(t, 'AccountsReceivable') or get_val(t, 'CurrentAssets') * 0.2 # Fallback
    inventory = get_val(t, 'Inventory')
    payables = get_val(t, 'Payables') or get_val(t, 'AccountsPayable') or get_val(t, 'CurrentLiabilities') * 0.2 # Fallback
    
    current_assets = get_val(t, 'CurrentAssets')
    current_liabilities = get_val(t, 'CurrentLiabilities')
    total_assets = get_val(t, 'TotalAssets')
    total_equity = get_val(t, 'TotalEquity') or get_val(t, 'StockholdersEquity')
    total_debt = get_val(t, 'TotalDebt')
    
    # Cash Flow
    cfo = get_val(t, 'OperatingCashFlow')
    cfi = get_val(t, 'InvestingCashFlow')
    cff = get_val(t, 'FinancingCashFlow')
    # Προσπάθεια εύρεσης CAPEX (συνήθως αρνητικό στο Investing, το θέλουμε θετικό για την αφαίρεση)
    capex = abs(get_val(t, 'CapitalExpenditures') or get_val(t, 'CapEx') or 0)

    # === ΚΑΤΗΓΟΡΙΑ 1: Ο ΚΟΡΜΟΣ (CORE FINANCIALS) ===
    
    # 1. Κατάσταση Ταμειακών Ροών
    fcf = cfo - capex
    
    cash_flow_metrics = {
        'CFO': cfo,
        'CFI': cfi,
        'CFF': cff,
        'FCF': fcf,
        'CAPEX': capex
    }

    # 2. Δείκτες Δραστηριότητας / Κύκλοι (Efficiency)
    dso = safe_div(receivables, revenue) * 365
    dsi = safe_div(inventory, cogs) * 365
    dpo = safe_div(payables, cogs) * 365
    ccc = dso + dsi - dpo
    
    efficiency_metrics = {
        'DSO': round(dso, 0),
        'DSI': round(dsi, 0),
        'DPO': round(dpo, 0),
        'CCC': round(ccc, 0)
    }

    # 3. Δείκτες Ρευστότητας (Liquidity)
    current_ratio = safe_div(current_assets, current_liabilities)
    quick_ratio = safe_div(current_assets - inventory, current_liabilities)
    
    liquidity_metrics = {
        'Current_Ratio': round(current_ratio, 2),
        'Quick_Ratio': round(quick_ratio, 2)
    }

    # 4. Δείκτες Φερεγγυότητας (Solvency)
    debt_to_equity = safe_div(total_debt, total_equity)
    int_coverage = safe_div(ebit, interest)
    
    solvency_metrics = {
        'Debt_to_Equity': round(debt_to_equity, 2),
        'Interest_Coverage': round(int_coverage, 2)
    }

    # 5. Δείκτες Κερδοφορίας (Profitability)
    gross_margin = safe_div(revenue - cogs, revenue) * 100
    oper_margin = safe_div(ebit, revenue) * 100
    net_margin = safe_div(net_income, revenue) * 100
    
    profitability_metrics = {
        'Gross_Margin': round(gross_margin, 2),
        'Operating_Margin': round(oper_margin, 2),
        'Net_Margin': round(net_margin, 2)
    }

    # === ΚΑΤΗΓΟΡΙΑ 2: FORENSICS (Z-Score, M-Score, Dupont) ===
    # (Τα κρατάμε γιατί είναι η "ψυχή" του ValuePy)
    
    # Altman Z-Score Components
    working_capital = current_assets - current_liabilities
    retained_earnings = get_val(t, 'RetainedEarnings')
    market_cap = get_val(t, 'Market Cap')
    total_liabilities = get_val(t, 'TotalLiabilities') or total_debt
    
    A = safe_div(working_capital, total_assets)
    B = safe_div(retained_earnings, total_assets)
    C = safe_div(ebit, total_assets)
    D = safe_div(market_cap, total_liabilities)
    E = safe_div(revenue, total_assets)
    z_score = (1.2*A) + (1.4*B) + (3.3*C) + (0.6*D) + (1.0*E)

    # Beneish M-Score (Simplified)
    # Χρειαζόμαστε τα t_prev για να δούμε αν "μαγειρεύουν"
    rev_prev = get_val(t_prev, 'Revenue')
    rec_prev = get_val(t_prev, 'Receivables') or get_val(t_prev, 'AccountsReceivable') or get_val(t_prev, 'CurrentAssets')*0.2
    
    dsri = safe_div(safe_div(receivables, revenue), safe_div(rec_prev, rev_prev)) # Days Sales in Receivables Index
    sgi = safe_div(revenue, rev_prev) # Sales Growth Index
    # (Χρησιμοποιούμε μια απλή μορφή για σταθερότητα)
    m_score = -4.84 + (0.92 * dsri) + (0.528 * sgi) # Basic M-Score Proxy

    forensics_metrics = {
        'Z_Score': round(z_score, 2),
        'M_Score': round(m_score, 2),
        'Health_Score': 0 # Θα υπολογιστεί στο app.py ή εδώ αν θες
    }

    # === ΣΥΓΚΕΝΤΡΩΣΗ ΟΛΩΝ ===
    return {
        'Core': {
            'Cash_Flow': cash_flow_metrics,
            'Efficiency': efficiency_metrics,
            'Liquidity': liquidity_metrics,
            'Solvency': solvency_metrics,
            'Profitability': profitability_metrics
        },
        'Forensics': forensics_metrics,
        # Κρατάμε και τα flat keys για συμβατότητα με το τωρινό app.py μέχρι να το αλλάξουμε
        'Pillar_1': {'Gap': net_income - cfo, 'Is_Paper_Profits': cfo < net_income, 'Net_Income': net_income, 'CFO': cfo},
        'Pillar_2': {'DSO': dso, 'Flag_Solvency': "SOLVENT" if int_coverage > 1.5 else "ZOMBIE"},
        'Pillar_3': {'ROE': round((net_margin/100) * (revenue/total_assets) * (total_assets/total_equity) * 100, 2)},
        'Pillar_5': {'EVA': 0, 'Value_Creation': 'N/A', 'PE_Ratio': 0}
    }