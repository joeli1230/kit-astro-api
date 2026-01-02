import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from kerykeion import AstrologicalSubject

app = Flask(__name__)
# 允許所有來源連線
CORS(app, resources={r"/*": {"origins": "*"}})

# --- 設定 Gemini API ---
# 請確保環境變數 GEMINI_API_KEY 已設定，或直接在此填入您的 API Key
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_KEY)

# 使用模型
model = genai.GenerativeModel('gemma-3-27b-it')

def calculate_custom_aspects(bodies_data):
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
        user = AstrologicalSubject(
            data.get('name', 'Guest'),
            int(data.get('year')), int(data.get('month')), int(data.get('day')),
            int(data.get('hour')), int(data.get('minute')),
            data.get('city', 'Hong Kong'), data.get('country', 'HK')
        )
        
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
        user = AstrologicalSubject(
            data.get('name', 'Guest'),
            int(data.get('year')), int(data.get('month')), int(data.get('day')),
            int(data.get('hour')), int(data.get('minute')),
            data.get('city', 'Hong Kong'), "HK"
        )
        
        # 1. 星座中英文對照表 (確保傳入 Prompt 的是中文)
        ZODIAC_CN = {
            "Aries": "白羊座",
            "Taurus": "金牛座",
            "Gemini": "雙子座",
            "Cancer": "巨蟹座",
            "Leo": "獅子座",
            "Virgo": "處女座",
            "Libra": "天秤座",
            "Scorpio": "天蠍座",
            "Sagittarius": "射手座",
            "Capricorn": "摩羯座",
            "Aquarius": "水瓶座",
            "Pisces": "雙魚座"
        }

        # 2. 轉換變數為中文 (若無對應則保留原文)
        sun_sign = ZODIAC_CN.get(user.sun.sign, user.sun.sign)
        moon_sign = ZODIAC_CN.get(user.moon.sign, user.moon.sign)
        asc_sign = ZODIAC_CN.get(user.first_house.sign, user.first_house.sign)

        # 3. 構建 Prompt：加入【用詞規範】，強制不準簡寫
        prompt = f"""
你是一位專業且溫暖的占星師。請根據以下星盤配置，用【繁體中文】為案主進行性格分析。

【用詞規範】
1. 請務必使用**完整的星座名稱**，嚴禁使用簡稱。
2. 錯誤示範：「蟹座」、「羊座」、「瓶座」。
3. 正確示範：「巨蟹座」、「白羊座」、「水瓶座」。
4. 特別注意：提到「巨蟹座」時，絕對不可以寫成「蟹座」。

【星盤配置】
- 太陽：{sun_sign}
- 月亮：{moon_sign}
- 上升：{asc_sign}

【輸出格式要求】
請嚴格依照以下格式輸出（使用 Emoji 作為標題，不要使用 Markdown）：
🌟 【核心性格分析】
(請在此分析太陽與上升的結合，約 100 字)
🌙 【內在情感需求】
(請在此分析月亮的影響，約 80 字)
🎯 【給您的人生建議】
1. (建議一)
2. (建議二)
(結語，一句溫暖的話)
"""
        response = model.generate_content(prompt)
        return jsonify({"status": "success", "analysis": response.text})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/')
def home():
    return "Kit Astrology API is Running on Render!", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

