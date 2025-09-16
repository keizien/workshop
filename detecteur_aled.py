import random
import socket
import json
from vosk import Model, KaldiRecognizer
import sounddevice as sd
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import hashlib

# Mots de code et leurs mots de passe
mots_de_code = {
    "oiseau": "bleu123",
    "plante": "vert456",
    "orage": "gris789"
}

# Préparer la reconnaissance VOSK
model = Model("vosk-fr")
rec = KaldiRecognizer(model, 16000)

# Fonction de dérivation de clé AES
def derive_cle(mdp):
    return hashlib.sha256(mdp.encode()).digest()[:16]  # 128-bit AES

# Fonction de chiffrement
def chiffrer_message(message, mdp):
    cle = derive_cle(mdp)
    cipher = AES.new(cle, AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(pad(message.encode(), 16))).decode()

# Fonction appelée quand de l'audio est reçu
def callback(indata, frames, time, status):
    if rec.AcceptWaveform(bytes(indata)):
        result = json.loads(rec.Result())
        texte = result.get("text", "").lower()
        print(f"Entendu : {texte}")

        # Vérifier si un mot de code est reconnu
        for mot_code, mdp in mots_de_code.items():
            if mot_code in texte:
                print(f"SOS MOT DE CODE DETECTE : {mot_code}")
                message_chiffre = chiffrer_message(mot_code, mdp)

                # Envoi au QG
                try:
                    HOST = "127.0.0.1"
                    PORT = 5000
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((HOST, PORT))
                        s.sendall(message_chiffre.encode())
                    print("Message chiffre envoyé au QG !")
                except:
                    print("Impossible d'envoyer au QG.")
                break

# Lancement de l’écoute audio
with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    print("En attente d’un mot de code (oiseau, plante, orage)")
    while True:
        pass