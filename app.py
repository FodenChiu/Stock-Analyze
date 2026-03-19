import streamlit as st
import yfinance as yf
import pandas as pd

# --- 🚀 全局介面設定 ---
st.set_page_config(page_title="台股短線買入評級", page_icon="⚡", layout="wide")

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

# --- 🎯 數據抓取核心 (加入快取與錯誤處理機制) ---
@st.cache_data(ttl=900)  # 數據緩存 15 分鐘，避免頻繁請求被封鎖
def fetch_stock_data(sid):
    try:
        for ext in [".TW", ".TWO"]:
            t = yf.Ticker(f"{sid}{ext}")
            d = t.history(period="1y")
            if not d.empty:
                return d, t.info
        return None, None
    except Exception as e:
        return "error", str(e)

# --- 輸入區域 ---
col_stock, col_chip_desc = st.columns([1, 2])
with col_stock:
    st.markdown('<p class="input-label">📍 股票代號</p>', unsafe_allow_html=True)
    stock_id = st.text_input("s_id", value="", label_visibility="collapsed", placeholder="例如: 2330")

with col_chip_desc:
    st.markdown('<p class="input-label">📊 近三日外資持股占比 (%) - 手動輸入 (左至右：最新、D-2、D-3)</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    f1 = c1.text_input("d1", placeholder="最新", label_visibility="collapsed")
    f2 = c2.text_input("d2", placeholder="D-2", label_visibility="collapsed")
    f3 = c3.text_input("d3", placeholder="D-3", label_visibility="collapsed")

analyze_btn = st.button("🚀 啟動深度診斷")

if analyze_btn and stock_id:
    with st.spinner(f"正在分析 {stock_id} ..."):
        df, info = fetch_stock_data(stock_id)
        
        if df == "error":
            st.error("⚠️ **伺服器連線忙碌中**")
            st.info("Yahoo Finance 目前暫時限制了請求頻率，請等待 1-2 分鐘後再重新點擊診斷。")
        elif df is None:
            st.error(f"❌ 查無代號「{stock_id}」")
        else:
            # --- 以下維持原有的 36.0 計算與顯示邏輯 ---
            df['5MA'] = df['Close'].rolling(5).mean(); df['10MA'] = df['Close'].rolling(10).mean(); df['20MA'] = df['Close'].rolling(20).mean()
            df['5VMA'] = df['Volume'].rolling(5).mean()
            df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
            df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
            df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
            df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
            
            today, yest = df.iloc[-1], df.iloc[-2]
            shares = info.get('sharesOutstanding', 0)
            turnover = (today['Volume'] / shares * 100) if shares else 0
            
            score = 0; tech_results = []; chip_results = []
            
            # 1. 週轉率 (5分階梯)
            if turnover > 8: ts, tc = 5, "status-pass"
            elif turnover > 5: ts, tc = 3, "status-mid"
            elif turnover > 1: ts, tc = 1, "status-fail"
            else: ts, tc = 0, "status-fail"
            score += ts; tech_results.append(("週轉率判定", f"實測 {turnover:.2f}%", f"+{ts}分", tc, "模擬分析：週轉率水平對應得分。"))
            
            # 2. KD 位階 (25分階梯)
            k_val = today['K']
            if 25 <= k_val <= 40: ks, kc, km = 25, "status-pass", "KD 25-40 低檔爆發區，滿分。"
            elif 45 <= k_val <= 60: ks, kc, km = 20, "status-mid", "KD 45-60 中位階穩定區。"
            elif 65 <= k_val <= 70: ks, kc, km = 10, "status-fail", "KD 65-70 稍嫌過熱。"
            else: ks, kc, km = 0, "status-fail", "過熱(>75)或未達標。"
            score += ks; tech_results.append(("KD 位階判定", f"K值: {k_val:.1f}", f"+{ks}分", kc, f"模擬分析：{km}"))
            
            # 3. 均線支撐 (10分階梯)
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
            tech_results.append(("量增紅K攻擊", f"{int(today['Volume']/1000):,}張", f"+{vs}分", "status-pass" if ok_v else "status-fail", "模擬分析：主力攻擊表態。"))

            # 5. 其他 (MACD 10/季線 5/均線翻揚 10)
            ok_m = (today['DIF'] - today['MACD']) > 0; ms = 10 if ok_m else 0; score += ms
            tech_results.append(("MACD 動能", "柱狀翻紅", f"+{ms}分", "status-pass" if ok_m else "status-fail", "模擬分析：動能轉正。"))
            ok_q = today['Close'] > df.iloc[-60]['Close']; qs = 5 if ok_q else 0; score += qs
            tech_results.append(("季線趨勢", "現價 > 60日前", f"+{qs}分", "status-pass" if ok_q else "status-fail", "模擬分析：長線翻多。"))
            ok_up = today['5MA'] > yest['5MA'] and today['10MA'] > yest['10MA'] and today['20MA'] > yest['20MA']
            ups = 10 if ok_up else 0; score += ups
            tech_results.append(("短期均線翻揚", "5/10/20T 同步向上", f"+{ups}分", "status-pass" if ok_up else "status-fail", "模擬分析：多頭共識強烈。"))

            # 6. 籌碼分析 (15分階梯)
            try:
                valid_vals = [float(v) for v in [f1, f2, f3] if v.strip()]
                if len(valid_vals) >= 2:
                    diff = valid_vals[0] - valid_vals[-1]
                    if diff >= 2: cs, cc = 15, "status-pass"
                    elif diff >= 1.5: cs, cc = 10, "status-mid"
                    elif diff >= 1: cs, cc = 5, "status-mid"
                    else: cs, cc = 0, "status-fail"
                    score += cs
                    chip_results.append(("籌碼三日趨勢", f"變動 {diff:.2f}%", f"+{cs}分", cc, f"模擬分析：外資持股 {'變高，值得買入' if diff > 0 else '減少，不值得買入'}。"))
            except ValueError: pass

            # 顯示結果
            col_res_sc, col_res_det = st.columns([1, 2])
            with col_res_sc:
                color = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 75 else "#E74C3C"
                st.markdown(f'<div class="score-circle" style="border-color:{color}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
            with col_res_det:
                st.markdown(f"## {stock_id} 診斷報告")
                if score >= 80: st.success("🎯 **值得買入**")
                elif score >= 75: st.warning("⚠️ **列入觀察**")
                else: st.error("❄️ **暫不參考**")

            if chip_results:
                st.markdown("### 🧬 籌碼面模擬分析")
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
""", unsafe_allow_html=True)
