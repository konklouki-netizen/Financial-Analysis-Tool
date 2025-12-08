# app.py (v10.2 - Fixed NameError & Integrated View)
import streamlit as st
import pandas as pd
import os
import sys
import plotly.graph_objects as go 
import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path: sys.path.append(script_dir)

try:
    from test_loader import resolve_to_ticker, load_company_info, get_company_df, normalize_dataframe
    from modules.analyzer import calculate_financial_ratios
    from modules.report_generator import create_pdf_bytes
    from modules.languages import get_text
except ImportError as e: st.error(f"System Error: {e}"); st.stop()

st.set_page_config(page_title="ValuePy Pro", page_icon="💎", layout="wide")
st.markdown("<style>.metric-card { background-color: white; border-left: 4px solid #3498db; border-radius: 5px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 10px; } .metric-label { font-size: 12px; color: #7f8c8d; font-weight: 600; } .metric-value { font-size: 20px; font-weight: 800; color: #2c3e50; } div[data-testid='stRadio'] > label { display: none; }</style>", unsafe_allow_html=True)

if 'history' not in st.session_state: st.session_state.history = [] 
if 'current_group' not in st.session_state: st.session_state.current_group = None

lang_choice = st.sidebar.selectbox("Language / Γλώσσα", ["English", "Ελληνικά"])
T = get_text('GR' if lang_choice == "Ελληνικά" else 'EN')

st.sidebar.title(T['sidebar_title'])
if st.sidebar.button(T['clear_history']): st.session_state.history = []; st.session_state.current_group = None; st.rerun()
for i, group in enumerate(reversed(st.session_state.history)):
    if st.sidebar.button(f"{group.get('title')} ({group.get('time')})", key=f"hist_{i}"): st.session_state.current_group = group; st.rerun()

st.markdown('<div style="font-size:32px; font-weight:700; text-align:center; color:#2c3e50;">💎 ValuePy <span style="color:#3498db">Pro</span></div>', unsafe_allow_html=True)
col_space_1, col_center, col_space_2 = st.columns([1, 2, 1])
trigger_analysis = False; input_mode = "Yahoo"; ticker_in = None; competitors_in = None

with col_center:
    tab_search, tab_upload = st.tabs([T['search_tab'], T['upload_tab']])
    with tab_search:
        ticker_in = st.text_input("Ticker:", placeholder=T['ticker_placeholder'])
        with st.expander(T['comp_label']): competitors_in = st.text_input("Competitors:", placeholder=T['comp_placeholder'])
        if st.button(T['btn_run'], type="primary", use_container_width=True): trigger_analysis = True
    with tab_upload:
        file_in = st.file_uploader("Report:", type=['pdf', 'xlsx'])
        if file_in and st.button(T['btn_upload'], type="primary", use_container_width=True): trigger_analysis = True; input_mode = "File"

if trigger_analysis:
    timestamp = datetime.datetime.now().strftime("%H:%M")
    analysis_group = {'time': timestamp, 'title': ticker_in or "Report", 'main_ticker': "", 'reports': {}, 'benchmark': {}}
    
    with st.spinner(T['processing']):
        try:
            if input_mode == "Yahoo" and ticker_in:
                main_ticker = resolve_to_ticker(ticker_in)
                analysis_group['main_ticker'] = main_ticker
                tickers = [main_ticker]
                if competitors_in: tickers += [c.strip().upper() for c in competitors_in.split(",")]
                
                for t in tickers:
                    data = get_company_df(t, "yahoo")
                    if data:
                        info_df, _ = load_company_info(t)
                        df = normalize_dataframe(data[0]['table'], "yahoo")
                        df['Market Cap'] = info_df['Κεφαλαιοποίηση'].iloc[0] if not info_df.empty else 0
                        forensics = calculate_financial_ratios(df)
                        analysis_group['reports'][t] = {'data': forensics, 'df': df}

                if analysis_group['reports']: st.session_state.history.append(analysis_group); st.session_state.current_group = analysis_group; st.rerun()
                else: st.error(f"❌ Δεν βρέθηκαν δεδομένα για '{main_ticker}'. Δοκίμασε 'TSLA' ή 'MSFT'.")

            elif input_mode == "File" and file_in:
                temp_path = f"temp_{file_in.name}"
                with open(temp_path, "wb") as f: f.write(file_in.getvalue())
                data = get_company_df(temp_path, "pdf" if "pdf" in file_in.name else "excel")
                if data:
                    full_df = pd.DataFrame()
                    for pkg in data:
                        norm = normalize_dataframe(pkg['table'], "pdf")
                        if not norm.empty and 'Year' in norm.columns: full_df = pd.concat([full_df, norm])
                    if not full_df.empty:
                        full_df['Year'] = pd.to_numeric(full_df['Year'], errors='coerce')
                        full_df = full_df.groupby('Year', as_index=False).first()
                        forensics = calculate_financial_ratios(full_df)
                        analysis_group['reports'][file_in.name] = {'data': forensics, 'df': full_df}
                        st.session_state.history.append(analysis_group); st.session_state.current_group = analysis_group; st.rerun()
                if os.path.exists(temp_path): os.remove(temp_path)

        except Exception as e: st.error(f"Error: {e}")

