import requests
import pandas as pd
import ta
import os
import datetime

# ==========================================
# 1. 參數設定區 (請務必在此填入你的 Token)
# ==========================================
FINMIND_TOKEN = "你的_TOKEN_貼在這裡" 
TARGET_DATE = datetime.date.today().strftime("%Y-%m-%d")

# 自動偵測桌面快取路徑
HOME = os.path.expanduser("~")
DESKTOP = os.path.join(HOME, "Desktop")
if not os.path.exists(DESKTOP): DESKTOP = os.path.join(HOME, "OneDrive", "桌面")
CACHE_DIR = os.path.join(DESKTOP, "Stock_Data", TARGET_DATE)
if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)

def get_stock_list():
    """【第一層】精確產業正面表列"""
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": "TaiwanStockInfo", "token": FINMIND_TOKEN}
    try:
        resp = requests.get(url, params=params).json()
        df = pd.DataFrame(resp['data'])
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

def fetch_or_load_data(sid, dataset_name):
    """【快取功能】優先讀取本地 CSV"""
    file_path = os.path.join(CACHE_DIR, f"{sid}_{dataset_name}.csv")
    if os.path.exists(file_path): return pd.read_csv(file_path)
    
    url = "https://api.finmindtrade.com/api/v4/data"
    start = (datetime.date.today() - datetime.timedelta(days=120)).strftime("%Y-%m-%d")
    params = {"dataset": dataset_name, "data_id": sid, "start_date": start, "token": FINMIND_TOKEN}
    try:
        data = requests.get(url, params=params).json().get('data', [])
        if not data: return None
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False)
        return df
    except: return None

def calculate_master_score(sid, df_p):
    """依照滿分 100 評級邏輯進行計分"""
    df = df_p.sort_values('date').reset_index(drop=True)
    
    stoch = ta.momentum.StochasticOscillator(high=df['max'], low=df['min'], close=df['close'], window=9)
    df['K'], macd = stoch.stoch(), ta.trend.MACD(close=df['close'])
    df['MACD_hist'] = macd.macd_diff()
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    
    td, yd, yyd, yyyd = df.iloc[-1], df.iloc[-2], df.iloc[-3], df.iloc[-4]
    score = 0
    tags = []

    # 1. KD 位階 (25分) + 高檔鈍化提醒
    k = td['K']
    if 30 <= k <= 45: score += 25; tags.append(f"KD({round(k,1)})[+25]")
    elif 46 <= k <= 65: score += 20; tags.append(f"KD({round(k,1)})[+20]")
    elif 66 <= k <= 70: score += 10; tags.append(f"KD({round(k,1)})[+10]")
    elif 71 <= k <= 75: score += 5; tags.append(f"KD({round(k,1)})[+5]")
    elif k > 80: tags.append(f"KD>80(留意高檔鈍化與量能)[0]")
    elif k < 30: tags.append(f"KD<30(動能不足)[0]")

    # 2. 近三天量能 (20分)
    v0, v1, v2, v3 = td['Trading_Volume'], yd['Trading_Volume'], yyd['Trading_Volume'], yyyd['Trading_Volume']
    if v0 > (v1 + v2 + v3):
        tags.append("量大於前三日總和[0]")
    elif v0 > v1 and v1 > v2:
        score += 20; tags.append("量能逐步增加[+20]")
    elif v0 > v1 * 1.5:  
        score += 15; tags.append("逐步爆量[+15]")

    # 3. 均線型態 (15分)
    pairs = 0
    if td['close'] > td['ma5'] and td['ma5'] > yd['ma5']: pairs += 1
    if td['close'] > td['ma10'] and td['ma10'] > yd['ma10']: pairs += 1
    if td['close'] > td['ma20'] and td['ma20'] > yd['ma20']: pairs += 1
    
    if pairs == 3: score += 15; tags.append("三支撐+三翻揚[+15]")
    elif pairs == 2: score += 10; tags.append("雙支撐+雙翻揚[+10]")
    elif pairs == 1: score += 5; tags.append("單支撐+單翻揚[+5]")

    # 4. MACD (10分)
    if td['MACD_hist'] > 0 and td['MACD_hist'] > yd['MACD_hist']:
        score += 10; tags.append("MACD翻紅[+10]")

    # 5. 季線趨勢 (5分)
    if len(df) > 60:
        if td['close'] > df['close'].iloc[-61]: 
            score += 5; tags.append("季線趨勢向上[+5]")

    # --- 籌碼與週轉率：初步技術面 > 30 分才深挖 API ---
    turnover = 0
    if score >= 30:
        # 6. 土洋籌碼 (外資+投信) (20分)
        di = fetch_or_load_data(sid, "TaiwanStockInstitutionalInvestorsBuySell")
        if di is not None and not di.empty:
            # 篩選外資與投信，並按日期加總每日淨買賣
            di_filtered = di[di['name'].isin(['Foreign_Investor', 'Investment_Trust'])]
            if not di_filtered.empty:
                daily_net = di_filtered.groupby('date').apply(lambda x: x['buy'].sum() - x['sell'].sum())
                if len(daily_net) >= 4:
                    net0, net1, net2, net3 = daily_net.iloc[-1], daily_net.iloc[-2], daily_net.iloc[-3], daily_net.iloc[-4]
                    
                    if net0 < 0 and abs(net0) > (max(0, net1) + max(0, net2) + max(0, net3)):
                        tags.append("土洋大賣勝前三日[0]")
                    elif net0 > 0 and net1 > 0 and net2 > 0:
                        score += 20; tags.append("土洋連續買超[+20]")
                    elif net0 > 0:
                        score += 15; tags.append("土洋持股增加[+15]")
                    elif net0 == 0:
                        score += 10; tags.append("土洋持平[+10]")
                    elif net0 < 0:
                        score += 5; tags.append("土洋遞減[+5]")

        # 7. 週轉率 (5分)
        ds = fetch_or_load_data(sid, "TaiwanStockShareholdersResidue")
        if ds is not None and not ds.empty:
            issued = ds.iloc[-1]['numberOfSharesIssued']
            turnover = (td['Trading_Volume'] / issued) * 100
            if 7 <= turnover <= 10: score += 5; tags.append("週轉率7~10%[+5]")
            elif (2 <= turnover < 7) or (11 <= turnover <= 15): score += 3; tags.append("週轉率2~6%或11~15%[+3]")
            elif (1 < turnover < 2) or (15 < turnover <= 20): score += 1; tags.append("週轉率>1%或15~20%[+1]")
            elif turnover > 20 or turnover <= 1: tags.append("週轉率過熱或冷清[0]")

    return score, tags, td, turnover

