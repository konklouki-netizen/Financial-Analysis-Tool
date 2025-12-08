# app.py (v9.1 - Syntax Error Fixed)
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
    .metric-card { background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .metric-label { font-size: 11px; color: #7f8c8d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 19px; font-weight: 800; color: #2c3e50; margin: 4px 0; }
    .header-bar { font-size: 18px; font-weight: 700; color: #34495e; margin: 25px 0 15px 0; border-left: 5px solid #3498db; padding-left: 10px; }
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
    sector_stats = {'ROE': [], 'PE_Ratio': []}

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
                                try:
                                    roe = c_metrics['Analysis']['5_Management']['ROE']
                                    if roe != 0: sector_stats['ROE'].append(roe)
                                except: pass

                benchmark_data = {}
                for k, v in sector_stats.items():
                    if v: benchmark_data[k] = sum(v) / len(v)
                analysis_group['benchmark'] = benchmark_data

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
    bench = group['benchmark']
    main_ticker = group['main_ticker']

    st.divider()
    
    # Selector
    company_options = list(reports_dict.keys())
    if main_ticker in company_options:
        company_options.remove(main_ticker)
        company_options.insert(0, main_ticker)
    
    st.markdown(f"<h5 style='text-align:center; color:#7f8c8d;'>{T['select_view']}</h5>", unsafe_allow_html=True)
    selected_company = st.radio("Select View", company_options, horizontal=True, label_visibility="collapsed")
    
    # Data Unpacking
    active_report = reports_dict[selected_company]
    res = active_report['data']
    df_raw = active_report['df']
    
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
        pdf_bytes = create_pdf_bytes(selected_company, res)
        st.download_button(T['download_pdf'], pdf_bytes, f"ValuePy_{selected_company}.pdf", "application/pdf")

    # Helper UI Function
    def ui_card(label, value, color="#2c3e50"):
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {color};">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    # === TABS ===
    t1, t2, t3, t4 = st.tabs(["📊 DASHBOARD", "🔍 DEEP DIVE (7 PILLARS)", "⚖️ VALUATION", "📄 DATA"])

    # --- TAB 1: VISUAL DASHBOARD ---
    with t1:
        # TOP ROW: HEALTH SCORE
        score = for_.get('Health_Score', 50)
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number", value = score,
            title = {'text': "Overall Health Score"},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#2c3e50"},
                     'steps': [{'range': [0, 40], 'color': "#e74c3c"}, {'range': [40, 70], 'color': "#f1c40f"}, {'range': [70, 100], 'color': "#27ae60"}]}
        ))
        fig_g.update_layout(height=200, margin=dict(t=20, b=20))
        st.plotly_chart(fig_g, use_container_width=True)

        st.divider()

        # ROW 2: Charts (Side by Side)
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("**1. Profit Quality (Waterfall)**")
            
            # ΔΙΟΡΘΩΣΗ: Σωστή λογική Waterfall χωρίς διπλά 'y'
            # Υπολογισμός τιμών για το γράφημα
            net_inc = for_.get('Net_Income', 0)
            cfo_val = for_.get('CFO', 0)
            gap_val = cfo_val - net_inc
            
            fig_wf = go.Figure(go.Waterfall(
                measure = ["relative", "relative", "total"],
                x = ["Net Income", "Gap", "CFO"],
                y = [net_inc, gap_val, cfo_val],
                text = [f"{net_inc/1e6:.1f}M", f"{gap_val/1e6:.1f}M", f"{cfo_val/1e6:.1f}M"],
                connector = {"line":{"color":"gray"}},
                decreasing = {"marker":{"color":"#e74c3c"}},
                increasing = {"marker":{"color":"#2ecc71"}},
                totals = {"marker":{"color":"#3498db"}}
            ))
            fig_wf.update_layout(height=300, margin=dict(t=20, b=20))
            st.plotly_chart(fig_wf, use_container_width=True)

        with c2:
            st.markdown("**2. ROE Drivers (DuPont Sunburst)**")
            labels = ["ROE", "Margins", "Turnover", "Leverage"]
            parents = ["", "ROE", "ROE", "ROE"]
            v_roe = max(mgmt.get('ROE', 1), 1)
            values = [v_roe, v_roe*0.4, v_roe*0.3, v_roe*0.3]
            
            fig_dupont = go.Figure(go.Sunburst(
                labels=labels, parents=parents, values=values,
                branchvalues="total", marker=dict(colors=["#2c3e50", "#3498db", "#e67e22", "#9b59b6"])
            ))
            fig_dupont.update_layout(height=300, margin=dict(t=20, b=20))
            st.plotly_chart(fig_dupont, use_container_width=True)

        # ROW 3: Risk Gauges
        st.divider()
        st.subheader("Risk Radar")
        r1, r2 = st.columns(2)
        with r1:
            z = for_.get('Z_Score', 0)
            fig_z = go.Figure(go.Indicator(
                mode="gauge+number", value=z, title={'text': "Z-Score (Bankruptcy)"},
                gauge={'axis': {'range': [0, 5]}, 'bar': {'color': "black"}, 'steps': [{'range': [0, 1.8], 'color': "#e74c3c"}, {'range': [1.8, 3], 'color': "#95a5a6"}, {'range': [3, 5], 'color': "#27ae60"}]}
            ))
            fig_z.update_layout(height=200, margin=dict(t=20, b=20))
            st.plotly_chart(fig_z, use_container_width=True)
        with r2:
            m = for_.get('M_Score', -3)
            fig_m = go.Figure(go.Indicator(
                mode="gauge+number", value=m, title={'text': "M-Score (Fraud)"},
                gauge={'axis': {'range': [-5, 0]}, 'bar': {'color': "black"}, 'steps': [{'range': [-5, -2.22], 'color': "#27ae60"}, {'range': [-2.22, -1.78], 'color': "#95a5a6"}, {'range': [-1.78, 0], 'color': "#e74c3c"}]}
            ))
            fig_m.update_layout(height=200, margin=dict(t=20, b=20))
            st.plotly_chart(fig_m, use_container_width=True)

    # --- TAB 2: DEEP DIVE (THE 7 PILLARS) ---
    with t2:
        st.markdown('<div class="header-bar">1. Liquidity (Ρευστότητα)</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: ui_card("Current Ratio", f"{liq.get('Current_Ratio',0)}x")
        with c2: ui_card("Quick Ratio", f"{liq.get('Quick_Ratio',0)}x")
        with c3: ui_card("Cash Ratio", f"{liq.get('Cash_Ratio',0)}x")

        st.markdown('<div class="header-bar">2. Activity (Δραστηριότητα)</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: ui_card("DSO (Collect)", f"{act.get('DSO',0):.0f} d")
        with c2: ui_card("DSI (Inventory)", f"{act.get('DSI',0):.0f} d")
        with c3: ui_card("DPO (Pay)", f"{act.get('DPO',0):.0f} d")
        with c4: ui_card("CCC (Cycle)", f"{act.get('CCC',0):.0f} d", "#e67e22")
        
        st.markdown('<div class="header-bar">3. Solvency (Φερεγγυότητα)</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: ui_card("Debt / Equity", f"{sol.get('Debt_to_Equity',0)}x")
        with c2: ui_card("Net Debt / EBITDA", f"{sol.get('Net_Debt_to_EBITDA',0)}x")
        with c3: ui_card("Interest Cov.", f"{sol.get('Interest_Coverage',0)}x")

        st.markdown('<div class="header-bar">4. Profitability (Κερδοφορία)</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: ui_card("Gross Margin", f"{prof.get('Gross_Margin',0)}%", "#3498db")
        with c2: ui_card("Operating Margin", f"{prof.get('Operating_Margin',0)}%", "#2980b9")
        with c3: ui_card("Net Margin", f"{prof.get('Net_Margin',0)}%", "#2c3e50")

        st.markdown('<div class="header-bar">5. Management (Απόδοση Διοίκησης)</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: ui_card("ROE", f"{mgmt.get('ROE',0)}%", "#8e44ad")
        with c2: ui_card("ROA", f"{mgmt.get('ROA',0)}%")
        with c3: ui_card("ROIC", f"{mgmt.get('ROIC',0)}%", "#8e44ad")

        st.markdown('<div class="header-bar">6. Cash Flows (Ταμειακές Ροές)</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: ui_card("CFO (Ops)", f"€{cf.get('CFO',0)/1e6:,.1f}M", "#27ae60")
        with c2: ui_card("Free Cash Flow", f"€{cf.get('FCF',0)/1e6:,.1f}M", "#27ae60")
        with c3: ui_card("CAPEX % Sales", f"{cf.get('CAPEX_Sales',0)}%")

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