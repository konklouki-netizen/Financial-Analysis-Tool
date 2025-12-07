# app.py (v4.4 - The Complete Suite: History, Groups, PDF & Valuation)
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
except ImportError as e:
    st.error(f"System Error: {e}")
    st.stop()

st.set_page_config(page_title="ValuePy", page_icon="💎", layout="wide")

# === CSS ===
st.markdown("""
<style>
    .main { background-color: #ffffff; }
    .hero-title { font-family: 'Helvetica Neue', sans-serif; font-size: 40px; font-weight: 700; text-align: center; color: #2c3e50; margin-top: 10px; }
    .metric-card { background-color: white; border: 1px solid #f0f0f0; border-radius: 12px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; }
    .metric-label { font-size: 12px; color: #95a5a6; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 22px; font-weight: 800; color: #2c3e50; margin: 5px 0; }
    .benchmark-val { font-size: 11px; color: #7f8c8d; font-style: italic; margin-top: 4px;}
    
    div[role="radiogroup"] { flex-direction: row; justify-content: center; background-color: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 20px;}
    div[data-testid="stRadio"] > label { display: none; }
</style>
""", unsafe_allow_html=True)

# === STATE MANAGEMENT ===
if 'history' not in st.session_state: st.session_state.history = [] 
if 'current_group' not in st.session_state: st.session_state.current_group = None

# === SIDEBAR (HISTORY) ===
st.sidebar.title("📜 History")
if st.sidebar.button("Clear History"):
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
st.markdown('<div class="hero-title">💎 ValuePy</div>', unsafe_allow_html=True)

col_space_1, col_center, col_space_2 = st.columns([1, 2, 1])
trigger_analysis = False
input_mode = "Yahoo"
ticker_in = None; competitors_in = None; file_in = None

with col_center:
    tab_search, tab_upload = st.tabs(["🔍 New Search", "📂 Upload File"])
    with tab_search:
        ticker_in = st.text_input("Main Ticker:", placeholder="e.g. MSFT, AEGN...", key="ticker_input")
        with st.expander("⚔️ Add Competitors (Comparison)"):
            competitors_in = st.text_input("Competitors (comma separated):", placeholder="e.g. GOOG, AMZN", key="comp_input")
            
        if st.button("Run Analysis", type="primary", use_container_width=True, key="btn_yahoo"):
            trigger_analysis = True; input_mode = "Yahoo"
    with tab_upload:
        file_in = st.file_uploader("Report:", type=['pdf', 'xlsx'], key="file_uploader")
        if file_in and st.button("Analyze File", type="primary", use_container_width=True, key="btn_file"):
            trigger_analysis = True; input_mode = "File"

# === ANALYSIS ENGINE ===
if trigger_analysis:
    timestamp = datetime.datetime.now().strftime("%H:%M")
    
    analysis_group = {
        'time': timestamp,
        'title': "",
        'main_ticker': "",
        'reports': {},
        'benchmark': {}
    }
    
    sector_stats = {'Net_Margin': [], 'ROE': [], 'PE_Ratio': [], 'DSO': []}

    with st.spinner("Processing Analysis Group..."):
        try:
            if input_mode == "Yahoo" and ticker_in:
                main_ticker = resolve_to_ticker(ticker_in)
                analysis_group['main_ticker'] = main_ticker
                
                if competitors_in:
                    analysis_group['title'] = f"{main_ticker} vs Peers"
                else:
                    analysis_group['title'] = f"{main_ticker}"

                # 1. Main
                if main_ticker:
                    data = get_company_df(main_ticker, "yahoo")
                    info_df, _ = load_company_info(main_ticker)
                    mcap = info_df['Κεφαλαιοποίηση'].iloc[0] if not info_df.empty else 0
                    if data:
                        df = normalize_dataframe(data[0]['table'], "yahoo")
                        df['Market Cap'] = mcap
                        forensics = calculate_financial_ratios(df)
                        analysis_group['reports'][main_ticker] = {'data': forensics, 'df': df}

                # 2. Competitors
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
                                
                                p3=c_metrics['Pillar_3']; p5=c_metrics['Pillar_5']; p2=c_metrics['Pillar_2']
                                if p3['Net_Margin']!=0: sector_stats['Net_Margin'].append(p3['Net_Margin'])
                                if p3['ROE']!=0: sector_stats['ROE'].append(p3['ROE'])
                                if p5['PE_Ratio']>0: sector_stats['PE_Ratio'].append(p5['PE_Ratio'])
                                if p2['DSO']>0: sector_stats['DSO'].append(p2['DSO'])

                # 3. Benchmark
                benchmark_data = {}
                for k, v in sector_stats.items():
                    if v: benchmark_data[k] = sum(v) / len(v)
                analysis_group['benchmark'] = benchmark_data

                # 4. Save
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

