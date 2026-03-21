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
    input[data-testid="stTextInput"], textarea[data-testid="stTextArea"] { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; font-size: 16px !important;}
    div[data-baseweb="select"] > div { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; font-size: 16px !important; }
    ul[role="listbox"] { background-color: #1E1E1E !important; color: #EAEAEA !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1A1A1A; border-radius: 8px 8px 0 0; padding: 10px 20px; color: #BBB; font-weight: bold; border: 1px solid #333; border-bottom: none; }
    .stTabs [aria-selected="true"] { background-color: #D4AF37 !important; color: #121212 !important; border-color: #D4AF37 !important; }
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
            shares = 0
            try: shares = t.fast_info.get('shares', 0)
            except: pass
            
            if not shares or shares == 0:
                shares = t.info.get('sharesOutstanding', 0)
                
            if shares and shares > 0: return shares
        except: continue
    return 0

@st.cache_data(ttl=900)
def fetch_finmind_data(sid):
    try:
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=150)).strftime("%Y-%m-%d")
        url = "https://api.finmindtrade.com/api/v4/data"
        res_p = requests.get(url, params={"dataset": "TaiwanStockPrice", "data_id": sid, "start_date": start_date, "end_date": end_date, "token": FINMIND_TOKEN}, timeout=10).json()
        if res_p.get("msg") != "success" or not res_p.get("data"): return None, None
        df = pd.DataFrame(res_p["data"])
        df.rename(columns={'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'}, inplace=True)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']: df[col] = pd.to_numeric(df[col])
        res_c = requests.get(url, params={"dataset": "TaiwanStockShareholding", "data_id": sid, "start_date": (datetime.datetime.now() - datetime.timedelta(days=20)).strftime("%Y-%m-%d"), "end_date": end_date, "token": FINMIND_TOKEN}, timeout=10).json()
        df_chip = pd.DataFrame(res_c.get("data", []))
        return df, df_chip
    except Exception as e: return "error", str(e)

stock_mapping = fetch_stock_mapping()
stock_list = [f"{k} {v}" for k, v in stock_mapping.items()]

