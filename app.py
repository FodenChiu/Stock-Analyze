import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 全局介面設定 ---
st.set_page_config(
    page_title="台股短線起漲診斷器",
    page_icon="⚡",
    layout="wide"
)

# 嵌入客製化 CSS (保持黑金配色，並加入超華麗神來也特效所需的所有樣式)
st.markdown("""
<style>
    /* 1. 全局背景與字體 (黑金風) */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: "Microsoft JhengHei", sans-serif;
        background-color: #121212; /* 深黑色 */
        color: #EAEAEA;
    }
    
    /* 2. 標題與輸入框 */
    .main-title { color: #D4AF37; font-weight: bold; margin-bottom: 5px; }
    .input-label { font-size: 18px; font-weight: bold; color: #D4AF37; margin-bottom: 8px; }
    
    /* 3. 卡片與計分盤 */
    .metric-card, .check-item { background-color: #1E1E1E; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px; border: 1px solid #333; }
    .score-circle { background-color: #121212; border-radius: 50%; width: 130px; height: 130px; display: flex; align-items: center; justify-content: center; border: 10px solid #333; margin: 0 auto; box-shadow: 0 0 15px rgba(212, 175, 55, 0.2); }
    .score-text { font-size: 42px; font-weight: bold; color: #D4AF37; }
    
    /* 4. 金色按鈕 */
    .stButton > button { background-color: #D4AF37 !important; color: #121212 !important; font-weight: bold !important; border-radius: 8px !important; transition: background-color 0.3s !important; }
    .stButton > button:hover { background-color: #F8D06B !important; }
    
    /* 5. 指標清單與狀態 */
    .check-title { font-weight: bold; color: #EAEAEA; font-size: 16px; }
    .check-reason { color: #AAA; font-size: 13.5px; margin-top: 6px; line-height: 1.4; }
    .status-pass { background-color: #1A3E2A; color: #2DCC70; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; border: 1px solid #2DCC70; }
    .status-fail { background-color: #3E1A1A; color: #E74C3C; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; border: 1px solid #E74C3C; }
    
    /* 深色輸入框 */
    input[data-testid="stTextInput"] { background-color: #1E1E1E !important; color: #EAEAEA !important; border: 1px solid #333 !important; }
    input[data-testid="stTextInput"]::placeholder { color: #777 !important; }
    
    /* --- 🌸 6. 核心：神來也「槓上開花」復刻特效 (買進爆炸) 🌸 --- */
    
    /* 爆炸特效容器 (覆蓋全螢幕) */
    .buy-blast-container {
        position: fixed; top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: radial-gradient(circle, rgba(231, 76, 60, 0.1) 0%, rgba(12, 12, 12, 0.9) 70%, rgba(12, 12, 12, 1) 100%); /* 深紅暈光底 */
        display: flex; align-items: center; justify-content: center;
        z-index: 1000; pointer-events: none; /* 不影響點擊 */
        opacity: 0; animation: blast-fade-in 0.5s ease-out forwards, blast-fade-out 0.5s ease-in 2.5s forwards; /* 整體淡入淡出 */
    }
    
    /* 金屬反光「買進」爆炸文字 (復刻金屬質感與紅暈) */
    @keyframes metallic-反光 {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    .buy-blast-text {
        font-size: 10rem;
        font-weight: 900;
        background: linear-gradient(90deg, #FAD02E, #F8D06B, #FAD02E); /* 金屬色漸層 */
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        color: #F8D06B; /* 備用金色 */
        animation: metallic-反光 2s linear infinite, blast-text-boom 0.3s ease-out forwards; /* 文字爆炸與反光 */
        letter-spacing: 20px;
        text-shadow: 0 0 30px rgba(255, 0, 0, 0.8), 0 0 60px rgba(12, 12, 12, 0.3), 0 0 100px rgba(212, 175, 55, 0.5); /* 金紅櫻花暈 */
    }
    
    /* 特效容器淡入淡出動畫 */
    @keyframes blast-fade-in { 0% { opacity: 0; } 100% { opacity: 1; } }
    @keyframes blast-fade-out { 0% { opacity: 1; } 100% { opacity: 0; visibility: hidden; } }
    
    /* 文字爆炸出現動畫 (砰！的放大) */
    @keyframes blast-text-boom {
        0% { transform: scale(0.1); opacity: 0; }
        30% { transform: scale(1.4); opacity: 1; }
        50% { transform: scale(1); }
        100% { transform: scale(1); opacity: 1; }
    }
    
    /* 🌸 櫻花樹枝 (復刻神來也兩側櫻花枝) 🌸 */
    .cherry-branch {
        position: absolute; width: 300px; height: 300px;
        background-image: url('https://img.pixers.pics/pho(s3:700/PI/91/97/99/700_PI919799_4e8677c77f0a8c2d5d85d7b5b5c96030_5b8a05a10f63a_w5b8a05a10f63b.png)'); /* 實體櫻花樹枝圖片 (選用最乾淨的) */
        background-size: contain; background-repeat: no-repeat;
        opacity: 0; animation: cherry-fade-in 0.5s ease-out 0.2s forwards; /* 櫻花樹枝淡入 */
    }
    .cherry-branch-left { top: 50px; left: -100px; transform: rotate(40deg); } /* 左上枝 */
    .cherry-branch-right { bottom: 50px; right: -100px; transform: scaleX(-1) rotate(-40deg); } /* 右下枝，並水平翻轉 */
    
    @keyframes cherry-fade-in { 0% { opacity: 0; } 100% { opacity: 0.8; } }
    
    /* 🌸 櫻花飄落 (復刻飄落的櫻花辦) 🌸 */
    @keyframes cherry-fall {
        0% { transform: translate(0, -10px) rotate(0); }
        25% { transform: translate(-10px, 25vh) rotate(90deg); }
        50% { transform: translate(10px, 50vh) rotate(180deg); }
        75% { transform: translate(-5px, 75vh) rotate(270deg); }
        100% { transform: translate(0, 100vh) rotate(360deg); }
    }
    .cherry-petal {
        position: absolute; width: 10px; height: 10px;
        background-color: #F8BBD0; /* 淡粉色花瓣 */
        border-radius: 50%;
        animation: cherry-fall 5s linear infinite; /* 飄落 */
    }
</style>
""", unsafe_allow_html=True)

