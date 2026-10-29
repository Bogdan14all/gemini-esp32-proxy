import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")

@app.route('/')
def health_check():
    return "Proxy is running!", 200

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    prompt = data.get('text', 'Salut!')
    
    print(f"[SERVER] Primit: {prompt}")
    
    # Folosim modelul stabil pentru text
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + API_KEY
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        
        resp_json = response.json()
        text_response = resp_json["candidates"][0]["content"]["parts"][0]["text"]
        
        return jsonify({"status": "ok", "text": text_response})
        
    except Exception as e:
        err_msg = str(e)
        print(f"[SERVER] Eroare: {err_msg}")
        # Extragem mesajul de eroare de la Google, dacă există
        try:
            err_json = response.json()
            err_msg = err_json.get("error", {}).get("message", err_msg)
        except:
            pass
            
        # Tăiem textul la 80 de caractere ca să nu dea crash la ESP32
        return jsonify({"status": "error", "text": "Eroare Google: " + err_msg[:80]}), 200
