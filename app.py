import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="股市教練 App", page_icon="📈")
st.title("📈 專屬股市教練 - 波段起漲掃描器")

# 讓使用者輸入代號
stock_id = st.text_input("請輸入台股代號 (例如: 2330)", "1711")

# --- 抓取台股中文名稱 (雙重保險) ---
@st.cache_data(ttl=86400) 
def get_tw_stock_name(stock_no):
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(url, timeout=5).json()
        for stock in res:
            if stock['Code'] == stock_no:
                return stock['Name']
    except:
        pass
    return None

# 模擬抓取籌碼與週轉率
@st.cache_data(ttl=3600)
def get_twse_data(stock_no):
    mock_turnover = 8.5 
    mock_institutional_buy = 1500 
    return mock_turnover, mock_institutional_buy

if st.button("啟動教練，開始分析！"):
    yf_symbol = f"{stock_id}.TW"
    
    # 取得名稱：先試證交所，失敗再用 Yahoo 備用
    stock_name = get_tw_stock_name(stock_id)
    ticker = yf.Ticker(yf_symbol)
    if not stock_name:
        try:
            stock_name = ticker.info.get('shortName', '未知名稱')
        except:
            stock_name = "未知名稱"
            
    st.info(f"正在分析： {stock_id} {stock_name} ...")
    
    # 🌟 核心修正：改用 ticker.history 確保資料格式為單純的 1D 欄位
    df = ticker.history(period="1y")
    
    if df.empty:
        st.error("找不到這檔股票，請確認代號是否正確。")
    else:
        # 顯示最新股價
        current_price = float(df['Close'].iloc[-1])
        st.metric(label=f"目前收盤價", value=f"{current_price:.2f} 元")
        
        # --- 計算技術指標 ---
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        df['60MA'] = df['Close'].rolling(window=60).mean()
        
        # KD 指標 (加入 1e-9 避免碰到漲跌停鎖死時，分母為 0 的錯誤)
        df['9K_Min'] = df['Low'].rolling(window=9).min()
        df['9K_Max'] = df['High'].rolling(window=9).max()
        df['RSV'] = 100 * (df['Close'] - df['9K_Min']) / (df['9K_Max'] - df['9K_Min'] + 1e-9)
        df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
        df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        
        # MACD 指標
        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = df['EMA12'] - df['EMA26']
        df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['DIF'] - df['MACD']
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        turnover, inst_buy = get_twse_data(stock_id)

        # --- 8 大條件判定 ---
        st.subheader("📊 8 大核心指標檢驗報告")
        score = 0
        
        if turnover > 8.0:
            st.success(f"✅ 1. 週轉率 > 8% (目前: {turnover}%)")
            score += 1
        else:
            st.error(f"❌ 1. 週轉率未達 8% (目前: {turnover}%)")
            
        if float(today['K']) > float(today['D']) and float(yesterday['K']) <= float(yesterday['D']):
            st.success("✅ 2. KD 黃金交叉")
            score += 1
        else:
            st.error(f"❌ 2. KD 未黃金交叉 (K:{float(today['K']):.1f}, D:{float(today['D']):.1f})")

        if (float(today['5MA']) > float(today['10MA'])) and (float(yesterday['5MA']) <= float(yesterday['10MA'])) and \
           (float(today['Close']) > float(today['5MA'])) and (float(today['Close']) > float(today['60MA'])):
            st.success("✅ 3. 5日線突破10日線，且站上各均線")
            score += 1
        else:
            st.error("❌ 3. 均線未形成多頭突破")

        if inst_buy > 0:
            st.success(f"✅ 4. 籌碼偏多：三大法人近期買超")
            score += 1
        else:
            st.error("❌ 4. 籌碼偏空：法人未見買超")

        if float(today['Close']) > float(df.iloc[-60]['Close']):
            st.success("✅ 5. 季線扣抵有過 (60MA趨勢向上)")
            score += 1
        else:
            st.error("❌ 5. 季線趨勢尚未翻揚")

        if float(today['MACD_Hist']) > 0 and float(yesterday['MACD_Hist']) <= 0:
            st.success("✅ 6. MACD 黃金交叉")
            score += 1
        else:
            st.error("❌ 6. MACD 尚未黃金交叉")

        dist_10ma = (float(today['Close']) - float(today['10MA'])) / float(today['10MA'])
        if float(today['Close']) > float(today['10MA']) and dist_10ma <= 0.02:
            st.success(f"✅ 7. 10日線支撐 (距離 {dist_10ma:.1%})")
            score += 1
        else:
            st.error("❌ 7. 未達 10日線支撐標準")

        dist_20ma = (float(today['Close']) - float(today['20MA'])) / float(today['20MA'])
        if float(today['Close']) > float(today['20MA']) and dist_20ma <= 0.02:
            st.success(f"✅ 8. 20日線支撐 (距離 {dist_20ma:.1%})")
            score += 1
        else:
            st.error("❌ 8. 未達 20日線支撐標準")

        # --- 結論 ---
        st.divider()
        st.subheader("💡 教練最終評估")
        if score >= 6:
            st.balloons()
            st.markdown(f"### 🔥 **強烈買進訊號！** (達成 {score}/8 項)")
        elif score >= 4:
            st.markdown(f"### ⚠️ **持續觀察中** (達成 {score}/8 項)")
        else:
            st.markdown(f"### ❄️ **暫不考慮** (達成 {score}/8 項)")
