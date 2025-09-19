import socket
import base64
import hashlib
import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import os
import platform
import pygame

messages_reels = {
    "oiseau": ("J'ai besoin d'aide", "Salle 5"),
    "plante": ("Besoin d'extraction immédiatement", "Toit"),
    "orage": ("Protocole d'urgence activé", "Entrée principale")
}

phrases_leurres = [
    "Le colis est sécurisé.",
    "Aucune activité détectée.",
    "Transmission interrompue.",
    "Zone sans incident.",
    "Agent en patrouille normale."
]

positions_possibles = [(60, 60), (320, 60), (60, 200), (320, 200), (190, 130)]
dernier_message_chiffre = None
agent_position = (190, 130)
ennemi_positions = [(50, 50), (200, 100), (150, 180), (300, 80)]

raspberry_ip = "192.168.137.225"
raspberry_port_led = 6060

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

def jouer_bip():
    try:
        pygame.mixer.init()
        pygame.mixer.music.load("alarme.wav")  # Ton fichier audio
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Erreur lors du bip : {e}")

def ouvrir_log():
    chemin_log = os.path.abspath("log.txt")
    try:
        if platform.system() == "Windows":
            os.startfile(chemin_log)
        elif platform.system() == "Darwin":
            os.system(f"open {chemin_log}")
        else:
            os.system(f"xdg-open {chemin_log}")
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'ouvrir le fichier log : {e}")

def afficher(msg):
    zone_affichage.insert(tk.END, msg + "\n")
    zone_affichage.see(tk.END)

def dessiner_plan():
    canvas.delete("all")
    canvas.create_rectangle(20, 20, 380, 230, outline="black")
    canvas.create_text(200, 10, text="Plan du site", font=("Arial", 12, "bold"))
    canvas.create_rectangle(40, 40, 120, 100, fill="white")
    canvas.create_text(80, 70, text="Salle 1")
    canvas.create_rectangle(260, 40, 340, 100, fill="white")
    canvas.create_text(300, 70, text="Salle 2")
    canvas.create_rectangle(40, 160, 120, 220, fill="white")
    canvas.create_text(80, 190, text="Salle 3")
    canvas.create_rectangle(260, 160, 340, 220, fill="white")
    canvas.create_text(300, 190, text="Salle 4")
    canvas.create_rectangle(160, 100, 240, 160, fill="white")
    canvas.create_text(200, 130, text="Salle 5")

    canvas.create_line(120, 70, 160, 130)
    canvas.create_line(240, 130, 260, 70)
    canvas.create_line(240, 130, 260, 190)
    canvas.create_line(160, 130, 120, 190)
    canvas.create_line(160, 130, 120, 70)
    canvas.create_line(240, 130, 260, 70)

    afficher_ennemis()
    afficher_agent()

def afficher_agent():
    global agent_position
    x, y = agent_position
    canvas.create_oval(x-5, y-5, x+5, y+5, fill="blue", tags="agent")

def afficher_ennemis():
    for x, y in ennemi_positions:
        canvas.create_text(x, y, text="X", fill="red", font=("Arial", 16, "bold"))

def mettre_a_jour_positions():
    global ennemi_positions, agent_position
    ennemi_positions = random.sample(positions_possibles, 4)
    agent_position = random.choice(positions_possibles)
    dessiner_plan()

# === Envoi des instructions LED ===
def envoyer_instruction_led(etat):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as led_socket:
            led_socket.connect((raspberry_ip, raspberry_port_led))
            led_socket.sendall(etat.encode())
        afficher(f"Instruction LED envoyée : {etat}")
    except Exception as e:
        afficher(f"Erreur d'envoi à la LED : {e}")

def afficher_choix_led():
    fenetre_led = tk.Toplevel(fenetre)
    fenetre_led.title("Réponse au terrain")

    tk.Label(fenetre_led, text="Peut-on extraire l'agent ?").pack(pady=10)

    tk.Button(fenetre_led, text="OUI - LED verte", bg="green",
              command=lambda:[envoyer_instruction_led("vert"), fenetre_led.destroy()]).pack(pady=5)

    tk.Button(fenetre_led, text="NON - LED rouge", bg="red",
              command=lambda:[envoyer_instruction_led("rouge"), fenetre_led.destroy()]).pack(pady=5)

def traiter_dechiffrement():
    global dernier_message_chiffre
    mdp = champ_mdp.get()
    champ_mdp.delete(0, tk.END)

    if not dernier_message_chiffre:
        afficher("Aucun message à déchiffrer.")
        return

    mot_code = dechiffrer_message(dernier_message_chiffre, mdp)

    if mot_code in messages_reels:
        message, lieu = messages_reels[mot_code]
        afficher(f"Message : {message} | Lieu : {lieu}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {mot_code} → {message} ({lieu})\n")
        mettre_a_jour_positions()
        afficher_choix_led()
    else:
        leurre = random.choice(phrases_leurres)
        afficher(f"Message : {leurre}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] ??? → {leurre}\n")
        mettre_a_jour_positions()

def start_server():
    global dernier_message_chiffre
    HOST = "192.168.137.1"
    PORT = 5050
    afficher(f"Serveur actif sur {HOST}:{PORT}")

    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            conn, addr = s.accept()
            with conn:
                afficher(f"Connexion reçue depuis {addr}")
                data = conn.recv(1024)
                if not data:
                    afficher("Aucun message reçu.")
                    continue
                dernier_message_chiffre = data.decode()
                afficher(f"Message chiffré reçu : {dernier_message_chiffre}")
                jouer_bip()
                afficher("Entrez le mot de passe et cliquez sur 'Déchiffrer'")

# === Interface graphique ===
fenetre = tk.Tk()
fenetre.title("QG - Surveillance des agents")
fenetre.geometry("1000x600")

zone_affichage = scrolledtext.ScrolledText(fenetre, wrap=tk.WORD, width=80, height=12)
zone_affichage.pack(padx=10, pady=10)

frame_mdp = tk.Frame(fenetre)
frame_mdp.pack(pady=5)

label_mdp = tk.Label(frame_mdp, text="Mot de passe :")
label_mdp.pack(side=tk.LEFT)

champ_mdp = tk.Entry(frame_mdp, show="*", width=30)
champ_mdp.pack(side=tk.LEFT, padx=5)

bouton_dechiffrer = tk.Button(frame_mdp, text="Déchiffrer", command=traiter_dechiffrement)
bouton_dechiffrer.pack(side=tk.LEFT, padx=5)

frame_bas = tk.Frame(fenetre)
frame_bas.pack(pady=10)

bouton_log = tk.Button(frame_bas, text="Ouvrir le fichier log", command=ouvrir_log)
bouton_log.pack(side=tk.LEFT, padx=10)

bouton_quitter = tk.Button(frame_bas, text="Quitter le QG", command=fenetre.destroy, bg="red", fg="white")
bouton_quitter.pack(side=tk.LEFT)

canvas = tk.Canvas(fenetre, width=400, height=250, bg="lightgray")
canvas.pack(pady=5)

dessiner_plan()
threading.Thread(target=start_server, daemon=True).start()
fenetre.mainloop()