# --- 🎯 核心運算引擎 ---
def analyze_single_stock(stock_id):
    df, df_chip = fetch_finmind_data(stock_id)
    if df is None: return "not_found", None, None
    if isinstance(df, str) and df == "error": return "error", None, None
    if len(df) < 5: return "insufficient_data", None, None

    df['5MA'] = df['Close'].rolling(5).mean(); df['10MA'] = df['Close'].rolling(10).mean(); df['20MA'] = df['Close'].rolling(20).mean()
    df['5VMA'] = df['Volume'].rolling(5).mean()
    df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
    df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
    
    today, yest = df.iloc[-1], df.iloc[-2]
    total_shares = fetch_total_shares(stock_id)
    
    if total_shares <= 0 and not df_chip.empty and "ForeignInvestmentSharesRatio" in df_chip.columns and "ForeignInvestmentShares" in df_chip.columns:
        try:
            latest_chip = df_chip.iloc[-1]
            ratio = float(latest_chip.get('ForeignInvestmentSharesRatio', 0))
            f_shares = float(latest_chip.get('ForeignInvestmentShares', 0))
            if ratio > 0: total_shares = f_shares / (ratio / 100)
        except: pass
        
    turnover = (today['Volume'] / total_shares) * 100 if total_shares > 0 else 0
    score = 0; tech_results = []; chip_results = []; summary = {}
    
    # 1. 週轉率 (5分)
    ts = 5 if turnover > 8 else (3 if turnover > 5 else (1 if turnover > 1 else 0))
    tc = "status-pass" if ts==5 else ("status-mid" if ts>0 else "status-fail")
    score += ts; tech_results.append(("週轉率判定", f"實測 {turnover:.2f}%" if total_shares > 0 else "無法估算(無總股數)", f"+{ts}分", tc, "週轉率水平。"))
    
    # 2. KD 位階 (25分)
    k_val = today['K']
    if 30 <= k_val <= 45: ks, kc, km = 25, "status-pass", "KD 30~45 起漲黃金區"
    elif 45 < k_val <= 65: ks, kc, km = 20, "status-mid", "KD 46~65 中位階"
    elif 65 < k_val <= 70: ks, kc, km = 10, "status-mid", "KD 66~70 稍高位階"
    elif 70 < k_val <= 75: ks, kc, km = 5, "status-fail", "KD 71~75 偏高"
    else: ks, kc, km = 0, "status-fail", "過熱或動能不足"
    score += ks; tech_results.append(("KD 位階", f"K值: {k_val:.1f}", f"+{ks}分", kc, km))
    summary['KD狀態'] = km
    
    # 3. 均線綜合型態 (15分)
    c_val, m5, m10, m20 = today['Close'], today['5MA'], today['10MA'], today['20MA']
    y_m5, y_m10, y_m20 = yest['5MA'], yest['10MA'], yest['20MA']
    sup_count = sum([c_val > m5, c_val > m10, c_val > m20])
    up_count = sum([m5 > y_m5, m10 > y_m10, m20 > y_m20])

    if sup_count == 3 and up_count == 3: mas, mac, mam = 15, "status-pass", "站穩三線且全數翻揚"
    elif sup_count >= 2 and up_count >= 2: mas, mac, mam = 10, "status-mid", "站穩雙線且雙線翻揚"
    elif sup_count >= 1 and up_count >= 1: mas, mac, mam = 5, "status-fail", "站穩單線且單線翻揚"
    else: mas, mac, mam = 0, "status-fail", "均線蓋頭或全數下彎"
    score += mas; tech_results.append(("均線綜合型態", f"站穩:{sup_count}線 / 翻揚:{up_count}線", f"+{mas}分", mac, mam))
    
    # 4. 近三天量能變化 (20分)
    v0, v1, v2, v3 = df['Volume'].iloc[-1], df['Volume'].iloc[-2], df['Volume'].iloc[-3], df['Volume'].iloc[-4]
    if v0 > (v1 + v2 + v3): vs, vc, vm = 0, "status-fail", "大於前三天總和(過熱)"
    elif v0 > v1 and v1 > v2:
        if v0 >= 1.5 * v1: vs, vc, vm = 15, "status-mid", "連續增加(逐步爆量)"
        else: vs, vc, vm = 20, "status-pass", "穩健逐步增加"
    else: vs, vc, vm = 0, "status-fail", "量能未連續增加"
    score += vs; tech_results.append(("近三天量能", f"今日 {int(v0/1000):,}張", f"+{vs}分", vc, vm))
    summary['量能狀態'] = vm

    # 5. 其他技術面 (15分)
    ms = 10 if (today['DIF'] - today['MACD']) > 0 else 0; score += ms
    tech_results.append(("MACD 動能", "柱狀翻紅", f"+{ms}分", "status-pass" if ms else "status-fail", "動能轉正"))
    qs = 5 if len(df) >= 60 and today['Close'] > df.iloc[-60]['Close'] else 0; score += qs
    tech_results.append(("季線趨勢", "現價 > 60日前", f"+{qs}分", "status-pass" if qs else "status-fail", "長線翻多"))

    # 6. 外資行為模式判定 (20分)
    chip_data_list = df_chip[['date', 'ForeignInvestmentShares']].tail(5).values.tolist() if not df_chip.empty and "ForeignInvestmentShares" in df_chip.columns else []
    if len(chip_data_list) == 5:
        shares = [float(x[1]) for x in chip_data_list]
        diffs = [shares[1]-shares[0], shares[2]-shares[1], shares[3]-shares[2], shares[4]-shares[3]]
        prev_3_buys = sum([d for d in diffs[:3] if d > 0])
        if diffs[3] < 0 and abs(diffs[3]) > prev_3_buys: cs, cc, cm = 0, "status-fail", "大賣勝前三日"
        elif diffs[3] > 0 and diffs[2] > 0 and diffs[1] > 0: cs, cc, cm = 20, "status-pass", "連續買超"
        elif shares[4] > shares[0]: cs, cc, cm = 15, "status-pass", "五日持股增加"
        elif shares[4] == shares[0]: cs, cc, cm = 10, "status-mid", "五日持股持平"
        else: cs, cc, cm = 5, "status-fail", "五日持股遞減"
        score += cs; chip_results.append(("外資籌碼", f"最新: {int(shares[4]/1000):,} 張", f"+{cs}分", cc, cm))
        summary['外資狀態'] = cm
    else:
        chip_results.append(("外資籌碼", "無資料", "+0分", "status-fail", "無完整資料"))
        summary['外資狀態'] = "無資料"

    # 評級判定
    if score >= 80: summary['評級'] = "🟢 值得買入"
    elif score >= 75: summary['評級'] = "🟡 列入觀察"
    else: summary['評級'] = "🔴 暫不參考"
    
    return "success", score, {"tech": tech_results, "chip": chip_results, "summary": summary}