# === REPORT DISPLAY ===
if st.session_state.current_group:
    group = st.session_state.current_group
    reports_dict = group['reports']
    bench = group['benchmark']
    main_ticker = group['main_ticker']

    st.divider()
    
    company_options = list(reports_dict.keys())
    if main_ticker in company_options:
        company_options.remove(main_ticker)
        company_options.insert(0, main_ticker)
    
    st.markdown("<h5 style='text-align:center; color:#7f8c8d;'>Select Company View:</h5>", unsafe_allow_html=True)
    selected_company = st.radio("Select View", company_options, horizontal=True, label_visibility="collapsed")
    
    active_data = reports_dict[selected_company]
    forensics = active_data['data']
    df_raw = active_data['df']

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"### 📑 Analysis: **{selected_company}**")
    with col_h2:
        pdf_bytes = create_pdf_bytes(selected_company, forensics)
        st.download_button("📥 Download PDF", pdf_bytes, f"ValuePy_{selected_company}.pdf", "application/pdf")

    p1 = forensics.get('Pillar_1', {})
    p2 = forensics.get('Pillar_2', {})
    p3 = forensics.get('Pillar_3', {})
    p5 = forensics.get('Pillar_5', {})

    def card(lbl, val, delta, clr):
        st.markdown(f"""<div class="metric-card"><div class="metric-label">{lbl}</div><div class="metric-value" style="color: {clr};">{val}</div><div class="benchmark-val">{delta}</div></div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        clr = "#e74c3c" if p1.get('Is_Paper_Profits') else "#27ae60"
        card("QUALITY", p1.get('Flag'), f"Gap: {p1.get('Gap',0)/1e6:.1f}M", clr)
    with c2:
        b_roe = f"vs Peer Avg: {bench.get('ROE', 0):.1f}%" if bench else "-"
        card("ROE", f"{p3.get('ROE')}%", b_roe, "black")
    with c3:
        b_dso = f"vs Peer Avg: {bench.get('DSO', 0):.0f}d" if bench else "-"
        card("DSO", f"{p2.get('DSO'):.0f}d", b_dso, "black")
    with c4:
        b_pe = f"vs Peer Avg: {bench.get('PE_Ratio', 0):.1f}x" if bench else "-"
        clr = "#27ae60" if p5.get('EVA', 0) > 0 else "#e74c3c"
        card("VALUATION", p5.get('Value_Creation'), b_pe, clr)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # === Η ΔΙΟΡΘΩΣΗ: 3 TABS ===
    t1, t2, t3 = st.tabs(["📊 Charts", "⚖️ Valuation", "📄 Data"])
    
    with t1:
        fig = go.Figure(go.Waterfall(
            measure = ["relative", "total", "relative"],
            x = ["Net Income", "CFO", "Gap"],
            y = [p1.get('Net_Income',0), 0, -p1.get('Gap',0)],
            text = [f"{p1.get('Net_Income',0)/1e6:.1f}M", f"{p1.get('CFO',0)/1e6:.1f}M", ""],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig.update_layout(title="Earnings vs Cash Flow Reality", height=300)
        st.plotly_chart(fig, use_container_width=True)

    # === ΕΠΑΝΑΦΟΡΑ VALUATION LAB ===
    with t2:
        st.subheader(f"🧪 Valuation Lab: {selected_company}")
        st.markdown("Adjust the **Cost of Capital (WACC)** to see if the company creates economic value.")
        
        # Slider με μοναδικό κλειδί για να μην μπερδεύεται
        wacc = st.slider("Target WACC", 0.04, 0.20, 0.10, 0.005, format="%.1f%%", key=f"wacc_{selected_company}")
        
        invested_cap = p5.get('Invested_Capital', 0)
        nopat = p5.get('NOPAT', 0)
        eva_calc = nopat - (invested_cap * wacc)
        
        c_v1, c_v2, c_v3 = st.columns(3)
        c_v1.metric("Invested Capital", f"€{invested_cap/1e6:,.1f}M")
        c_v2.metric("NOPAT (Operating Profit)", f"€{nopat/1e6:,.1f}M")
        c_v3.metric("EVA (Economic Value Added)", f"€{eva_calc/1e6:,.1f}M", delta_color="normal" if eva_calc>0 else "inverse")
        
        if eva_calc > 0:
            st.success(f"With WACC {wacc*100:.1f}%, the company is **Creating Value** for shareholders.")
        else:
            st.error(f"With WACC {wacc*100:.1f}%, the company is **Destroying Value**.")

    with t3:
        st.dataframe(df_raw, use_container_width=True)

else:
    st.info("Start by searching for a company or uploading a file.")