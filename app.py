# app.py (v6.0 - Professional Financial Structure)
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

st.set_page_config(page_title="ValuePy", page_icon="💎", layout="wide")

# === CSS ===
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .hero-title { font-family: 'Helvetica Neue', sans-serif; font-size: 36px; font-weight: 700; text-align: center; color: #2c3e50; margin-top: 10px; }
    .metric-card { background-color: white; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); text-align: center; }
    .metric-label { font-size: 11px; color: #7f8c8d; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 20px; font-weight: 800; color: #2c3e50; margin: 5px 0; }
    .section-header { font-size: 18px; font-weight: 700; color: #34495e; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #3498db; display: inline-block; }
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
st.markdown('<div class="hero-title">💎 ValuePy Pro</div>', unsafe_allow_html=True)

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
    sector_stats = {'Net_Margin': [], 'ROE': [], 'PE_Ratio': [], 'DSO': []} # Simplified stats for now

    with st.spinner(T['processing']):
        try:
            if input_mode == "Yahoo" and ticker_in:
                main_ticker = resolve_to_ticker(ticker_in)
                analysis_group['main_ticker'] = main_ticker
                analysis_group['title'] = f"{main_ticker} vs Peers" if competitors_in else f"{main_ticker}"

                if main_ticker:
                    data = get_company_df(main_ticker, "yahoo")
                    info_df, _ = load_company_info(main_ticker)
                    mcap = info_df['Κεφαλαιοποίηση'].iloc[0] if not info_df.empty else 0
                    if data:
                        df = normalize_dataframe(data[0]['table'], "yahoo")
                        df['Market Cap'] = mcap
                        forensics = calculate_financial_ratios(df)
                        analysis_group['reports'][main_ticker] = {'data': forensics, 'df': df}

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
    
    active_data = reports_dict[selected_company]
    # DATA EXTRACTION (New Structure v6.0)
    res = active_data['data']
    core = res.get('Core', {})
    risk = res.get('Forensics', {})
    df_raw = active_data['df']

    # Unpack Core
    cf = core.get('Cash_Flow', {})
    eff = core.get('Efficiency', {})
    liq = core.get('Liquidity', {})
    sol = core.get('Solvency', {})
    prof = core.get('Profitability', {})

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"### 📑 {selected_company}")
    with col_h2:
        pdf_bytes = create_pdf_bytes(selected_company, res)
        st.download_button(T['download_pdf'], pdf_bytes, f"ValuePy_{selected_company}.pdf", "application/pdf")

    # === UI CARD FUNCTION ===
    def ui_card(label, value, color="#2c3e50", subtext=None):
        sub_html = f"<div style='font-size:10px; color:#95a5a6;'>{subtext}</div>" if subtext else ""
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {color};">{value}</div>
            {sub_html}
        </div>
        """, unsafe_allow_html=True)

    # === TABS: The New Architecture ===
    t1, t2, t3, t4 = st.tabs(["📊 THE CORE", "🕵️ FORENSICS", "⚖️ VALUATION", "📄 DATA"])

    # --- TAB 1: CORE FINANCIALS ---
    with t1:
        # 1. Profitability (Margins)
        st.markdown('<div class="section-header">1. Profitability & Margins</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: ui_card("Gross Margin", f"{prof.get('Gross_Margin', 0)}%", "#3498db")
        with c2: ui_card("Operating Margin", f"{prof.get('Operating_Margin', 0)}%", "#2980b9")
        with c3: ui_card("Net Margin", f"{prof.get('Net_Margin', 0)}%", "#2c3e50")
        
        # 2. Cash Flow
        st.markdown('<div class="section-header">2. Cash Flow Analysis</div>', unsafe_allow_html=True)
        cf_col1, cf_col2 = st.columns([1, 2])
        with cf_col1:
            ui_card("CFO (Operating)", f"€{cf.get('CFO',0)/1e6:,.1f}M", "#27ae60", "Cash from Ops")
            ui_card("Free Cash Flow", f"€{cf.get('FCF',0)/1e6:,.1f}M", "#27ae60", "CFO - CAPEX")
        with cf_col2:
            fig_wf = go.Figure(go.Waterfall(
                measure = ["relative", "relative", "total"],
                x = ["CFO", "CAPEX", "FCF"],
                y = [cf.get('CFO',0), -cf.get('CAPEX',0), cf.get('FCF',0)],
                text = [f"{cf.get('CFO',0)/1e6:.0f}M", f"-{cf.get('CAPEX',0)/1e6:.0f}M", f"{cf.get('FCF',0)/1e6:.0f}M"],
                connector = {"line":{"color":"gray"}},
                decreasing = {"marker":{"color":"#e74c3c"}},
                increasing = {"marker":{"color":"#2ecc71"}},
                totals = {"marker":{"color":"#3498db"}}
            ))
            fig_wf.update_layout(height=250, margin=dict(t=20, b=20), title="Free Cash Flow Bridge")
            st.plotly_chart(fig_wf, use_container_width=True)

        # 3. Efficiency & Liquidity (Grid)
        st.markdown('<div class="section-header">3. Efficiency, Liquidity & Solvency</div>', unsafe_allow_html=True)
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.markdown("**Efficiency (Days)**")
            st.write(f"**DSO (Collect):** {eff.get('DSO',0):.0f} days")
            st.write(f"**DSI (Inventory):** {eff.get('DSI',0):.0f} days")
            st.write(f"**DPO (Pay):** {eff.get('DPO',0):.0f} days")
            st.divider()
            ui_card("CCC (Cycle)", f"{eff.get('CCC',0):.0f} days", "#e67e22")
        
        with col_b:
            st.markdown("**Liquidity**")
            ui_card("Current Ratio", f"{liq.get('Current_Ratio', 0)}x", "black")
            ui_card("Quick Ratio", f"{liq.get('Quick_Ratio', 0)}x", "black")
            
        with col_c:
            st.markdown("**Solvency**")
            ui_card("Debt / Equity", f"{sol.get('Debt_to_Equity', 0)}x", "black")
            cov = sol.get('Interest_Coverage', 0)
            clr_cov = "#e74c3c" if cov < 1.5 else "#27ae60"
            ui_card("Int. Coverage", f"{cov}x", clr_cov)

    # --- TAB 2: FORENSICS ---
    with t2:
        st.info("🕵️ **Forensic Analysis:** Advanced models to detect bankruptcy risk and accounting manipulation.")
        
        z_col, m_col = st.columns(2)
        
        with z_col:
            z_score = risk.get('Z_Score', 0)
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
            st.caption("Safe Zone: > 3.0 | Distress Zone: < 1.8")

        with m_col:
            m_score = risk.get('M_Score', -3)
            fig_m = go.Figure(go.Indicator(
                mode = "gauge+number", value = m_score,
                title = {'text': "Beneish M-Score (Manipulation)"},
                gauge = {
                    'axis': {'range': [-5, 0]}, 'bar': {'color': "black"},
                    'steps': [{'range': [-5, -2.22], 'color': "#27ae60"}, {'range': [-2.22, -1.78], 'color': "#95a5a6"}, {'range': [-1.78, 0], 'color': "#e74c3c"}],
                }
            ))
            fig_m.update_layout(height=250, margin=dict(t=30, b=20))
            st.plotly_chart(fig_m, use_container_width=True)
            st.caption("Likely Manipulator: > -1.78 | Safe: < -2.22")

    # --- TAB 3: VALUATION ---
    with t3:
        st.subheader(f"{T['val_lab_title']}: {selected_company}")
        st.markdown(T['val_lab_desc'])
        wacc = st.slider("Target WACC", 0.04, 0.20, 0.10, 0.005, format="%.1f%%", key=f"wacc_{selected_company}")
        
        # Fallback to old path if needed
        p5 = res.get('Pillar_5', {})
        invested_cap = p5.get('Invested_Capital', 0)
        nopat = p5.get('NOPAT', 0)
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