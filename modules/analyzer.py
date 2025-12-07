import pandas as pd
import numpy as np

def calculate_financial_ratios(df):
    """
    Δέχεται ένα DataFrame (με στήλες όπως 'Total Revenue', 'Net Income' κ.λπ.)
    και επιστρέφει ένα λεξικό με όλους τους δείκτες για το CFA.
    """
    
    # Παίρνουμε την τελευταία διαθέσιμη χρονιά (Most Recent Year - MRY)
    # Υποθέτουμε ότι το DF είναι ταξινομημένο, αλλά για σιγουριά το ξανα-ταξινομούμε
    df = df.sort_values(by='Year')
    latest = df.iloc[-1]
    
    # Helper για ασφαλή διαίρεση (αποφυγή division by zero)
    def safe_div(n, d):
        return n / d if d != 0 and pd.notnull(d) else 0

    # === 1. ΒΑΣΙΚΑ ΔΕΔΟΜΕΝΑ (Data Extraction) ===
    revenue = latest.get('Total Revenue', 0)
    cogs = latest.get('Cost Of Revenue', 0)
    gross_profit = latest.get('Gross Profit', revenue - cogs)
    ebit = latest.get('EBIT', 0)
    net_income = latest.get('Net Income', 0)
    
    # Balance Sheet
    total_assets = latest.get('Total Assets', 0)
    current_assets = latest.get('Current Assets', 0)
    current_liabilities = latest.get('Current Liabilities', 0)
    inventory = latest.get('Inventory', 0)
    receivables = latest.get('Receivables', 0)
    payables = latest.get('Payables', 0)
    total_equity = latest.get('Total Equity Gross Minority Interest', latest.get('Stockholders Equity', 0))
    total_debt = latest.get('Total Debt', 0)
    cash = latest.get('Cash And Cash Equivalents', 0)
    
    # Cash Flow
    cfo = latest.get('Operating Cash Flow', 0)
    capex = abs(latest.get('Capital Expenditure', 0)) # Συνήθως είναι αρνητικό, το θέλουμε απόλυτο

    # === 2. ΥΠΟΛΟΓΙΣΜΟΣ ΔΕΙΚΤΩΝ (The CFA Core) ===
    
    # --- Liquidity ---
    current_ratio = safe_div(current_assets, current_liabilities)
    quick_ratio = safe_div(current_assets - inventory, current_liabilities)
    
    # --- Activity / Efficiency ---
    dso = safe_div(receivables, revenue) * 365
    dsi = safe_div(inventory, cogs) * 365
    dpo = safe_div(payables, cogs) * 365
    ccc = dso + dsi - dpo
    asset_turnover = safe_div(revenue, total_assets)
    
    # --- Solvency ---
    debt_to_equity = safe_div(total_debt, total_equity)
    interest_expense = abs(latest.get('Interest Expense', 0))
    interest_coverage = safe_div(ebit, interest_expense)
    financial_leverage = safe_div(total_assets, total_equity) # Equity Multiplier
    
    # --- Profitability ---
    gross_margin = safe_div(gross_profit, revenue) * 100
    operating_margin = safe_div(ebit, revenue) * 100
    net_margin = safe_div(net_income, revenue) * 100
    ebitda = latest.get('EBITDA', ebit + latest.get('Depreciation And Amortization', 0))
    ebitda_margin = safe_div(ebitda, revenue) * 100
    
    # --- Management Returns ---
    roe = safe_div(net_income, total_equity) * 100
    roa = safe_div(net_income, total_assets) * 100
    
    # ROIC Calculation (Critical for CFA)
    # NOPAT = EBIT * (1 - Tax Rate)
    tax_expense = latest.get('Tax Provision', 0)
    pre_tax_income = latest.get('Pretax Income', 0)
    effective_tax_rate = safe_div(tax_expense, pre_tax_income) if pre_tax_income > 0 else 0.22
    nopat = ebit * (1 - effective_tax_rate)
    invested_capital = total_equity + total_debt - cash
    roic = safe_div(nopat, invested_capital) * 100

    # === 3. FORENSICS & SCORING (The "UrbanStyle" Logic) ===
    
    # A. Altman Z-Score (Για κατασκευαστικές/εμπορικές - όχι τράπεζες)
    # Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
    # A = Working Capital / Total Assets
    # B = Retained Earnings / Total Assets (Χρησιμοποιούμε Net Income ως proxy αν λείπει)
    # C = EBIT / Total Assets
    # D = Market Value of Equity / Total Liabilities (Χρησιμοποιούμε Book Value αν δεν έχουμε Market Cap live)
    # E = Sales / Total Assets
    
    market_cap = latest.get('Market Cap', total_equity) # Fallback σε Book Value αν δεν έχουμε Market Cap
    total_liabilities = total_assets - total_equity
    
    A = safe_div((current_assets - current_liabilities), total_assets)
    B = safe_div(latest.get('Retained Earnings', net_income), total_assets) 
    C = safe_div(ebit, total_assets)
    D = safe_div(market_cap, total_liabilities)
    E = safe_div(revenue, total_assets)
    
    z_score = (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
    
    # B. Beneish M-Score (Simplified Proxy - Μόνο ένα μέρος)
    # Εδώ κάνουμε έναν απλό έλεγχο ποιότητας κερδών αντί για το πλήρες Beneish που θέλει 2 χρόνια
    m_score = -2.5 # Default "Safe" value
    if cfo < net_income and net_income > 0:
        m_score = -1.5 # Suspicious
        
    # C. Health Score (0-100)
    # Ένας δικός μας αλγόριθμος βαθμολόγησης
    health_points = 0
    if roe > 8: health_points += 20
    if current_ratio > 1.2: health_points += 20
    if interest_coverage > 3: health_points += 20
    if net_margin > 5: health_points += 20
    if cfo > 0: health_points += 20
    # Penalty
    if z_score < 1.8: health_points -= 30
    
    health_score = max(0, min(100, health_points))

    # === 4. ΠΡΟΕΤΟΙΜΑΣΙΑ ΓΙΑ ΤΟ REPORT ===
    return {
        'Analysis': {
            '1_Liquidity': {
                'Current_Ratio': round(current_ratio, 2),
                'Quick_Ratio': round(quick_ratio, 2)
            },
            '2_Activity': {
                'DSO': round(dso, 0),
                'DSI': round(dsi, 0),
                'DPO': round(dpo, 0),
                'CCC': round(ccc, 0),
                'Total_Asset_Turnover': round(asset_turnover, 2)
            },
            '3_Solvency': {
                'Debt_to_Equity': round(debt_to_equity, 2),
                'Interest_Coverage': round(interest_coverage, 2),
                'Financial_Leverage': round(financial_leverage, 2)
            },
            '4_Profitability': {
                'Gross_Margin': round(gross_margin, 1),
                'EBITDA_Margin': round(ebitda_margin, 1),
                'Operating_Margin': round(operating_margin, 1),
                'Net_Margin': round(net_margin, 1)
            },
            '5_Management': {
                'ROE': round(roe, 1),
                'ROA': round(roa, 1),
                'ROIC': round(roic, 1)
            },
            '6_Per_Share': {
                'EPS': round(latest.get('Diluted EPS', 0), 2)
            },
            '7_Cash_Flow': {
                'CFO': cfo,
                'FCF': cfo - capex,
                'CAPEX': capex
            }
        },
        'Forensics': {
            'Health_Score': health_score,
            'Z_Score': round(z_score, 2),
            'M_Score': round(m_score, 2),
            'Net_Income': net_income, # Χρειάζεται για το Waterfall στο app.py
            'CFO': cfo                # Χρειάζεται για το Waterfall στο app.py
        },
        'Valuation': {
            'NOPAT': nopat,
            'Invested_Capital': invested_capital
        }
    }