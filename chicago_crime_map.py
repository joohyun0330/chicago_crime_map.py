import requests
import folium
from datetime import datetime, timedelta, UTC
from streamlit_folium import st_folium
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# 페이지 설정
st.set_page_config(page_title="시카고 실시간 범죄 지도", layout="wide")
st.title("🗺 시카고 실시간 범죄 지도")
st.markdown("최근 1년 이내 사건만 표시됩니다. (10분마다 자동 갱신)")

# 10분마다 자동 새로고침
count = st_autorefresh(interval=600*1000, limit=0, key="refresh")

# 범죄 심각도 분류
SEVERITY_LEVELS = {
    "HIGHEST": [
        "HOMICIDE", "CRIMINAL SEXUAL ASSAULT", "ROBBERY",
        "WEAPONS VIOLATION", "ARSON", "KIDNAPPING"
    ],
    "HIGH": [
        "BATTERY", "ASSAULT", "BURGLARY", "MOTOR VEHICLE THEFT",
        "AGGRAVATED ASSAULT", "AGGRAVATED BATTERY", "INTIMIDATION"
    ],
    "MEDIUM": [
        "THEFT", "CRIMINAL DAMAGE", "NARCOTICS", "STALKING",
        "INTERFERENCE WITH PUBLIC OFFICER", "RECKLESS CONDUCT"
    ],
    "LOW": [
        "OTHER OFFENSE", "PUBLIC PEACE VIOLATION", "DECEPTIVE PRACTICE",
        "LIQUOR LAW VIOLATION", "GAMBLING", "PROSTITUTION",
        "OBSCENITY", "NON-CRIMINAL", "CONCEALED CARRY LICENSE VIOLATION"
    ]
}

# 색상 및 크기 설정
SEVERITY_COLORS = {
    "HIGHEST": "red",
    "HIGH": "orange",
    "MEDIUM": "blue",
    "LOW": "green"
}

SEVERITY_RADIUS = {
    "HIGHEST": 8,
    "HIGH": 7,
    "MEDIUM": 6,
    "LOW": 5
}

# 심각도 판별 함수
def get_severity_level(crime_type):
    crime_type = crime_type.strip().upper()
    for level, types in SEVERITY_LEVELS.items():
        if crime_type in types:
            return level
    return "MEDIUM"

def get_color_by_crime(crime_type):
    severity = get_severity_level(crime_type)
    return SEVERITY_COLORS[severity]

def get_radius_by_crime(crime_type):
    severity = get_severity_level(crime_type)
    return SEVERITY_RADIUS[severity]

# 범죄 데이터 가져오기
def get_crime_data():
    API_URL = "https://data.cityofchicago.org/resource/t7ek-mgzi.json"
    one_year_ago = (datetime.now(UTC) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

    params = {
        "$where": f"date >= '{one_year_ago}' AND latitude IS NOT NULL AND longitude IS NOT NULL",
        "$select": "primary_type,description,date,latitude,longitude",
        "$order": "date DESC",
        "$limit": 1000
    }

    headers = {}
    app_token = st.secrets.get("SODA_APP_TOKEN")
    if app_token:
        headers["X-App-Token"] = app_token

    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code in (403, 429):
            st.warning("API 제한(403/429)에 걸렸습니다. 잠시 후 다시 시도하거나 App Token을 설정하세요.")
            return []
        else:
            st.error(f"API 오류: {response.status_code} - {response.text[:200]}")
            return []
    except requests.RequestException as e:
        st.error(f"네트워크 오류: {e}")
        return []

# 데이터 불러오기
data = get_crime_data()
st.write(f"불러온 사건 수: {len(data)}건 (UTC 기준 {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')})")

# 지도 생성
m = folium.Map(location=[41.8781, -87.6298], zoom_start=11)

# 마커 생성
valid_count = 0
for incident in data:
    try:
        lat = float(incident["latitude"])
        lon = float(incident["longitude"])
        category = incident.get("primary_type", "Unknown")
        description = incident.get("description", "No description")
        date_time = incident.get("date", "Unknown time")

        color = get_color_by_crime(category)
        radius = get_radius_by_crime(category)

        popup_text = f"""
        <b>사건 종류:</b> {category}<br>
        <b>세부 유형:</b> {description}<br>
        <b>발생 시간(UTC):</b> {date_time}
        """

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(m)

        valid_count += 1

    except:
        continue

st.write(f"지도에 표시된 사건 수: {valid_count}건")

# 지도 표시
st_folium(m, width=900, height=600)