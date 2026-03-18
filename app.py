import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import datetime

# --- 🚀 核心設定：已自動填入你的 Gemini API Key ---
# ⚠️ 提醒：此為私人金鑰，請勿外流 ⚠️
GOOGLE_API_KEY = "你的_GEMINI_API_KEY_貼在這邊"
genai.configure(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="股市短線評級 7.0", page_icon="⚡", layout="wide")
st.title("⚡ 股市短線評級 - AI 視覺輔助版")

# --- 第一區：AI 視覺辨識名稱與籌碼 ---
st.subheader("📸 第一步：上傳【籌碼圖】或【技術圖】(辨識名稱與籌碼)")
uploaded_file = st.file_uploader("請上傳手機看盤截圖，我會自動幫你抓代號與籌碼數據", type=['png', 'jpg', 'jpeg'])

target_code = ""
target_name = ""
inst_3d_avg = 0
should_analyze = False # 控制是否自動執行分析

if uploaded_file:
    img = Image.open(uploaded_file)
    # 在網頁顯示圖片
    st.image(img, caption="已上傳截圖", width=400)
    
    # 建立一個進度指示器
    with st.spinner("AI 大腦正在盯著圖片看，努力辨識股票代號與籌碼數據..."):
        try:
            # 使用 gemini-1.5-flash 模型，速度最快
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # 給 AI 的精密指令，確保回傳資料格式正確
            prompt = "這是一張台灣股市截圖。請幫我找出三個關鍵資訊：1.股票代號 2.股票中文名稱 3.圖中顯示的【近三日法人買賣超張數的平均值】(或者是圖中最接近今日的3筆法人買賣超合計張數的平均)。請只回傳格式：代號,名稱,平均張數。例如：2337,旺宏,1500。如果是賣超，平均張數請加上負號(-)。若真的找不到籌碼資料，平均張數請回傳 0。"
            
            # 讓 AI 分析圖片
            response = model.generate_content([prompt, img])
            
            # 解析 AI 回傳的文字 (格式: 代號,名稱,平均張數)
            ai_result = response.text.strip().split(',')
            
            # 填入辨識結果
            target_code = ai_result[0]
            target_name = ai_result[1]
            inst_3d_avg = int(ai_result[2].replace('張', '').replace(',', ''))
            
            # 顯示辨識成功訊息
            st.success(f"✅ AI 辨識成功：**{target_code} {target_name}** | 近三日籌碼平均：**{inst_3d_avg:,} 張**")
            should_analyze = True # 辨識成功，設定為自動執行分析
            
        except Exception as e:
            st.error(f"❌ AI 辨識失敗，可能是圖片清晰度不夠或交易所資料尚未更新。錯誤訊息: {e}")
            should_analyze = False

st.divider()

