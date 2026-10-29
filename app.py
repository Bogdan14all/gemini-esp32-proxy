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
    
    print(f"\n[SERVER] Primit de la ESP32: {prompt}")
    
    # Folosim exact modelul sugerat de Google in logurile tale
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + API_KEY
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        print("[SERVER] Trimitere catre Google...")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        
        resp_json = response.json()
        text_response = resp_json["candidates"][0]["content"]["parts"][0]["text"]
        print(f"[SERVER] Succes! Răspuns: {text_response[:50]}...")
        
        return jsonify({"status": "ok", "text": text_response})
        
    except Exception as e:
        err_msg = str(e)
        print(f"[SERVER] Eroare HTTP: {err_msg}")
        
        # Încercăm să extragem eroarea exactă de la Google
        try:
            err_json = response.json()
            err_msg = err_json.get("error", {}).get("message", err_msg)
            print(f"[SERVER] Eroare Google: {err_msg}")
        except:
            pass
            
        # Tăiem textul la 120 de caractere ca să încapă pe ecranul ESP32
        return jsonify({"status": "error", "text": "Eroare Google: " + err_msg[:120]}), 200
