# ==========================================
# 📊 modules/analyzer.py — Version 3.1 (Smarter Gross Profit)
# ==========================================
import pandas as pd
import numpy as np
from typing import Optional

# ==========================================
# 🔹 Helper Functions
# ==========================================

def safe_divide(numerator, denominator):
    try:
        num = pd.to_numeric(numerator, errors='coerce')
        den = pd.to_numeric(denominator, errors='coerce').replace(0, np.nan)
        if den is None or den.empty or num is None or num.empty:
            return pd.Series([np.nan] * len(numerator), index=numerator.index)
        return num / den
    except Exception:
        try:
            return pd.Series([np.nan] * len(numerator), index=numerator.index)
        except:
             return pd.Series([np.nan]) 

def get_col(df, col_name):
    if col_name in df.columns:
        return df[col_name]
    else:
        return pd.Series([np.nan] * len(df), index=df.index, name=col_name)

# ==========================================
# 🔹 Υπολογισμός Χρηματοοικονομικών Δεικτών
# ==========================================

def calculate_financial_ratios(
    company_df: pd.DataFrame, 
    sector: str = "General", 
    competitor_df: Optional[pd.DataFrame] = None, 
    competitor_sector: str = "General"
):
    
    if company_df is None or company_df.empty:
        print("⚠️ Analyzer: παρέλαβε κενό DataFrame.")
        return {"ratios": pd.DataFrame(), "categories": {}, "sector": sector}

    ratios = pd.DataFrame()
    
    if 'Year' in company_df.columns:
        year_date_cols = ['Year']
        if 'Date' in company_df.columns:
             year_date_cols.append('Date')
        ratios_index_data = company_df[year_date_cols]
        company_df = company_df.set_index('Year').copy() 
    else:
        ratios_index_data = pd.DataFrame({'Year': range(len(company_df))})
        company_df = company_df.copy()
        company_df.index = ratios_index_data['Year']
        
    ratios = pd.DataFrame(index=company_df.index)

    print(f"🏢 Analyzer: Υπολογισμός για κλάδο: {sector}")

    # --- Υπολογισμοί δεικτών (Standard Ονόματα) ---
    
    # Ρευστότητα
    ratios['Current Ratio'] = safe_divide(get_col(company_df, 'CurrentAssets'), get_col(company_df, 'CurrentLiabilities'))
    ratios['Quick Ratio'] = safe_divide(get_col(company_df, 'CurrentAssets') - get_col(company_df, 'Inventory').fillna(0), get_col(company_df, 'CurrentLiabilities'))
    ratios['Cash Ratio'] = safe_divide(get_col(company_df, 'Cash'), get_col(company_df, 'CurrentLiabilities'))

    # Μόχλευση (Debt)
    debt_col = get_col(company_df, 'TotalDebt')
    if debt_col.isnull().all():
        debt_col = get_col(company_df, 'TotalLiabilities')
        
    ratios['Debt to Equity'] = safe_divide(debt_col, get_col(company_df, 'TotalEquity'))
    ratios['Debt to Assets'] = safe_divide(debt_col, get_col(company_df, 'TotalAssets'))

    # Κερδοφορία
    # === v3.1 FIX: Υπολογίζουμε το GrossProfit αν λείπει ===
    revenue = get_col(company_df, 'Revenue')
    gross_profit = get_col(company_df, 'GrossProfit')
    if gross_profit.isnull().all(): # Αν λείπει η στήλη GrossProfit
        cost_of_goods = get_col(company_df, 'CostOfGoodsSold')
        if not cost_of_goods.isnull().all():
            print("Info: Υπολογισμός 'GrossProfit' από 'Revenue' - 'CostOfGoodsSold'.")
            gross_profit = revenue - cost_of_goods
    # ===================================================
    
    ratios['Gross Profit Margin'] = safe_divide(gross_profit, revenue)
    ratios['Operating Margin'] = safe_divide(get_col(company_df, 'OperatingIncome'), revenue)
    ratios['Net Profit Margin'] = safe_divide(get_col(company_df, 'NetIncome'), revenue)

    # Απόδοση
    ratios['ROA'] = safe_divide(get_col(company_df, 'NetIncome'), get_col(company_df, 'TotalAssets'))
    ratios['ROE'] = safe_divide(get_col(company_df, 'NetIncome'), get_col(company_df, 'TotalEquity'))

    # Αποδοτικότητα
    ratios['Asset Turnover'] = safe_divide(revenue, get_col(company_df, 'TotalAssets'))
    ratios['Inventory Turnover'] = safe_divide(get_col(company_df, 'CostOfGoodsSold'), get_col(company_df, 'Inventory'))

    # Premium/Market
    ratios['EPS'] = safe_divide(get_col(company_df, 'NetIncome'), get_col(company_df, 'SharesOutstanding'))
    ratios['Operating Cash Flow Ratio'] = safe_divide(get_col(company_df, 'OperatingCashFlow'), get_col(company_df, 'CurrentLiabilities'))

    # --- Ειδικοί δείκτες ανά κλάδο ---
    if 'Bank' in sector or 'Financial' in sector:
        ratios['Loan to Deposit'] = safe_divide(get_col(company_df, 'Loans'), get_col(company_df, 'Deposits'))
        ratios['Net Interest Margin'] = safe_divide(get_col(company_df, 'NetInterestIncome'), get_col(company_df, 'AverageEarningAssets'))
    elif 'Technology' in sector or 'Software' in sector:
        ratios['R&D to Sales'] = safe_divide(get_col(company_df, 'R&D'), revenue)
    elif 'Auto' in sector or 'Vehicles' in sector:
        ratios['Inventory to Sales'] = safe_divide(get_col(company_df, 'Inventory'), revenue)
    elif 'Energy' in sector or 'Oil' in sector:
        ratios['Production Efficiency'] = safe_divide(get_col(company_df, 'OilProduction').fillna(0) + get_col(company_df, 'GasProduction').fillna(0), get_col(company_df, 'OperatingExpenses'))

    # --- Οργάνωση δεικτών ανά κατηγορία ---
    categories = {
        'Liquidity': ['Current Ratio', 'Quick Ratio', 'Cash Ratio'],
        'Debt': ['Debt to Equity', 'Debt to Assets'],
        'Profitability': ['Gross Profit Margin', 'Operating Margin', 'Net Profit Margin'],
        'Return': ['ROA', 'ROE', 'EPS'],
        'Efficiency': ['Asset Turnover', 'Inventory Turnover', 'Operating Cash Flow Ratio']
    }
    
    sector_specific_cats = {
        'Banking': ['Loan to Deposit', 'Net Interest Margin'],
        'Technology': ['R&D to Sales'],
        'Automotive': ['Inventory to Sales'],
        'Energy': ['Production Efficiency']
    }
    
    for cat_name, cat_cols in sector_specific_cats.items():
        if any(col in ratios.columns for col in cat_cols):
            categories[cat_name] = cat_cols

    ratios.reset_index(inplace=True)
    if 'Date' in ratios_index_data.columns and 'Date' not in ratios.columns:
        ratios = pd.merge(ratios, ratios_index_data, on='Year', how='left')


    organized = {}
    for cat, cols in categories.items():
        display_cols = ['Year']
        if 'Date' in ratios.columns:
            display_cols.append('Date')
            
        valid_cols = [col for col in cols if col in ratios.columns and not ratios[col].isnull().all()]
        if valid_cols:
            display_cols.extend(valid_cols)
            organized[cat] = ratios[display_cols]

    # --- Αν υπάρχει ανταγωνιστής ---
    if competitor_df is not None and not competitor_df.empty:
        print("⚔️ Υπολογισμός συγκριτικών δεικτών με ανταγωνιστή...")
        competitor_result = calculate_financial_ratios(
            competitor_df, 
            sector=competitor_sector
        )
        competitor_ratios = competitor_result.get("ratios")
        
        if competitor_ratios is not None and not competitor_ratios.empty:
            comp_cols = {col: f"Comp_{col}" for col in competitor_ratios.columns if col not in ['Year', 'Date']}
            competitor_ratios_renamed = competitor_ratios.rename(columns=comp_cols)
            ratios = pd.merge(ratios, competitor_ratios_renamed, on='Year', how='left', suffixes=('', '_Comp'))
            
            for col in categories['Profitability'] + categories['Return'] + categories['Efficiency']:
                if col in ratios.columns and f"Comp_{col}" in ratios.columns:
                    ratios[f"Diff_{col}"] = ratios[col] - ratios[f"Comp_{col}"]

    ratios = ratios.round(3)
    ratios['Sector'] = sector
    if 'Sector' in ratios.columns:
        cols = ratios.columns.tolist()
        cols.insert(1, cols.pop(cols.index('Sector')))
        ratios = ratios[cols]

    return {
        "ratios": ratios,
        "categories": organized,
        "sector": sector
    }