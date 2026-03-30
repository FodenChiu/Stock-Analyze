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
    ul[role="listbox"] { background-color: #1E1E1E !important; color: #EAEAEA !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1A1A1A; border-radius: 8px 8px 0 0; padding: 10px 20px; color: #BBB; font-weight: bold; border: 1px solid #333; border-bottom: none; }
    .stTabs [aria-selected="true"] { background-color: #D4AF37 !important; color: #121212 !important; border-color: #D4AF37 !important; }
    .streamlit-expanderHeader { font-size: 16px !important; font-weight: bold !important; color: #EAEAEA !important; }
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
            df = pd.DataFrame(res["data"])
            return dict(zip(df['stock_id'].astype(str).str.strip(), df['stock_name'].astype(str).str.strip()))
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
        res_p = requests.get(url, params={"dataset": "TaiwanStockPrice", "data_id": sid, "start_date": start_date, "end_date": end_date, "token": FINMIND_TOKEN}, timeout=10).json()
        if res_p.get("msg") != "success" or not res_p.get("data"): return None, None, None
        df = pd.DataFrame(res_p["data"])
        df.rename(columns={'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'}, inplace=True)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']: df[col] = pd.to_numeric(df[col])
        res_fi = requests.get(url, params={"dataset": "TaiwanStockShareholding", "data_id": sid, "start_date": (datetime.datetime.now() - datetime.timedelta(days=20)).strftime("%Y-%m-%d"), "end_date": end_date, "token": FINMIND_TOKEN}, timeout=10).json()
        df_fi = pd.DataFrame(res_fi.get("data", []))
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

    df['5MA'] = df['Close'].rolling(5).mean(); df['10MA'] = df['Close'].rolling(10).mean(); df['20MA'] = df['Close'].rolling(20).mean()
    df['5VMA'] = df['Volume'].rolling(5).mean()
    
    df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
    df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    
    df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
    
    today, yest = df.iloc[-1], df.iloc[-2]
    total_shares = fetch_total_shares(stock_id)
    
    # 🎯 修復區：將 df_chip 改為 df_fi 解決 NameError
    if total_shares <= 0 and not df_fi.empty and "ForeignInvestmentSharesRatio" in df_fi.columns and "ForeignInvestmentShares" in df_fi.columns:
        try:
            latest_chip = df_fi.iloc[-1]
            ratio = float(latest_chip.get('ForeignInvestmentSharesRatio', 0))
            f_shares = float(latest_chip.get('ForeignInvestmentShares', 0))
            if ratio > 0: total_shares = f_shares / (ratio / 100)
        except: pass
        
    turnover = (today['Volume'] / total_shares) * 100 if total_shares > 0 else 0
    score = 0; tech_results = []; chip_results = []; summary = {}
    
    def check_death_cross(fast, slow):
        cross_today = (fast.iloc[-2] >= slow.iloc[-2]) and (fast.iloc[-1] < slow.iloc[-1])
        cross_yest = (fast.iloc[-3] >= slow.iloc[-3]) and (fast.iloc[-2] < slow.iloc[-2])
        return cross_today or cross_yest

    kd_death = check_death_cross(df['K'], df['D'])
    macd_death = check_death_cross(df['DIF'], df['MACD'])
    ma_death = check_death_cross(df['5MA'], df['10MA']) or check_death_cross(df['5MA'], df['20MA'])
    
    death_labels = []
    if kd_death: death_labels.append("KD")
    if macd_death: death_labels.append("MACD")
    if ma_death: death_labels.append("均線(5MA破線)")
    
    summary['death_cross_msg'] = "、".join(death_labels) + " 死亡交叉" if death_labels else ""

    fi_s = 0
    if not df_fi.empty and len(df_fi) >= 5:
        fi_sh = df_fi['ForeignInvestmentShares'].tail(5).tolist()
        fi_d = [fi_sh[i] - fi_sh[i-1] for i in range(1, 5)]
        p_buys = sum([d for d in fi_d[:3] if d > 0])
        if fi_d[3] < 0 and abs(fi_d[3]) > p_buys: fi_s = 0
        elif all(d > 0 for d in fi_d[1:]): fi_s = 15 
        elif fi_sh[4] > fi_sh[0]: fi_s = 10 
        elif fi_sh[4] == fi_sh[0]: fi_s = 5 
        else: fi_s = 3
    
    it_s = 0
    if not df_it.empty and len(df_it) >= 5:
        it_sh = df_it['HoldingShares'].tail(5).tolist()
        it_d = [it_sh[i] - it_sh[i-1] for i in range(1, 5)]
        if all(d > 0 for d in it_d[1:]): it_s = 5 
        elif it_sh[4] > it_sh[0]: it_s = 3 
        else: it_s = 0 
        
    chip_score_total = fi_s + it_s
    is_chip_weak = chip_score_total < 10 

    # 1. 週轉率 (5分)
    if 6.0 <= turnover <= 10.0:
        ts = 5; tc = "status-pass"
    elif (3.0 <= turnover < 6.0) or (10.0 < turnover <= 15.0):
        ts = 3; tc = "status-mid"
    elif 16.0 <= turnover <= 20.0:
        ts = 1; tc = "status-mid"
    else: 
        ts = 0; tc = "status-fail"
        
    score += ts; tech_results.append(("週轉率判定", f"實測 {turnover:.2f}%" if total_shares > 0 else "無法估算", f"+{ts}分", tc, ""))
    
    # 2. KD 位階 (25分) 
    k_val = today['K']
    v0, v1, v2, v3 = df['Volume'].iloc[-1], df['Volume'].iloc[-2], df['Volume'].iloc[-3], df['Volume'].iloc[-4]
    
    c_list = df['Close'].tail(6).tolist()
    if len(c_list) == 6:
        ret = [(c_list[i] - c_list[i-1]) / c_list[i-1] for i in range(1, 6)]
        lim_up = [r >= 0.095 for r in ret]
        lim_dn = [r <= -0.095 for r in ret]
        has_3_lim_up = (lim_up[0] and lim_up[1] and lim_up[2]) or \
                       (lim_up[1] and lim_up[2] and lim_up[3]) or \
                       (lim_up[2] and lim_up[3] and lim_up[4])
        has_lim_dn = any(lim_dn)
    else:
        has_3_lim_up = False; has_lim_dn = False

    is_today_black = today['Close'] < today['Open']
    is_today_red = today['Close'] > today['Open']
    is_today_vol_up = v0 > v1
    is_today_dump = is_today_black and is_today_vol_up
    is_excessive_vol = v0 > (v1 + v2 + v3)

    is_yest_black = yest['Close'] < yest['Open']
    is_yest_vol_up = v1 > v2
    is_yest_dump = is_yest_black and is_yest_vol_up

    summary['show_high_k_warning'] = (k_val >= 80) and is_today_vol_up and is_today_red

    if has_3_lim_up:
        ks, kc, km = 0, "status-fail", "⚠️ 近五日連三漲停 (處置妖股風險)"
    elif has_lim_dn:
        if k_val > 60 and is_excessive_vol and is_chip_weak:
            ks, kc, km = 0, "status-fail", "⚠️ 高檔爆量跌停且法人無買盤 (強力出貨)"
        else:
            ks, kc, km = 10, "status-mid", "⚠️ 跌停回檔 (但籌碼或位階尚有支撐，觀望)"
    elif kd_death:
        ks, kc, km = 0, "status-fail", "⚠️ KD 死亡交叉 (趨勢轉弱訊號)"
    elif k_val > 60 and (is_today_dump or is_yest_dump):
        ks, kc, km = 0, "status-fail", "⚠️ 近兩日放量收黑 (大戶出貨疑慮)"
    elif k_val > 75: 
        if today['Close'] > today['5MA']: 
            ks, kc, km = 10, "status-mid", "🔥 高檔鈍化 (觀望隔日量能)"
        else: 
            ks, kc, km = 0, "status-fail", "過熱且量價背離"
    elif 30 <= k_val <= 45: ks, kc, km = 25, "status-pass", "KD 30~45 起漲黃金區"
    elif 45 < k_val <= 60: ks, kc, km = 20, "status-mid", "KD 46~60 中位階穩定"
    elif 60 < k_val <= 75: ks, kc, km = 10, "status-mid", "KD 61~75 稍高位階"
    elif k_val < 30: ks, kc, km = 0, "status-fail", "動能不足"
    else: ks, kc, km = 0, "status-fail", "位階不明"
    
    score += ks; tech_results.append(("KD 位階", f"K值: {k_val:.1f} / D值: {today['D']:.1f}", f"+{ks}分", kc, km))
    summary['KD狀態'] = km
    
    # 3. 均線綜合型態 (15分)
    c_val, m5, m10, m20 = today['Close'], today['5MA'], today['10MA'], today['20MA']
    y_m5, y_m10, y_m20 = yest['5MA'], yest['10MA'], yest['20MA']
    sup_count = sum([c_val > m5, c_val > m10, c_val > m20])
    up_count = sum([m5 > y_m5, m10 > y_m10, m20 > y_m20])

    if ma_death: 
        mas, mac, mam = 0, "status-fail", "⚠️ 短均線死亡交叉 (跌破防守線)"
    elif sup_count == 3 and up_count == 3: mas, mac, mam = 15, "status-pass", "站穩三線且全數翻揚"
    elif sup_count >= 2 and up_count >= 2: mas, mac, mam = 10, "status-mid", "站穩雙線且雙線翻揚"
    elif sup_count >= 1 and up_count >= 1: mas, mac, mam = 5, "status-fail", "站穩單線且單線翻揚"
    else: mas, mac, mam = 0, "status-fail", "均線蓋頭或全數下彎"
    score += mas; tech_results.append(("均線綜合型態", f"站穩:{sup_count}線 / 翻揚:{up_count}線", f"+{mas}分", mac, mam))
    
    # 4. 量能變化 (20分)
    if v0 > v1 and v1 > v2:
        vs, vc, vm = 20, "status-pass", "成交量續增 (連兩日遞增)"
    elif v0 > v1:
        vs, vc, vm = 10, "status-mid", "成交量大於昨日"
    else:
        vs, vc, vm = 5, "status-mid", "成交量持平或量縮"

    score += vs; tech_results.append(("量能健康度", f"今日量: {int(v0/1000):,}張", f"+{vs}分", vc, vm))
    summary['量能狀態'] = vm

    # 5. 其他技術面 (15分)
    if macd_death: 
        ms, mc, mm = 0, "status-fail", "⚠️ MACD 死亡交叉 (波段翻空)"
    elif (today['DIF'] - today['MACD']) > 0: 
        ms, mc, mm = 10, "status-pass", "動能轉正"
    else: 
        ms, mc, mm = 0, "status-fail", "空頭動能"
        
    score += ms; tech_results.append(("MACD 動能", "柱狀狀態", f"+{ms}分", mc, mm))
    
    qs = 5 if len(df) >= 60 and today['Close'] > df.iloc[-60]['Close'] else 0; score += qs
    tech_results.append(("季線趨勢", "現價 > 60日前", f"+{qs}分", "status-pass" if qs else "status-fail", "長線翻多"))

    # 6. 法人籌碼
    score += chip_score_total
    chip_results.append(("法人籌碼", f"外資:{fi_s} / 投信:{it_s}", f"+{chip_score_total}分", "status-pass" if chip_score_total>=15 else "status-mid", f"外資{'買超' if fi_s>=10 else '普通'}，投信{'加持' if it_s>0 else '觀望'}"))
    summary['外資狀態'] = "買超" if fi_s >= 10 else "賣超"
    summary['投信狀態'] = "加持" if it_s >= 3 else "觀望"

    # 評級判定
    if score >= 80: summary['評級'] = "🟢 值得買入"
    elif score >= 70: summary['評級'] = "🟡 列入觀察"
    else: summary['評級'] = "🔴 暫不參考"
    
    return "success", score, {"tech": tech_results, "chip": chip_results, "summary": summary}

# --- 📝 報表生成器 ---
def generate_html_report(sum_d_sorted):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows_html = ""
    for row in sum_d_sorted:
        sc = row['總分']
        color = "#2DCC70" if sc >= 80 else "#F1C40F" if sc >= 70 else "#E74C3C"
        
        tech_str = "".join([f"<div style='margin-bottom:4px; font-size:12px;'><b>{t}</b>: {d} <span style='color:#777;'>({r})</span> <span style='color:#D4AF37; font-weight:bold;'>[{stg}]</span></div>" for t, d, stg, cls, r in row['詳細資料']['tech']])
        chip_str = "".join([f"<div style='margin-bottom:4px; font-size:12px;'><b>{t}</b>: {d} <span style='color:#777;'>({r})</span> <span style='color:#D4AF37; font-weight:bold;'>[{stg}]</span></div>" for t, d, stg, cls, r in row['詳細資料']['chip']])

        details_html = f"""
        <details style="margin-top: 8px; cursor: pointer; text-align: left; padding: 6px; background: #FDFBF5; border-radius: 6px; border: 1px solid #EEDDCC;">
            <summary style="font-weight: bold; color: #B8860B; outline: none;">🔍 查看診斷細節 (點擊展開)</summary>
            <div style="margin-top: 8px; color: #333;">
                <div style="margin-bottom: 5px; border-bottom: 1px dashed #CCC; padding-bottom: 3px; font-size: 13px;"><b>🧬 法人籌碼面</b></div>
                {chip_str}
                <div style="margin-top: 8px; margin-bottom: 5px; border-bottom: 1px dashed #CCC; padding-bottom: 3px; font-size: 13px;"><b>🔍 技術面得分細節</b></div>
                {tech_str}
            </div>
        </details>
        """

        rows_html += f"""
        <tr>
            <td style="font-weight:bold; font-size:15px; vertical-align: middle; text-align:center;">
                {row['代號']}<br>
                <span style="color:#666; font-size:13px;">{row['名稱']}</span>
            </td>
            <td style="color:{color}; font-weight:bold; font-size:18px; vertical-align: middle;">{sc}</td>
            <td style="font-weight:bold; vertical-align: middle;">{row['評級']}</td>
            <td style="vertical-align: middle;">{row['量能']}</td>
            <td style="vertical-align: middle;">{row['外資']}</td>
            <td style="vertical-align: middle;">{row['投信']}</td>
            <td style="text-align:left; color:#555; vertical-align: top;">
                {row['KD狀態']}
                {details_html}
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>台股短線掃描報告</title>
        <style>
            body {{ font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif; background-color: #FFFFFF; color: #333333; padding: 20px; }}
            h1 {{ color: #B8860B; text-align: center; border-bottom: 2px solid #B8860B; padding-bottom: 10px; margin-bottom: 5px; }}
            .meta-info {{ text-align: right; color: #777; font-size: 12px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
            th, td {{ border: 1px solid #DDDDDD; padding: 12px 8px; text-align: center; }}
            th {{ background-color: #F8F4E6; color: #B8860B; font-weight: bold; font-size: 15px; }}
            tr:nth-child(even) {{ background-color: #FDFDFD; }}
            @media print {{ body {{ padding: 0; }} }}
        </style>
    </head>
    <body>
        <h1>⚡ 台股短線買入評級 - 批量掃描報告</h1>
        <div class="meta-info">報告生成時間：{now_str}</div>
        <table>
            <tr>
                <th width="12%">股票標的</th>
                <th width="8%">總分</th>
                <th width="12%">綜合評級</th>
                <th width="15%">量能健康度</th>
                <th width="10%">外資狀態</th>
                <th width="10%">投信狀態</th>
                <th width="33%">KD 位階與防禦狀態</th>
            </tr>
            {rows_html}
        </table>
        <p style="text-align:center; font-size:11px; color:#999; margin-top:30px;">
            ⚠️ 系統自動生成之技術籌碼分析報告，請使用 Ctrl+P (或 Cmd+P) 另存為 PDF。本資料僅供策略回測與觀察，不構成任何買賣投資建議。
        </p>
    </body>
    </html>
    """
    return html

# --- 🎯 雙頁籤介面設計 ---
tab1, tab2 = st.tabs(["🎯 單檔深度診斷", "📊 批量多檔掃描"])

with tab1:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<p class="input-label" style="text-align:center; margin-top:20px;">📍 請輸入台股代號並按 Enter</p>', unsafe_allow_html=True)
        selected_option = st.selectbox("s_id_single", options=stock_list, index=None, placeholder="🔍 搜尋股票", label_visibility="collapsed")
    
    if selected_option:
        st.markdown("---")
        stock_id = str(selected_option).split(" ")[0]
        display_name = selected_option
        with st.spinner(f"正在分析 {display_name} ..."):
            status, score, results = analyze_single_stock(stock_id)
            if status == "not_found": st.error(f"❌ 查無代號「{stock_id}」。")
            elif status == "error": st.error("⚠️ 伺服器忙碌，請稍後再試。")
            elif status == "insufficient_data": st.error("⚠️ 該檔股票資料不足，無法進行運算。")
            else:
                
                if results['summary'].get('death_cross_msg'):
                    st.error(f"🚨 **死亡交叉警告**：{display_name} 近兩日內出現了『{results['summary']['death_cross_msg']}』！")
                    st.info("💡 趨勢已正式轉弱或跌破重要支撐，這通常是波段下跌的起點，請務必避開或考慮停損。")
                elif "連三漲停" in results['summary']['KD狀態']:
                    st.error(f"🚨 **妖股警報**：{display_name} 近五日內連續三日觸及『漲停板』！")
                    st.info("💡 系統已自動排除波動過劇、隨時可能面臨處置分盤交易的極端妖股，建議切勿追高。")
                elif "爆量跌停" in results['summary']['KD狀態']:
                    st.error(f"🚨 **崩盤出貨警告**：{display_name} 出現了『高檔爆量跌停』，且外資投信完全沒有進場護盤！")
                    st.info("💡 這是極度危險的主力倒貨訊號，買盤全數套牢，強烈建議避開。")
                elif "⚠️" in results['summary']['KD狀態']:
                    st.error(f"⚠️ **風險提示**：{display_name} 近期出現跌停回檔或放量收黑。")
                    st.info("💡 若為跌停，系統偵測到籌碼尚未完全潰散，給予觀望分；若為放量收黑，則需提防換手失敗。")

                col_res_sc, col_res_det = st.columns([1, 2])
                with col_res_sc:
                    color = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 70 else "#E74C3C"
                    st.markdown(f'<div class="score-circle" style="border-color:{color}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                    st.markdown(f"<p style='text-align:center; color:{color}; font-weight:bold; margin-top:10px;'>綜合診斷總分 (滿分100)</p>", unsafe_allow_html=True)
                with col_res_det:
                    st.markdown(f"## {display_name} 診斷報告")
                    if score >= 80: st.success(f"🎯 **值得買入**：{results['summary']['KD狀態']}")
                    elif score >= 70: st.warning("⚠️ **列入觀察**：分數已達標")
                    else: st.error("❄️ **暫不參考**：綜合評分未達標。")
                    
                    if results['summary'].get('show_high_k_warning', False):
                        st.info("💡 **高檔鈍化提醒**：指標極強，但需觀望隔日開盤量能是否遞增，切勿追高。")

                st.markdown("### 🧬 法人籌碼面")
                for t, d, stg, cls, r in results['chip']: st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

                st.markdown("### 🔍 技術面得分細節")
                for t, d, stg, cls, r in results['tech']: st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

                st.markdown("""
                <div class="weight-box">
                    <h3 style="color:#D4AF37; margin-top:0;">📊 買入評級 - 得分細節說明 (滿分100)</h3>
                    <table style="width:100%; color:#BBB; font-size:14px;">
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>KD 位階 (25分)</b></td><td>30~45(25) | 46~60(20) | 高檔鈍化觀望(10) | KD死亡交叉/跌停(0)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>量能健康度 (20分)</b></td><td>成交量續增(20) | 大於昨日(10) | 持平或量縮(5)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>外資核心 (15分)</b></td><td>連續買超(15) | 五日持股增加(10) | 持平(5) | 遞減(3)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>投信加分 (5分)</b></td><td>連續買超(5) | 五日持股增加(3) | 其餘不加分(0)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>均線型態 (15分)</b></td><td>三線翻揚(15) | 雙線翻揚(10) | 單線翻揚(5) | 均線死亡交叉(0)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>MACD/季線 (15分)</b></td><td>MACD 翻紅(10) + 季線翻多(5) | MACD死亡交叉(0)</td></tr>
                        <tr><td style="color:#EAEAEA; padding:5px 0;"><b>週轉率 (5分)</b></td><td>6~10%(5) | 3~5%、11~15%(3) | 16~20%(1) | >20%或<3%(0)</td></tr>
                    </table>
                    <p style="margin-top:15px; font-weight:bold; color:#D4AF37;">🟢 80+ 值得買入 | 🟡 70+ 列入觀察 | 🔴 69 以下 暫不參考</p>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.markdown('<p class="input-label" style="margin-top:20px;">📋 貼上自選股清單 (支援 Excel 複製貼上)</p>', unsafe_allow_html=True)
    batch_input = st.text_area("batch_input", height=150, placeholder="例如：\n6530 創威\n8039 台虹", label_visibility="collapsed")
    if st.button("🚀 啟動批量掃描"):
        raw_ids = list(dict.fromkeys([line.strip().split()[0] for line in batch_input.strip().split('\n') if line.strip() and line.strip().split()[0].isalnum()]))
        if raw_ids:
            prog = st.progress(0); st_t = st.empty(); sum_d = []
            for i, sid in enumerate(raw_ids):
                prog.progress(int((i/len(raw_ids))*100)); st_t.text(f"分析中: {sid}...")
                status, s_sc, s_res = analyze_single_stock(sid)
                if status == "success": 
                    sum_d.append({
                        "代號": sid, "名稱": stock_mapping.get(sid, ""), "總分": s_sc, 
                        "評級": s_res['summary']['評級'], "量能": s_res['summary']['量能狀態'], "外資": s_res['summary']['外資狀態'], 
                        "投信": s_res['summary']['投信狀態'], "KD狀態": s_res['summary']['KD狀態'],
                        "詳細資料": s_res
                    })
                time.sleep(0.2)
            prog.progress(100); st_t.text("✅ 掃描完成！")
            
            if sum_d: 
                sum_d_sorted = sorted(sum_d, key=lambda x: x["總分"], reverse=True)
                df_res_display = pd.DataFrame([{k: v for k, v in d.items() if k != "詳細資料"} for d in sum_d_sorted])
                st.dataframe(df_res_display, use_container_width=True, hide_index=True)
                
                st.markdown("<br><h3 style='color:#D4AF37; margin-bottom:15px;'>📋 批量掃描詳細報告 (點擊下拉展開)</h3>", unsafe_allow_html=True)
                for item in sum_d_sorted:
                    sc = item['總分']
                    status_icon = "🟢" if sc >= 80 else "🟡" if sc >= 70 else "🔴"
                    with st.expander(f"{status_icon} {item['代號']} {item['名稱']} - 總分: {sc}分 ({item['評級']})"):
                        res = item['詳細資料']
                        
                        st.markdown("#### 🧬 法人籌碼面")
                        for t, d, stg, cls, r in res['chip']:
                            st.markdown(f'<div class="check-item" style="padding:15px;"><div style="flex: 1;"><div class="check-title" style="font-weight:bold; color:#D4AF37;">{t} <span style="color:#EAEAEA; font-weight:normal;">({d})</span></div><div class="check-reason" style="font-size:13px; color:#AAA;">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)
                            
                        st.markdown("#### 🔍 技術面得分細節")
                        for t, d, stg, cls, r in res['tech']:
                            st.markdown(f'<div class="check-item" style="padding:15px;"><div style="flex: 1;"><div class="check-title" style="font-weight:bold; color:#D4AF37;">{t} <span style="color:#EAEAEA; font-weight:normal;">({d})</span></div><div class="check-reason" style="font-size:13px; color:#AAA;">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

                html_data = generate_html_report(sum_d_sorted)
                st.download_button(
                    label="📄 匯出精美掃描報告 (點開後按 Ctrl+P 存成 PDF)",
                    data=html_data,
                    file_name=f"Stock_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.html",
                    mime="text/html"
                )

st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown('<div style="font-size: 12px; color: #777; text-align: center;">⚠️ 免責聲明：數據由 FinMind 提供。本工具僅為模擬用途，不構成投資建議。</div>', unsafe_allow_html=True)
