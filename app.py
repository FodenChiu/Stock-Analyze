import streamlit as st
import pandas as pd
import requests
import datetime
import yfinance as yf
import time

# --- 🚀 全局介面與 Token 設定 ---
st.set_page_config(page_title="台股短線買入評級", page_icon="⚡", layout="wide")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0xOSAyMjo1Njo0NyIsInVzZXJfaWQiOiJGb2RlbkNoaXUiLCJlbWFpbCI6InlpaGFuY2hpdTExMDZAZ21haWwuY29tIiwiaXAiOiI0OS4xNTkuMjE3LjIwMiJ9.yYlYV7Y-PPQJxR6amyp9mDsK5su2T4HsZO0oYpotMEg"

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: "Microsoft JhengHei", sans-serif;
        background-color: #121212; color: #EAEAEA;
    }
    .main-title { color: #D4AF37; font-weight: bold; margin-bottom: 5px; }
    .input-label { font-size: 15px; font-weight: bold; color: #D4AF37; margin-bottom: 5px; }
    .weight-box { background-color: #1A1A1A; border: 1px solid #D4AF37; border-radius: 8px; padding: 20px; margin-top: 30px; margin-bottom: 20px; }
    .check-item { background-color: #1E1E1E; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px; border: 1px solid #333; display: flex; align-items: center; }
    .score-circle { background-color: #121212; border-radius: 50%; width: 130px; height: 130px; display: flex; align-items: center; justify-content: center; border: 10px solid #333; margin: 0 auto; box-shadow: 0 0 15px rgba(212, 175, 55, 0.2); }
    .score-text { font-size: 42px; font-weight: bold; color: #D4AF37; }
    .stButton > button { background-color: #D4AF37 !important; color: #121212 !important; font-weight: bold !important; border-radius: 8px !important; width: 100%; height: 50px; font-size: 16px !important; }
    .status-pass { background-color: #1A3E2A; color: #2DCC70; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #2DCC70; min-width: 90px; text-align: center; }
    .status-mid { background-color: #3E321A; color: #F1C40F; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #F1C40F; min-width: 90px; text-align: center; }
    .status-fail { background-color: #3E1A1A; color: #E74C3C; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #E74C3C; min-width: 90px; text-align: center; }
    input[data-testid="stTextInput"], textarea[data-testid="stTextArea"] { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; text-align: center; font-size: 18px !important;}
    div[data-baseweb="select"] > div { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; font-size: 16px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title" style="text-align:center;">⚡ 台股短線買入評級</h1>', unsafe_allow_html=True)
st.write("") 

# --- 🎯 數據庫引擎 ---
@st.cache_data(ttl=86400)
def fetch_stock_mapping():
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {"dataset": "TaiwanStockInfo", "token": FINMIND_TOKEN}
        res = requests.get(url, params=params, timeout=10).json()
        if res.get("msg") == "success":
            return dict(zip(pd.DataFrame(res["data"])['stock_id'], pd.DataFrame(res["data"])['stock_name']))
        return {}
    except: return {}

@st.cache_data(ttl=86400)
def fetch_total_shares(sid):
    for ext in [".TW", ".TWO"]:
        try:
            t = yf.Ticker(f"{sid}{ext}")
            shares = t.fast_info.get('shares', 0)
            if not shares or shares == 0: shares = t.info.get('sharesOutstanding', 0)
            if shares and shares > 0: return shares
        except: continue
    return 0

@st.cache_data(ttl=900)
def fetch_finmind_data(sid):
    try:
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=150)).strftime("%Y-%m-%d")
        url = "https://api.finmindtrade.com/api/v4/data"
        
        # 1. 股價
        res_p = requests.get(url, params={"dataset": "TaiwanStockPrice", "data_id": sid, "start_date": start_date, "end_date": end_date, "token": FINMIND_TOKEN}, timeout=10).json()
        if res_p.get("msg") != "success" or not res_p.get("data"): return None, None, None
        df = pd.DataFrame(res_p["data"])
        df.rename(columns={'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'}, inplace=True)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']: df[col] = pd.to_numeric(df[col])
        
        # 2. 外資持股
        res_fi = requests.get(url, params={"dataset": "TaiwanStockShareholding", "data_id": sid, "start_date": (datetime.datetime.now() - datetime.timedelta(days=20)).strftime("%Y-%m-%d"), "end_date": end_date, "token": FINMIND_TOKEN}, timeout=10).json()
        df_fi = pd.DataFrame(res_fi.get("data", []))
        
        # 3. 投信持股
        res_it = requests.get(url, params={"dataset": "TaiwanStockHoldingTrust", "data_id": sid, "start_date": (datetime.datetime.now() - datetime.timedelta(days=20)).strftime("%Y-%m-%d"), "end_date": end_date, "token": FINMIND_TOKEN}, timeout=10).json()
        df_it = pd.DataFrame(res_it.get("data", []))
        
        return df, df_fi, df_it
    except Exception as e: return "error", None, None

stock_mapping = fetch_stock_mapping()
stock_list = [f"{k} {v}" for k, v in stock_mapping.items()]

# --- 🎯 核心運算引擎 ---
def analyze_single_stock(stock_id):
    df, df_fi, df_it = fetch_finmind_data(stock_id)
    if df is None: return "not_found", None, None
    if isinstance(df, str) and df == "error": return "error", None, None
    if len(df) < 10: return "insufficient_data", None, None

    # 技術指標運算
    df['5MA'] = df['Close'].rolling(5).mean(); df['10MA'] = df['Close'].rolling(10).mean(); df['20MA'] = df['Close'].rolling(20).mean()
    df['5VMA'] = df['Volume'].rolling(5).mean()
    df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
    df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
    
    today, yest = df.iloc[-1], df.iloc[-2]
    total_shares = fetch_total_shares(stock_id)
    
    score = 0; tech_results = []; chip_results = []; summary = {}
    
    # 1. 週轉率 (5分)
    turnover = (today['Volume'] / total_shares) * 100 if total_shares > 0 else 0
    if 7.0 <= turnover <= 10.0: ts, tc = 5, "status-pass"
    elif (2.0 <= turnover < 7.0) or (10.0 < turnover <= 15.0): ts, tc = 3, "status-mid"
    elif (1.0 <= turnover < 2.0) or (15.0 < turnover <= 20.0): ts, tc = 1, "status-mid"
    else: ts, tc = 0, "status-fail"
    score += ts; tech_results.append(("週轉率判定", f"實測 {turnover:.2f}%", f"+{ts}分", tc, ""))

    # 2. KD 位階 (25分) + 高檔鈍化邏輯
    k_val = today['K']
    v0, v1, v2, v3 = df['Volume'].iloc[-1], df['Volume'].iloc[-2], df['Volume'].iloc[-3], df['Volume'].iloc[-4]
    is_excessive_vol = v0 > (v1 + v2 + v3) # 是否爆量
    is_above_5ma = today['Close'] > today['5MA']

    if k_val > 80:
        if is_above_5ma and not is_excessive_vol:
            ks, kc, km = 25, "status-pass", "🔥 高檔強勢鈍化 (動能極強)"
        else:
            ks, kc, km = 0, "status-fail", "過熱且量價背離"
    elif 30 <= k_val <= 45: ks, kc, km = 25, "status-pass", "KD 30~45 起漲黃金區"
    elif 45 < k_val <= 65: ks, kc, km = 20, "status-mid", "KD 46~65 中位階穩定"
    elif 65 < k_val <= 70: ks, kc, km = 10, "status-mid", "KD 66~70 稍高位階"
    elif 70 < k_val <= 80: ks, kc, km = 5, "status-fail", "KD 71~80 偏高"
    elif k_val < 30: ks, kc, km = 0, "status-fail", "動能不足"
    else: ks, kc, km = 0, "status-fail", "區間不明"
    score += ks; tech_results.append(("KD 位階判定", f"K值: {k_val:.1f}", f"+{ks}分", kc, km))
    summary['KD狀態'] = km

    # 3. 均線型態 (15分)
    sup_count = sum([today['Close'] > today['5MA'], today['Close'] > today['10MA'], today['Close'] > today['20MA']])
    up_count = sum([today['5MA'] > yest['5MA'], today['10MA'] > yest['10MA'], today['20MA'] > yest['20MA']])
    if sup_count == 3 and up_count == 3: mas, mac, mam = 15, "status-pass", "站穩三線且全數翻揚"
    elif sup_count >= 2 and up_count >= 2: mas, mac, mam = 10, "status-mid", "站穩雙線且雙線翻揚"
    elif sup_count >= 1 and up_count >= 1: mas, mac, mam = 5, "status-fail", "站穩單線且單線翻揚"
    else: mas, mac, mam = 0, "status-fail", "均線蓋頭或下彎"
    score += mas; tech_results.append(("均線綜合型態", f"站穩:{sup_count} / 翻揚:{up_count}", f"+{mas}分", mac, mam))

    # 4. 量能變化 (20分)
    if is_excessive_vol: vs, vc, vm = 0, "status-fail", "爆量過大 (>前三日總和)"
    elif v0 > v1 and v1 > v2:
        if v0 >= 1.5 * v1: vs, vc, vm = 15, "status-mid", "連續放量 (逐步爆量)"
        else: vs, vc, vm = 20, "status-pass", "穩健逐步量增"
    else: vs, vc, vm = 0, "status-fail", "量能萎縮或未增"
    score += vs; tech_results.append(("量能型態判定", f"今日 {int(v0/1000):,}張", f"+{vs}分", vc, vm))
    summary['量能狀態'] = vm

    # 5. MACD(10) + 季線(5)
    ms = 10 if (today['DIF'] - today['MACD']) > 0 else 0; score += ms
    tech_results.append(("MACD 動能", "柱狀翻紅", f"+{ms}分", "status-pass" if ms else "status-fail", "動能轉正"))
    qs = 5 if len(df) >= 60 and today['Close'] > df.iloc[-60]['Close'] else 0; score += qs
    tech_results.append(("季線趨勢", "現價 > 60日前", f"+{qs}分", "status-pass" if qs else "status-fail", "波段翻多"))

    # 6. 法人籌碼判定 (20分：外資10 + 投信10)
    total_chip_score = 0
    # 外資計算
    fi_s = 0
    if not df_fi.empty and len(df_fi) >= 5:
        fi_shares = df_fi['ForeignInvestmentShares'].tail(5).tolist()
        fi_diffs = [fi_shares[i] - fi_shares[i-1] for i in range(1, 5)]
        prev_buys = sum([d for d in fi_diffs[:3] if d > 0])
        if fi_diffs[3] < 0 and abs(fi_diffs[3]) > prev_buys: fi_s = 0 # 大賣
        elif all(d > 0 for d in fi_diffs[1:]): fi_s = 10 # 三連買
        elif fi_shares[4] > fi_shares[0]: fi_s = 7 # 五日增
        elif fi_shares[4] == fi_shares[0]: fi_s = 5 # 持平
        else: fi_s = 3 # 遞減
    total_chip_score += fi_s
    
    # 投信計算
    it_s = 0
    if not df_it.empty and len(df_it) >= 5:
        it_shares = df_it['HoldingShares'].tail(5).tolist()
        it_diffs = [it_shares[i] - it_shares[i-1] for i in range(1, 5)]
        if all(d > 0 for d in it_diffs[1:]): it_s = 10 # 三連買
        elif it_shares[4] > it_shares[0]: it_s = 7 # 五日增
        elif it_shares[4] == it_shares[0]: it_s = 5 # 持平
        else: it_s = 3
    total_chip_score += it_s
    
    score += total_chip_score
    chip_results.append(("法人籌碼 (外資+投信)", f"外資:{fi_s} / 投信:{it_s}", f"+{total_chip_score}分", "status-pass" if total_chip_score >= 15 else "status-mid", "觀察內外資同步動向"))
    summary['外資狀態'] = "買超" if fi_s >= 7 else "賣超"
    summary['投信狀態'] = "買超" if it_s >= 7 else "賣超"

    summary['評級'] = "🟢 值得買入" if score >= 80 else ("🟡 列入觀察" if score >= 75 else "🔴 暫不參考")
    return "success", score, {"tech": tech_results, "chip": chip_results, "summary": summary}

# --- 🎯 介面渲染 ---
tab1, tab2 = st.tabs(["🎯 單檔深度診斷", "📊 批量多檔掃描"])

with tab1:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<p class="input-label" style="text-align:center; margin-top:20px;">📍 請輸入台股代號或名稱</p>', unsafe_allow_html=True)
        selected_option = st.selectbox("s_id_single", options=stock_list, index=None, placeholder="🔍 輸入代號並按 Enter", label_visibility="collapsed")
    
    if selected_option:
        st.markdown("---")
        stock_id = str(selected_option).split(" ")[0]
        with st.spinner(f"正在深度分析 {selected_option} ..."):
            status, score, results = analyze_single_stock(stock_id)
            if status == "success":
                c_sc, c_det = st.columns([1, 2])
                with c_sc:
                    color = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 75 else "#E74C3C"
                    st.markdown(f'<div class="score-circle" style="border-color:{color}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                with c_det:
                    st.markdown(f"## {selected_option} 診斷報告")
                    if score >= 80: st.success(f"🎯 **值得買入**：{results['summary']['KD狀態']}")
                    elif score >= 75: st.warning("⚠️ **列入觀察**：分數達標但須留意位階")
                    else: st.error("❄️ **暫不參考**：綜合評分未達標")
                    if "🔥" in results['summary']['KD狀態']:
                        st.info("💡 **強勢鈍化提醒**：股價正處於極強動能區，只要不放量收黑且守穩 5MA，漲勢通常會延續。")

                st.markdown("### 🧬 法人籌碼面 (外資10 + 投信10)")
                for t, d, stg, cls, r in results['chip']: st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

                st.markdown("### 🔍 技術面得分細節")
                for t, d, stg, cls, r in results['tech']: st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

                st.markdown("""
                <div class="weight-box">
                    <h3 style="color:#D4AF37; margin-top:0;">📊 買入評級 - 得分細節說明 (滿分100)</h3>
                    <table style="width:100%; color:#BBB; font-size:14px;">
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>KD 位階 (25分)</b></td><td>30~45(25) | 46~65(20) | 66~70(10) | >80強勢鈍化且不爆量(25) | 其餘(0)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>量能變化 (20分)</b></td><td>逐步增加(20) | 逐步爆量(15) | 大於前三天總和(0)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>法人籌碼 (20分)</b></td><td>外資投信同步連買(20) | 兩者皆五日增加(14) | 單一連買(10)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>均線型態 (15分)</b></td><td>三支撐+三翻揚(15) | 雙支撐+雙翻揚(10) | 單支撐+單翻揚(5)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>MACD (10分)</b></td><td>DIF > MACD 柱狀翻紅</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>週轉率 (5分)</b></td><td>7~10%(5) | 2~6%、11~15%(3) | >1%、15~20%(1) | >20% 或 <1%(0)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>季線趨勢 (5分)</b></td><td>現價 > 60 日前價格</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.markdown('<p class="input-label" style="margin-top:20px;">📋 貼上自選股清單 (支援 Excel 直接複製貼上)</p>', unsafe_allow_html=True)
    batch_input = st.text_area("batch_input", height=150, placeholder="例如：\n6530 創威\n5291 邑昇", label_visibility="collapsed")
    if st.button("🚀 啟動批量掃描", key="btn_batch"):
        raw_lines = batch_input.strip().split('\n')
        stock_ids = list(dict.fromkeys([line.strip().split()[0] for line in raw_lines if line.strip() and line.strip().split()[0].isalnum()]))
        if stock_ids:
            progress = st.progress(0); status_t = st.empty(); summary_data = []
            for i, sid in enumerate(stock_ids):
                progress.progress(int(((i) / len(stock_ids)) * 100))
                status_t.text(f"正在分析: {sid} ...")
                st_status, score, res = analyze_single_stock(sid)
                if st_status == "success":
                    summary_data.append({
                        "代號": sid, "名稱": stock_mapping.get(sid, ""), "總分": score,
                        "評級": res['summary']['評級'], "量能": res['summary']['量能狀態'],
                        "外資": res['summary']['外資狀態'], "投信": res['summary']['投信狀態'], "KD位階": res['summary']['KD狀態']
                    })
                time.sleep(0.2)
            progress.progress(100); status_t.text("✅ 完成！")
            if summary_data:
                st.dataframe(pd.DataFrame(summary_data).sort_values(by="總分", ascending=False), use_container_width=True, hide_index=True)

st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown('<div style="font-size: 12px; color: #777; text-align: center;">⚠️ 免責聲明：數據由 FinMind 提供。本工具僅為模擬用途，不構成投資建議。</div>', unsafe_allow_html=True)
