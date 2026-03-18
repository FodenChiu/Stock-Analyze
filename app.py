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
    .status-pass { background-color: #1A3E2A; color: #2DCC70; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #2DCC70; min-width: 80px; text-align: center; }
    .status-mid { background-color: #3E321A; color: #F1C40F; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #F1C40F; min-width: 80px; text-align: center; }
    .status-fail { background-color: #3E1A1A; color: #E74C3C; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: bold; border: 1px solid #E74C3C; min-width: 80px; text-align: center; }
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
            ok = turnover > 8.0; item_score = 5 if ok else 0; score += item_score
            results.append(("週轉率 > 8%", f"實測 {turnover:.2f}%", f"+{item_score}分", "status-pass" if ok else "status-fail", "週轉率代表換手動能，8% 以上代表具備短線熱度。"))
            
            # 2. KD 位階 (20%)
            k_val = today['K']
            if 20 <= k_val <= 30: kd_score = 20; kd_status = "+20分"; kd_cls = "status-pass"; kd_r = "KD 處於 20-30 低檔起漲區，最具備爆發潛力。"
            elif 40 <= k_val <= 65: kd_score = 10; kd_status = "+10分"; kd_cls = "status-mid"; kd_r = "KD 處於 40-65 中位階，動能發酵中。"
            else: kd_score = 0; kd_status = "+0分"; kd_cls = "status-fail"; kd_r = f"K值 {k_val:.1f} 不在加分區間 (過熱或過冷)。"
            score += kd_score
            results.append(("KD 位階判定", f"目前 K 值: {k_val:.1f}", kd_status, kd_cls, kd_r))

            # 3. 均線翻揚 (20%)
            ok = today['5MA'] > yest['5MA'] and today['10MA'] > yest['10MA'] and today['20MA'] > yest['20MA']
            item_score = 20 if ok else 0; score += item_score
            results.append(("均線全面上揚", "短中長期均線翻揚", f"+{item_score}分", "status-pass" if ok else "status-fail", "均線同向翻揚是趨勢確認的最強訊號。"))
            
            # 9. 量價配合 (30%)
            ok = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']
            item_score = 30 if ok else 0; score += item_score
            results.append(("量增紅K攻擊", "帶量且收紅K", f"+{item_score}分", "status-pass" if ok else "status-fail", "帶量紅K代表主力表態攻擊，權重最高。"))

            # 其他指標 (各 5%)
            for ma, lbl in [('5MA','5T'),('10MA','10T'),('20MA','20T')]:
                ok_st = today['Close'] > today[ma]; item_score = 5 if ok_st else 0; score += item_score
                results.append((f"站穩 {lbl}", f"股價 > {lbl}", f"+{item_score}分", "status-pass" if ok_st else "status-fail", f"股價維持在 {lbl} 之上，代表強勢格局未破。"))
            
            ok_60 = today['Close'] > df.iloc[-60]['Close']; item_score = 5 if ok_60 else 0; score += item_score
            results.append(("季線扣抵有過", "60MA 趨勢向上", f"+{item_score}分", "status-pass" if ok_60 else "status-fail", "股價大於60日前價格，長線趨勢翻多。"))
            
            ok_macd = (today['DIF'] - today['MACD']) > 0; item_score = 5 if ok_macd else 0; score += item_score
            results.append(("DIF-MACD > 0", "柱狀翻紅", f"+{item_score}分", "status-pass" if ok_macd else "status-fail", "動能指標轉正，代表攻擊力道增強。"))

            # --- 顯示總分報告 ---
            col_sc, col_det = st.columns([1, 2])
            with col_sc:
                c = "#2DCC70" if score >= 80 else "#F1C40F" if score >= 70 else "#E74C3C"
                st.markdown(f'<div class="score-circle" style="border-color:{c}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:{c}; font-weight:bold; margin-top:10px;'>診斷總分</p>", unsafe_allow_html=True)
            
            with col_det:
                st.markdown(f"## {stock_id} 模擬診斷分析")
                if score >= 80: st.success("🎯 **值得買入**：技術面具備強大起漲動能！"); st.balloons()
                elif score >= 70: st.warning("⚠️ **列入觀察**：分數達標，建議確認大盤走勢。")
                elif score >= 60: st.info("⚪ **保守看對**：分數剛好及格，建議等待更明確訊號。")
                else: st.error("❄️ **暫不參考**：總分未達門檻，動能不足。")

            st.markdown("### 🔍 各項得分細節")
            for title, data, score_tag, cls, reason in results:
                st.markdown(f"""
                    <div class="check-item">
                        <div style="flex: 1;">
                            <div class="check-title">{title} ({data})</div>
                            <div class="check-reason"><b>分析：</b>{reason}</div>
                        </div>
                        <div class="{cls}">{score_tag}</div>
                    </div>
                """, unsafe_allow_html=True)
