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
    .weight-box { background-color: #1A1A1A; border: 1px solid #D4AF37; border-radius: 8px; padding: 15px; margin-bottom: 20px; font-size: 13px; color: #BBB; }
    .check-item { background-color: #1E1E1E; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px; border: 1px solid #333; display: flex; align-items: center; }
    .score-circle { background-color: #121212; border-radius: 50%; width: 130px; height: 130px; display: flex; align-items: center; justify-content: center; border: 10px solid #333; margin: 0 auto; box-shadow: 0 0 15px rgba(212, 175, 55, 0.2); }
    .score-text { font-size: 42px; font-weight: bold; color: #D4AF37; }
    .stButton > button { background-color: #D4AF37 !important; color: #121212 !important; font-weight: bold !important; border-radius: 8px !important; width: 100%; height: 50px; }
    .check-title { font-weight: bold; color: #EAEAEA; font-size: 16px; }
    .check-reason { color: #AAA; font-size: 13.5px; margin-top: 6px; line-height: 1.4; }
    .status-pass { background-color: #1A3E2A; color: #2DCC70; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #2DCC70; min-width: 90px; text-align: center; }
    .status-mid { background-color: #3E321A; color: #F1C40F; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #F1C40F; min-width: 90px; text-align: center; }
    .status-fail { background-color: #3E1A1A; color: #E74C3C; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #E74C3C; min-width: 90px; text-align: center; }
    input[data-testid="stTextInput"] { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">⚡ 台股短線買入評級</h1>', unsafe_allow_html=True)

# --- 🎯 輸入區域 ---
col_stock, col_chip_desc = st.columns([1, 2])
with col_stock:
    st.markdown('<p class="input-label">📍 股票代號</p>', unsafe_allow_html=True)
    stock_id = st.text_input("s_id", value="", label_visibility="collapsed", placeholder="例如: 2330")

with col_chip_desc:
    st.markdown('<p class="input-label">📊 近五日外資持股占比 (%) - 手動輸入 (左至右為最新至最舊)</p>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    f1 = c1.text_input("d1", placeholder="最新", label_visibility="collapsed")
    f2 = c2.text_input("d2", placeholder="D-2", label_visibility="collapsed")
    f3 = c3.text_input("d3", placeholder="D-3", label_visibility="collapsed")
    f4 = c4.text_input("d4", placeholder="D-4", label_visibility="collapsed")
    f5 = c5.text_input("d5", placeholder="D-5", label_visibility="collapsed")

analyze_btn = st.button("🚀 啟動深度診斷")

if analyze_btn and stock_id:
    def fetch_data(sid):
        for ext in [".TW", ".TWO"]:
            t = yf.Ticker(f"{sid}{ext}"); d = t.history(period="1y")
            if not d.empty: return d, t
        return None, None

    with st.spinner(f"正在分析 {stock_id} ..."):
        df, ticker = fetch_data(stock_id)
        if df is None: st.error(f"❌ 查無代號「{stock_id}」")
        else:
            # --- 技術指標運算 ---
            df['5MA'] = df['Close'].rolling(5).mean(); df['10MA'] = df['Close'].rolling(10).mean(); df['20MA'] = df['Close'].rolling(20).mean()
            df['5VMA'] = df['Volume'].rolling(5).mean()
            df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
            df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
            df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
            
            today, yest = df.iloc[-1], df.iloc[-2]
            shares = ticker.info.get('sharesOutstanding', 0)
            turnover = (today['Volume'] / shares * 100) if shares else 0
            
            score = 0; tech_results = []; chip_results = []
            
            # --- 1. 週轉率 (5分階梯) ---
            if turnover > 8: t_s = 5; t_cls = "status-pass"
            elif turnover > 5: t_s = 3; t_cls = "status-mid"
            elif turnover > 1: t_s = 1; t_cls = "status-fail"
            else: t_s = 0; t_cls = "status-fail"
            score += t_s
            tech_results.append(("週轉率判定", f"實測 {turnover:.2f}%", f"+{t_s}分", t_cls, f"模擬分析：週轉率水平對應得分為 {t_s} 分。"))
            
            # --- 2. KD 位階 (25分階梯) ---
            k_val = today['K']
            if 25 <= k_val <= 40: ks = 25; kc = "status-pass"; km = "KD 25-40 低檔爆發區，給予滿分。"
            elif 45 <= k_val <= 60: ks = 20; kc = "status-mid"; km = "KD 45-60 中位階穩定區，給予 20 分。"
            elif 65 <= k_val <= 70: ks = 10; kc = "status-fail"; km = "KD 65-70 稍嫌過熱，僅給予 10 分。"
            elif k_val > 75: ks = 0; kc = "status-fail"; km = "KD > 75 嚴重過熱，不給分。"
            else: ks = 0; kc = "status-fail"; km = "KD 低於 25 或位階不明確，不給分。"
            score += ks
            tech_results.append(("KD 位階判定", f"K值: {k_val:.1f}", f"+{ks}分", kc, f"模擬分析：{km}"))
            
            # --- 3. 均線支撐與翻揚 (10分階梯) ---
            c_val = today['Close']; m5, m10, m20 = today['5MA'], today['10MA'], today['20MA']
            if c_val > m5 and c_val > m10 and c_val > m20: ma_s = 10; ma_c = "status-pass"; ma_m = "股價站穩 5/10/20T 之上，給予滿分。"
            elif c_val > m5 and c_val > m10: ma_s = 5; ma_c = "status-mid"; ma_m = "股價僅站穩 5/10T 之上，給予 5 分。"
            elif c_val > m5: ma_s = 3; ma_c = "status-fail"; ma_m = "股價僅站穩 5T 之上，給予 3 分。"
            else: ma_s = 0; ma_c = "status-fail"; ma_m = "股價在所有均線之下，不給分。"
            score += ma_s
            tech_results.append(("短期均線支撐", f"收盤:{c_val:.1f}", f"+{ma_s}分", ma_c, f"模擬分析：{ma_m}"))
            
            # --- 4. 量增紅K攻擊 (20分) ---
            ok_vol = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']
            v_score = 20 if ok_vol else 0; score += v_score
            tech_results.append(("量增紅K攻擊", f"{int(today['Volume']/1000):,}張", f"+{v_score}分", "status-pass" if ok_vol else "status-fail", "模擬分析：帶量且收紅K代表主力攻擊表態。"))
            
            # --- 5. 其它技術面 (15分) ---
            # MACD (10分)
            df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
            ok_m = (df.iloc[-1]['DIF'] - df.iloc[-1]['MACD']) > 0
            m_s = 10 if ok_m else 0; score += m_s
            tech_results.append(("MACD 動能", "柱狀翻紅", f"+{m_s}分", "status-pass" if ok_m else "status-fail", "模擬分析：MACD 動能轉正。"))
            # 季線 (5分)
            ok_60 = today['Close'] > df.iloc[-60]['Close']
            q_s = 5 if ok_60 else 0; score += q_s
            tech_results.append(("季線趨勢", "現價 > 60日前", f"+{q_s}分", "status-pass" if ok_60 else "status-fail", "模擬分析：中長線多頭判定。"))

            # --- 🎯 6. 籌碼趨勢分析 (15分階梯) ---
            try:
                raw_inputs = [f1, f2, f3, f4, f5]
                valid_vals = [float(v) for v in raw_inputs if v.strip()]
                if len(valid_vals) >= 2:
                    diff = valid_vals[0] - valid_vals[-1] # 最新 - 最舊
                    if diff >= 2: cs = 15; c_c = "status-pass"
                    elif diff >= 1.5: cs = 10; c_c = "status-mid"
                    elif diff >= 1: cs = 5; c_c = "status-mid"
                    else: cs = 0; c_c = "status-fail"
                    score += cs
                    chip_results.append(("籌碼趨勢分析", f"5日增長 {diff:.2f}%", f"+{cs}分", c_c, f"模擬分析：外資持股由 {valid_vals[-1]}% 變動至 {valid_vals[0]}%，得分 {cs}。"))
            except ValueError:
                st.error("⚠️ 籌碼占比請輸入數字！")

            # --- 顯示報告 ---
            col_sc, col_det = st.columns([1, 2])
            with col_sc:
                c_hex = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 75 else "#E74C3C"
                st.markdown(f'<div class="score-circle" style="border-color:{c_hex}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:{c_hex}; font-weight:bold; margin-top:10px;'>綜合診斷總分</p>", unsafe_allow_html=True)
            
            with col_det:
                st.markdown(f"## {stock_id} 買入評級診斷報告")
                st.markdown(f"""
                <div class="weight-box">
                    <b>📈 階梯評分權重說明：</b><br>
                    KD位階 (25) | 量增紅K (20) | 籌碼增加率 (15) | 均線支撐 (10) | MACD (10) | 週轉率 (5) | 季線 (5)<br>
                    <b>判定標準：</b> 🟢 80+ 值得買入 | 🟡 75+ 列入觀察 | 🔴 75- 暫不參考
                </div>
                """, unsafe_allow_html=True)
                if score >= 80: st.success("🎯 **值得買入**：技術與籌碼面指標極佳！")
                elif score >= 75: st.warning("⚠️ **列入觀察**：分數已達觀察區間，建議確認大盤。")
                else: st.error("❄️ **暫不參考**：目前綜合評分未達標。")

            if chip_results:
                st.markdown("### 🧬 籌碼面趨勢分析")
                for t, d, stg, cls, r in chip_results:
                    st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

            st.markdown("### 🔍 技術面得分細節")
            for t, d, stg, cls, r in tech_results:
                st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="disclaimer">⚠️ 免責聲明：本工具僅為技術指標與趨勢模擬用途，不構成投資建議。</div>', unsafe_allow_html=True)