# --- 🎯 雙頁籤介面設計 ---
tab1, tab2 = st.tabs(["🎯 單檔深度診斷", "📊 批量多檔掃描"])

# --- 頁籤 1: 單檔深度診斷 ---
with tab1:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<p class="input-label" style="text-align:center; margin-top:20px;">📍 請輸入台股代號或名稱</p>', unsafe_allow_html=True)
        if stock_list:
            selected_option = st.selectbox("s_id_single", options=stock_list, index=None, placeholder="🔍 輸入代號並按 Enter 即可瞬間掃描", label_visibility="collapsed")
        else:
            selected_option = st.text_input("s_id_single", value="", label_visibility="collapsed", placeholder="請輸入台股代號並按 Enter")
        st.write("")
        # 按鈕現在只是視覺輔助，真正驅動的是 selected_option 的改變
        st.button("🚀 啟動深度診斷", key="btn_single")

    # 🔥 終極優化：只要輸入框有選到東西，就算沒按按鈕也會自動開始跑！
    if selected_option:
        st.markdown("---")
        stock_id = str(selected_option).split(" ")[0]
        display_name = selected_option
        with st.spinner(f"正在深度分析 {display_name} ..."):
            status, score, results = analyze_single_stock(stock_id)
            if status == "not_found": st.error(f"❌ 查無代號「{stock_id}」。")
            elif status == "error": st.error("⚠️ 伺服器忙碌，請稍後再試。")
            elif status == "insufficient_data": st.error("⚠️ 該檔股票資料不足，無法進行運算。")
            else:
                col_res_sc, col_res_det = st.columns([1, 2])
                with col_res_sc:
                    color = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 75 else "#E74C3C"
                    st.markdown(f'<div class="score-circle" style="border-color:{color}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                    st.markdown(f"<p style='text-align:center; color:{color}; font-weight:bold; margin-top:10px;'>綜合診斷總分 (滿分100)</p>", unsafe_allow_html=True)
                with col_res_det:
                    st.markdown(f"## {display_name} 診斷報告")
                    if score >= 80: st.success("🎯 **值得買入**：技術面與籌碼面極佳！")
                    elif score >= 75: st.warning("⚠️ **列入觀察**：分數已達觀察區間。")
                    else: st.error("❄️ **暫不參考**：綜合評分未達標。")

                st.markdown("### 🧬 外資籌碼面 (行為判定)")
                for t, d, stg, cls, r in results['chip']: st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

                st.markdown("### 🔍 技術面得分細節")
                for t, d, stg, cls, r in results['tech']: st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

                st.markdown("""
                <div class="weight-box">
                    <h3 style="color:#D4AF37; margin-top:0;">📊 買入評級 - 得分細節說明 (滿分100)</h3>
                    <table style="width:100%; color:#BBB; font-size:14px;">
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>KD 位階 (25分)</b></td><td>30~45(25分) | 46~65(20分) | 66~70(10分) | 71~75(5分)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>近三天量能 (20分)</b></td><td>逐步增加(20分) | 逐步爆量(15分) | 大於前三天總和(0分)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>外資籌碼 (20分)</b></td><td>連續買超(20) | 持股增加(15) | 持平(10) | 遞減(5) | 大賣勝前三日(0)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>均線型態 (15分)</b></td><td>三支撐+三翻揚(15分) | 雙支撐+雙翻揚(10分) | 單支撐+單翻揚(5分)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>MACD (10分)</b></td><td>DIF > MACD 柱狀翻紅</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>週轉率 (5分)</b></td><td>>8%(5分) | >5%(3分) | >1%(1分)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>季線趨勢 (5分)</b></td><td>現價 > 60 日前價格</td></tr>
                    </table>
                    <p style="margin-top:15px; font-weight:bold; color:#D4AF37;">🟢 80+ 值得買入 | 🟡 75+ 列入觀察 | 🔴 75- 暫不參考</p>
                </div>
                """, unsafe_allow_html=True)

# --- 頁籤 2: 批量多檔掃描 ---
with tab2:
    st.markdown('<p class="input-label" style="margin-top:20px;">📋 貼上自選股清單 (支援 Excel 直接複製貼上)</p>', unsafe_allow_html=True)
    batch_input = st.text_area("batch_input", height=150, placeholder="例如：\n6530 創威\n5291 邑昇\n4967 十銓", label_visibility="collapsed")
    # 這裡保留按鈕，因為輸入框按 Enter 會變成換行
    batch_btn = st.button("🚀 啟動批量掃描", key="btn_batch")

    if batch_btn and batch_input.strip():
        raw_lines = batch_input.strip().split('\n')
        stock_ids_to_scan = []
        for line in raw_lines:
            cleaned = line.strip()
            if not cleaned: continue
            s_id = cleaned.split()[0]
            if s_id.isalnum(): stock_ids_to_scan.append(s_id)
        
        stock_ids_to_scan = list(dict.fromkeys(stock_ids_to_scan))
        
        if not stock_ids_to_scan:
            st.warning("⚠️ 無法解析股票代號，請確保每一行開頭是數字代號。")
        else:
            st.markdown(f"### 🔍 共偵測到 {len(stock_ids_to_scan)} 檔股票，開始掃描...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            summary_data = []
            
            for i, sid in enumerate(stock_ids_to_scan):
                progress = int(((i) / len(stock_ids_to_scan)) * 100)
                progress_bar.progress(progress)
                status_text.text(f"正在運算: {sid} ({i+1}/{len(stock_ids_to_scan)}) ...")
                s_name = stock_mapping.get(sid, "")
                status, score, results = analyze_single_stock(sid)
                
                if status == "success":
                    summary_data.append({
                        "代號": sid,
                        "名稱": s_name,
                        "總分": score,
                        "評級": results['summary']['評級'],
                        "量能型態": results['summary']['量能狀態'],
                        "外資動向": results['summary']['外資狀態'],
                        "KD位階": results['summary']['KD狀態']
                    })
                time.sleep(0.2)
                
            progress_bar.progress(100)
            status_text.text("✅ 掃描完成！")
            
            if summary_data:
                df_summary = pd.DataFrame(summary_data)
                df_summary = df_summary.sort_values(by="總分", ascending=False).reset_index(drop=True)
                st.markdown("### 🏆 掃描結果排行榜")
                st.dataframe(
                    df_summary,
                    column_config={"總分": st.column_config.NumberColumn("總分 (滿分100)", format="%d 🌟")},
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.error("⚠️ 所有掃描皆失敗或查無資料。")

st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown('<div style="font-size: 12px; color: #777; text-align: center;">⚠️ 免責聲明：數據由 FinMind 提供。本工具僅為模擬用途，不構成投資建議。</div>', unsafe_allow_html=True)
