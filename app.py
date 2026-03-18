import streamlit as st
from PIL import Image

st.set_page_config(page_title="股市短線評級 5.0", page_icon="⚡", layout="wide")
st.title("⚡ 專屬股市短線評級 - 實戰診斷器")

# --- 新增：上傳截圖區域 ---
st.subheader("📸 第一步：上傳看盤截圖 (技術圖 + 籌碼圖)")
uploaded_files = st.file_uploader("點擊或拖曳圖片到這裡", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    cols = st.columns(len(uploaded_files))
    for i, file in enumerate(uploaded_files):
        with cols[i]:
            img = Image.open(file)
            st.image(img, caption=f"截圖 {i+1}", use_container_width=True)

st.divider()

# --- 第二部分：對照截圖，手動勾選指標 ---
st.subheader("📝 第二步：對照圖片，勾選 10 大指標")
col_input1, col_input2 = st.columns(2)

with col_input1:
    v_turnover = st.checkbox("1. 週轉率 > 9%", value=False)
    v_kd_cross = st.checkbox("2. KD 低檔黃金交叉 (K<60, D<55)", value=False)
    v_ma_up = st.checkbox("3. 5T、10T、20T 均線全面上揚", value=False)
    v_inst_3d = st.checkbox("4. 近三日法人平均買超 (逐漸增加)", value=False)
    v_above_60ma = st.checkbox("5. 股價大於季線扣抵 (60MA 趨勢向上)", value=False)

with col_input2:
    v_macd_red = st.checkbox("6. DIF - MACD 位於 0 軸之上 (柱狀圖翻紅)", value=False)
    v_stay_5t = st.checkbox("7. 股價站穩 5T", value=False)
    v_stay_10t = st.checkbox("8. 股價站穩 10T", value=False)
    v_stay_20t = st.checkbox("9. 股價站穩 20T", value=False)
    v_vol_healthy = st.checkbox("10. 量增收紅 K (或強勢漲停)", value=False)

if st.button("🏁 生成最終評級報告"):
    # 計算得分
    checks = [v_turnover, v_kd_cross, v_ma_up, v_inst_3d, v_above_60ma, 
              v_macd_red, v_stay_5t, v_stay_10t, v_stay_20t, v_vol_healthy]
    score = sum(checks)
    
    st.divider()
    st.subheader(f"📊 診斷結果：{score} / 10 分")
    
    if score >= 8:
        st.balloons()
        st.success("🔥 S 級：強勢爆發！這檔極具潛力！")
    elif score >= 5:
        st.warning("⚠️ A 級：多頭發酵中，建議列入觀察。")
    else:
        st.error("❄️ B 級：弱勢或盤整，目前不建議介入。")
