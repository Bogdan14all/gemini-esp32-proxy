import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "")

@app.route('/')
def health_check():
    return "Proxy is running!", 200

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Preluăm datele în siguranță
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "text": "Eroare: Date JSON invalide."}), 200
            
        prompt = data.get('text', 'Salut!')
        print(f"\n[SERVER] Primit: {prompt}")
        
        if not API_KEY:
            return jsonify({"status": "error", "text": "Eroare: API_KEY lipseste."}), 200
            
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + API_KEY
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        # Setăm un timeout de 30 secunde
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            err_msg = "Status " + str(response.status_code)
            try:
                err_msg = response.json().get("error", {}).get("message", err_msg)
            except:
                pass
            print(f"[SERVER] Eroare Google: {err_msg}")
            return jsonify({"status": "error", "text": "Google: " + err_msg[:100]}), 200

        resp_json = response.json()
        text_response = resp_json["candidates"][0]["content"]["parts"][0]["text"]
        
        print(f"[SERVER] Succes! Răspuns: {text_response[:50]}...")
        return jsonify({"status": "ok", "text": text_response})
        
    except Exception as e:
        # Prindem orice altă eroare (inclusiv timeout)
        print(f"[SERVER] Exceptie: {str(e)}")
        return jsonify({"status": "error", "text": "Eroare Server: " + str(e)[:100]}), 200
