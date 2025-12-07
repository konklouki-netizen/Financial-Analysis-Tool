# app.py (v4.6 - Health Score & Strategic Charts)
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
st.markdown('<div class="hero-title">💎 ValuePy</div>', unsafe_allow_html=True)

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
    sector_stats = {'Net_Margin': [], 'ROE': [], 'PE_Ratio': [], 'DSO': []}

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
                                p3=c_metrics['Pillar_3']; p5=c_metrics['Pillar_5']; p2=c_metrics['Pillar_2']
                                if p3['Net_Margin']!=0: sector_stats['Net_Margin'].append(p3['Net_Margin'])
                                if p3['ROE']!=0: sector_stats['ROE'].append(p3['ROE'])
                                if p5['PE_Ratio']>0: sector_stats['PE_Ratio'].append(p5['PE_Ratio'])
                                if p2['DSO']>0: sector_stats['DSO'].append(p2['DSO'])

                # Benchmark
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
    
    # 1. SELECTOR
    company_options = list(reports_dict.keys())
    if main_ticker in company_options:
        company_options.remove(main_ticker)
        company_options.insert(0, main_ticker)
    
    st.markdown(f"<h5 style='text-align:center; color:#7f8c8d;'>{T['select_view']}</h5>", unsafe_allow_html=True)
    selected_company = st.radio("Select View", company_options, horizontal=True, label_visibility="collapsed")
    
    active_data = reports_dict[selected_company]
    forensics = active_data['data']
    df_raw = active_data['df']

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"### 📑 {selected_company}")
    with col_h2:
        pdf_bytes = create_pdf_bytes(selected_company, forensics)
        st.download_button(T['download_pdf'], pdf_bytes, f"ValuePy_{selected_company}.pdf", "application/pdf")

    # Shortcuts
    p1 = forensics.get('Pillar_1', {})
    p2 = forensics.get('Pillar_2', {})
    p3 = forensics.get('Pillar_3', {})
    p5 = forensics.get('Pillar_5', {})
    score = forensics.get('Health_Score', 50)

    # 2. HEALTH SCORE GAUGE (Top Banner)
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        title = {'text': "Health Score"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "#2c3e50"},
            'steps': [
                {'range': [0, 40], 'color': "#e74c3c"},
                {'range': [40, 70], 'color': "#f1c40f"},
                {'range': [70, 100], 'color': "#27ae60"}],
        }
    ))
    fig_gauge.update_layout(height=150, margin=dict(l=20,r=20,t=30,b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # 3. METRIC CARDS
    def card(lbl, val, delta, clr):
        st.markdown(f"""<div class="metric-card"><div class="metric-label">{lbl}</div><div class="metric-value" style="color: {clr};">{val}</div><div class="benchmark-val">{delta}</div></div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        flag_text = T['metrics']['ok']; clr = "#27ae60"
        if p1.get('Is_Paper_Profits'): flag_text = T['metrics']['red_flag']; clr = "#e74c3c"
        card(T['metrics']['quality'], flag_text, f"{T['metrics']['gap']}: {p1.get('Gap',0)/1e6:.1f}M", clr)
    with c2:
        b_roe = f"vs Avg: {bench.get('ROE', 0):.1f}%" if bench else "-"
        card(T['metrics']['roe'], f"{p3.get('ROE')}%", b_roe, "black")
    with c3:
        flag_sol = T['metrics']['solvent']
        if "ZOMBIE" in str(p2.get('Flag_Solvency')): flag_sol = T['metrics']['zombie']
        b_dso = f"vs Avg: {bench.get('DSO', 0):.0f}d" if bench else "-"
        card(T['metrics']['dso'], f"{p2.get('DSO'):.0f}d", flag_sol, "black")
    with c4:
        val_text = T['metrics']['creating']; clr = "#27ae60"
        if p5.get('EVA', 0) < 0: val_text = T['metrics']['destroying']; clr = "#e74c3c"
        b_pe = f"vs Avg: {bench.get('PE_Ratio', 0):.1f}x" if bench else "-"
        card(T['metrics']['valuation'], val_text, b_pe, clr)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 4. STRATEGIC CHARTS
    t1, t2, t3 = st.tabs(T['tabs'])
    
    with t1:
        # Chart Layout: 2 Columns
        g1, g2 = st.columns(2)
        
        with g1:
            st.markdown(f"**1. {T['waterfall_title']}**")
            # Waterfall (Profitability)
            fig_wf = go.Figure(go.Waterfall(
                measure = ["relative", "total", "relative"],
                x = ["Net Income", "CFO", "Gap"],
                y = [p1.get('Net_Income',0), 0, -p1.get('Gap',0)],
                text = [f"{p1.get('Net_Income',0)/1e6:.1f}M", f"{p1.get('CFO',0)/1e6:.1f}M", ""],
                connector = {"line":{"color":"rgb(63, 63, 63)"}},
                decreasing = {"marker":{"color":"#e74c3c"}},
                increasing = {"marker":{"color":"#2ecc71"}},
                totals = {"marker":{"color":"#3498db"}}
            ))
            fig_wf.update_layout(height=350, margin=dict(t=20, b=20))
            st.plotly_chart(fig_wf, use_container_width=True)
            if p1.get('Is_Paper_Profits'):
                st.warning("⚠️ **Warning:** Profits are not converting to cash.")
            else:
                st.success("✅ **Quality:** High cash conversion.")

        with g2:
            st.markdown(f"**2. Efficiency Risk (DSO Comparison)**")
            # Bar Chart (DSO)
            dso_val = p2.get('DSO', 0)
            bench_dso = bench.get('DSO', 0) if bench else 0
            
            fig_dso = go.Figure(data=[
                go.Bar(name=selected_company, x=['Days Sales Outstanding'], y=[dso_val], marker_color='#2c3e50'),
                go.Bar(name='Peer Avg', x=['Days Sales Outstanding'], y=[bench_dso], marker_color='#95a5a6')
            ])
            fig_dso.update_layout(height=350, margin=dict(t=20, b=20), barmode='group')
            st.plotly_chart(fig_dso, use_container_width=True)
            
            if bench and dso_val > bench_dso * 1.2:
                st.warning(f"⚠️ Collection is slower than peers ({dso_val:.0f} vs {bench_dso:.0f} days).")
            else:
                st.success("✅ Collection efficiency is healthy.")

    with t2:
        st.subheader(f"{T['val_lab_title']}: {selected_company}")
        st.markdown(T['val_lab_desc'])
        wacc = st.slider("Target WACC", 0.04, 0.20, 0.10, 0.005, format="%.1f%%", key=f"wacc_{selected_company}")
        
        invested_cap = p5.get('Invested_Capital', 0)
        nopat = p5.get('NOPAT', 0)
        eva_calc = nopat - (invested_cap * wacc)
        
        c_v1, c_v2, c_v3 = st.columns(3)
        c_v1.metric("Invested Capital", f"€{invested_cap/1e6:,.1f}M")
        c_v2.metric("NOPAT", f"€{nopat/1e6:,.1f}M")
        c_v3.metric("EVA", f"€{eva_calc/1e6:,.1f}M", delta_color="normal" if eva_calc>0 else "inverse")

    with t3:
        st.dataframe(df_raw, use_container_width=True)

else:
    st.info("Start by searching for a company or uploading a file.")