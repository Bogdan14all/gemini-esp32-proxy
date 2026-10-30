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
    
    print(f"\n[SERVER] Primit: {prompt}")
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + API_KEY
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # Încercăm de până la 3 ori, cu timeout mărit
    for attempt in range(3):
        try:
            print(f"[SERVER] Încercarea {attempt+1}/3...")
            # Timeout mărit la 60 de secunde
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            resp_json = response.json()
            text_response = resp_json["candidates"][0]["content"]["parts"][0]["text"]
            
            print(f"[SERVER] Succes! Răspuns: {text_response[:50]}...")
            return jsonify({"status": "ok", "text": text_response})
            
        except requests.exceptions.Timeout:
            print(f"[SERVER] Încercarea {attempt+1} a expirat. Reîncerc...")
            if attempt == 2: # Dacă a treia încercare a eșuat
                return jsonify({"status": "error", "text": "Eroare: Serverul Google nu răspunde. Încearcă din nou."}), 200
            continue # Trecem la următoarea încercare
        except Exception as e:
            err_msg = str(e)
            print(f"[SERVER] Eroare: {err_msg}")
            return jsonify({"status": "error", "text": "Eroare: " + err_msg[:100]}), 200

    # Dacă ieșim din buclă fără succes
    return jsonify({"status": "error", "text": "Eroare necunoscută la server."}), 200
