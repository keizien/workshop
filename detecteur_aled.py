import random
import socket
import json
import threading
from vosk import Model, KaldiRecognizer
import sounddevice as sd
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import hashlib
import RPi.GPIO as GPIO
import time

# === CONFIGURATION ===
MODEL_PATH = "vosk-fr"
QG_IP = "192.168.137.1"       # IP du PC QG
QG_PORT = 5050                # Port principal pour messages
LED_PORT = 6060               # Port pour recevoir instructions LED

LED_VERTE = 17  # GPIO17 = pin physique 11
LED_ROUGE = 27  # GPIO27 = pin physique 13

mots_de_code = {
    "oiseau": "bleu123",
    "plante": "vert456",
    "orage": "gris789"
}

# === INIT VOSK ===
model = Model(MODEL_PATH)
rec = KaldiRecognizer(model, 16000)

# === INIT GPIO ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_VERTE, GPIO.OUT)
GPIO.setup(LED_ROUGE, GPIO.OUT)
GPIO.output(LED_VERTE, GPIO.LOW)
GPIO.output(LED_ROUGE, GPIO.LOW)

# === CRYPTO ===
def derive_cle(mdp):
    return hashlib.sha256(mdp.encode()).digest()[:16]

def chiffrer_message(message, mdp):
    cle = derive_cle(mdp)
    cipher = AES.new(cle, AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(pad(message.encode(), 16))).decode()

# === ENVOI AU QG ===
def envoyer_au_qg(message_chiffre):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((QG_IP, QG_PORT))
            s.sendall(message_chiffre.encode())
        print("Message chiffré envoyé au QG.")
    except Exception as e:
        print(f"Erreur : impossible d'envoyer au QG : {e}")

# === DETECTION VOCALE ===
def callback(indata, frames, time, status):
    if rec.AcceptWaveform(bytes(indata)):
        result = json.loads(rec.Result())
        texte = result.get("text", "").lower()
        print(f"Entendu : {texte}")

        for mot_code, mdp in mots_de_code.items():
            if mot_code in texte:
                print(f"Mot de code détecté : {mot_code}")
                message_chiffre = chiffrer_message(mot_code, mdp)
                envoyer_au_qg(message_chiffre)
                break

# === SERVEUR LED ===
def serveur_led():
    print(f"Serveur LED actif sur le port {LED_PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", LED_PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connexion du QG pour LEDs : {addr}")
                data = conn.recv(1024).decode().strip()
                print(f"Commande LED reçue : {data}")

                if data == "vert":
                    GPIO.output(LED_VERTE, GPIO.HIGH)
                    GPIO.output(LED_ROUGE, GPIO.LOW)
                    print("LED verte allumée (extraction possible)")
                elif data == "rouge":
                    GPIO.output(LED_VERTE, GPIO.LOW)
                    GPIO.output(LED_ROUGE, GPIO.HIGH)
                    print("LED rouge allumée (extraction impossible)")
                else:
                    GPIO.output(LED_VERTE, GPIO.LOW)
                    GPIO.output(LED_ROUGE, GPIO.LOW)
                    print("Commande LED inconnue")

                time.sleep(5)
                GPIO.output(LED_VERTE, GPIO.LOW)
                GPIO.output(LED_ROUGE, GPIO.LOW)

# === MAIN ===
if __name__ == "__main__":
    try:
        threading.Thread(target=serveur_led, daemon=True).start()
        print("En attente d’un mot de code (oiseau, plante, orage)...")
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                               channels=1, callback=callback):
            while True:
                pass
    except KeyboardInterrupt:
        print("Arrêt manuel")
    finally:
        GPIO.cleanup()