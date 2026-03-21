import streamlit as st
import requests
import pandas as pd
import ta
import datetime

# ==========================================
# 1. 網頁介面與基礎設定
# ==========================================
st.set_page_config(page_title="台股飆股雷達 (百大評級版)", page_icon="🚀", layout="wide")
st.title("🚀 台股自動選股機器人 (滿分 100 評級)")
st.markdown("結合 **技術面 (KD/均線/MACD/量能)** 與 **籌碼面 (土洋雙打)** 的精準打擊系統。")

# 讓使用者在網頁輸入 Token (更安全)
FINMIND_TOKEN = st.text_input("🔑 請輸入你的 FinMind Token (必填):", type="password")
TARGET_DATE = datetime.date.today().strftime("%Y-%m-%d")

def get_stock_list():
    """【第一層】精確產業正面表列"""
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": "TaiwanStockInfo", "token": FINMIND_TOKEN}
    try:
        resp = requests.get(url, params=params).json()
        df = pd.DataFrame(resp.get('data', []))
        if df.empty: return []
        df = df[(df['type'].isin(['twse', 'tpex'])) & (df['stock_id'].str.len() == 4)]
        df = df[df['stock_id'].str.isdigit() & (~df['stock_id'].str.startswith('0'))]
        df = df[~df['stock_name'].str.endswith('KY')]
        
        target_industries = [
            '半導體業', '電腦及週邊設備業', '電子零組件業', '通信網路業', 
            '光電業', '其他電子業', '電子通路業', '資訊服務業', 
            '生技醫療業', '電機機械', '金融業', '電子商務', '綠能環保'
        ]
        df = df[df['industry_category'].str.contains('|'.join(target_industries), na=False)]
        exclude_keywords = ['遊戲', '文化創意', '貿易', '百貨', '觀光', '居家', '生活']
        df = df[~df['industry_category'].str.contains('|'.join(exclude_keywords), na=False)]
        return df[['stock_id', 'stock_name']].values.tolist()
    except: return []

# 使用 Streamlit 內建快取，取代原本的硬碟存檔
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(sid, dataset_name):
    url = "https://api.finmindtrade.com/api/v4/data"
    start = (datetime.date.today() - datetime.timedelta(days=120)).strftime("%Y-%m-%d")
    params = {"dataset": dataset_name, "data_id": sid, "start_date": start, "token": FINMIND_TOKEN}
    try:
        data = requests.get(url, params=params).json().get('data', [])
        if not data: return None
        return pd.DataFrame(data)
    except: return None

