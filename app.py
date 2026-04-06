import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from kerykeion import AstrologicalSubject

# 這裡不再需要 geopy，因為前端會直接傳經緯度過來
# from geopy.geocoders import Nominatim 

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemma-4-31b-it')

def calculate_custom_aspects(bodies_data):
    # ... (這部分代碼保持不變，照舊) ...
    aspects = []
    ORB = 8
    IGNORE_KEYWORDS = ["First", "Tenth", "Ascendant", "Midheaven", "House", "Node", "Chiron"]
    for i in range(len(bodies_data)):
        for j in range(i + 1, len(bodies_data)):
            p1 = bodies_data[i]
            p2 = bodies_data[j]
            name1 = p1['name']
            name2 = p2['name']
            is_ignored = False
            for keyword in IGNORE_KEYWORDS:
                if keyword in name1 or keyword in name2:
                    is_ignored = True
                    break
            if is_ignored: continue
            diff = abs(p1['angle'] - p2['angle'])
            if diff > 180: diff = 360 - diff
            aspect_name = None
            if abs(diff - 0) < ORB: aspect_name = "conjunction"
            elif abs(diff - 180) < ORB: aspect_name = "opposition"
            elif abs(diff - 120) < ORB: aspect_name = "trine"
            elif abs(diff - 90) < ORB: aspect_name = "square"
            elif abs(diff - 60) < ORB: aspect_name = "sextile"
            if aspect_name:
                aspects.append({"p1": name1, "p2": name2, "aspect": aspect_name, "orb": round(diff, 2)})
    return aspects

@app.route('/api/get-data', methods=['POST'])
def get_data():
    try:
        data = request.json
        
        # --- 修改開始 ---
        # 接收前端傳來的經緯度 (lat, lng)
        # 如果前端有傳 lat/lng，就用前端的；如果無，就預設用 Hong Kong
        city_name = data.get('city', 'Hong Kong')
        lat = data.get('lat')
        lng = data.get('lng')
        country_code = data.get('country', 'HK') # 這裡只作顯示用，計算會用 lat/lng

        # 初始化 AstrologicalSubject
        # 注意：kerykeion 支援直接傳入 lat (緯度) 和 lng (經度)
        if lat and lng:
            user = AstrologicalSubject(
                data.get('name', 'Guest'),
                int(data.get('year')), int(data.get('month')), int(data.get('day')),
                int(data.get('hour')), int(data.get('minute')),
                city=city_name,
                nation=country_code,
                lat=float(lat),
                lng=float(lng) # 直接鎖定經緯度，不再模糊搜尋
            )
        else:
            # 如果前端沒傳座標（舊版兼容），才用舊方法
            user = AstrologicalSubject(
                data.get('name', 'Guest'),
                int(data.get('year')), int(data.get('month')), int(data.get('day')),
                int(data.get('hour')), int(data.get('minute')),
                city_name, "HK"
            )
        # --- 修改結束 ---
        
        raw_bodies = [user.sun, user.moon, user.mercury, user.venus, user.mars,
                      user.jupiter, user.saturn, user.uranus, user.neptune, user.pluto,
                      user.chiron, user.true_node, user.first_house, user.tenth_house]

        planet_name_mapping = {"True_Node": "北交點"}
        planets_data = []
        for p in raw_bodies:
            mapped_name = planet_name_mapping.get(p.name, p.name)
            planets_data.append({
                "name": mapped_name, "sign": p.sign, "angle": p.abs_pos, "house": p.house
            })
        
        raw_houses = [user.first_house, user.second_house, user.third_house, user.fourth_house,
                      user.fifth_house, user.sixth_house, user.seventh_house, user.eighth_house,
                      user.ninth_house, user.tenth_house, user.eleventh_house, user.twelfth_house]

        chinese_house_names = ["第一宮", "第二宮", "第三宮", "第四宮", "第五宮", "第六宮", "第七宮", "第八宮", "第九宮", "第十宮", "第十一宮", "第十二宮"]
        houses_data = [{"id": i+1, "angle": h.abs_pos, "chinese_name": chinese_house_names[i]} for i, h in enumerate(raw_houses)]
        
        aspects_data = calculate_custom_aspects(planets_data)

        return jsonify({
            "status": "success",
            "location_used": f"{city_name} ({lat}, {lng})", # 回傳確認用的位置
            "planets": planets_data,
            "aspects": aspects_data,
            "houses": houses_data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/analyze-big-three', methods=['POST'])
def analyze_big_three():
    try:
        data = request.json
        city_name = data.get('city', 'Hong Kong')
        lat = data.get('lat')
        lng = data.get('lng')
        country_code = data.get('country', 'HK')

        if lat and lng:
            user = AstrologicalSubject(
                data.get('name', 'Guest'),
                int(data.get('year')), int(data.get('month')), int(data.get('day')),
                int(data.get('hour')), int(data.get('minute')),
                city=city_name,
                nation=country_code,
                lat=float(lat),
                lng=float(lng)
            )
        else:
            user = AstrologicalSubject(
                data.get('name', 'Guest'),
                int(data.get('year')), int(data.get('month')), int(data.get('day')),
                int(data.get('hour')), int(data.get('minute')),
                city_name, "HK"
            )
        
        ZODIAC_CN = {
            "Aries": "白羊座", "Taurus": "金牛座", "Gemini": "雙子座", "Cancer": "巨蟹座",
            "Leo": "獅子座", "Virgo": "處女座", "Libra": "天秤座", "Scorpio": "天蠍座",
            "Sagittarius": "射手座", "Capricorn": "摩羯座", "Aquarius": "水瓶座", "Pisces": "雙魚座"
        }

        sun_sign = ZODIAC_CN.get(user.sun.sign, user.sun.sign)
        moon_sign = ZODIAC_CN.get(user.moon.sign, user.moon.sign)
        asc_sign = ZODIAC_CN.get(user.first_house.sign, user.first_house.sign)

        prompt = f"""
你是一位專業且溫暖的占星師。請根據以下星盤配置，用【繁體中文】為案主進行性格分析。
案主出生地：{city_name}

【星盤配置】
- 太陽：{sun_sign}
- 月亮：{moon_sign}
- 上升：{asc_sign}

【輸出格式要求】
1. 請「僅輸出」分析內容，不要包含任何前言（如「好的，以下是分析」）或後記。
2. 嚴格禁止使用任何 Markdown 格式，包括但不限於粗體（**）、標題（#）或清單符號（-）。
3. 必須嚴格依照以下格式輸出（僅使用 Emoji 和括號作為分隔）：

🌟 【核心性格分析】
(請在此分析太陽與上升的結合，約 100 字)

🌙 【內在情感需求】
(請在此分析月亮的影響，約 80 字)

🎯 【你的長處】
1. (長處一)
2. (長處二)

🎯 【給您的人生建議】
1. (建議一)
2. (建議二)

(最後請加上一句溫暖的結語)
"""
        

        response = model.generate_content(prompt)
        return jsonify({"status": "success", "analysis": response.text})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/')
def home():
    return "Kit Astrology API is Running!", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
