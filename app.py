import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 全局介面設定：復刻範例的乾淨專業風 ---
st.set_page_config(
    page_title="股市短線教練",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 嵌入客製化 CSS：調整字體、卡片樣式、計分盤樣式
st.markdown("""
<style>
    /* 調整整體字體與背景 */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: "Microsoft JhengHei", "Source Sans Pro", sans-serif;
        background-color: #F4F7F6; /* 微灰藍色背景 */
    }
    
    /* 客製化卡片樣式 (Card UI) */
    .metric-card, .check-item {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); /* 微妙陰影 */
        margin-bottom: 15px;
        border: 1px solid #EAEAEA;
    }
    
    /* 核心計分盤樣式 */
    .score-circle {
        background-color: #FFFFFF;
        border-radius: 50%;
        width: 120px;
        height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 8px solid #E0E0E0; /* 預設灰圈 */
        margin: 0 auto;
    }
    .score-text {
        font-size: 36px;
        font-weight: bold;
        color: #333;
    }
    .score-total {
        font-size: 16px;
        color: #777;
    }
    
    /* 指標檢查清單樣式 */
    .check-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px;
    }
    .check-title {
        font-weight: bold;
        font-size: 16px;
    }
    .check-desc {
        color: #666;
        font-size: 14px;
    }
    .status-badge {
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    .status-pass {
        background-color: #E6F7ED;
        color: #1A9F63; /* 綠色 */
    }
    .status-fail {
        background-color: #FEECEB;
        color: #E03E3E; /* 紅色 */
    }
</style>
""", unsafe_allow_stdio=True)

# --- 快速輸入區域 (設計得更精簡) ---
with st.container():
    col_input, _ = st.columns([1, 2])
    with col_input:
        stock_id = st.text_input("輸入台股代號 (例: 1711)", "1711", key="stock_input")
        analyze_btn = st.button("啟動教練，開始分析！", key="analyze_btn")

if analyze_btn:
    # 判斷上市櫃邏輯 (保留 11.0 的強大功能)
    def get_stock_data(sid):
        ticker = yf.Ticker(f"{sid}.TW")
        df = ticker.history(period="1y")
        if not df.empty: return df, ticker
        ticker = yf.Ticker(f"{sid}.TWO")
        df = ticker.history(period="1y")
        if not df.empty: return df, ticker
        return None, None

    with st.spinner(f"正在分析 {stock_id} 的數據..."):
        df, ticker = get_stock_data(stock_id)
        
        if df is None:
            st.error(f"❌ 找不到代號「{stock_id}」的數據，請確認。")
        else:
            # 1. 自動運算指標 (你的加權家法)
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
            
            # 週轉率計算
            shares = ticker.info.get('sharesOutstanding', 0)
            real_turnover = (today['Volume'] / shares * 100) if shares else 0
            
            # 2. 加權計分與細節 (依據你的比重)
            total_score = 0
            check_list = []
            
            # 周轉率 (10%)
            if real_turnover > 9.0: total_score += 10; status, badge = "✅ 值得買入", "status-pass"
            else: status, badge = "❌ 動能不足", "status-fail"
            check_list.append(("週轉率高 (週轉率爆發)", f"目前: {real_turnover:.2f}% (目標>9%)", status, badge))
            
            # KD (20%)
            k_val, d_val = float(today['K']), float(today['D'])
            if k_val > d_val and k_val < 60 and d_val < 55: total_score += 20; status, badge = "✅ 值得買入", "status-pass"
            else: status, badge = "❌ 失效的", "status-fail"
            check_list.append(("KD指標黃金交叉 (低檔翻揚)", f"目前 K:{k_val:.1f}, D:{d_val:.1f} (目標 K>D 且 K<60)", status, badge))
            
            # 均線 (20%)
            if today['5MA'] > yesterday['5MA'] and today['10MA'] > yesterday['10MA'] and today['20MA'] > yesterday['20MA']:
                total_score += 20; status, badge = "✅ 值得買入", "status-pass"
            else: status, badge = "❌ 失效的", "status-fail"
            check_list.append(("均線全面上揚 (多頭排列)", "5T、10T、20T均線數值大於昨日", status, badge))
            
            # 季線 (5%)
            if today['Close'] > df.iloc[-60]['Close']: total_score += 5; status, badge = "✅ 值得買入", "status-pass"
            else: status, badge = "❌ 失效的", "status-fail"
            check_list.append(("季線扣抵有過 (季MA趨勢向上)", "今日收盤價 > 60日前的收盤價", status, badge))
            
            # MACD (5%)
            if (today['DIF'] - today['MACD']) > 0: total_score += 5; status, badge = "✅ 值得買入", "status-pass"
            else: status, badge = "❌ 失效的", "status-fail"
            check_list.append(("MACD黃金交叉 (零軸之上)", "DIF線位於MACD線之上 (紅柱狀態)", status, badge))
            
            # 站穩 5/10/20T (各 5%)
            for ma_key, label, weight in [('5MA', '5T均線', 5), ('10MA', '10T均線', 5), ('20MA', '20T均線', 5)]:
                if today['Close'] > today[ma_key]: total_score += weight; status, badge = "✅ 值得買入", "status-pass"
                else: status, badge = "❌ 跌破支撐", "status-fail"
                check_list.append((f"站穩 {label} (短線支撐區)", f"今日收盤價大於 {label}", status, badge))
            
            # 量能 (20%)
            is_red = today['Close'] > today['Open']
            if today['Volume'] > today['5VMA'] and is_red: total_score += 20; status, badge = "✅ 值得買入", "status-pass"
            else: status, badge = "❌ 失效的", "status-fail"
            check_list.append(("量能健康爆發 (量增紅K)", "今日量大於5T均量且收紅K", status, badge))

            # --- 3. 呈現復刻介面 ---
            
            # 頂部狀態列：偵測結果與計分盤
            col_header, col_score = st.columns([3, 1])
            
            with col_header:
                # 依分數調整標題與狀態
                if total_score >= 70:
                    st.markdown("## 🎯 **偵測到值得買入訊號！**")
                    st.markdown("各種條件都符合波段起漲行情，具備高度攻擊動能。")
                else:
                    st.markdown("## ⚪ **持續觀察或暫不介入**")
                    st.markdown("指標尚未完全到位，動能或均線仍需確認。")
                
            with col_score:
                # 客製化復刻範例的計分圓圈
                circle_color = "#1A9F63" if total_score >= 70 else "#E0E0E0" # 綠色或灰色
                st.markdown(f"""
                    <div class="score-circle" style="border-color: {circle_color};">
                        <div>
                            <span class="score-text">{total_score}</span>
                            <span class="score-total">/100</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            st.divider()
            
            # 資產概覽與核心指標卡片 (卡片 UI)
            col_asset, col_tech = st.columns([1, 2])
            
            with col_asset:
                st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 24px; font-weight: bold; color: #111;">{stock_id} 台股</div>
                        <div style="font-size: 14px; color: #777;">{datetime.date.today().strftime("%Y/%m/%d")}</div>
                        <div style="font-size: 32px; font-weight: bold; color: #333; margin: 15px 0;">{today['Close']:.2f} 元</div>
                    </div>
                """, unsafe_allow_html=True)
                
            with col_tech:
                # 復刻範例的 5/10/20/60MA 指標卡片
                st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">核心均線狀態 (MA)</div>
                        <div style="display: flex; justify-content: space-between;">
                            <div>MA 5 (1W): <strong>{today['5MA']:.2f}</strong></div>
                            <div>MA 10 (2W): <strong>{today['10MA']:.2f}</strong></div>
                            <div>MA 20 (1M): <strong>{today['20MA']:.2f}</strong></div>
                            <div>MA 60 (季MA): <strong>{today['60MA']:.2f}</strong></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            st.divider()
            
            # 詳細評估清單 (清單 UI)
            st.markdown("### ✨ **詳細指標審查**")
            
            for title, desc, status_text, badge_class in check_list:
                st.markdown(f"""
                    <div class="check-item">
                        <div>
                            <div class="check-title">{title}</div>
                            <div class="check-desc">{desc}</div>
                        </div>
                        <div class="status-badge {badge_class}">{status_text}</div>
                    </div>
                """, unsafe_allow_html=True)

            if total_score >= 70:
                st.balloons()
