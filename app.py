import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 🚀 全局介面設定 ---
st.set_page_config(
    page_title="台股短線起漲診斷器",
    page_icon="⚡",
    layout="wide"
)

# 嵌入客製化 CSS (優化欄位辨識度)
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        font-family: "Microsoft JhengHei", sans-serif;
        background-color: #F8F9FA;
    }
    .main-title { color: #1E3A8A; font-weight: bold; margin-bottom: 5px; }
    .input-label { font-size: 18px; font-weight: bold; color: #333; margin-bottom: 8px; }
    .score-circle {
        background-color: #FFFFFF;
        border-radius: 50%;
        width: 130px;
        height: 130px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 10px solid #E0E0E0;
        margin: 0 auto;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .score-text { font-size: 42px; font-weight: bold; color: #1E3A8A; }
    .check-item {
        background-color: #FFFFFF;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 18px;
        border-radius: 12px;
        margin-bottom: 12px;
        border-left: 6px solid #EEE;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .check-content { flex: 1; }
    .check-title { font-weight: bold; color: #333; font-size: 16px; }
    .check-reason { color: #666; font-size: 13.5px; margin-top: 6px; line-height: 1.4; }
    .status-pass { background-color: #E6F7ED; color: #1A9F63; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; }
    .status-fail { background-color: #FEECEB; color: #E03E3E; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; }
    .disclaimer { font-size: 12px; color: #999; text-align: center; margin-top: 50px; }
</style>
""", unsafe_allow_html=True)

# --- 頂部標題 ---
st.markdown('<h1 class="main-title">⚡ 台股短線起漲點診斷</h1>', unsafe_allow_html=True)

# --- 🎯 關鍵修改：將提示文字移到欄位上方，方便辨識 ---
st.markdown('<p class="input-label">📍 請輸入台股代號 (上市櫃均可)</p>', unsafe_allow_html=True)
stock_id = st.text_input("label_hidden", "1711", label_visibility="collapsed", placeholder="例如: 2330, 8069, 1711...")

# 按鈕稍微加寬，更有啟動感
analyze_btn = st.button("🚀 啟動深度診斷", use_container_width=False)

with st.expander("📖 查看評分權重說明"):
    st.write("""
    本系統採用 **100% 加權計分邏輯**：
    * **權重 20%：** KD 低檔黃叉、5/10/20T 均線多頭、量增紅K
    * **權重 10%：** 週轉率 > 9%
    * **權重 5%：** 季線趨勢、MACD 翻紅、站穩各短期均線
    * **買入門檻：** 總分需達 **70%** 以上。
    """)

if analyze_btn:
    def fetch_data(sid):
        for ext in [".TW", ".TWO"]:
            t = yf.Ticker(f"{sid}{ext}")
            d = t.history(period="1y")
            if not d.empty: return d, t
        return None, None

    with st.spinner(f"正在分析 {stock_id} ..."):
        df, ticker = fetch_data(stock_id)
        
        if df is None:
            st.error(f"❌ 查無代號「{stock_id}」，請檢查輸入。")
        else:
            # 運算指標邏輯 (維持 14.0 的權重與分析內容)
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
            
            today, yest = df.iloc[-1], df.iloc[-2]
            shares = ticker.info.get('sharesOutstanding', 0)
            turnover = (today['Volume'] / shares * 100) if shares else 0
            
            score = 0
            results = []
            
            # 1. 週轉率 (10%)
            ok = turnover > 9.0; score += 10 if ok else 0
            results.append(("週轉率 > 9%", f"實測 {turnover:.2f}%", ok, "高週轉率代表換手積極，是短線強勢股的標準配備。"))
            
            # 2. KD (20%)
            ok = today['K'] > today['D'] and today['K'] < 60 and today['D'] < 55; score += 20 if ok else 0
            results.append(("KD 低檔黃叉", f"K:{today['K']:.1f}, D:{today['D']:.1f}", ok, "低位階交叉代表初次起漲，風險報酬比較佳。"))
            
            # 3. 均線 (20%)
            ok = today['5MA'] > yest['5MA'] and today['10MA'] > yest['10MA'] and today['20MA'] > yest['20MA']; score += 20 if ok else 0
            results.append(("均線全面上揚", "短中長期均線翻揚", ok, "多頭共識形成，趨勢支撐力道強。"))
            
            # 4. 季線扣抵 (5%)
            ok = today['Close'] > df.iloc[-60]['Close']; score += 5 if ok else 0
            results.append(("季線扣抵有過", "60MA 支撐判定", ok, "股價大於60日前價格，代表中長線大底已完成。"))
            
            # 5. MACD (5%)
            ok = (today['DIF'] - today['MACD']) > 0; score += 5 if ok else 0
            results.append(("DIF-MACD > 0", "MACD 柱狀翻紅", ok, "動能指標轉正，攻擊力道正在加強。"))
            
            for ma, lbl in [('5MA','5T'),('10MA','10T'),('20MA','20T')]:
                ok = today['Close'] > today[ma]; score += 5 if ok else 0
                results.append((f"站穩 {lbl}", f"守住 {lbl} 支撐", ok, f"維持在 {lbl} 之上，代表強勢格局未破。"))
            
            ok = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']; score += 20 if ok else 0
            results.append(("量增紅K", "實體放量攻擊", ok, "量大代表主力介入，紅K代表買盤掌握主導權。"))

            # --- 顯示報告介面 ---
            col_sc, col_det = st.columns([1, 2])
            with col_sc:
                c = "#1A9F63" if score >= 70 else "#DC2626" if score < 40 else "#F59E0B"
                st.markdown(f'<div class="score-circle" style="border-color:{c}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; color:{c}; font-weight:bold; margin-top:10px;'>模擬診斷總分</p>", unsafe_allow_html=True)
            
            with col_det:
                st.markdown(f"## {stock_id} 模擬診斷報告")
                st.write(f"當前收盤：**{today['Close']:.2f} 元**")
                if score >= 70: 
                    st.success("🎯 **偵測到高勝率訊號**：建議納入參考。")
                    st.balloons()
                elif score >= 50: st.warning("⚠️ **動能累積中**：需補量或等待 KD 交叉到位。")
                else: st.error("❄️ **指標弱勢**：目前動能不足。")

            st.markdown("### 🔍 詳細分析清單")
            for t, d, ok, r in results:
                s_cls = "status-pass" if ok else "status-fail"
                st.markdown(f"""
                    <div class="check-item">
                        <div class="check-content">
                            <div class="check-title">{t} ({d})</div>
                            <div class="check-reason"><b>教練分析：</b>{r}</div>
                        </div>
                        <div class="{s_cls}">{'通過' if ok else '未過'}</div>
                    </div>
                """, unsafe_allow_html=True)

st.markdown('<div class="disclaimer">⚠️ 免責聲明：本工具僅為技術指標分析用途，不構成投資建議。投資一定有風險。</div>', unsafe_allow_html=True)
