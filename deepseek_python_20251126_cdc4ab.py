from flask import Flask, request, jsonify
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('eco_violations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            violation_type TEXT NOT NULL,
            description TEXT NOT NULL,
            law_article TEXT NOT NULL,
            punishment TEXT NOT NULL,
            authority TEXT NOT NULL,
            appeal_tips TEXT NOT NULL,
            keywords TEXT NOT NULL
        )
    ''')
    
    # Тестовые данные
    violations_data = [
        ("Незаконное размещение отходов", "Сброс мусора в неположенном месте", "Статья 8.2 КоАП РФ", "Штраф для граждан: 1,000 - 2,000 руб.", "Росприроднадзор, Полиция", "Укажите точный адрес, приложите фото/видео", "мусор свалка отходы"),
        ("Загрязнение водных объектов", "Сброс сточных вод в реку", "Статья 8.13 КоАП РФ", "Штраф для граждан: 500 - 1,000 руб.", "Росприроднадзор", "Укажите координаты места сброса", "река вода загрязнение"),
        ("Незаконная вырубка деревьев", "Вырубка лесных насаждений", "Статья 8.28 КоАП РФ", "Штраф для граждан: 3,000 - 4,000 руб.", "Рослесхоз, Полиция", "Укажите место вырубки, количество деревьев", "вырубка деревья лес")
    ]
    
    for violation in violations_data:
        cursor.execute('''
            INSERT OR IGNORE INTO violations 
            (violation_type, description, law_article, punishment, authority, appeal_tips, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', violation)
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def classify_violation(description):
    try:
        conn = sqlite3.connect('eco_violations.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM violations")
        violations = cursor.fetchall()
        
        best_match = None
        max_keywords = 0
        
        for violation in violations:
            keywords = violation[7].split()
            matched_keywords = sum(1 for keyword in keywords if keyword.lower() in description.lower())
            
            if matched_keywords > max_keywords:
                max_keywords = matched_keywords
                best_match = violation
        
        conn.close()
        return best_match if best_match and max_keywords > 0 else None
        
    except Exception as e:
        logger.error(f"Ошибка при классификации: {e}")
        return None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        req = request.get_json(silent=True, force=True)
        
        if not req:
            return jsonify({"fulfillmentText": "Ошибка: пустой запрос"})
        
        intent_name = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
        parameters = req.get('queryResult', {}).get('parameters', {})
        
        if intent_name == 'classify_violation':
            violation_desc = parameters.get('violation_description', '')
            
            if not violation_desc:
                return jsonify({
                    "fulfillmentText": "Пожалуйста, опишите правонарушение. Например: 'Свалили мусор в лесу'"
                })
            
            violation_data = classify_violation(violation_desc)
            
            if violation_data:
                response_text = f"""
📋 **Классификация правонарушения:**

*Тип нарушения:* {violation_data[1]}
*Описание:* {violation_data[2]}
*Статья закона:* {violation_data[3]}

Теперь вы можете узнать о наказании или куда обращаться.
                """
            else:
                response_text = f"Не удалось классифицировать нарушение: '{violation_desc}'. Опишите более подробно."
            
            return jsonify({"fulfillmentText": response_text})
            
        else:
            return jsonify({
                "fulfillmentText": "Извините, я не понял ваш запрос. Пожалуйста, выберите один из пунктов меню."
            })
            
    except Exception as e:
        logger.error(f"Ошибка в веб-хуке: {e}")
        return jsonify({"fulfillmentText": "Произошла внутренняя ошибка сервера."})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Eco Bot Webhook is running"})

@app.route('/')
def home():
    return "Eco Violation Bot Webhook Server is running on Render!"

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)