# --- 第二區：程式自動運算 10 大技術指標 ---
if should_analyze and target_code:
    # 加上緩存機制，避免重複抓取
    @st.cache_data(ttl=3600)
    def get_stock_metrics(code, inst_avg):
        # 簡單起見，上市櫃後綴判斷保留在程式邏輯中，這裡預設 .TW
        yf_symbol = f"{code}.TW"
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="1y")
        
        if df.empty:
            return None
        
        # 1. 自動運算指標 (不靠圖片，靠程式抓最準)
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        df['60MA'] = df['Close'].rolling(window=60).mean()
        
        df['5VMA'] = df['Volume'].rolling(window=5).mean()
        df['10VMA'] = df['Volume'].rolling(window=10).mean()
        
        # KD 指標
        df['9L'], df['9H'] = df['Low'].rolling(window=9).min(), df['High'].rolling(window=9).max()
        df['RSV'] = 100 * (df['Close'] - df['9L']) / (df['9H'] - df['9L'] + 1e-9)
        df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
        df['D'] = df['K'].ewm(com=2, adjust=False).mean()
        
        # MACD 指標
        df['DIF'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        # 真實週轉率計算 (這部分你是最看重的，保留自動抓取)
        shares = ticker.info.get('sharesOutstanding', 0)
        today_volume = float(today['Volume'])
        if shares and shares > 0:
            real_turnover = (today_volume / shares) * 100
        else:
            real_turnover = 0 # 無法抓到則歸零
            
        return today, yesterday, real_turnover, df

    metrics_result = get_stock_metrics(target_code, inst_3d_avg)
    
    if metrics_result is None:
        st.error(f"❌ 找不到代號「{target_code}」的歷史數據，可能是新上市或代號有誤。")
    else:
        today, yesterday, real_turnover, df = metrics_result
        current_price = float(today['Close'])
        prev_close = float(yesterday['Close'])
        
        # 判斷今日是否漲停 (簡單粗略判斷 9.5% 以上)
        is_limit_up = (current_price - prev_close) / prev_close >= 0.095

        # 3. 呈現 10 大指標評級報告
        st.subheader(f"📊 {target_code} {target_name} 評級報告")
        st.metric(label=f"目前收盤價", value=f"{current_price:.2f} 元", delta="🔥 強勢漲停" if is_limit_up else None)
        
        score = 0
        details = []
        
        # --- 動能與籌碼 ---
        if real_turnover > 9.0:
            score += 1; details.append(f"✅ 1. 週轉率 > 9% (實測: {real_turnover:.2f}%)")
        else:
            details.append(f"❌ 1. 週轉率未達 9% (實測: {real_turnover:.2f}%)")
            
        # 🚀 法人籌碼 (AI 辨識版本)
        if inst_3d_avg > 0:
            score += 1; details.append(f"✅ 2. 籌碼偏多：近三日法人平均買超 {inst_3d_avg:,} 張")
        elif inst_3d_avg < 0:
            details.append(f"❌ 2. 籌碼偏空：近三日法人平均賣超 {abs(inst_3d_avg):,} 張")
        else:
            details.append(f"❌ 2. 籌碼無明顯買超動向 (平均 0 張)")

        # --- 技術指標 ---
        k_val, d_val = float(today['K']), float(today['D'])
        # KD 嚴格版：噴太高(K>60)一律不買！
        if k_val > d_val and k_val < 60 and d_val < 55:
            score += 1; details.append(f"✅ 3. KD 呈現低檔交叉 (K:{k_val:.1f}, D:{d_val:.1f})")
        else:
            details.append(f"❌ 3. KD 未符合低檔交叉條件 (K:{k_val:.1f})")

        # DIF-MACD 零軸之上
        macd_diff = float(today['DIF']) - float(today['MACD'])
        if macd_diff > 0:
            score += 1; details.append(f"✅ 4. DIF - MACD 大於 0 (零軸之上，紅柱翻紅)")
        else:
            details.append(f"❌ 4. DIF - MACD 小於 0 (水下弱勢)")

        # --- 均線與支撐 ---
        # 均線全面上揚
        if float(today['5MA']) > float(yesterday['5MA']) and float(today['10MA']) > float(yesterday['10MA']) and float(today['20MA']) > float(yesterday['20MA']):
            score += 1; details.append("✅ 5. 5T、10T、20T 均線全面上揚")
        else:
            details.append("❌ 5. 均線尚未全面上揚")

        # 季線趨勢向上
        if float(today['Close']) > float(df.iloc[-60]['Close']):
            score += 1; details.append("✅ 6. 股價大於季線扣抵 (60MA 趨勢向上)")
        else:
            details.append("❌ 6. 股價小於季線扣抵 (季線趨勢尚未翻揚)")

        # 站穩 5T
        if float(today['Close']) > float(today['5MA']):
            score += 1; details.append("✅ 7. 股價站穩 5T")
        else:
            details.append("❌ 7. 股價跌破 5T")

        # 站穩 10T
        if float(today['Close']) > float(today['10MA']):
            score += 1; details.append("✅ 8. 股價站穩 10T")
        else:
            details.append("❌ 8. 股價跌破 10T")

        # 站穩 20T
        if float(today['Close']) > float(today['20MA']):
            score += 1; details.append("✅ 9. 股價站穩 20T")
        else:
            details.append("❌ 9. 股價跌破 20T")
            
        # --- 量價關係 ---
        is_red_candle = float(today['Close']) > float(today['Open'])
        if (float(today['Volume']) > float(today['5VMA']) and float(today['Volume']) > float(today['10VMA']) and is_red_candle) or is_limit_up:
            score += 1; details.append(f"✅ 10. 量能健康：溫放量收紅K，或強勢漲停籌碼鎖定")
        else:
            details.append(f"❌ 10. 量能未達標：量縮或收黑K (留意出貨風險)")

        # 顯示詳細評級列表
        for d in details:
            if "✅" in d: st.write(d)
            else: st.error(d)
            
        st.divider()
        st.subheader("💡 系統最終評級 (滿分 10 項)")
        if score >= 8:
            st.balloons()
            st.markdown(f"### 🔥 **S 級：強勢爆發！** (達成 {score}/10 項)")
            st.write("量價配合極佳，短線動能極強，是勝率極高的突破點！")
        elif score >= 5:
            st.markdown(f"### ⚠️ **A 級：多頭發酵中** (達成 {score}/10 項)")
            st.write("指標逐步轉強，建議列入自選股密切觀察量能變化。")
        else:
            st.markdown(f"### ❄️ **B 級：弱勢或盤整** (達成 {score}/10 項)")
            st.write("動能與籌碼不足，建議保留資金等待更好時機。")
