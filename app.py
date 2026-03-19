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

# --- 輸入區域：股票代號 + 手動籌碼 ---
col_stock, col_chip_desc = st.columns([1, 2])
with col_stock:
    st.markdown('<p class="input-label">📍 股票代號</p>', unsafe_allow_html=True)
    stock_id = st.text_input("s_id", value="", label_visibility="collapsed", placeholder="例如: 2330")

with col_chip_desc:
    st.markdown('<p class="input-label">📊 近五日外資買賣超占比 (%) - 手動輸入 (選填)</p>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    f1 = c1.text_input("d1", placeholder="D-1", label_visibility="collapsed")
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
            df['60MA'] = df['Close'].rolling(60).mean(); df['5VMA'] = df['Volume'].rolling(5).mean()
            df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
            df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
            df['K'] = df['RSV'].ewm(com=2, adjust=False).mean(); df['D'] = df['K'].ewm(com=2, adjust=False).mean()
            df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
            
            today, yest = df.iloc[-1], df.iloc[-2]
            shares = ticker.info.get('sharesOutstanding', 0)
            turnover = (today['Volume'] / shares * 100) if shares else 0
            
            score = 0; results = []
            
            # --- 1. 週轉率 (5分) ---
            ok = turnover > 8.0; iscore = 5 if ok else 0; score += iscore
            results.append(("週轉率 > 8%", f"實測 {turnover:.2f}%", f"+{iscore}分", "status-pass" if ok else "status-fail", "週轉率代表換手積極度。"))
            
            # --- 2. KD 位階 (20分) ---
            k_val = today['K']
            if 20 <= k_val <= 30: ks, k_tag, kc, kr = 20, "+20分", "status-pass", "KD 20-30 低檔起漲區，噴發潛力最高。"
            elif 40 <= k_val <= 65: ks, k_tag, kc, kr = 10, "+10分", "status-mid", "KD 40-65 中位階，動能累積中。"
            else: ks, k_tag, kc, kr = 0, "+0分", "status-fail", f"K值 {k_val:.1f} 處於非加分區間。"
            score += ks; results.append(("KD 位階判定", f"K值: {k_val:.1f}", k_tag, kc, kr))
            
            # --- 3. 均線翻揚 (10分) ---
            ok = today['5MA'] > yest['5MA'] and today['10MA'] > yest['10MA'] and today['20MA'] > yest['20MA']
            iscore = 10 if ok else 0; score += iscore
            results.append(("短期均線翻揚", "5/10/20T 同步向上", f"+{iscore}分", "status-pass" if ok else "status-fail", "趨勢一致向上，多頭共識強。"))
            
            # --- 4. 均線支撐 (10分) ---
            c_val = today['Close']; m5, m10, m20 = today['5MA'], today['10MA'], today['20MA']
            count = sum([c_val > m5, c_val > m10, c_val > m20])
            iscore = 10 if count == 3 else 7 if count == 2 else 3 if count == 1 else 0
            score += iscore
            results.append(("均線支撐強度", f"站穩 {count} 條線", f"+{iscore}分", "status-pass" if count==3 else "status-mid" if count>=1 else "status-fail", f"收盤({c_val:.2f}) vs 均線({m5:.1f}/{m10:.1f}/{m20:.1f})。"))
            
            # --- 5. 量增紅K攻擊 (20分) ---
            v_vol, v_avg = int(today['Volume']/1000), int(today['5VMA']/1000)
            ok = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']
            iscore = 20 if ok else 0; score += iscore
            results.append(("量增紅K攻擊", f"{v_vol:,}張 / 5T均 {v_avg:,}張", f"+{iscore}分", "status-pass" if ok else "status-fail", "帶量紅K為主力的攻擊表態。"))
            
            # --- 6. 季線與 MACD (共 15分) ---
            ok60 = today['Close'] > df.iloc[-60]['Close']; s60 = 5 if ok60 else 0; score += s60
            results.append(("季線趨勢向上", f"現價 > 60日前", f"+{s60}分", "status-pass" if ok60 else "status-fail", "中長線多頭底氣判定。"))
            okm = (today['DIF'] - today['MACD']) > 0; sm = 10 if okm else 0; score += sm
            results.append(("MACD 動能轉正", "柱狀翻紅", f"+{sm}分", "status-pass" if okm else "status-fail", "DIF > MACD，攻擊動能發散。"))

            # --- 🎯 7. 籌碼面手動分析 (20分) ---
            chip_results = []
            try:
                chip_vals = [float(v) if v.strip() else 0.0 for v in [f1, f2, f3, f4, f5]]
                if any(v != 0.0 for v in chip_vals):
                    total_chip = sum(chip_vals)
                    is_pass = total_chip > 0
                    cs = 20 if is_pass else 0; score += cs
                    chip_results.append(("籌碼面模擬分析", f"5日合計: {total_chip:.2f}%", f"+{cs}分", "status-pass" if is_pass else "status-fail", f"模擬分析：外資近五日呈現 {'買超' if is_pass else '賣超'}，籌碼 {'有利多頭' if is_pass else '需留意拋售'}。"))
            except ValueError:
                st.error("⚠️ 籌碼占比請輸入數字！")

            # --- 顯示總分報告 ---
            col_sc, col_det = st.columns([1, 2])
            with col_sc:
                c_hex = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 75 else "#E74C3C"
                st.markdown(f'<div class="score-circle" style="border-color:{c_hex}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:{c_hex}; font-weight:bold; margin-top:10px;'>診斷總分 (滿分100)</p>", unsafe_allow_html=True)
            
            with col_det:
                st.markdown(f"## {stock_id} 買入評級診斷報告")
                st.markdown(f"""
                <div class="weight-box">
                    <b>📈 評分權重說明：</b><br>
                    技術面(80分)：量增紅K 20 | KD位階 20 | 均線翻揚 10 | 均線支撐 10 | MACD 10 | 週轉率 5 | 季線 5<br>
                    籌碼面(20分)：外資 5 日占比合計 > 0 得滿分<br>
                    <b>判定標準：</b> 🟢 80+ 值得買入 | 🟡 75+ 列入觀察 | 🔴 75- 暫不參考
                </div>
                """, unsafe_allow_html=True)
                if score >= 80: st.success("🎯 **值得買入**：技術與籌碼面高度契合！")
                elif score >= 75: st.warning("⚠️ **列入觀察**：分數接近門檻，建議分批佈局。")
                else: st.error("❄️ **暫不參考**：綜合評分未達門檻。")

            if chip_results:
                st.markdown("### 🧬 籌碼面模擬分析")
                for t, d, stg, cls, r in chip_results:
                    st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason">{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

            st.markdown("### 🔍 技術面得分細節")
            for t, d, stg, cls, r in results:
                st.markdown(f'<div class="check-item"><div style="flex: 1;"><div class="check-title">{t} ({d})</div><div class="check-reason"><b>模擬分析：</b>{r}</div></div><div class="{cls}">{stg}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="disclaimer">⚠️ 免責聲明：本工具僅為技術指標與模擬分析用途，不構成投資建議。投資一定有風險。</div>', unsafe_allow_html=True)