def calculate_master_score(sid, df_p):
    """依照滿分 100 評級邏輯進行計分"""
    df = df_p.sort_values('date').reset_index(drop=True)
    stoch = ta.momentum.StochasticOscillator(high=df['max'], low=df['min'], close=df['close'], window=9)
    df['K'], macd = stoch.stoch(), ta.trend.MACD(close=df['close'])
    df['MACD_hist'] = macd.macd_diff()
    df['ma5'], df['ma10'], df['ma20'] = df['close'].rolling(5).mean(), df['close'].rolling(10).mean(), df['close'].rolling(20).mean()
    
    td, yd, yyd, yyyd = df.iloc[-1], df.iloc[-2], df.iloc[-3], df.iloc[-4]
    score = 0
    tags = []

    # 1. KD 位階
    k = td['K']
    if 30 <= k <= 45: score += 25; tags.append(f"KD({round(k,1)})[+25]")
    elif 46 <= k <= 65: score += 20; tags.append(f"KD({round(k,1)})[+20]")
    elif 66 <= k <= 70: score += 10; tags.append(f"KD({round(k,1)})[+10]")
    elif 71 <= k <= 75: score += 5; tags.append(f"KD({round(k,1)})[+5]")
    elif k > 80: tags.append("KD過熱[0]")
    elif k < 30: tags.append("KD不足[0]")

    # 2. 量能
    v0, v1, v2, v3 = td['Trading_Volume'], yd['Trading_Volume'], yyd['Trading_Volume'], yyyd['Trading_Volume']
    if v0 > (v1 + v2 + v3): tags.append("竭盡爆量[0]")
    elif v0 > v1 > v2: score += 20; tags.append("量能逐步增加[+20]")
    elif v0 > v1 * 1.5: score += 15; tags.append("逐步爆量[+15]")

    # 3. 均線
    pairs = 0
    if td['close'] > td['ma5'] and td['ma5'] > yd['ma5']: pairs += 1
    if td['close'] > td['ma10'] and td['ma10'] > yd['ma10']: pairs += 1
    if td['close'] > td['ma20'] and td['ma20'] > yd['ma20']: pairs += 1
    if pairs == 3: score += 15; tags.append("三支撐+翻揚[+15]")
    elif pairs == 2: score += 10; tags.append("雙支撐+翻揚[+10]")
    elif pairs == 1: score += 5; tags.append("單支撐+翻揚[+5]")

    # 4. MACD & 季線
    if td['MACD_hist'] > 0 and td['MACD_hist'] > yd['MACD_hist']: score += 10; tags.append("MACD翻紅[+10]")
    if len(df) > 60 and td['close'] > df['close'].iloc[-61]: score += 5; tags.append("季線向上[+5]")

    turnover = 0
    if score >= 30:
        di = fetch_data(sid, "TaiwanStockInstitutionalInvestorsBuySell")
        if di is not None and not di.empty:
            di_filtered = di[di['name'].isin(['Foreign_Investor', 'Investment_Trust'])]
            if not di_filtered.empty:
                daily_net = di_filtered.groupby('date').apply(lambda x: x['buy'].sum() - x['sell'].sum())
                if len(daily_net) >= 4:
                    net0, net1, net2, net3 = daily_net.iloc[-1], daily_net.iloc[-2], daily_net.iloc[-3], daily_net.iloc[-4]
                    if net0 < 0 and abs(net0) > (max(0, net1) + max(0, net2) + max(0, net3)): tags.append("土洋大賣[0]")
                    elif net0 > 0 and net1 > 0 and net2 > 0: score += 20; tags.append("土洋連買[+20]")
                    elif net0 > 0: score += 15; tags.append("土洋增持[+15]")
                    elif net0 == 0: score += 10; tags.append("土洋持平[+10]")
                    elif net0 < 0: score += 5; tags.append("土洋遞減[+5]")

        ds = fetch_data(sid, "TaiwanStockShareholdersResidue")
        if ds is not None and not ds.empty:
            issued = ds.iloc[-1]['numberOfSharesIssued']
            turnover = (td['Trading_Volume'] / issued) * 100
            if 7 <= turnover <= 10: score += 5; tags.append("週轉7~10%[+5]")
            elif (2 <= turnover < 7) or (11 <= turnover <= 15): score += 3; tags.append("週轉達標[+3]")
            elif (1 < turnover < 2) or (15 < turnover <= 20): score += 1; tags.append("週轉微熱[+1]")

    return score, tags, td, turnover

# ==========================================
# 2. 執行主程式 (UI 互動區)
# ==========================================
if st.button("開始掃描"):
    if not FINMIND_TOKEN:
        st.error("請先在上方輸入你的 FinMind Token！")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        status_text.text("正在抓取符合產業條件的股票名單...")
        stocks = get_stock_list()
        
        if not stocks:
            st.error("找不到名單，可能是 Token 錯誤或連線問題。")
        else:
            res_list = []
            total = len(stocks)
            
            for i, (sid, sname) in enumerate(stocks):
                status_text.text(f"掃描進度：[{i+1}/{total}] 正在分析 {sid} {sname}...")
                progress_bar.progress((i + 1) / total)
                
                dp = fetch_data(sid, "TaiwanStockPrice")
                if dp is not None and len(dp) > 65 and dp.iloc[-1]['Trading_Volume'] >= 5000000:
                    score, tags, td, turn = calculate_master_score(sid, dp)
                    
                    if score >= 60:
                        res_list.append({
                            "股票": f"{sid} {sname}", 
                            "總分": score, 
                            "收盤價": td['close'], 
                            "週轉率(%)": round(turn, 2), 
                            "今日張數": int(td['Trading_Volume']/1000),
                            "得分細節": " | ".join(tags)
                        })
            
            status_text.text("✅ 掃描完成！")
            
            if res_list:
                df_f = pd.DataFrame(res_list).sort_values('總分', ascending=False)
                
                # 在網頁上展示表格
                st.success(f"發現 {len(res_list)} 檔 60 分以上的潛力股！")
                st.dataframe(df_f, use_container_width=True)
                
                # 提供 CSV 下載按鈕 (編碼為 utf-8-sig 以支援 Excel 中文)
                csv = df_f.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 下載完整報告 (CSV)",
                    data=csv,
                    file_name=f"台股評級報告_{TARGET_DATE}.csv",
                    mime="text/csv",
                )
            else:
                st.warning("今日掃描完畢，暫無符合 60 分以上的高共振標的。")
