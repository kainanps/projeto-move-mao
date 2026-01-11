from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import base64
import math
import json
from websocket import create_connection # Biblioteca websocket-client

app = Flask(__name__)
CORS(app)

# --- Configuração MediaPipe ---
base_options = python.BaseOptions(model_asset_path="hand_landmarker.task")
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

# Endereço do WebSocket PHP (ajuste o IP se necessário)
WS_SERVER_URL = "ws://192.168.0.4:8080"

def calcular_distancia(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def mao_esta_fechada(landmarks):
    pulso = landmarks[0]
    dedos_indices = [(8, 6), (12, 10), (16, 14), (20, 18)]
    dedos_dobrados = 0
    for ponta_idx, junta_idx in dedos_indices:
        if calcular_distancia(landmarks[ponta_idx], pulso) < calcular_distancia(landmarks[junta_idx], pulso):
            dedos_dobrados += 1
    return dedos_dobrados >= 3

def enviar_para_socket(payload):
    try:
        # Conecta, envia e desconecta a cada frame (simples para Flask)
        ws = create_connection(WS_SERVER_URL, timeout=0.1)
        ws.send(json.dumps(payload))
        ws.close()
    except Exception as e:
        print(f"Erro ao conectar no Socket: {e}")

@app.route('/frame', methods=['POST'])
def process_frame():
    print("📨 Request recebido!") # <- Aqui
    try:
        data = request.json
        image_data = data.get('image')

        if not image_data: return jsonify({"error": "No image"}), 400

        if "," in image_data: image_data = image_data.split(",")[1]
        
        frame = cv2.imdecode(np.frombuffer(base64.b64decode(image_data), np.uint8), cv2.IMREAD_COLOR)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        result = detector.detect(mp_image)
        
        response_data = {"detectado": False}

        if result.hand_landmarks:
            hand = result.hand_landmarks[0]
            
            # Usaremos a ponta do indicador (Index Finger Tip = 8) para coordenadas
            # Ou o centro da palma (9) se preferir
            ponto_controle = hand[8] 
            
            x = ponto_controle.x
            y = ponto_controle.y
            estado = "fechada" if mao_esta_fechada(hand) else "aberta"

            # Invertemos o X para ficar espelhado (natural para interação em tela)
            x_invertido = 1 - x 

            print(f"📍 X: {x_invertido:.2f} | Y: {y:.2f} | 🖐️ {estado}")

            # Prepara dados para o Socket PHP
            socket_payload = {
                "x": x_invertido,
                "y": y,
                "estado": estado
            }
            
            # Envia para o PHP
            enviar_para_socket(socket_payload)

            response_data = {"detectado": True, "estado": estado}

        return jsonify(response_data)

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Importante: host 0.0.0.0 para aceitar conexões da LAN
    app.run(host='0.0.0.0', port=5000, debug=True)