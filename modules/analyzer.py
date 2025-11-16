# modules/analyzer.py (v3.7 - Διόρθωση PyArrow Error)
import pandas as pd
import numpy as np

def calculate_financial_ratios(df, sector="General"):
    """
    Υπολογίζει ένα σετ χρηματοοικονομικών δεικτών από ένα DataFrame.
    """
    print(f"🏢 Analyzer: Υπολογισμός για κλάδο: {sector}")
    
    # Αρχικοποίηση λίστας για τα αποτελέσματα
    all_ratios = []

    # v3.7 FIX: ΒΕΒΑΙΩΝΟΜΑΣΤΕ ότι η στήλη 'Date' (Timestamp) ΔΕΝ θα μπει στους υπολογισμούς
    if 'Date' in df.columns:
        df = df.drop(columns=['Date'])
        
    # Σιγουρευόμαστε ότι τα 'Year' είναι index για εύκολη πρόσβαση
    if 'Year' in df.columns:
        df = df.set_index('Year')
        
    df = df.sort_index(ascending=False) # Ταξινόμηση (νεότερο πρώτα)

    for year in df.index:
        try:
            row = df.loc[year]
            
            # --- Βασικά Δεδομένα ---
            revenue = pd.to_numeric(row.get('Revenue'), errors='coerce')
            cogs = pd.to_numeric(row.get('CostOfGoodsSold'), errors='coerce')
            op_income = pd.to_numeric(row.get('OperatingIncome'), errors='coerce')
            net_income = pd.to_numeric(row.get('NetIncome'), errors='coerce')
            
            current_assets = pd.to_numeric(row.get('CurrentAssets'), errors='coerce')
            current_liab = pd.to_numeric(row.get('CurrentLiabilities'), errors='coerce')
            total_assets = pd.to_numeric(row.get('TotalAssets'), errors='coerce')
            total_liab = pd.to_numeric(row.get('TotalLiabilities'), errors='coerce')
            total_equity = pd.to_numeric(row.get('TotalEquity'), errors='coerce')
            
            cash = pd.to_numeric(row.get('Cash'), errors='coerce')
            inventory = pd.to_numeric(row.get('Inventory'), errors='coerce')
            op_cash_flow = pd.to_numeric(row.get('OperatingCashFlow'), errors='coerce')
            
            # Υπολογισμός Gross Profit
            if pd.isna(cogs):
                gross_profit = pd.to_numeric(row.get('GrossProfit'), errors='coerce')
                if not pd.isna(gross_profit):
                    cogs = revenue - gross_profit
            else:
                gross_profit = revenue - cogs

            # --- 1. Δείκτες Ρευστότητας (Liquidity) ---
            current_ratio = current_assets / current_liab
            quick_ratio = (current_assets - inventory) / current_liab if not pd.isna(inventory) else np.nan
            cash_ratio = cash / current_liab if not pd.isna(cash) else np.nan

            # --- 2. Δείκτες Μόχλευσης (Leverage) ---
            debt_to_equity = total_liab / total_equity
            debt_to_assets = total_liab / total_assets

            # --- 3. Δείκτες Αποδοτικότητας (Profitability) ---
            gross_profit_margin = gross_profit / revenue
            operating_margin = op_income / revenue
            net_profit_margin = net_income / revenue

            # --- 4. Δείκτες Απόδοσης (Efficiency/Returns) ---
            return_on_assets_roa = net_income / total_assets
            return_on_equity_roe = net_income / total_equity
            asset_turnover = revenue / total_assets

            ratios = {
                "Year": int(year),
                "Sector": sector,
                
                # Liquidity
                "Current Ratio": current_ratio,
                "Quick Ratio": quick_ratio,
                "Cash Ratio": cash_ratio,
                
                # Leverage
                "Debt to Equity": debt_to_equity,
                "Debt to Assets": debt_to_assets,
                
                # Profitability
                "Gross Profit Margin": gross_profit_margin,
                "Operating Margin": operating_margin,
                "Net Profit Margin": net_profit_margin,
                
                # Efficiency/Returns
                "Return on Assets (ROA)": return_on_assets_roa,
                "Return on Equity (ROE)": return_on_equity_roe,
                "Asset Turnover": asset_turnover,
            }
            all_ratios.append(ratios)

        except Exception as e:
            print(f"⚠️ Analyzer Warning: Αποτυχία υπολογισμού δεικτών για το έτος {year}: {e}")
            continue

    if not all_ratios:
        print("❌ Analyzer Error: Δεν μπόρεσε να υπολογιστεί κανένας δείκτης.")
        return {"ratios": pd.DataFrame(), "categories": {}}

    # --- Δημιουργία Πινάκων ---
    ratios_df = pd.DataFrame(all_ratios)
    ratios_df = ratios_df.replace([np.inf, -np.inf], np.nan) 
    
    # --- Ομαδοποίηση (v1.20) ---
    categories = {}
    
    liquidity_cols = ['Year', 'Current Ratio', 'Quick Ratio', 'Cash Ratio']
    leverage_cols = ['Year', 'Debt to Equity', 'Debt to Assets']
    profitability_cols = ['Year', 'Gross Profit Margin', 'Operating Margin', 'Net Profit Margin']
    efficiency_cols = ['Year', 'Return on Assets (ROA)', 'Return on Equity (ROE)', 'Asset Turnover']

    categories["Ρευστότητα (Liquidity)"] = ratios_df[[col for col in liquidity_cols if col in ratios_df.columns]].copy()
    categories["Μόχλευση (Leverage)"] = ratios_df[[col for col in leverage_cols if col in ratios_df.columns]].copy()
    categories["Κερδοφορία (Profitability)"] = ratios_df[[col for col in profitability_cols if col in ratios_df.columns]].copy()
    categories["Απόδοση (Efficiency)"] = ratios_df[[col for col in efficiency_cols if col in ratios_df.columns]].copy()

    return {
        "ratios": ratios_df,
        "categories": categories
    }