# --- 頂部標題與輸入 ---
st.markdown('<h1 class="main-title">⚡ 台股短線起漲點診斷</h1>', unsafe_allow_html=True)
st.markdown('<p class="input-label">📍 請輸入台股代號 (上市櫃均可)</p>', unsafe_allow_html=True)
stock_id = st.text_input("label_hidden", value="", label_visibility="collapsed", placeholder="請輸入代號 (例如: 2330, 8069...)")

# 分析按鈕
analyze_btn = st.button("🚀 啟動深度診斷")

with st.expander("📖 查看評分權重說明"):
    st.write("""
    本系統採用 **100% 加權計分邏輯**：
    * **權重 20%：** KD 低檔黃叉、5/10/20T 均線多頭、量增紅K
    * **權重 10%：** 週轉率 > 9%
    * **權重 5%：** 季線趨勢、MACD 翻紅、站穩各短期均線
    * **買入門檻：** 總分需達 **70%** 以上。
    """)

if analyze_btn:
    if not stock_id.strip():
        st.error("⚠️ 請先輸入股票代號再進行分析！")
    else:
        def fetch_data(sid):
            for ext in [".TW", ".TWO"]:
                t = yf.Ticker(f"{sid}{ext}")
                d = t.history(period="1y")
                if not d.empty: return d, t
            return None, None

        with st.spinner(f"正在深度分析 {stock_id} ..."):
            df, ticker = fetch_data(stock_id)
            
            if df is None:
                st.error(f"❌ 查無代號「{stock_id}」，請檢查輸入。")
            else:
                # 指標運算邏輯 (維持 17.0 穩定版)
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
                
                # 保留原邏輯...
                ok = turnover > 9.0; score += 10 if ok else 0
                results.append(("週轉率 > 9%", f"實測 {turnover:.2f}%", ok, "高週轉率代表換手積極，是短線強勢股配備。"))
                ok_kd = today['K'] > today['D'] and today['K'] < 60 and today['D'] < 55; score += 20 if ok_kd else 0
                results.append(("KD 低檔黃叉", f"K:{today['K']:.1f}, D:{today['D']:.1f}", ok_kd, "低位階交叉代表初次起漲，風險報酬佳。"))
                ok_ma = today['5MA'] > yest['5MA'] and today['10MA'] > yest['10MA'] and today['20MA'] > yest['20MA']; score += 20 if ok_ma else 0
                results.append(("均線全面上揚", "短中長期均線翻揚", ok_ma, "多頭共識形成，趨勢支撐力強。"))
                ok_60 = today['Close'] > df.iloc[-60]['Close']; score += 5 if ok_60 else 0
                results.append(("季線扣抵有過", "60MA 支撐判定", ok_60, "股價大於60日前價格，長線大底完成。"))
                ok_macd = (today['DIF'] - today['MACD']) > 0; score += 5 if ok_macd else 0
                results.append(("DIF-MACD > 0", "柱狀翻紅", ok_macd, "動能指標轉正，攻擊力加強。"))
                for ma, lbl in [('5MA','5T'),('10MA','10T'),('20MA','20T')]:
                    ok_st = today['Close'] > today[ma]; score += 5 if ok_st else 0
                    results.append((f"站穩 {lbl}", f"守住 {lbl} 支撐", ok_st, f"維持在 {lbl} 之上，強勢格局未破。"))
                ok_vol = today['Volume'] > today['5VMA'] and today['Close'] > today['Open']; score += 20 if ok_vol else 0
                results.append(("量增紅K", "實體放量攻擊", ok_vol, "量大代表主力介入，買盤掌握主導權。"))

                # --- 🌸 核心：當分數達標時，觸發神來也櫻花爆炸特效 🌸 ---
                if score >= 70:
                    st.markdown(f"""
                        <div class="buy-blast-container">
                            <div class="buy-blast-text">買進</div>
                            <div class="cherry-branch cherry-branch-left"></div> /* 左上枝 */
                            <div class="cherry-branch cherry-branch-right"></div> /* 右下枝 */
                            
                            /* 🌸 生成櫻花飘落花辦 (手動生成幾個) 🌸 */
                            <div class="cherry-petal" style="left: 10vw; animation-delay: 0.1s; animation-duration: 5.2s;"></div>
                            <div class="cherry-petal" style="left: 25vw; animation-delay: 0.3s; animation-duration: 4.8s;"></div>
                            <div class="cherry-petal" style="left: 40vw; animation-delay: 0.5s; animation-duration: 5.5s;"></div>
                            <div class="cherry-petal" style="left: 55vw; animation-delay: 0.7s; animation-duration: 5.0s;"></div>
                            <div class="cherry-petal" style="left: 70vw; animation-delay: 0.9s; animation-duration: 4.6s;"></div>
                            <div class="cherry-petal" style="left: 85vw; animation-delay: 1.1s; animation-duration: 5.3s;"></div>
                        </div>
                    """, unsafe_allow_html=True)

                # --- 顯示報告介面 ---
                col_sc, col_det = st.columns([1, 2])
                with col_sc:
                    c = "#2DCC70" if score >= 70 else "#E74C3C" if score < 40 else "#F1C40F"
                    st.markdown(f'<div class="score-circle" style="border-color:{c}"><div class="score-text">{score}</div></div>', unsafe_allow_html=True)
                    st.markdown(f"<p style='text-align:center; color:{c}; font-weight:bold; margin-top:10px;'>模擬診斷總分</p>", unsafe_allow_html=True)
                
                with col_det:
                    st.markdown(f"## {stock_id} 模擬診斷報告")
                    st.write(f"當前收盤：**{today['Close']:.2f} 元**")
                    if score >= 70: st.success("🎯 **偵測到高勝率訊號**：建議納入參考。")
                    elif score >= 50: st.warning("⚠️ **動能累積中**：需補量或等待到位。")
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
