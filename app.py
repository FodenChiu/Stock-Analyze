import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# 更新了網頁標題與圖示
st.set_page_config(page_title="股市短線評級 App", page_icon="⚡")
st.title("⚡ 專屬股市短線評級 - 強勢股掃描器")

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
    # 這裡未來可以串接真實 API，目前先給定測試數值
    mock_turnover = 9.5 
    mock_institutional_buy = 1500 
    return mock_turnover, mock_institutional_buy

if st.button("啟動評級，開始分析！"):
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
    
    # 確保資料格式正確
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
        
        # KD 指標
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

        # --- 9 大條件判定 ---
        st.subheader("📊 9 大短線指標檢驗報告")
        score = 0
        
        # 1. 周轉率 > 9%
        if turnover > 9.0:
            st.success(f"✅ 1. 週轉率 > 9% (目前: {turnover}%)")
            score += 1
        else:
            st.error(f"❌ 1. 週轉率未達 9% (目前: {turnover}%)")
            
        # 2. KD 黃金交叉
        if float(today['K']) > float(today['D']) and float(yesterday['K']) <= float(yesterday['D']):
            st.success("✅ 2. KD 呈現黃金交叉")
            score += 1
        else:
            st.error(f"❌ 2. KD 未黃金交叉 (目前 K:{float(today['K']):.1f}, D:{float(today['D']):.1f})")

        # 3. 均線上揚 (5, 10, 20MA皆大於昨日)
        if float(today['5MA']) > float(yesterday['5MA']) and float(today['10MA']) > float(yesterday['10MA']) and float(today['20MA']) > float(yesterday['20MA']):
            st.success("✅ 3. 均線全面上揚 (5T、10T、20T 皆大於昨日)")
            score += 1
        else:
            st.error("❌ 3. 均線尚未全面上揚")

        # 4. 籌碼買超
        if inst_buy > 0:
            st.success(f"✅ 4. 籌碼偏多：三大法人近期買超")
            score += 1
        else:
            st.error("❌ 4. 籌碼偏空：法人未見明顯買超")

        # 5. 股價大於季線扣抵
        if float(today['Close']) > float(df.iloc[-60]['Close']):
            st.success("✅ 5. 股價大於季線扣抵 (60MA趨勢向上)")
            score += 1
        else:
            st.error("❌ 5. 股價小於季線扣抵 (季線趨勢尚未翻揚)")

        # 6. MACD 黃金交叉
        if float(today['MACD_Hist']) > 0 and float(yesterday['MACD_Hist']) <= 0:
            st.success("✅ 6. MACD 呈現黃金交叉")
            score += 1
        else:
            st.error("❌ 6. MACD 尚未黃金交叉")

        # 7. 站穩 5T
        if float(today['Close']) > float(today['5MA']):
            st.success(f"✅ 7. 股價站穩 5T (目前股價大於 5日線 {float(today['5MA']):.2f})")
            score += 1
        else:
            st.error(f"❌ 7. 股價跌破 5T (目前 5日線為 {float(today['5MA']):.2f})")

        # 8. 站穩 10T
        if float(today['Close']) > float(today['10MA']):
            st.success(f"✅ 8. 股價站穩 10T (目前股價大於 10日線 {float(today['10MA']):.2f})")
            score += 1
        else:
            st.error(f"❌ 8. 股價跌破 10T (目前 10日線為 {float(today['10MA']):.2f})")

        # 9. 站穩 20T
        if float(today['Close']) > float(today['20MA']):
            st.success(f"✅ 9. 股價站穩 20T (目前股價大於 20日線 {float(today['20MA']):.2f})")
            score += 1
        else:
            st.error(f"❌ 9. 股價跌破 20T (目前 20日線為 {float(today['20MA']):.2f})")

        # --- 結論 ---
        st.divider()
        st.subheader("💡 系統最終評級")
        if score >= 7:
            st.balloons()
            st.markdown(f"### 🔥 **S 級：強勢爆發！** (達成 {score}/9 項)")
            st.write("短線動能極強，均線與指標皆站在多方，是勝率極高的突破點！")
        elif score >= 4:
            st.markdown(f"### ⚠️ **A 級：多頭發酵中** (達成 {score}/9 項)")
            st.write("指標尚未完全到位，但已有轉強跡象，建議列入自選股密切觀察。")
        else:
            st.markdown(f"### ❄️ **B 級：弱勢或盤整** (達成 {score}/9 項)")
            st.write("短線動能不足，建議保留資金，耐心等待更好的標的。")
