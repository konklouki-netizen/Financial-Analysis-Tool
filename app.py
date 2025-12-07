# app.py (v10.1 - ValuePy Pro with Forensics)
import streamlit as st
import pandas as pd
import os
import sys
import plotly.graph_objects as go 
import datetime

# === Setup ===
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Mock imports for the sake of the provided snippet. 
# In production, ensure your 'modules' folder exists.
try:
    from test_loader import resolve_to_ticker, load_company_info, get_company_df, normalize_dataframe
    from modules.analyzer import calculate_financial_ratios
    from modules.report_generator import create_pdf_bytes
    from modules.languages import get_text
except ImportError as e:
    # Fallback for demonstration if modules are missing
    st.warning(f"Modules not found ({e}). Running in isolated UI mode.")
    def get_text(lang): return {'sidebar_title': "History", 'clear_history': "Clear", 'search_tab': "Search", 'upload_tab': "Upload", 'ticker_placeholder': "e.g. AAPL", 'comp_label': "Competitors", 'comp_placeholder': "e.g. MSFT, GOOG", 'btn_run': "Analyze", 'btn_upload': "Upload", 'processing': "Crunching numbers...", 'select_view': "Select Company", 'download_pdf': "Download Report"}

st.set_page_config(page_title="ValuePy Pro", page_icon="💎", layout="wide")

