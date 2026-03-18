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

# 嵌入客製化 CSS (修正了 unsafe_allow_html 的錯誤字)
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
    .status-pass { background-color: #E6F7ED; color: #1A9F63; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; }
    .status-fail { background-color: #FEECEB; color: #E03E3E; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 輸入區域 ---
st.title("⚡ 專屬股市短線教練")
col_input, _ = st.columns([1, 2])
with col_input:
    stock_id = st.text_input("輸入台股代號 (例: 1711 或 8069)", "1711")
    analyze_btn = st.button("🚀 開始分析")

if analyze_btn:
    def get_stock_data(sid):
        ticker = yf.Ticker(f"{sid}.TW")
        df = ticker.history(period="1y")
        if not df.empty: return df, ticker
        ticker = yf.Ticker(f"{sid}.TWO")
        df = ticker.history(period="1y")
        if not df.empty: return df, ticker
        return None, None

    with st.spinner(f"正在診斷 {stock_id}..."):
        df, ticker = get_stock_data(stock_id)
        
        if df is None:
            st.error(f"❌ 找不到代號「{stock_id}」。")
        else:
            # 運算指標
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
            yesterday = df.iloc[-2]
            shares = ticker.info.get('sharesOutstanding', 0)
            real_turnover = (today['Volume'] / shares * 100) if shares else 0
            
            # 計分邏輯
            total_score = 0
            results = []
            
            # 1. 周轉率 (10%)
            ok = real_turnover > 9.0
            if ok: total_score += 10
            results.append(("週轉率 > 9%", f"實測: {real_turnover:.2f}%", ok))
            
            # 2. KD (20%)
            ok = today['K'] > today['D'] and today['K'] < 60 and today['D'] < 55
            if ok: total_score += 20
            results.append(("KD 低檔黃叉", f"K: {today['K']:.1f}", ok))
            
            # 3. 均線 (20%)
            ok = today['5MA'] > yesterday['5MA'] and today['10MA'] > yesterday['10MA'] and today['20MA'] > yesterday['20MA']
            if ok: total_score += 20
            results.append(("均線全面上揚", "5/10/20T 皆向上", ok))
            
            # 4. 季線扣抵 (5%)
            ok = today['Close'] > df.iloc[-60]['Close']
            if ok: total_score += 5
            results.append(("大於季線扣抵", "60MA 趨勢向上", ok))
            
            # 5. MACD (5%)
            ok = (today['DIF'] - today['MACD']) > 0
            if ok: total_score += 5
            results.append(("DIF-MACD > 0", "紅柱狀態", ok))
            
            # 6-8. 站穩 (各 5%)
            for ma, label in [('5MA', '5T'), ('10MA', '10T'), ('20MA', '20T')]:
                ok = today['Close'] > today[ma]
                if ok: total_score += 5
                results.append((f"站穩 {label}", f"收盤 > {label}", ok))
            
            # 9. 量能 (20%)
            ok = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']
            if ok: total_score += 20
            results.append(("量增紅K", "動能充足", ok))

            # --- 顯示漂亮介面 ---
            col_left, col_right = st.columns([3, 1])
            with col_right:
                color = "#1A9F63" if total_score >= 70 else "#E0E0E0"
                st.markdown(f'<div class="score-circle" style="border-color:{color}"><div class="score-text">{total_score}</div></div>', unsafe_allow_html=True)
            
            with col_left:
                st.markdown(f"### {stock_id} 診斷結果")
                st.write(f"今日收盤：**{today['Close']:.2f} 元**")
                if total_score >= 70: st.success("🔥 值得買入！")
                else: st.info("⚪ 繼續觀察")

            for title, desc, ok in results:
                status_cls = "status-pass" if ok else "status-fail"
                status_txt = "通過" if ok else "未過"
                st.markdown(f'<div class="check-item"><div><b>{title}</b><br><small>{desc}</small></div><div class="{status_cls}">{status_txt}</div></div>', unsafe_allow_html=True)

            if total_score >= 70: st.balloons()
