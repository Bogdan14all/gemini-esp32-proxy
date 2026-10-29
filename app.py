import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY nu este setată în variabilele de mediu!")

@app.route('/')
def health_check():
    return "Proxy is running!", 200

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('text', 'Salut! Cine esti?')
    
    print(f"[SERVER] Primit: {prompt}")
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + API_KEY
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        
        resp_json = response.json()
        text_response = resp_json["candidates"][0]["content"]["parts"][0]["text"]
        
        print(f"[SERVER] Răspuns: {text_response}")
        return jsonify({"status": "ok", "text": text_response})
        
    except Exception as e:
        print(f"[SERVER] Eroare: {e}")
        return jsonify({"status": "error", "text": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)