def main():
    print(f"--- 啟動【法人雙打+百分配分版】選股程式 ---")
    print(f"📁 快取目錄：{CACHE_DIR}")
    
    stocks = get_stock_list()
    if not stocks: return
    
    res_list = []
    total = len(stocks)
    for i, (sid, sname) in enumerate(stocks):
        print(f"[{i+1}/{total}] 評分中: {sid} {sname}...", end="\r")
        
        dp = fetch_or_load_data(sid, "TaiwanStockPrice")
        
        # 門檻：成交張數 >= 5000 張且資料充足
        if dp is not None and len(dp) > 65 and dp.iloc[-1]['Trading_Volume'] >= 5000000:
            score, tags, td, turn = calculate_master_score(sid, dp)
            
            # 目前設定為 60 分為及格門檻列出報告
            if score >= 60:
                res_list.append({
                    "股票": f"{sid} {sname}", "綜合得分": score, "得分細節": " | ".join(tags),
                    "收盤價": td['close'], "週轉率%": round(turn, 2), "今日成交量(張)": int(td['Trading_Volume']/1000)
                })
                print(f"\n🎯 達標: {sid} {sname} (總分: {score})")

    if res_list:
        df_f = pd.DataFrame(res_list).sort_values('綜合得分', ascending=False)
        p = os.path.join(DESKTOP, f"滿分百大評級報告_{TARGET_DATE}.xlsx")
        df_f.to_excel(p, index=False)
        print(f"\n\n✅ 任務完成！已產出 60分以上名單。報告已存至桌面：{p}")
    else:
        print("\n\n😩 掃描完成，今日暫無符合 60 分以上標的。")

if __name__ == "__main__":
    main()
