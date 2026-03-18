import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 全局介面設定 ---
st.set_page_config(
    page_title="股市短線教練",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 嵌入客製化 CSS (保持專業 FinTech 風格)
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: "Microsoft JhengHei", sans-serif;
        background-color: #F8F9FA;
    }
    .metric-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border: 1px solid #EEE;
    }
    .score-circle {
        background-color: #FFFFFF;
        border-radius: 50%;
        width: 120px;
        height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 8px solid #E0E0E0;
        margin: 0 auto;
    }
    .score-text { font-size: 36px; font-weight: bold; color: #333; }
    .check-item {
        background-color: #FFFFFF;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #EEE;
    }
    .check-content { flex: 1; }
    .check-title { font-weight: bold; color: #333; }
    .check-reason { color: #888; font-size: 13px; margin-top: 4px; }
    .status-pass { background-color: #E6F7ED; color: #1A9F63; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; min-width: 60px; text-align: center; }
    .status-fail { background-color: #FEECEB; color: #E03E3E; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; min-width: 60px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 輸入區域 ---
st.title("⚡ 專屬股市短線教練 - 深度分析版")
col_input, _ = st.columns([1, 2])
with col_input:
    stock_id = st.text_input("輸入台股代號 (例: 1711 或 8069)", "1711")
    analyze_btn = st.button("🚀 啟動深度診斷")

if analyze_btn:
    def get_stock_data(sid):
        ticker = yf.Ticker(f"{sid}.TW")
        df = ticker.history(period="1y")
        if not df.empty: return df, ticker
        ticker = yf.Ticker(f"{sid}.TWO")
        df = ticker.history(period="1y")
        if not df.empty: return df, ticker
        return None, None

    with st.spinner(f"正在深度分析 {stock_id}..."):
        df, ticker = get_stock_data(stock_id)
        
        if df is None:
            st.error(f"❌ 找不到代號「{stock_id}」。")
        else:
            # 1. 運算核心指標
            df['5MA'] = df['Close'].rolling(5).mean()
            df['10MA'] = df['Close'].rolling(10).mean()
            df['20MA'] = df['Close'].rolling(20).mean()
            df['60MA'] = df['Close'].rolling(60).mean()
            df['5VMA'] = df['Volume'].rolling(5).mean()
            df['10VMA'] = df['Volume'].rolling(10).mean()
            df['9L'], df['9H'] = df['Low'].rolling(9).min(), df['High'].rolling(9).max()
            df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
            df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
            df['D'] = df['K'].ewm(com=2, adjust=False).mean()
            df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
            
            today = df.iloc[-1]
            yest = df.iloc[-2]
            shares = ticker.info.get('sharesOutstanding', 0)
            real_turnover = (today['Volume'] / shares * 100) if shares else 0
            
            # 2. 深度診斷清單
            total_score = 0
            results = []
            
            # 1. 週轉率 (10%)
            ok = real_turnover > 9.0
            total_score += 10 if ok else 0
            reason = "這代表市場人氣極旺，籌碼換手積極，容易出現強勢噴出。" if ok else "這代表交投清淡，屬於冷門或盤整期，短線爆發力不足。"
            results.append(("週轉率 > 9%", f"實測: {real_turnover:.2f}%", ok, reason))
            
            # 2. KD (20%)
            ok = today['K'] > today['D'] and today['K'] < 60 and today['D'] < 55
            total_score += 20 if ok else 0
            reason = "低檔黃金交叉且未過熱，屬於安全且有漲升空間的起漲點。" if ok else f"目前 K 值為 {today['K']:.1f}，可能太強勢已噴發或正處於下行修正中。"
            results.append(("KD 低檔黃叉", f"K:{today['K']:.1f}, D:{today['D']:.1f}", ok, reason))
            
            # 3. 均線 (20%)
            ok = today['5MA'] > yest['5MA'] and today['10MA'] > yest['10MA'] and today['20MA'] > yest['20MA']
            total_score += 20 if ok else 0
            reason = "短中長期趨勢同步向上，代表多頭結構穩固，買盤支撐強勁。" if ok else "均線尚未全面轉強，趨勢不明顯或正在轉弱，建議先等待。"
            results.append(("5/10/20T 全面上揚", "均線趨勢同步向上", ok, reason))
            
            # 4. 季線扣抵 (5%)
            ok = today['Close'] > df.iloc[-60]['Close']
            total_score += 5 if ok else 0
            reason = "股價位於60日前之上，代表季線趨勢向上，具備波段多頭支撐。" if ok else "股價低於60日前，季線趨勢向下，上方賣壓可能較沉重。"
            results.append(("大於季線扣抵", "60MA 趨勢判定", ok, reason))
            
            # 5. MACD (5%)
            ok = (today['DIF'] - today['MACD']) > 0
            total_score += 5 if ok else 0
            reason = "MACD柱狀圖翻紅，代表動能正處於轉強階段，攻擊力道較強。" if ok else "MACD柱狀圖為綠色，代表多頭動能尚未發散，仍需觀察。"
            results.append(("DIF-MACD > 0", "動能趨勢轉強", ok, reason))
            
            # 6-8. 站穩均線 (各 5%)
            for ma, label in [('5MA', '5T'), ('10MA', '10T'), ('20MA', '20T')]:
                ok = today['Close'] > today[ma]
                total_score += 5 if ok else 0
                reason = f"守住 {label} 支撐，有利於短線攻擊力道延續。" if ok else f"跌破 {label} 短期支撐，需留意股價轉弱或進入回檔。"
                results.append((f"站穩 {label}", f"股價 > {label}", ok, reason))
            
            # 9. 量能 (20%)
            ok = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']
            total_score += 20 if ok else 0
            reason = "量增且收紅K，代表有主力大買跡象，是標準的攻擊訊號。" if ok else "量能不足或收黑K，代表買盤不積極，可能有假突破風險。"
            results.append(("量增紅K", "實體紅K且放量", ok, reason))

            # --- 3. 呈現漂亮介面 ---
            col_score, col_info = st.columns([1, 2])
            with col_score:
                color = "#1A9F63" if total_score >= 70 else "#E0E0E0"
                st.markdown(f'<div class="score-circle" style="border-color:{color}"><div class="score-text">{total_score}</div></div>', unsafe_allow_html=True)
            
            with col_info:
                st.markdown(f"### {stock_id} 綜合診斷報告")
                st.write(f"今日收盤：**{today['Close']:.2f} 元**")
                if total_score >= 70:
                    st.success("🎯 **值得買入！** 滿足大部分短線強勢條件。")
                    st.balloons()
                elif total_score >= 40:
                    st.warning("⚠️ **繼續觀察**：目前動能尚在累積中，分數未達門檻。")
                else:
                    st.error("❄️ **暫不考慮**：指標顯示目前處於弱勢或盤整階段。")

            st.divider()
            st.markdown("### ✨ **深度分析清單**")

            for title, desc, ok, reason_text in results:
                status_cls = "status-pass" if ok else "status-fail"
                status_txt = "通過" if ok else "未過"
                st.markdown(f"""
                    <div class="check-item">
                        <div class="check-content">
                            <div class="check-title">{title} - {desc}</div>
                            <div class="check-reason">{reason_text}</div>
                        </div>
                        <div class="{status_cls}">{status_txt}</div>
                    </div>
                """, unsafe_allow_html=True)
