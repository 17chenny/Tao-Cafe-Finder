#!/usr/bin/env python
# coding: utf-8

# In[2]:


import math
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium  # 用來在 Streamlit 網頁中顯示地圖的工具
import urllib.parse
import requests

# 設定網頁標題與圖標（這行一定要放在最前面）
st.set_page_config(page_title="桃憩時光 - 桃園智慧咖啡廳搜尋", page_icon="☕", layout="wide")

# 1. 哈維辛公式：計算兩個經緯度之間的直線距離（公里）
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # 地球半徑 (km)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 2. 免費的 Geocoding 服務：將文字地址/地標轉成經緯度
def geocode_address(address):
    # 預設如果查不到，就停留在元智大學
    default_lat, default_lng = 24.9723, 121.2662
    if not address.strip() or address == "元智大學":
        return default_lat, default_lng
        
    if "桃園" not in address:
        search_query = f"桃園市{address}"
    else:
        search_query = address
        
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(search_query)}&format=json&limit=1"
        headers = {'User-Agent': 'TaoCafeFinder/1.0 (student_project)'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return default_lat, default_lng

# 3. 智慧搜尋核心函式
def search_cafes(user_lat, user_lng, selected_tags, keyword="", max_distance_km=1.0):
    try:
        df = pd.read_csv("cafe.csv")
    except FileNotFoundError:
        st.error("找不到 cafe.csv 檔案！請確保該檔案與 app.py 放在同一個資料夾。")
        return pd.DataFrame()

    # 篩選距離
    df["distance"] = df.apply(
        lambda row: haversine(user_lat, user_lng, row["lat"], row["lng"]),
        axis=1,
    )
    filtered_df = df[df["distance"] <= max_distance_km].copy()

    # 篩選標籤
    for tag in selected_tags:
        filtered_df = filtered_df[filtered_df[tag] == 1]

    # 篩選店名關鍵字
    if keyword.strip():
        filtered_df = filtered_df[
            filtered_df["name"].str.contains(keyword, na=False, case=False)
        ]

    return filtered_df


# ─── Streamlit 前端網頁介面設計 ───

st.title("☕ 桃憩時光 (Tao-Café Finder)")
st.subheader("桃園專屬智慧標籤與交通圈咖啡廳導航系統")

# ─── ⚖️ 位置定位選擇區（純 Python，100% 穩定不卡死） ───
st.write("### 📍 位置權限與起點設定")
location_consent = st.radio(
    "【隱私授權詢問】為了計算您與咖啡廳的距離，本系統需要設定您的出發位置：",
    ("✅ 同意使用預設當前位置 (元智大學)", "❌ 不同意位置追蹤，我想自行輸入起點"),
    horizontal=True
)

if location_consent == "✅ 同意使用預設當前位置 (元智大學)":
    my_lat, my_lng = 24.9723, 121.2662
    location_message = "🟢 已成功取得定位！目前出發起點設定為：【元智大學】"
else:
    user_start_input = st.text_input("🏠 請輸入您目前的地址或附近地標：", value="中壢火車站")
    my_lat, my_lng = geocode_address(user_start_input)
    location_message = f"🏠 已切換手動模式！目前出發起點設定為：【{user_start_input}】"

# 顯示目前的定位狀態文字提示
st.info(location_message)


# ─── 側邊欄：搜尋與篩選條件 ───
st.sidebar.header("🔍 搜尋與篩選條件")

user_keyword = st.sidebar.text_input("請輸入咖啡廳店名關鍵字：", placeholder="例如：妮咖啡、老宅...")

transport_mode = st.sidebar.selectbox("🚗 請選擇您的代步工具：", ("🚶 步行", "🛵 機車", "🚗 汽車"))

# 根據代步工具計算移動半徑
if transport_mode == "🚶 步行":
    speed_per_minute = 0.07  # 公里/分鐘
    max_time_value = 30
    default_time_value = 15
    time_label = "預計最大步行時間 (分鐘)"
    icon_name = "user"       
elif transport_mode == "🛵 機車":
    speed_per_minute = 0.50  # 公里/分鐘
    max_time_value = 45
    default_time_value = 10
    time_label = "預計最大騎車時間 (分鐘)"
    icon_name = "motorcycle" 
else:
    speed_per_minute = 0.66  # 公里/分鐘
    max_time_value = 60
    default_time_value = 15
    time_label = "預計最大開車時間 (分鐘)"
    icon_name = "car"        

travel_minutes = st.sidebar.slider(time_label, min_value=5, max_value=max_time_value, value=default_time_value, step=5)
max_dist = travel_minutes * speed_per_minute

# 標籤勾選區
st.sidebar.write("📌 空間與氛圍標籤（可複選）：")
tag_dict = {
    "pudding": st.sidebar.checkbox("🍮 布丁好吃"),
    "basque": st.sidebar.checkbox("🍰 巴斯克好吃"),
    "midnight": st.sidebar.checkbox("🌙 主打深夜"),
    "study": st.sidebar.checkbox("💻 適合讀書"),
    "chat": st.sidebar.checkbox("💬 適合聊天"),
    "photo": st.sidebar.checkbox("📷 適合拍照"),
}
active_tags = [key for key, value in tag_dict.items() if value]


# ─── 執行搜尋與主畫面渲染 ───

# 執行搜尋
results = search_cafes(my_lat, my_lng, active_tags, keyword=user_keyword, max_distance_km=max_dist)

st.write(f"### 📍 搜尋結果 (在您使用【{transport_mode[2:]}】移動 {travel_minutes} 分鐘範圍內)")
action_verb = "步行" if "步行" in transport_mode else ("騎車" if "機車" in transport_mode else "開車")

if not results.empty:
    st.success(f"太棒了！幫您找到 {len(results)} 間符合條件的咖啡廳：")

    # 建立 Folium 地圖
    current_zoom = 15 if "步行" in transport_mode else (13 if "機車" in transport_mode else 12)
    mymap = folium.Map(location=[my_lat, my_lng], zoom_start=current_zoom)

    # 在地圖上標記出中心起點 (紅色大頭針)
    current_loc_title = "我的位置 (元智大學)" if location_consent == "✅ 同意使用預設當前位置 (元智大學)" else "手動輸入的起點"
    folium.Marker(
        location=[my_lat, my_lng],
        popup=f"<b>🎯 {current_loc_title}</b><br>以此為中心搜尋周邊咖啡廳",
        icon=folium.Icon(color="red", icon=icon_name, prefix="fa"),
    ).add_to(mymap)

    # 標記咖啡廳位置
    for _, row in results.iterrows():
        t_time = round(row["distance"] / speed_per_minute)
        if t_time < 1:
            t_time = 1  
            
        popup_text = f"<b>{row['name']}</b><br>距離：{row['distance']:.2f} km<br>{action_verb}約：{t_time} 分鐘<br>營業時間：{row['open_hours']}"

        folium.Marker(
            location=[row["lat"], row["lng"]],
            popup=popup_text,
            icon=folium.Icon(color="blue", icon="coffee", prefix="fa"),
        ).add_to(mymap)

    # 在網頁中央直接顯示互動地圖畫面
    st_folium(mymap, width=850, height=500)

    # 在地圖下方用表格顯示詳細資訊
    st.write("#### 📝 店家詳細資訊清單：")
    st.dataframe(results[["name", "address", "open_hours", "distance"]], use_container_width=True)

else:
    st.warning(f"在該範圍內找不到符合這些條件的咖啡廳，可能太遠囉！請調整一下工具、時間或篩選標籤。")


# In[ ]:




