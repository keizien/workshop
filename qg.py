import socket
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64
import hashlib
import random

# Mots de code → mot de passe
mots_de_code = {
    "oiseau": "bleu123",
    "plante": "vert456",
    "orage": "gris789"
}

# Mots de code → message réel
messages_reels = {
    "oiseau": "J'ai besoin d'aide",
    "plante": "Besoin d'extraction immédiatement",
    "orage": "Protocole d'urgence activé"
}

# Phrases leurres à afficher si le mot de passe est faux
phrases_leurres = [
    "Le colis est sécurisé.",
    "Aucune activité détectée.",
    "Transmission interrompue.",
    "Zone sans incident.",
    "Agent en patrouille normale."
]

def derive_cle(mdp):
    return hashlib.sha256(mdp.encode()).digest()[:16]

def dechiffrer_message(message_chiffre, mdp):
    try:
        cle = derive_cle(mdp)
        cipher = AES.new(cle, AES.MODE_ECB)
        message_bytes = base64.b64decode(message_chiffre)
        message_dechiffre = unpad(cipher.decrypt(message_bytes), 16)
        return message_dechiffre.decode()
    except:
        return None

HOST = "127.0.0.1"
PORT = 5000

print("QG pret, en attente de message...")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print(f"Connexion de {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            message_chiffre = data.decode()
            print(f"Message chiffre reçu : {message_chiffre}")

            mot_de_passe = input("Entrez le mot de passe : ")
            mot_code = dechiffrer_message(message_chiffre, mot_de_passe)

            if mot_code in messages_reels:
                print(f"Mot de code dechiffre : {mot_code}")
                message_alerte = messages_reels[mot_code]
                print(f"Alerte : {message_alerte}")
                with open("log.txt", "a", encoding="utf-8") as f:
                    f.write(f"{mot_code} → {message_alerte}\n")
            else:
                # Mot de passe incorrect ou message inconnu
                phrase_fausse = random.choice(phrases_leurres)
                print("Mot de passe incorrect.")
                print(f"Message leurre : {phrase_fausse}")