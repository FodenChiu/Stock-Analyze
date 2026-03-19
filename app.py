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
            df['K'] = df['RSV'].ewm(com=2, adjust=False).mean(); df['D'] = df['K'].ewm(com=2, adjust=False).mean()
            df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
            
            today, yest = df.iloc[-1], df.iloc[-2]
            shares = ticker.info.get('sharesOutstanding', 0)
            turnover = (today['Volume'] / shares * 100) if shares else 0
            
            score = 0; tech_results = []; chip_results = []
            
            # --- 1. 週轉率 (5分) ---
            ok = turnover > 8.0; iscore = 5 if ok else 0; score += iscore
            tech_results.append(("週轉率 > 8%", f"實測 {turnover:.2f}%", f"+{iscore}分", "status-pass" if ok else "status-fail", "週轉率代表換手積極度。"))
            
            # --- 2. KD 位階 (20分) ---
            k_val = today['K']
            if 20 <= k_val <= 30: ks = 20; kr = "KD 20-30 低檔起漲區，最具噴發潛力。"
            elif 40 <= k_val <= 65: ks = 10; kr = "KD 40-65 中位階，動能發揮中。"
            else: ks = 0; kr = f"K值 {k_val:.1f} 不在加分區間。"
            score += ks; tech_results.append(("KD 位階判定", f"K值: {k_val:.1f}", f"+{ks}分", "status-pass" if ks>0 else "status-fail", kr))
            
            # --- 3. 均線翻揚 (10分) ---
            ok = today['5MA'] > yest['5MA'] and today['10MA'] > yest['10MA'] and today['20MA'] > yest['20MA']
            iscore = 10 if ok else 0; score += iscore
            tech_results.append(("短期均線翻揚", "5/10/20T 同步向上", f"+{iscore}分", "status-pass" if ok else "status-fail", "趨勢一致向上，多頭共識強。"))
            
            # --- 4. 均線支撐 (10分) ---
            count = sum([today['Close'] > today['5MA'], today['Close'] > today['10MA'], today['Close'] > today['20MA']])
            iscore = 10 if count == 3 else 5 if count >= 1 else 0
            score += iscore
            tech_results.append(("均線支撐強度", f"站穩 {count} 條線", f"+{iscore}分", "status-pass" if count==3 else "status-fail", f"股價({today['Close']:.2f})與各均線支撐對比。"))
            
            # --- 5. 量增紅K攻擊 (20分) ---
            v_vol, v_avg = int(today['Volume']/1000), int(today['5VMA']/1000)
            ok = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']
            iscore = 20 if ok else 0; score += iscore
            tech_results.append(("量增紅K攻擊", f"{v_vol:,}張 / 5T均 {v_avg:,}張", f"+{iscore}分", "status-pass" if ok else "status-fail", "帶量紅K為主力的攻擊表態。"))
            
            # --- 6. 其它 (MACD/季線 各5分) ---
            ok60 = today['Close'] > df.iloc[-60]['Close']; score += 5 if ok60 else 0
            tech_results.append(("季線趨勢向上", "大於60日前價格", "+5分" if ok60 else "+0分", "status-pass" if ok60 else "status-fail", "中長線多頭底氣判定。"))
            okm = (today['DIF'] - today['MACD']) > 0; score += 10 if okm else 0
            tech_results.append(("MACD 動能轉正", "柱狀翻紅", "+10分" if okm else "+0分", "status-pass" if okm else "status-fail", "DIF > MACD，短線攻擊力強。"))

            # --- 🎯 7. 籌碼趨勢分析 (20分) ---
            try:
                # 抓取有填寫的數值
                raw_inputs = [f1, f2, f3, f4, f5]
                valid_vals = [float(v) for v in raw_inputs if v.strip()]
                if len(valid_vals) >= 2:
                    latest = valid_vals[0]
                    oldest = valid_vals[-1]
                    trend_up = latest > oldest
                    cs = 20 if trend_up else 0; score += cs
                    status_txt = "占比變高" if trend_up else "占比減少"
                    reason_txt = f"模擬分析：外資持股由 {oldest}% 增加至 {latest}%，籌碼集中度提升，值得買入。" if trend_up else f"模擬分析：外資持股由 {oldest}% 減少至 {latest}%，籌碼鬆動，不值得買入。"
                    chip_results.append(("籌碼趨勢分析", f"{oldest}% → {latest}%", f"+{cs}分", "status-pass" if trend_up else "status-fail", reason_txt))
                elif len(valid_vals) == 1:
                    st.info("💡 籌碼趨勢需至少輸入兩天數據方可分析。")
            except ValueError:
                st.error("⚠️ 籌碼占比請輸入純數字！")

            # --- 顯示介面 ---
            col_sc, col_det = st.columns([1, 2])
            with col_sc:
                c_hex = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 75 else "#E74C3C"
                st.markdown(f'<div class="score-circle" style="border-color:{c_hex}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:{c_hex}; font-weight:bold; margin-top:10px;'>綜合診斷總分</p>", unsafe_allow_html=True)
            
            with col_det:
                st.markdown(f"## {stock_id} 買入評級診斷報告")
                st.markdown(f"""
                <div class="weight-box">
                    <b>📈 權重配比：</b>技術面 80分 + 籌碼面 20分 = 100分<br>
                    <b>判定標準：</b> 🟢 80+ 值得買入 | 🟡 75+ 列入觀察 | 🔴 75- 暫不參考
                </div>
                """, unsafe_allow_html=True)
                if score >= 80: st.success("🎯 **值得買入**：趨勢與籌碼同步走強！")
                elif score >= 75: st.warning("⚠️ **列入觀察**：分數接近門檻，建議確認支撐位。")
                else: st.error("❄️ **暫不參考**：目前評分未達買入標準。")

            if chip_results:
                st.markdown("### 🧬 籌碼面趨勢分析")
                for t, d, stg, cls, r in chip_results:
                    st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

            st.markdown("### 🔍 技術面得分細節")
            for t, d, stg, cls, r in tech_results:
                st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason"><b>模擬分析：</b>{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="disclaimer">⚠️ 免責聲明：本工具僅為技術指標與趨勢模擬用途，不構成投資建議。</div>', unsafe_allow_html=True)
