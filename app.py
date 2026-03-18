import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 🚀 全局介面設定 ---
st.set_page_config(page_title="台股短線起漲診斷器", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: "Microsoft JhengHei", sans-serif;
        background-color: #121212; color: #EAEAEA;
    }
    .main-title { color: #D4AF37; font-weight: bold; margin-bottom: 5px; }
    .input-label { font-size: 18px; font-weight: bold; color: #D4AF37; margin-bottom: 8px; }
    .metric-card, .check-item { background-color: #1E1E1E; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px; border: 1px solid #333; }
    .score-circle { background-color: #121212; border-radius: 50%; width: 130px; height: 130px; display: flex; align-items: center; justify-content: center; border: 10px solid #333; margin: 0 auto; box-shadow: 0 0 15px rgba(212, 175, 55, 0.2); }
    .score-text { font-size: 42px; font-weight: bold; color: #D4AF37; }
    .stButton > button { background-color: #D4AF37 !important; color: #121212 !important; font-weight: bold !important; border-radius: 8px !important; }
    .check-title { font-weight: bold; color: #EAEAEA; font-size: 16px; }
    .check-reason { color: #AAA; font-size: 13.5px; margin-top: 6px; line-height: 1.4; }
    .status-pass { background-color: #1A3E2A; color: #2DCC70; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #2DCC70; }
    .status-mid { background-color: #3E321A; color: #F1C40F; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #F1C40F; }
    .status-fail { background-color: #3E1A1A; color: #E74C3C; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #E74C3C; }
    input[data-testid="stTextInput"] { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">⚡ 台股短線起漲點診斷</h1>', unsafe_allow_html=True)
st.markdown('<p class="input-label">📍 請輸入台股代號 (上市櫃均可)</p>', unsafe_allow_html=True)
stock_id = st.text_input("label_hidden", value="", label_visibility="collapsed", placeholder="請輸入代號 (例如: 2330, 8069...)")
analyze_btn = st.button("🚀 啟動深度診斷")

if analyze_btn and stock_id:
    def fetch_data(sid):
        for ext in [".TW", ".TWO"]:
            t = yf.Ticker(f"{sid}{ext}")
            d = t.history(period="1y")
            if not d.empty: return d, t
        return None, None

    with st.spinner(f"正在分析 {stock_id} ..."):
        df, ticker = fetch_data(stock_id)
        if df is None: st.error(f"❌ 查無代號「{stock_id}」")
        else:
            # 指標運算
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
            
            # 1. 週轉率 (5%)
            ok = turnover > 8.0; score += 5 if ok else 0
            results.append(("週轉率 > 8%", f"實測 {turnover:.2f}%", "通過" if ok else "未過", "status-pass" if ok else "status-fail", "週轉率代表換手動能，8% 以上代表具備短線熱度。"))
            
            # 2. KD 位階 (20%) - 關鍵修改
            k_val = today['K']
            if 20 <= k_val <= 30:
                kd_score = 20; kd_status = "高分通過"; kd_cls = "status-pass"
                kd_reason = "目前 KD 處於 20-30 低檔起漲區，最具備爆發潛力與風險報酬比。"
            elif 40 <= k_val <= 65:
                kd_score = 10; kd_status = "中分通過"; kd_cls = "status-mid"
                kd_reason = "目前 KD 處於 40-65 中位階，動能發酵中但需留意上方空間。"
            elif k_val > 70:
                kd_score = 0; kd_status = "低分未過"; kd_cls = "status-fail"
                kd_reason = "目前 KD 超過 70 進入高檔過熱區，追高風險增加，故不給分。"
            else:
                kd_score = 0; kd_status = "未達標"; kd_cls = "status-fail"
                kd_reason = "KD 位階尚未進入有效攻擊區間。"
            score += kd_score
            results.append(("KD 位階判定", f"目前 K 值: {k_val:.1f}", kd_status, kd_cls, kd_reason))

            # 3. 均線 (20%)
            ok = today['5MA'] > yest['5MA'] and today['10MA'] > yest['10MA'] and today['20MA'] > yest['20MA']; score += 20 if ok else 0
            results.append(("均線全面上揚", "短中長期均線翻揚", "通過" if ok else "未過", "status-pass" if ok else "status-fail", "均線同向翻揚是趨勢確認的最強訊號。"))
            
            # 9. 量價配合 (30%) - 權重提高
            ok = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']; score += 30 if ok else 0
            results.append(("量增紅K攻擊", "成交量大於5T均量", "通過" if ok else "未過", "status-pass" if ok else "status-fail", "帶量紅K代表主力表態攻擊，是權重最高的動能指標。"))

            # 其他指標 (維持邏輯)
            for ma, lbl in [('5MA','5T'),('10MA','10T'),('20MA','20T')]:
                ok_st = today['Close'] > today[ma]; score += 5 if ok_st else 0
                results.append((f"站穩 {lbl}", f"守住 {lbl} 支撐", "通過" if ok_st else "未過", "status-pass" if ok_st else "status-fail", f"股價維持在 {lbl} 之上，代表強勢格局未破。"))
            
            ok_60 = today['Close'] > df.iloc[-60]['Close']; score += 5 if ok_60 else 0
            results.append(("季線扣抵", "60MA 趨勢向上", "通過" if ok_60 else "未過", "status-pass" if ok_60 else "status-fail", "股價大於60日前價格，代表中長線趨勢翻多。"))
            ok_macd = (today['DIF'] - today['MACD']) > 0; score += 5 if ok_macd else 0
            results.append(("DIF-MACD > 0", "柱狀翻紅", "通過" if ok_macd else "未過", "status-pass" if ok_macd else "status-fail", "動能指標轉正，代表攻擊力道正在增強。"))

            # --- 顯示報告 ---
            col_sc, col_det = st.columns([1, 2])
            with col_sc:
                c = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 70 else "#E74C3C"
                st.markdown(f'<div class="score-circle" style="border-color:{c}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
            
            with col_det:
                st.markdown(f"## {stock_id} 模擬診斷報告")
                if score >= 80: st.success("🎯 **值得買入**：指標高度契合起漲邏輯。"); st.balloons()
                elif score >= 70: st.warning("⚠️ **列入觀察**：分數達標但仍有進步空間。")
                else: st.error("❄️ **暫不參考**：總分未達 60 分門檻。")

            st.markdown("### 🔍 詳細分析清單")
            for t, d, s, cls, r in results:
                st.markdown(f'<div class="check-item"><div class="check-content"><div class="check-title">{t} ({d})</div><div class="check-reason"><b>教練分析：</b>{r}</div></div><div class="{cls}">{s}</div></div>', unsafe_allow_html=True)
