from flask import Flask, request, jsonify
import cv2
import numpy as np
import base64
import mediapipe as mp
import math

app = Flask(__name__)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

@app.route("/frame", methods=["POST"])
def receive_frame():
    data = request.json["image"]

    # Remove cabeçalho base64
    image_data = base64.b64decode(data.split(",")[1])

    # Converte para OpenCV
    np_img = np.frombuffer(image_data, np.uint8)
    frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    segurando = False

    if result.multi_hand_landmarks:
        hand = result.multi_hand_landmarks[0]
        polegar = hand.landmark[4]
        indicador = hand.landmark[8]

        h, w, _ = frame.shape
        x1, y1 = int(polegar.x * w), int(polegar.y * h)
        x2, y2 = int(indicador.x * w), int(indicador.y * h)

        distancia = math.hypot(x2 - x1, y2 - y1)

        if distancia < 40:
            segurando = True

    return jsonify({"segurando": segurando})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
