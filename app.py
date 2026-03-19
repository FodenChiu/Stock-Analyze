import streamlit as st
import pandas as pd
import requests
import datetime
import yfinance as yf

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
    /* 針對輸入框與智慧選單的暗黑風格優化 */
    input[data-testid="stTextInput"] { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; text-align: center; font-size: 18px !important;}
    div[data-baseweb="select"] > div { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; font-size: 16px !important; }
    ul[role="listbox"] { background-color: #1E1E1E !important; color: #EAEAEA !important; }
</style>
""", unsafe_allow_html=True)

# --- 首頁標題 ---
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
    try:
        for ext in [".TW", ".TWO"]:
            t = yf.Ticker(f"{sid}{ext}")
            shares = t.info.get('sharesOutstanding')
            if shares and shares > 0:
                return shares
        return 0
    except: return 0

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

# 取得股票清單字典
stock_mapping = fetch_stock_mapping()
stock_list = [f"{k} {v}" for k, v in stock_mapping.items()]

# --- 🎯 智慧輸入區塊 ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<p class="input-label" style="text-align:center;">📍 請輸入台股代號或名稱</p>', unsafe_allow_html=True)
    
    # 如果名單有成功抓到，就顯示智慧選單；如果網路異常抓不到，退回一般的文字輸入框
    if stock_list:
        selected_option = st.selectbox(
            "s_id", 
            options=stock_list, 
            index=None, 
            placeholder="🔍 支援打字搜尋 (例如: 2330 或 台積電)", 
            label_visibility="collapsed"
        )
    else:
        selected_option = st.text_input("s_id", value="", label_visibility="collapsed", placeholder="請輸入台股代號 (例如: 2330)")
        
    st.write("")
    analyze_btn = st.button("🚀 啟動全自動深度診斷")


# --- 🎯 核心邏輯區 (報告展開) ---
if analyze_btn and selected_option:
    st.markdown("---")
    
    # 自動分離出前面的數字代號 (不管使用者輸入的是 '1301' 還是 '1301 台塑'，都會萃取出 '1301')
    stock_id = str(selected_option).split(" ")[0]
    display_name = selected_option

    with st.spinner(f"正在深度分析 {display_name} ..."):
        df, df_chip = fetch_finmind_data(stock_id)
        
        if df is None: 
            st.error(f"❌ 查無代號「{stock_id}」。")
        elif isinstance(df, str) and df == "error": 
            st.error("⚠️ 伺服器忙碌，請稍後再試。")
        else:
            # 運算技術指標
            df['5MA'] = df['Close'].rolling(5).mean(); df['10MA'] = df['Close'].rolling(10).mean(); df['20MA'] = df['Close'].rolling(20).mean()
            df['5VMA'] = df['Volume'].rolling(5).mean()
            df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
            df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
            df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
            df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
            
            today, yest = df.iloc[-1], df.iloc[-2]
            
            total_shares = fetch_total_shares(stock_id)
            if total_shares > 0:
                turnover = (today['Volume'] / total_shares) * 100
                turnover_str = f"實測 {turnover:.2f}%"
            else:
                turnover = 0
                turnover_str = "無法估算(無總股數資料)"
            
            score = 0; tech_results = []; chip_results = []
            
            # 1. 週轉率
            if turnover > 8: ts, tc = 5, "status-pass"
            elif turnover > 5: ts, tc = 3, "status-mid"
            elif turnover > 1: ts, tc = 1, "status-fail"
            else: ts, tc = 0, "status-fail"
            score += ts; tech_results.append(("週轉率判定", turnover_str, f"+{ts}分", tc, "模擬分析：週轉率水平對應得分。"))
            
            # 2. KD 位階
            k_val = today['K']
            if 25 <= k_val <= 40: ks, kc, km = 25, "status-pass", "KD 25-40 低檔爆發區，滿分。"
            elif 45 <= k_val <= 60: ks, kc, km = 20, "status-mid", "KD 45-60 中位階穩定區。"
            elif 65 <= k_val <= 70: ks, kc, km = 10, "status-fail", "KD 65-70 稍嫌過熱。"
            else: ks, kc, km = 0, "status-fail", "過熱(>75)或未達標。"
            score += ks; tech_results.append(("KD 位階判定", f"K值: {k_val:.1f}", f"+{ks}分", kc, f"模擬分析：{km}"))
            
            # 3. 均線支撐
            c_val, m5, m10, m20 = today['Close'], today['5MA'], today['10MA'], today['20MA']
            count = sum([c_val > m5, c_val > m10, c_val > m20])
            if count == 3: mas, mac, mam = 10, "status-pass", "站穩三線滿分。"
            elif count == 2: mas, mac, mam = 5, "status-mid", "站穩雙線。"
            elif count == 1: mas, mac, mam = 3, "status-fail", "僅站穩 5T。"
            else: mas, mac, mam = 0, "status-fail", "均線之下。"
            score += mas; tech_results.append(("短期均線支撐", f"收盤:{c_val:.1f}", f"+{mas}分", mac, f"模擬分析：{mam}"))
            
            # 4. 量增紅K攻擊
            ok_v = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']
            vs = 20 if ok_v else 0; score += vs
            v_vol, v_avg = int(today['Volume']/1000), int(today['5VMA']/1000)
            tech_results.append(("量增紅K攻擊", f"{v_vol:,}張 / 5T均 {v_avg:,}張", f"+{vs}分", "status-pass" if ok_v else "status-fail", "模擬分析：主力攻擊表態。"))

            # 5. 其他技術面
            ok_m = (today['DIF'] - today['MACD']) > 0; ms = 10 if ok_m else 0; score += ms
            tech_results.append(("MACD 動能", "柱狀翻紅", f"+{ms}分", "status-pass" if ok_m else "status-fail", "模擬分析：動能轉正。"))
            ok_q = today['Close'] > df.iloc[-60]['Close'] if len(df) >= 60 else False
            qs = 5 if ok_q else 0; score += qs
            tech_results.append(("季線趨勢", "現價 > 60日前", f"+{qs}分", "status-pass" if ok_q else "status-fail", "模擬分析：長線翻多。"))
            ok_up = today['5MA'] > yest['5MA'] and today['10MA'] > yest['10MA'] and today['20MA'] > yest['20MA']
            ups = 10 if ok_up else 0; score += ups
            tech_results.append(("短期均線翻揚", "5/10/20T 同步向上", f"+{ups}分", "status-pass" if ok_up else "status-fail", "模擬分析：多頭共識強烈。"))

            # 6. 籌碼五日趨勢
            chip_data_list = []
            if not df_chip.empty and "ForeignInvestmentSharesRatio" in df_chip.columns:
                chip_data_list = df_chip[['date', 'ForeignInvestmentSharesRatio']].tail(5).values.tolist()

            if chip_data_list and len(chip_data_list) >= 2:
                oldest_date, oldest_val = chip_data_list[0]
                latest_date, latest_val = chip_data_list[-1]
                diff = float(latest_val) - float(oldest_val)
                
                if diff >= 2: cs, cc = 15, "status-pass"
                elif diff >= 1.5: cs, cc = 10, "status-mid"
                elif diff >= 1: cs, cc = 5, "status-mid"
                else: cs, cc = 0, "status-fail"
                score += cs
                
                status_msg = "增加，有利多頭" if diff > 0 else "減少，籌碼鬆動"
                chip_results.append(("外資持股 5 日趨勢", f"自動抓取: {oldest_val}% → {latest_val}%", f"+{cs}分", cc, f"模擬分析：從 {oldest_date} 至 {latest_date} 外資持股{status_msg}。"))
            else:
                chip_results.append(("外資持股 5 日趨勢", "無自動數據", "+0分", "status-fail", "模擬分析：無法抓取該檔股票的籌碼數據(可能為剛上市或無外資)。"))

            # --- 報告 UI 渲染 ---
            col_res_sc, col_res_det = st.columns([1, 2])
            with col_res_sc:
                color = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 75 else "#E74C3C"
                st.markdown(f'<div class="score-circle" style="border-color:{color}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:{color}; font-weight:bold; margin-top:10px;'>綜合診斷總分</p>", unsafe_allow_html=True)
            with col_res_det:
                st.markdown(f"## {display_name} 全自動診斷報告")
                if score >= 80: st.success("🎯 **值得買入**：技術面與籌碼面極佳！")
                elif score >= 75: st.warning("⚠️ **列入觀察**：分數已達觀察區間。")
                else: st.error("❄️ **暫不參考**：綜合評分未達標。")

            st.markdown("### 🧬 外資籌碼面 (FinMind 自動判定)")
            for t, d, stg, cls, r in chip_results: st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

            st.markdown("### 🔍 技術面得分細節")
            for t, d, stg, cls, r in tech_results: st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

            # --- 評分細節說明表 (只在報告展開後顯示) ---
            st.markdown("""
            <div class="weight-box">
                <h3 style="color:#D4AF37; margin-top:0;">📊 買入評級 - 得分細節說明</h3>
                <table style="width:100%; color:#BBB; font-size:14px;">
                    <tr><td style="color:#EAEAEA; padding:5px 0;"><b>KD 位階 (25分)</b></td><td>25-40(25分) | 45-60(20分) | 65-70(10分)</td></tr>
                    <tr><td style="color:#EAEAEA; padding:5px 0;"><b>量增紅K (20分)</b></td><td>成交量 > 5T 均量 且 收紅 K</td></tr>
                    <tr><td style="color:#EAEAEA; padding:5px 0;"><b>籌碼五日 (15分)</b></td><td>增加率 ≥2%(15分) | ≥1.5%(10分) | ≥1%(5分)</td></tr>
                    <tr><td style="color:#EAEAEA; padding:5px 0;"><b>均線支撐 (10分)</b></td><td>站穩 5/10/20T(10分) | 5/10T(5分) | 5T(3分)</td></tr>
                    <tr><td style="color:#EAEAEA; padding:5px 0;"><b>均線翻揚 (10分)</b></td><td>5T、10T、20T 同步向上</td></tr>
                    <tr><td style="color:#EAEAEA; padding:5px 0;"><b>MACD (10分)</b></td><td>DIF > MACD 柱狀翻紅</td></tr>
                    <tr><td style="color:#EAEAEA; padding:5px 0;"><b>週轉率 (5分)</b></td><td>>8%(5分) | >5%(3分) | >1%(1分)</td></tr>
                    <tr><td style="color:#EAEAEA; padding:5px 0;"><b>季線趨勢 (5分)</b></td><td>現價 > 60 日前價格</td></tr>
                </table>
                <p style="margin-top:15px; font-weight:bold; color:#D4AF37;">🟢 80+ 值得買入 | 🟡 75+ 列入觀察 | 🔴 75- 暫不參考</p>
            </div>
            <div style="font-size: 12px; color: #777; text-align: center;">⚠️ 免責聲明：數據由 FinMind 提供。本工具僅為模擬用途，不構成投資建議。</div>
            """, unsafe_allow_html=True)
