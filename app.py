import streamlit as st
import pandas as pd
import requests
import datetime

# --- 🚀 全局介面與 Token 設定 ---
st.set_page_config(page_title="台股短線買入評級", page_icon="⚡", layout="wide")

# 🔑 你的 FinMind VIP Token
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
    .stButton > button { background-color: #D4AF37 !important; color: #121212 !important; font-weight: bold !important; border-radius: 8px !important; width: 100%; height: 50px; }
    .status-pass { background-color: #1A3E2A; color: #2DCC70; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #2DCC70; min-width: 90px; text-align: center; }
    .status-mid { background-color: #3E321A; color: #F1C40F; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #F1C40F; min-width: 90px; text-align: center; }
    .status-fail { background-color: #3E1A1A; color: #E74C3C; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #E74C3C; min-width: 90px; text-align: center; }
    input[data-testid="stTextInput"] { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">⚡ 台股短線買入評級</h1>', unsafe_allow_html=True)

# --- 🎯 100% FinMind 數據引擎 ---

@st.cache_data(ttl=86400) # 緩存一天 (24小時)，抓取全台股代號與名稱字典
def fetch_stock_mapping():
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockInfo",
            "token": FINMIND_TOKEN
        }
        res = requests.get(url, params=params, timeout=10).json()
        if res.get("msg") == "success":
            df = pd.DataFrame(res["data"])
            # 建立 { "2330": "台積電", "1301": "台塑" } 的字典
            return dict(zip(df['stock_id'], df['stock_name']))
        return {}
    except:
        return {}

@st.cache_data(ttl=900)
def fetch_finmind_data(sid):
    try:
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=150)).strftime("%Y-%m-%d")
        url = "https://api.finmindtrade.com/api/v4/data"
        
        price_params = {
            "dataset": "TaiwanStockPrice",
            "data_id": sid,
            "start_date": start_date,
            "end_date": end_date,
            "token": FINMIND_TOKEN
        }
        res_p = requests.get(url, params=price_params, timeout=10).json()
        if res_p.get("msg") != "success" or len(res_p.get("data", [])) == 0:
            return None, None
            
        df = pd.DataFrame(res_p["data"])
        df.rename(columns={'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'}, inplace=True)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col])
            
        chip_params = {
            "dataset": "TaiwanStockShareholding",
            "data_id": sid,
            "start_date": (datetime.datetime.now() - datetime.timedelta(days=15)).strftime("%Y-%m-%d"),
            "end_date": end_date,
            "token": FINMIND_TOKEN
        }
        res_c = requests.get(url, params=chip_params, timeout=10).json()
        df_chip = pd.DataFrame(res_c.get("data", []))
        
        return df, df_chip
    except Exception as e:
        return "error", str(e)

# --- 介面輸入 ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<p class="input-label" style="text-align:center;">📍 請輸入台股代號</p>', unsafe_allow_html=True)
    stock_id = st.text_input("s_id", value="", label_visibility="collapsed", placeholder="例如: 1301")
    analyze_btn = st.button("🚀 啟動全自動深度診斷")

# 預先載入股票名稱字典
stock_mapping = fetch_stock_mapping()

