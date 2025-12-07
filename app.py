# app.py (v8.0 - Full 7-Pillar CFA Dashboard)
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

try:
    from test_loader import resolve_to_ticker, load_company_info, get_company_df, normalize_dataframe
    from modules.analyzer import calculate_financial_ratios
    from modules.report_generator import create_pdf_bytes
    from modules.languages import get_text
except ImportError as e:
    st.error(f"System Error: {e}")
    st.stop()

st.set_page_config(page_title="ValuePy Pro", page_icon="💎", layout="wide")

# === CSS ===
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .hero-title { font-family: 'Helvetica Neue', sans-serif; font-size: 32px; font-weight: 700; text-align: center; color: #2c3e50; margin-top: 10px; }
    .metric-card { background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); text-align: center; }
    .metric-label { font-size: 11px; color: #7f8c8d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 18px; font-weight: 800; color: #2c3e50; margin: 4px 0; }
    .category-header { font-size: 16px; font-weight: 700; color: #2980b9; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #3498db; padding-bottom: 5px; display:inline-block; }
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
st.markdown('<div class="hero-title">💎 ValuePy <span style="color:#3498db">CFA Edition</span></div>', unsafe_allow_html=True)

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
    
    with st.spinner(T['processing']):
        try:
            if input_mode == "Yahoo" and ticker_in:
                main_ticker = resolve_to_ticker(ticker_in)
                analysis_group['main_ticker'] = main_ticker
                analysis_group['title'] = f"{main_ticker} vs Peers" if competitors_in else f"{main_ticker}"

                # Main
                if main_ticker:
                    data = get_company_df(main_ticker, "yahoo")
                    info_df, _ = load_company_info(main_ticker)
                    mcap = info_df['Κεφαλαιοποίηση'].iloc[0] if not info_df.empty else 0
                    if data:
                        df = normalize_dataframe(data[0]['table'], "yahoo")
                        df['Market Cap'] = mcap
                        forensics = calculate_financial_ratios(df)
                        analysis_group['reports'][main_ticker] = {'data': forensics, 'df': df}

                # Competitors
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
                        if not norm.empty and 'Year' in norm.columns:
                            full_df = pd.concat([full_df, norm])
                    if not full_df.empty:
                        full_df['Year'] = pd.to_numeric(full_df['Year'], errors='coerce')
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
    main_ticker = group['main_ticker']

    st.divider()
    
    # Selector
    company_options = list(reports_dict.keys())
    if main_ticker in company_options:
        company_options.remove(main_ticker)
        company_options.insert(0, main_ticker)
    
    st.markdown(f"<h5 style='text-align:center; color:#7f8c8d;'>{T['select_view']}</h5>", unsafe_allow_html=True)
    selected_company = st.radio("Select View", company_options, horizontal=True, label_visibility="collapsed")
    
    active_report = reports_dict[selected_company]
    res = active_report['data']
    df_raw = active_report['df']
    
    # === DATA UNPACKING (v8.0 Structure) ===
    analysis = res.get('Analysis', {})
    forensics = res.get('Forensics', {})
    val = res.get('Valuation', {})
    
    # The 7 Pillars
    liq = analysis.get('1_Liquidity', {})
    act = analysis.get('2_Activity', {})
    sol = analysis.get('3_Solvency', {})
    prof = analysis.get('4_Profitability', {})
    mgmt = analysis.get('5_Management', {})
    share = analysis.get('6_Per_Share', {})
    cf = analysis.get('7_Cash_Flow', {})

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"### 📑 {selected_company}")
    with col_h2:
        pdf_bytes = create_pdf_bytes(selected_company, res)
        st.download_button(T['download_pdf'], pdf_bytes, f"ValuePy_{selected_company}.pdf", "application/pdf")

    def ui_card(label, value, color="#2c3e50"):
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {color};">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    # === TABS ===
    t1, t2, t3, t4 = st.tabs(["📊 FUNDAMENTALS", "🕵️ FORENSICS", "⚖️ VALUATION", "📄 DATA"])

    # --- TAB 1: THE 7 PILLARS ---
    with t1:
        # 1. CASH FLOWS (The Foundation)
        st.markdown('<div class="category-header">1. Cash Flows & CAPEX</div>', unsafe_allow_html=True)
        cf1, cf2, cf3, cf4 = st.columns(4)
        with cf1: ui_card("CFO (Operating)", f"€{cf.get('CFO',0)/1e6:,.1f}M", "#27ae60")
        with cf2: ui_card("FCF (Free)", f"€{cf.get('FCF',0)/1e6:,.1f}M", "#27ae60")
        with cf3: ui_card("CAPEX", f"€{cf.get('CAPEX',0)/1e6:,.1f}M", "#e74c3c")
        with cf4: ui_card("CAPEX / Sales", f"{cf.get('CAPEX_Sales',0)}%", "black")

        # 2. ACTIVITY & EFFICIENCY
        st.markdown('<div class="category-header">2. Activity & Efficiency (The Cycle)</div>', unsafe_allow_html=True)
        col_eff1, col_eff2 = st.columns([3, 1])
        with col_eff1:
            e1, e2, e3, e4 = st.columns(4)
            with e1: ui_card("DSO (Collect)", f"{act.get('DSO',0):.0f} d")
            with e2: ui_card("DSI (Inventory)", f"{act.get('DSI',0):.0f} d")
            with e3: ui_card("DPO (Pay)", f"{act.get('DPO',0):.0f} d")
            with e4: ui_card("CCC (Cash Cycle)", f"{act.get('CCC',0):.0f} d", "#e67e22")
        with col_eff2:
            ui_card("Asset Turnover", f"{act.get('Total_Asset_Turnover',0)}x")
            ui_card("Fixed Asset Turn", f"{act.get('Fixed_Asset_Turnover',0)}x")

        # 3. LIQUIDITY & SOLVENCY
        st.markdown('<div class="category-header">3. Liquidity & Solvency (Risk)</div>', unsafe_allow_html=True)
        r1, r2, r3, r4 = st.columns(4)
        with r1: ui_card("Current Ratio", f"{liq.get('Current_Ratio',0)}x")
        with r2: ui_card("Quick Ratio", f"{liq.get('Quick_Ratio',0)}x")
        with r3: ui_card("Net Debt / EBITDA", f"{sol.get('Net_Debt_to_EBITDA',0)}x")
        with r4: ui_card("Interest Cov.", f"{sol.get('Interest_Coverage',0)}x")

        # 4. PROFITABILITY & MANAGEMENT
        st.markdown('<div class="category-header">4. Profitability & Management Returns</div>', unsafe_allow_html=True)
        p1, p2, p3, p4 = st.columns(4)
        with p1: ui_card("Gross Margin", f"{prof.get('Gross_Margin',0)}%")
        with p2: ui_card("EBITDA Margin", f"{prof.get('EBITDA_Margin',0)}%")
        with p3: ui_card("ROE", f"{mgmt.get('ROE',0)}%", "#8e44ad")
        with p4: ui_card("ROIC", f"{mgmt.get('ROIC',0)}%", "#8e44ad")

        # 5. PER SHARE
        st.markdown('<div class="category-header">5. Per Share Data</div>', unsafe_allow_html=True)
        ps1, ps2, ps3 = st.columns(3)
        with ps1: ui_card("EPS", f"€{share.get('EPS',0)}")
        with ps2: ui_card("Book Value / Sh", f"€{share.get('BVPS',0)}")
        with ps3: ui_card("Dividend Payout", f"{share.get('Dividend_Payout',0)}%")

    # --- TAB 2: FORENSICS ---
    with t2:
        st.info("🕵️ **Forensic Analysis:** Advanced models to detect bankruptcy risk and accounting manipulation.")
        
        z_col, m_col = st.columns(2)
        with z_col:
            z_score = forensics.get('Z_Score', 0)
            fig_z = go.Figure(go.Indicator(
                mode = "gauge+number", value = z_score,
                title = {'text': "Altman Z-Score (Bankruptcy)"},
                gauge = {
                    'axis': {'range': [0, 5]}, 'bar': {'color': "black"},
                    'steps': [{'range': [0, 1.8], 'color': "#e74c3c"}, {'range': [1.8, 3], 'color': "#95a5a6"}, {'range': [3, 5], 'color': "#27ae60"}],
                }
            ))
            fig_z.update_layout(height=250, margin=dict(t=30, b=20))
            st.plotly_chart(fig_z, use_container_width=True)

        with m_col:
            # Waterfall Quality
            fig_wf = go.Figure(go.Waterfall(
                measure = ["relative", "total", "relative"],
                x = ["Net Income", "CFO", "Gap"],
                y = [forensics.get('Net_Income',0), 0, forensics.get('Gap',0)], # Logic simplified
                text = ["Net Inc", "CFO", "Gap"],
                connector = {"line":{"color":"gray"}},
                decreasing = {"marker":{"color":"#e74c3c"}},
                increasing = {"marker":{"color":"#2ecc71"}},
                totals = {"marker":{"color":"#3498db"}}
            ))
            fig_wf.update_layout(height=250, margin=dict(t=10,b=10), title="Earnings Quality (Income vs Cash)")
            st.plotly_chart(fig_wf, use_container_width=True)

    # --- TAB 3: VALUATION ---
    with t3:
        st.subheader(f"{T['val_lab_title']}: {selected_company}")
        st.markdown(T['val_lab_desc'])
        wacc = st.slider("Target WACC", 0.04, 0.20, 0.10, 0.005, format="%.1f%%", key=f"wacc_{selected_company}")
        
        invested_cap = val.get('Invested_Capital', 0)
        nopat = val.get('NOPAT', 0)
        eva_calc = nopat - (invested_cap * wacc)
        
        c_v1, c_v2, c_v3 = st.columns(3)
        c_v1.metric("Invested Capital", f"€{invested_cap/1e6:,.1f}M")
        c_v2.metric("NOPAT", f"€{nopat/1e6:,.1f}M")
        c_v3.metric("EVA", f"€{eva_calc/1e6:,.1f}M", delta_color="normal" if eva_calc>0 else "inverse")

    # --- TAB 4: DATA ---
    with t4:
        st.dataframe(df_raw, use_container_width=True)

else:
    st.info("Start by searching for a company or uploading a file.")