# === CSS ===
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .hero-title { font-family: 'Helvetica Neue', sans-serif; font-size: 32px; font-weight: 700; text-align: center; color: #2c3e50; margin-top: 10px; }
    .metric-card { background-color: white; border-left: 4px solid #3498db; border-radius: 5px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 10px; }
    .metric-label { font-size: 12px; color: #7f8c8d; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 20px; font-weight: 800; color: #2c3e50; margin: 2px 0; }
    .metric-sub { font-size: 11px; color: #95a5a6; }
    .red-flag { background-color: #fce4ec; border: 1px solid #e91e63; color: #c2185b; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-weight: bold; }
    div[role="radiogroup"] { flex-direction: row; justify-content: center; background-color: white; padding: 10px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 20px;}
    div[data-testid="stRadio"] > label { display: none; }
</style>
""", unsafe_allow_html=True)

# === STATE ===
if 'history' not in st.session_state: st.session_state.history = [] 
if 'current_group' not in st.session_state: st.session_state.current_group = None

# === SIDEBAR ===
lang_choice = st.sidebar.selectbox("Language / Γλώσσα", ["English", "Ελληνικά"])
lang_code = 'GR' if lang_choice == "Ελληνικά" else 'EN'
T = get_text(lang_code)

st.sidebar.markdown("---")
st.sidebar.title(T['sidebar_title'])
if st.sidebar.button(T['clear_history']):
    st.session_state.history = []
    st.session_state.current_group = None
    st.rerun()
st.sidebar.markdown("---")
for i, group in enumerate(reversed(st.session_state.history)):
    timestamp = group.get('time', '')
    title = group.get('title', 'Analysis')
    if st.sidebar.button(f"{title} ({timestamp})", key=f"hist_{i}"):
        st.session_state.current_group = group
        st.rerun()

# === MAIN AREA ===
st.markdown('<div class="hero-title">💎 ValuePy <span style="color:#3498db">Pro</span></div>', unsafe_allow_html=True)

col_space_1, col_center, col_space_2 = st.columns([1, 2, 1])
trigger_analysis = False
input_mode = "Yahoo"
ticker_in = None; competitors_in = None; file_in = None

with col_center:
    tab_search, tab_upload = st.tabs([T['search_tab'], T['upload_tab']])
    with tab_search:
        ticker_in = st.text_input("Ticker:", placeholder=T['ticker_placeholder'], key="ticker_input")
        with st.expander(T['comp_label']):
            competitors_in = st.text_input("Competitors:", placeholder=T['comp_placeholder'], key="comp_input")
        if st.button(T['btn_run'], type="primary", use_container_width=True, key="btn_yahoo"):
            trigger_analysis = True; input_mode = "Yahoo"
    with tab_upload:
        file_in = st.file_uploader("Report:", type=['pdf', 'xlsx'], key="file_uploader")
        if file_in and st.button(T['btn_upload'], type="primary", use_container_width=True, key="btn_file"):
            trigger_analysis = True; input_mode = "File"

# === ENGINE ===
if trigger_analysis:
    timestamp = datetime.datetime.now().strftime("%H:%M")
    analysis_group = {'time': timestamp, 'title': "", 'main_ticker': "", 'reports': {}, 'benchmark': {}}
    sector_stats = {'ROE': [], 'PE_Ratio': [], 'DSO': []}

    with st.spinner(T['processing']):
        try:
            if input_mode == "Yahoo" and ticker_in:
                # Resolve Ticker
                main_ticker = resolve_to_ticker(ticker_in)
                analysis_group['main_ticker'] = main_ticker
                analysis_group['title'] = f"{main_ticker} vs Peers" if competitors_in else f"{main_ticker}"

                # Fetch Main Company
                if main_ticker:
                    data = get_company_df(main_ticker, "yahoo")
                    info_df, _ = load_company_info(main_ticker)
                    mcap = info_df['Κεφαλαιοποίηση'].iloc[0] if not info_df.empty else 0
                    if data:
                        df = normalize_dataframe(data[0]['table'], "yahoo")
                        df['Market Cap'] = mcap
                        forensics = calculate_financial_ratios(df)
                        analysis_group['reports'][main_ticker] = {'data': forensics, 'df': df}

                # Fetch Competitors
                if competitors_in:
                    comp_list = [c.strip() for c in competitors_in.split(",")]
                    for c_raw in comp_list:
                        c_ticker = resolve_to_ticker(c_raw)
                        if c_ticker and c_ticker != main_ticker:
                            c_data = get_company_df(c_ticker, "yahoo")
                            c_info, _ = load_company_info(c_ticker)
                            c_mcap = c_info['Κεφαλαιοποίηση'].iloc[0] if not c_info.empty else 0
                            if c_data:
                                c_df = normalize_dataframe(c_data[0]['table'], "yahoo")
                                c_df['Market Cap'] = c_mcap
                                c_metrics = calculate_financial_ratios(c_df)
                                analysis_group['reports'][c_ticker] = {'data': c_metrics, 'df': c_df}
                                
                                # Collect stats for benchmark
                                try:
                                    roe = c_metrics['Analysis']['5_Management']['ROE']
                                    dso = c_metrics['Analysis']['2_Activity']['DSO']
                                    if roe != 0: sector_stats['ROE'].append(roe)
                                    if dso > 0: sector_stats['DSO'].append(dso)
                                except: pass

                # Build Benchmark
                benchmark_data = {}
                for k, v in sector_stats.items():
                    if v: benchmark_data[k] = sum(v) / len(v)
                analysis_group['benchmark'] = benchmark_data

                # Save to History
                if analysis_group['reports']:
                    st.session_state.history.append(analysis_group)
                    st.session_state.current_group = analysis_group
                    st.rerun()

            elif input_mode == "File" and file_in:
                temp_path = f"temp_{file_in.name}"
                with open(temp_path, "wb") as f: f.write(file_in.getvalue())
                src_type = "pdf" if "pdf" in file_in.name.lower() else "excel"
                data = get_company_df(temp_path, src_type)
                
                if data:
                    full_df = pd.DataFrame()
                    for pkg in data:
                        norm = normalize_dataframe(pkg['table'], src_type)
                        if not norm.empty and 'Year' in norm.columns: full_df = pd.concat([full_df, norm])
                    
                    if not full_df.empty:
                        # Clean Year and Sort
                        full_df['Year'] = pd.to_numeric(full_df['Year'], errors='coerce')
                        full_df = full_df.sort_values('Year')
                        full_df = full_df.groupby('Year', as_index=False).first()
                        
                        forensics = calculate_financial_ratios(full_df)
                        analysis_group['title'] = file_in.name
                        analysis_group['main_ticker'] = file_in.name
                        analysis_group['reports'][file_in.name] = {'data': forensics, 'df': full_df}
                        
                        st.session_state.history.append(analysis_group)
                        st.session_state.current_group = analysis_group
                        st.rerun()
                if os.path.exists(temp_path): os.remove(temp_path)

        except Exception as e:
            st.error(f"Error: {e}")

# === VISUALIZATION ===
if st.session_state.current_group:
    group = st.session_state.current_group
    reports_dict = group['reports']
    bench = group['benchmark']
    main_ticker = group['main_ticker']

    st.divider()
    
    # Selector
    company_options = list(reports_dict.keys())
    if main_ticker in company_options:
        company_options.remove(main_ticker)
        company_options.insert(0, main_ticker)
    
    selected_company = st.radio(T['select_view'], company_options, horizontal=True)
    
    # Data Unpacking
    active_report = reports_dict[selected_company]
    res = active_report['data']
    df_raw = active_report['df']
    
    # --- Local Calculation for Advanced Red Flags ---
    # We calculate growth rates manually here to drive the visual alerts
    red_flags = []
    if len(df_raw) > 1:
        latest = df_raw.iloc[-1]
        prev = df_raw.iloc[-2]
        
        # 1. Inventory Bloat (Inventory grows faster than Sales)
        inv_growth = (latest.get('Inventory', 0) - prev.get('Inventory', 0)) / prev.get('Inventory', 1)
        sales_growth = (latest.get('Total Revenue', 0) - prev.get('Total Revenue', 0)) / prev.get('Total Revenue', 1)
        if inv_growth > sales_growth + 0.15: # 15% threshold
            red_flags.append(f"🚨 INVENTORY BLOAT: Inventory (+{inv_growth:.1%}) growing much faster than Sales (+{sales_growth:.1%}). Risk of obsolescence.")
            
        # 2. Divergence (Profit > Cash Flow)
        net_income = latest.get('Net Income', 0)
        cfo = latest.get('Operating Cash Flow', 0)
        if net_income > 0 and cfo < 0:
            red_flags.append("🚨 CASH STARVATION: Company is booking profits but burning cash (CFO Negative). Check Receivables quality.")
        elif net_income > 0 and cfo < (net_income * 0.5):
            red_flags.append("⚠️ LOW QUALITY EARNINGS: Cash Flow is less than 50% of Net Income.")

    # Dictionary Unpacking
    an = res.get('Analysis', {})
    for_ = res.get('Forensics', {})
    val = res.get('Valuation', {})
    
    liq = an.get('1_Liquidity', {})
    act = an.get('2_Activity', {})
    sol = an.get('3_Solvency', {})
    prof = an.get('4_Profitability', {})
    mgmt = an.get('5_Management', {})
    share = an.get('6_Per_Share', {})
    cf = an.get('7_Cash_Flow', {})

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"### 📑 {selected_company}")
    with col_h2:
        try:
            pdf_bytes = create_pdf_bytes(selected_company, res)
            st.download_button(T['download_pdf'], pdf_bytes, f"ValuePy_{selected_company}.pdf", "application/pdf")
        except: pass

    # UI Helper
    def ui_card(label, value, subtext=None, color="#2c3e50"):
        border_c = "#3498db"
        if "RED" in str(subtext) or "ZOMBIE" in str(subtext): border_c = "#e74c3c"
        elif "OK" in str(subtext) or "SOLVENT" in str(subtext): border_c = "#27ae60"
        
        st.markdown(f"""
        <div class="metric-card" style="border-left: 4px solid {border_c};">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{color}">{value}</div>
            <div class="metric-sub">{subtext if subtext else ''}</div>
        </div>
        """, unsafe_allow_html=True)

    # === RED FLAGS BANNER ===
    if red_flags:
        for flag in red_flags:
            st.markdown(f'<div class="red-flag">{flag}</div>', unsafe_allow_html=True)

    # === TABS ===
    t1, t2, t3, t4 = st.tabs(["🏥 HEALTH & RISK", "💰 PROFIT & CASH", "⚙️ EFFICIENCY", "⚖️ VALUATION & ROE"])

    # --- TAB 1: HEALTH & RISK ---
    with t1:
        col_g, col_info = st.columns([1, 2])
        with col_g:
            score = for_.get('Health_Score', 50)
            fig_g = go.Figure(go.Indicator(
                mode = "gauge+number", value = score,
                title = {'text': "Health Score"},
                gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#2c3e50"},
                         'steps': [{'range': [0, 40], 'color': "#e74c3c"}, {'range': [40, 70], 'color': "#f1c40f"}, {'range': [70, 100], 'color': "#27ae60"}]}
            ))
            fig_g.update_layout(height=220, margin=dict(t=30, b=20))
            st.plotly_chart(fig_g, use_container_width=True)
        
        with col_info:
            st.subheader("Risk Assessment")
            c1, c2 = st.columns(2)
            with c1:
                de_ratio = sol.get('Debt_to_Equity',0)
                ui_card("Debt / Equity", f"{de_ratio}x", "High Risk" if de_ratio > 2 else "Manageable")
                cov = sol.get('Interest_Coverage', 0)
                ui_card("Interest Coverage", f"{cov}x", "ZOMBIE RISK" if cov < 1.5 else "Solvent")
            with c2:
                ui_card("Current Ratio", f"{liq.get('Current_Ratio',0)}x", "Liquidity")
                ui_card("Quick Ratio", f"{liq.get('Quick_Ratio',0)}x", "Acid Test")

        st.divider()
        st.subheader("Forensic Models")
        r1, r2 = st.columns(2)
        with r1:
            z = for_.get('Z_Score', 0)
            fig_z = go.Figure(go.Indicator(
                mode="gauge+number", value=z, title={'text': "Altman Z-Score (Bankruptcy)"},
                gauge={'axis': {'range': [0, 5]}, 'bar': {'color': "black"}, 'steps': [{'range': [0, 1.8], 'color': "#e74c3c"}, {'range': [1.8, 3], 'color': "#95a5a6"}, {'range': [3, 5], 'color': "#27ae60"}]}
            ))
            fig_z.update_layout(height=200, margin=dict(t=20, b=20))
            st.plotly_chart(fig_z, use_container_width=True)
        with r2:
            m = for_.get('M_Score', -3)
            fig_m = go.Figure(go.Indicator(
                mode="gauge+number", value=m, title={'text': "Beneish M-Score (Manipulation)"},
                gauge={'axis': {'range': [-5, 0]}, 'bar': {'color': "black"}, 'steps': [{'range': [-5, -2.22], 'color': "#27ae60"}, {'range': [-2.22, -1.78], 'color': "#95a5a6"}, {'range': [-1.78, 0], 'color': "#e74c3c"}]}
            ))
            fig_m.update_layout(height=200, margin=dict(t=20, b=20))
            st.plotly_chart(fig_m, use_container_width=True)

    # --- TAB 2: PROFIT & CASH (Enhanced Waterfall) ---
    with t2:
        col_L, col_R = st.columns([1, 2])
        
        with col_L:
            st.subheader("Margins")
            ui_card("Gross Margin", f"{prof.get('Gross_Margin',0)}%")
            ui_card("EBITDA Margin", f"{prof.get('EBITDA_Margin',0)}%")
            ui_card("Operating Margin", f"{prof.get('Operating_Margin',0)}%")
            ui_card("Net Margin", f"{prof.get('Net_Margin',0)}%", "#2c3e50")
            st.divider()
            ui_card("EPS", f"€{share.get('EPS',0)}")
        
        with col_R:
            st.subheader("Cash Flow Reality (Detailed Waterfall)")
            
            # Extract Components from raw DF for detailed plotting
            try:
                latest = df_raw.iloc[-1]
                net_inc = latest.get('Net Income', 0)
                depr = latest.get('Depreciation', 0)
                # Changes in WC (We approximate if exact delta columns aren't there)
                # Assuming raw DF has these from Yahoo or calc:
                chg_receivables = -1 * (latest.get('Change In Receivables', 0)) # Cash Out
                chg_inventory = -1 * (latest.get('Change In Inventory', 0))     # Cash Out
                chg_payables = latest.get('Change In Payables', 0)              # Cash In
                cfo_val = latest.get('Operating Cash Flow', 0)
                
                # If deltas are missing, fallback to gap
                if cfo_val == 0: cfo_val = net_inc # Prevent crash
                
                # Plot
                fig_wf = go.Figure(go.Waterfall(
                    measure = ["relative", "relative", "relative", "relative", "relative", "total"],
                    x = ["Net Income", "Depreciation", "Receivables", "Inventory", "Payables", "CFO"],
                    y = [net_inc, depr, chg_receivables, chg_inventory, chg_payables, 0],
                    textposition = "outside",
                    connector = {"line":{"color":"gray"}},
                    decreasing = {"marker":{"color":"#e74c3c"}}, # Red for cash outflow
                    increasing = {"marker":{"color":"#2ecc71"}}, # Green for cash inflow
                    totals = {"marker":{"color":"#3498db"}}
                ))
            except:
                # Fallback to simple waterfall if detailed fields missing
                net_inc = for_.get('Net_Income', 0)
                cfo_val = for_.get('CFO', 0)
                gap_val = cfo_val - net_inc
                fig_wf = go.Figure(go.Waterfall(
                    measure = ["relative", "relative", "total"],
                    x = ["Net Income", "Gap (WC & Depr)", "CFO"],
                    y = [net_inc, gap_val, cfo_val],
                    text = [f"{net_inc:,.0f}", f"{gap_val:,.0f}", f"{cfo_val:,.0f}"],
                    connector = {"line":{"color":"gray"}},
                    decreasing = {"marker":{"color":"#e74c3c"}},
                    increasing = {"marker":{"color":"#2ecc71"}},
                    totals = {"marker":{"color":"#3498db"}}
                ))

            fig_wf.update_layout(height=400, margin=dict(t=20, b=20), title="Net Income → Cash Flow Bridge")
            st.plotly_chart(fig_wf, use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: ui_card("CFO (Ops)", f"€{cf.get('CFO',0)/1e6:,.1f}M", "#27ae60")
            with c2: ui_card("Free Cash Flow", f"€{cf.get('FCF',0)/1e6:,.1f}M", "#27ae60")
            with c3: ui_card("CAPEX", f"€{cf.get('CAPEX',0)/1e6:,.1f}M", "#e74c3c")

    # --- TAB 3: EFFICIENCY ---
    # --- TAB 3: EFFICIENCY ---
    with t3:
        # Μέρος Α: Η "Βιτρίνα" (Φαίνεται Πάντα)
        col_L, col_R = st.columns([2, 1])
        
        with col_L:
            st.subheader("Days Sales Outstanding (DSO) vs Peers")
            dso_val = act.get('DSO', 0)
            bench_dso = bench.get('DSO', 0) if bench else 0
            
            # Αυτό το διάγραμμα το κρατάμε μόνιμο (είναι σημαντικό για σύγκριση)
            fig_dso = go.Figure(data=[
                go.Bar(name=selected_company, x=['DSO'], y=[dso_val], marker_color='#2c3e50', text=f"{dso_val:.0f}", textposition='auto'),
                go.Bar(name='Peer Avg', x=['DSO'], y=[bench_dso], marker_color='#95a5a6', text=f"{bench_dso:.0f}", textposition='auto')
            ])
            fig_dso.update_layout(height=350, margin=dict(t=20, b=20), barmode='group')
            st.plotly_chart(fig_dso, use_container_width=True)
            
        with col_R:
            st.subheader("Current Metrics")
            ui_card("DSO (Collect)", f"{act.get('DSO',0):.0f} days")
            ui_card("DSI (Inventory)", f"{act.get('DSI',0):.0f} days")
            ui_card("DPO (Pay)", f"{act.get('DPO',0):.0f} days")
            st.divider()
            ui_card("CCC (Cash Cycle)", f"{act.get('CCC',0):.0f} days", "#e67e22")

        # Μέρος Β: Η Επιλογή του Χρήστη (Extra Διαγράμματα)
        st.divider()
        st.markdown("### 🕵️ Deep Dive Analysis")
        # Εδώ είναι η επιλογή που ζήτησες
        show_history = st.checkbox("📉 Εμφάνιση Ιστορικής Τάσης (Show Historical Trends)", value=False)

        if show_history:
            st.info("Αναλύουμε τα ιστορικά δεδομένα για να δούμε αν οι κύκλοι 'φουσκώνουν' (π.χ. Inventory Bloat).")
            
            # Έλεγχος αν έχουμε ιστορικά δεδομένα στο df_raw
            if not df_raw.empty and 'Year' in df_raw.columns:
                try:
                    # Υπολογισμός Ιστορικών Δεικτών για κάθε έτος
                    # Προσέχουμε να μην σκάσει αν λείπουν στήλες (χρήση .get)
                    hist_years = df_raw['Year'].tolist()
                    
                    # Υπολογισμός με ασφάλεια (αν είναι 0 ο παρονομαστής βάζουμε 1)
                    hist_dso = ((df_raw['Receivables'] / df_raw['Total Revenue'].replace(0, 1)) * 365).fillna(0).tolist()
                    hist_dsi = ((df_raw['Inventory'] / df_raw['Cost Of Revenue'].replace(0, 1)) * 365).fillna(0).tolist()
                    hist_dpo = ((df_raw['Payables'] / df_raw['Cost Of Revenue'].replace(0, 1)) * 365).fillna(0).tolist()
                    
                    # Δημιουργία Stacked Bar Chart (Το "UrbanStyle" Chart)
                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Bar(name='DSO (Receivables)', x=hist_years, y=hist_dso, marker_color='blue'))
                    fig_trend.add_trace(go.Bar(name='DSI (Inventory)', x=hist_years, y=hist_dsi, marker_color='orange'))
                    fig_trend.add_trace(go.Bar(name='- DPO (Payables)', x=hist_years, y=[-x for x in hist_dpo], marker_color='red'))
                    
                    # Προσθήκη γραμμής CCC
                    hist_ccc = [dso + dsi - dpo for dso, dsi, dpo in zip(hist_dso, hist_dsi, hist_dpo)]
                    fig_trend.add_trace(go.Scatter(name='Net CCC Cycle', x=hist_years, y=hist_ccc, mode='lines+markers', line=dict(color='black', width=2)))

                    fig_trend.update_layout(
                        title='Historical Cash Conversion Cycle (Trend Analysis)',
                        barmode='relative', 
                        height=400,
                        yaxis_title="Days"
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
                    
                except Exception as e:
                    st.warning(f"Δεν βρέθηκαν επαρκή ιστορικά δεδομένα για γράφημα τάσης. ({e})")
            else:
                st.warning("Χρειάζονται δεδομένα πολλαπλών ετών για αυτό το γράφημα.")

    # --- TAB 4: VALUATION & ROE ---
    with t4:
        col_L, col_R = st.columns([1, 1])
        
        with col_L:
            st.subheader("ROE Architecture (DuPont)")
            # DuPont decomposition logic: Net Margin * Turnover * Leverage = ROE
            nm = prof.get('Net_Margin', 0)
            at = act.get('Total_Asset_Turnover', 0)
            lev = sol.get('Financial_Leverage', 1) 
            roe = mgmt.get('ROE', 0)
            
            # Simple fallback for visualization sizing
            labels = ["ROE", "Net Margin", "Asset Turnover", "Leverage"]
            parents = ["", "ROE", "ROE", "ROE"]
            values = [roe if roe>0 else 1, roe*0.4, roe*0.3, roe*0.3] # Stylized split for visual
            
            fig_dupont = go.Figure(go.Sunburst(
                labels=labels, parents=parents, values=values,
                branchvalues="total", marker=dict(colors=["#2c3e50", "#3498db", "#e67e22", "#9b59b6"])
            ))
            fig_dupont.update_layout(height=350, margin=dict(t=20, b=20))
            st.plotly_chart(fig_dupont, use_container_width=True)
            
            c1, c2 = st.columns(2)
            with c1: ui_card("ROE", f"{mgmt.get('ROE',0)}%", "#8e44ad")
            with c2: ui_card("ROIC", f"{mgmt.get('ROIC',0)}%", "#8e44ad")

        with col_R:
            st.subheader("Valuation Lab")
            st.markdown("Adjust **WACC** to calculate Economic Value Added (EVA).")
            
            wacc = st.slider("Cost of Capital (WACC)", 0.04, 0.20, 0.10, 0.005, format="%.1f%%", key=f"wacc_{selected_company}")
            
            invested_cap = val.get('Invested_Capital', 0)
            nopat = val.get('NOPAT', 0)
            eva_calc = nopat - (invested_cap * wacc)
            
            c_v1, c_v2 = st.columns(2)
            with c_v1: ui_card("Invested Cap", f"€{invested_cap/1e6:,.1f}M")
            with c_v2: ui_card("NOPAT", f"€{nopat/1e6:,.1f}M")
            
            st.divider()
            
            color_eva = "#27ae60" if eva_calc > 0 else "#e74c3c"
            ui_card("EVA (Value Added)", f"€{eva_calc/1e6:,.1f}M", "Creating Value" if eva_calc > 0 else "Destroying Value", color_eva)

    # DATA TAB
    with st.expander("📄 View Raw Data"):
        st.dataframe(df_raw, use_container_width=True)

else:
    st.info("Start by searching for a company or uploading a file.")