if analyze_btn and stock_id:
    # 🎯 取得公司名稱，如果有抓到就顯示「1301 台塑」，沒抓到就只顯示「1301」
    stock_name = stock_mapping.get(stock_id, "")
    display_name = f"{stock_id} {stock_name}" if stock_name else stock_id

    with st.spinner(f"正在透過 FinMind 雙引擎分析 {display_name} ..."):
        df, df_chip = fetch_finmind_data(stock_id)
        
        if df is None: st.error(f"❌ 查無代號「{stock_id}」的資料，請確認是否為有效台股代號。")
        elif isinstance(df, str) and df == "error": st.error("⚠️ 伺服器連線發生錯誤，請稍後再試。")
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
            
            # --- 精算發行總股數與週轉率 ---
            total_shares = 0
            chip_data_list = []
            if not df_chip.empty and "ForeignInvestmentSharesRatio" in df_chip.columns:
                latest_chip = df_chip.iloc[-1]
                ratio = pd.to_numeric(latest_chip.get('ForeignInvestmentSharesRatio', 0))
                f_shares = pd.to_numeric(latest_chip.get('ForeignInvestmentRemainShares', 0))
                if ratio > 0: total_shares = f_shares / (ratio / 100)
                chip_data_list = df_chip[['date', 'ForeignInvestmentSharesRatio']].tail(3).values.tolist()
            
            turnover = (today['Volume'] / total_shares * 100) if total_shares > 0 else 0
            
            score = 0; tech_results = []; chip_results = []
            
            # 1. 週轉率 (5分)
            if turnover > 8: ts, tc = 5, "status-pass"
            elif turnover > 5: ts, tc = 3, "status-mid"
            elif turnover > 1: ts, tc = 1, "status-fail"
            else: ts, tc = 0, "status-fail"
            score += ts; tech_results.append(("週轉率判定", f"實測 {turnover:.2f}%", f"+{ts}分", tc, "模擬分析：週轉率水平對應得分。"))
            
            # 2. KD 位階 (25分)
            k_val = today['K']
            if 25 <= k_val <= 40: ks, kc, km = 25, "status-pass", "KD 25-40 低檔爆發區，滿分。"
            elif 45 <= k_val <= 60: ks, kc, km = 20, "status-mid", "KD 45-60 中位階穩定區。"
            elif 65 <= k_val <= 70: ks, kc, km = 10, "status-fail", "KD 65-70 稍嫌過熱。"
            else: ks, kc, km = 0, "status-fail", "過熱(>75)或未達標。"
            score += ks; tech_results.append(("KD 位階判定", f"K值: {k_val:.1f}", f"+{ks}分", kc, f"模擬分析：{km}"))
            
            # 3. 均線支撐 (10分)
            c_val, m5, m10, m20 = today['Close'], today['5MA'], today['10MA'], today['20MA']
            count = sum([c_val > m5, c_val > m10, c_val > m20])
            if count == 3: mas, mac, mam = 10, "status-pass", "站穩三線滿分。"
            elif count == 2: mas, mac, mam = 5, "status-mid", "站穩雙線。"
            elif count == 1: mas, mac, mam = 3, "status-fail", "僅站穩 5T。"
            else: mas, mac, mam = 0, "status-fail", "均線之下。"
            score += mas; tech_results.append(("短期均線支撐", f"收盤:{c_val:.1f}", f"+{mas}分", mac, f"模擬分析：{mam}"))
            
            # 4. 量增紅K攻擊 (20分)
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

            # 🎯 6. 全自動籌碼分析 (15分)
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
                chip_results.append(("外資持股 3 日趨勢", f"自動抓取: {oldest_val}% → {latest_val}%", f"+{cs}分", cc, f"模擬分析：從 {oldest_date} 至 {latest_date} 外資持股{status_msg}。"))
            else:
                chip_results.append(("外資持股 3 日趨勢", "無自動數據", "+0分", "status-fail", "模擬分析：無法抓取該檔股票的籌碼數據(可能為剛上市或無外資)。"))

            # --- 顯示結果 ---
            col_res_sc, col_res_det = st.columns([1, 2])
            with col_res_sc:
                color = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 75 else "#E74C3C"
                st.markdown(f'<div class="score-circle" style="border-color:{color}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:{color}; font-weight:bold; margin-top:10px;'>綜合診斷總分</p>", unsafe_allow_html=True)
            with col_res_det:
                # 🎯 標題現在會自動加上公司名稱了！
                st.markdown(f"## {display_name} 全自動診斷報告")
                if score >= 80: st.success("🎯 **值得買入**：技術面與籌碼面極佳！")
                elif score >= 75: st.warning("⚠️ **列入觀察**：分數已達觀察區間。")
                else: st.error("❄️ **暫不參考**：綜合評分未達標。")

            st.markdown("### 🧬 外資籌碼面 (FinMind 自動判定)")
            for t, d, stg, cls, r in chip_results:
                st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

            st.markdown("### 🔍 技術面得分細節")
            for t, d, stg, cls, r in tech_results:
                st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

# --- 固定顯示說明表 ---
st.markdown("""
<div class="weight-box">
    <h3 style="color:#D4AF37; margin-top:0;">📊 買入評級 - 得分細節說明</h3>
    <table style="width:100%; color:#BBB; font-size:14px;">
        <tr><td style="color:#EAEAEA;"><b>KD 位階 (25分)</b></td><td>25-40(25分) | 45-60(20分) | 65-70(10分)</td></tr>
        <tr><td style="color:#EAEAEA;"><b>量增紅K (20分)</b></td><td>成交量 > 5T 均量 且 收紅 K</td></tr>
        <tr><td style="color:#EAEAEA;"><b>籌碼三日 (15分)</b></td><td>增加率 ≥2%(15分) | ≥1.5%(10分) | ≥1%(5分)</td></tr>
        <tr><td style="color:#EAEAEA;"><b>均線支撐 (10分)</b></td><td>站穩 5/10/20T(10分) | 5/10T(5分) | 5T(3分)</td></tr>
        <tr><td style="color:#EAEAEA;"><b>均線翻揚 (10分)</b></td><td>5T、10T、20T 同步向上</td></tr>
        <tr><td style="color:#EAEAEA;"><b>MACD (10分)</b></td><td>DIF > MACD 柱狀翻紅</td></tr>
        <tr><td style="color:#EAEAEA;"><b>週轉率 (5分)</b></td><td>>8%(5分) | >5%(3分) | >1%(1分)</td></tr>
        <tr><td style="color:#EAEAEA;"><b>季線趨勢 (5分)</b></td><td>現價 > 60 日前價格</td></tr>
    </table>
    <p style="margin-top:15px; font-weight:bold; color:#D4AF37;">🟢 80+ 值得買入 | 🟡 75+ 列入觀察 | 🔴 75- 暫不參考</p>
</div>
<div style="font-size: 12px; color: #777; text-align: center;">⚠️ 免責聲明：所有數據均由 FinMind API 提供。本工具僅為模擬用途，不構成投資建議。</div>
""", unsafe_allow_html=True)
