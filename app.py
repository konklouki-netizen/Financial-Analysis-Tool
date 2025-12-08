# app.py (Final Fix)
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
trigger_analysis = False; input_mode = "Yahoo"; ticker_in = None

with col_center:
    tab_search, tab_upload = st.tabs([T['search_tab'], T['upload_tab']])
    with tab_search:
        ticker_in = st.text_input("Ticker:", placeholder=T['ticker_placeholder'])
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
                
                # Fetch Data
                data = get_company_df(main_ticker, "yahoo")
                
                # Check list emptiness explicitly
                if data and len(data) > 0:
                    info_df, _ = load_company_info(main_ticker)
                    df = normalize_dataframe(data[0]['table'], "yahoo")
                    
                    # Ensure DF is not empty
                    if not df.empty:
                        df['Market Cap'] = info_df['Κεφαλαιοποίηση'].iloc[0] if not info_df.empty else 0
                        forensics = calculate_financial_ratios(df)
                        analysis_group['reports'][main_ticker] = {'data': forensics, 'df': df}
                        st.session_state.history.append(analysis_group)
                        st.session_state.current_group = analysis_group
                        st.rerun()
                    else:
                        st.error("❌ Dataframe is empty.")
                else:
                    st.error(f"❌ No data found for {main_ticker}. Try 'TSLA'.")

            elif input_mode == "File" and file_in:
                # File logic simplified
                pass 

        except Exception as e: st.error(f"Error: {e}")

if st.session_state.current_group:
    group = st.session_state.current_group
    reports = group['reports']
    selected_company = list(reports.keys())[0]
    
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

    t1, t2, t3, t4 = st.tabs(["🏥 HEALTH", "💰 PROFIT", "⚙️ EFFICIENCY", "⚖️ VALUATION"])

    with t1:
        col_g, col_info = st.columns([1, 2])
        with col_g:
            fig_g = go.Figure(go.Indicator(mode="gauge+number", value=for_.get('Health_Score', 0), title={'text': "Health Score"}, gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2c3e50"}, 'steps': [{'range': [0, 40], 'color': "#e74c3c"}, {'range': [40, 70], 'color': "#f1c40f"}, {'range': [70, 100], 'color': "#27ae60"}]}))
            fig_g.update_layout(height=220, margin=dict(t=30, b=20)); st.plotly_chart(fig_g, use_container_width=True)
        with col_info:
            c1, c2 = st.columns(2)
            with c1: ui_card("Debt / Equity", f"{an.get('3_Solvency',{}).get('Debt_to_Equity',0)}x"); ui_card("Z-Score", f"{for_.get('Z_Score',0)}")
            with c2: ui_card("Current Ratio", f"{an.get('1_Liquidity',{}).get('Current_Ratio',0)}x"); ui_card("M-Score", f"{for_.get('M_Score',0)}")

    with t2:
        col_L, col_R = st.columns([1, 2])
        with col_L:
            prof = an.get('4_Profitability', {})
            ui_card("Gross Margin", f"{prof.get('Gross_Margin',0)}%"); ui_card("Net Margin", f"{prof.get('Net_Margin',0)}%")
        with col_R:
            st.subheader("Cash Flow")
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
        wacc = st.slider("WACC", 0.04, 0.20, 0.10, 0.005)
        ic = val.get('Invested_Capital', 0); nopat = val.get('NOPAT', 0); eva = nopat - (ic * wacc)
        c1, c2 = st.columns(2)
        c1.metric("NOPAT", f"€{nopat/1e6:,.1f}M"); c2.metric("EVA", f"€{eva/1e6:,.1f}M")

else: st.info("Start by searching for a company (e.g. TSLA) or uploading a file.")