if st.session_state.current_group:
    group = st.session_state.current_group
    reports = group['reports']
    main_ticker = group['main_ticker']
    
    company_options = list(reports.keys())
    if main_ticker in company_options: company_options.remove(main_ticker); company_options.insert(0, main_ticker)
    
    st.divider()
    selected_company = st.radio(T['select_view'], company_options, horizontal=True)
    
    active = reports[selected_company]['data']
    df_raw = reports[selected_company]['df']
    an = active.get('Analysis', {}); for_ = active.get('Forensics', {}); val = active.get('Valuation', {})
    
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1: st.markdown(f"### 📑 {selected_company}")
    with col_h2: st.download_button(T['download_pdf'], create_pdf_bytes(selected_company, active), f"{selected_company}.pdf", "application/pdf")

    def ui_card(label, value, subtext=None, color="#2c3e50"):
        border_c = "#3498db"
        if "RED" in str(subtext) or "ZOMBIE" in str(subtext): border_c = "#e74c3c"
        elif "OK" in str(subtext) or "SOLVENT" in str(subtext): border_c = "#27ae60"
        st.markdown(f"""<div class="metric-card" style="border-left: 4px solid {border_c};"><div class="metric-label">{label}</div><div class="metric-value" style="color:{color}">{value}</div><div style="font-size:11px; color:#95a5a6;">{subtext if subtext else ''}</div></div>""", unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["🏥 HEALTH & RISK", "💰 PROFIT & CASH", "⚙️ EFFICIENCY", "⚖️ VALUATION"])

    with t1:
        col_g, col_info = st.columns([1, 2])
        with col_g:
            fig_g = go.Figure(go.Indicator(mode="gauge+number", value=for_.get('Health_Score', 0), title={'text': "Health Score"}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2c3e50"}, 'steps': [{'range': [0, 40], 'color': "#e74c3c"}, {'range': [40, 70], 'color': "#f1c40f"}, {'range': [70, 100], 'color': "#27ae60"}]}))
            fig_g.update_layout(height=220, margin=dict(t=30, b=20)); st.plotly_chart(fig_g, use_container_width=True)
        with col_info:
            st.subheader("Risk Assessment")
            c1, c2 = st.columns(2)
            with c1: ui_card("Debt / Equity", f"{an.get('3_Solvency',{}).get('Debt_to_Equity',0)}x"); ui_card("Interest Cov.", f"{an.get('3_Solvency',{}).get('Interest_Coverage',0)}x")
            with c2: ui_card("Current Ratio", f"{an.get('1_Liquidity',{}).get('Current_Ratio',0)}x"); ui_card("Z-Score", f"{for_.get('Z_Score',0)}", "Bankruptcy Risk" if for_.get('Z_Score',0)<1.8 else "Safe")

    with t2:
        col_L, col_R = st.columns([1, 2])
        with col_L:
            prof = an.get('4_Profitability', {})
            ui_card("Gross Margin", f"{prof.get('Gross_Margin',0)}%"); ui_card("Operating Margin", f"{prof.get('Operating_Margin',0)}%"); ui_card("Net Margin", f"{prof.get('Net_Margin',0)}%")
        with col_R:
            st.subheader("Cash Flow Reality")
            net_inc = for_.get('Net_Income', 0); cfo = for_.get('CFO', 0); gap = cfo - net_inc
            fig_wf = go.Figure(go.Waterfall(measure=["relative", "relative", "total"], x=["Net Income", "Gap", "CFO"], y=[net_inc, gap, cfo], text=[f"{net_inc/1e6:.1f}M", "", f"{cfo/1e6:.1f}M"], connector={"line":{"color":"gray"}}, decreasing={"marker":{"color":"#e74c3c"}}, increasing={"marker":{"color":"#2ecc71"}}, totals={"marker":{"color":"#3498db"}}))
            fig_wf.update_layout(height=400, margin=dict(t=20, b=20)); st.plotly_chart(fig_wf, use_container_width=True)

    with t3:
        act = an.get('2_Activity', {})
        c1, c2, c3, c4 = st.columns(4)
        with c1: ui_card("DSO", f"{act.get('DSO',0):.0f} d"); 
        with c2: ui_card("DSI", f"{act.get('DSI',0):.0f} d"); 
        with c3: ui_card("DPO", f"{act.get('DPO',0):.0f} d"); 
        with c4: ui_card("CCC", f"{act.get('CCC',0):.0f} d")

    with t4:
        st.subheader(f"{T['val_lab_title']}: {selected_company}")
        wacc = st.slider("Target WACC", 0.04, 0.20, 0.10, 0.005, format="%.1f%%", key=f"wacc_{selected_company}")
        ic = val.get('Invested_Capital', 0); nopat = val.get('NOPAT', 0); eva = nopat - (ic * wacc)
        c1, c2, c3 = st.columns(3)
        c1.metric("Invested Cap", f"€{ic/1e6:,.1f}M"); c2.metric("NOPAT", f"€{nopat/1e6:,.1f}M"); c3.metric("EVA", f"€{eva/1e6:,.1f}M")

else: st.info("Start by searching for a company or uploading a file.")