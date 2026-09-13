import os
import socket
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk
import webbrowser

# Chemins absolus vers les sous-projets
OMNIROUTE_DIR = r"C:\Users\USER\Desktop\4 espace\OmniRoute-release-v3.8.51"
BACKEND_DIR = r"C:\Users\USER\Desktop\prototype B2B - Modernisation\src"
VENV_ACTIVATE = r"C:\Users\USER\Desktop\prototype B2B - Modernisation\venv\Scripts\activate.bat"
FRONTEND_DIR = r"C:\Users\USER\Desktop\prototype B2B - Modernisation\silalink-frontend"

# Définition des services et de leurs ports d'écoute
SERVICES = [
    {
        "name": "OmniRoute LLM",
        "port": 20128,
        "url": "http://localhost:20128",
        "cmd": f'cd /d "{OMNIROUTE_DIR}" && npm start',
    },
    {
        "name": "Backend FastAPI",
        "port": 8000,
        "url": "http://127.0.0.1:8000/docs",
        "cmd": f'cd /d "{BACKEND_DIR}" && call "{VENV_ACTIVATE}" && uvicorn main:app --reload --host 127.0.0.1 --port 8000',
    },
    {
        "name": "Frontend Vite",
        "port": 5173,
        "url": "http://localhost:5173",
        "cmd": f'cd /d "{FRONTEND_DIR}" && npm run dev',
    },
]


def check_port(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Vérifie si un port TCP écoute les connexions."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        return result == 0


class SilaLinkLauncherApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("SilaLink CRM — Centre de Contrôle")
        self.geometry("540x520")
        self.resizable(False, False)
        self.configure(bg="#F8FAFC")

        self.service_indicators = {}
        self.processes = []

        self.build_ui()
        # Démarrage de l'orchestration dans un thread séparé pour ne pas geler la fenêtre
        threading.Thread(target=self.start_orchestration, daemon=True).start()

    def build_ui(self):
        # Header
        header_frame = tk.Frame(self, bg="#0F172A", padx=24, pady=20)
        header_frame.pack(fill="x")

        title = tk.Label(
            header_frame,
            text="SilaLink CRM",
            font=("Segoe UI", 18, "bold"),
            fg="#FFFFFF",
            bg="#0F172A",
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            header_frame,
            text="Plateforme B2B — Initialisation des micro-services",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#0F172A",
        )
        subtitle.pack(anchor="w")

        # Conteneur principal
        body_frame = tk.Frame(self, bg="#F8FAFC", padx=24, pady=20)
        body_frame.pack(fill="both", expand=True)

        # Section statuts
        status_card = tk.LabelFrame(
            body_frame,
            text=" État des Services Locaux ",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#334155",
            padx=16,
            pady=12,
            relief="solid",
            bd=1,
        )
        status_card.pack(fill="x", pady=(0, 16))

        for svc in SERVICES:
            row = tk.Frame(status_card, bg="#FFFFFF", pady=6)
            row.pack(fill="x")

            lbl_name = tk.Label(
                row,
                text=f"{svc['name']} (Port {svc['port']})",
                font=("Segoe UI", 10),
                fg="#1E293B",
                bg="#FFFFFF",
            )
            lbl_name.pack(side="left")

            badge = tk.Label(
                row,
                text="● EN ATTENTE",
                font=("Segoe UI", 9, "bold"),
                fg="#94A3B8",
                bg="#FFFFFF",
            )
            badge.pack(side="right")
            self.service_indicators[svc["name"]] = badge

        # Barre de progression
        self.progress = ttk.Progressbar(body_frame, mode="determinate", maximum=3)
        self.progress.pack(fill="x", pady=(0, 12))

        # Texte d'état global
        self.lbl_status = tk.Label(
            body_frame,
            text="Démarrage de la séquence d'orchestration...",
            font=("Segoe UI", 9, "italic"),
            fg="#64748B",
            bg="#F8FAFC",
        )
        self.lbl_status.pack(pady=(0, 20))

        # Bouton principal d'accès
        self.btn_open = tk.Button(
            body_frame,
            text="Démarrage des serveurs en cours...",
            font=("Segoe UI", 11, "bold"),
            fg="#94A3B8",
            bg="#E2E8F0",
            activeforeground="#94A3B8",
            activebackground="#E2E8F0",
            relief="flat",
            state="disabled",
            cursor="watch",
            pady=10,
            command=self.open_dashboard,
        )
        self.btn_open.pack(fill="x")

        # Bouton d'arrêt
        self.btn_stop = tk.Button(
            body_frame,
            text="Tout Arrêter & Quitter",
            font=("Segoe UI", 9),
            fg="#EF4444",
            bg="#FFFFFF",
            activeforeground="#B91C1C",
            activebackground="#FEE2E2",
            relief="solid",
            bd=1,
            pady=6,
            command=self.shutdown_all,
        )
        self.btn_stop.pack(fill="x", pady=(10, 0))

    def update_badge(self, service_name: str, state: str):
        badge = self.service_indicators[service_name]
        if state == "starting":
            badge.config(text="● INITIALISATION...", fg="#F59E0B")
        elif state == "ready":
            badge.config(text="✔ OPÉRATIONNEL", fg="#10B981")
        elif state == "failed":
            badge.config(text="✖ ÉCHEC", fg="#EF4444")

    def start_orchestration(self):
        progress_val = 0

        for svc in SERVICES:
            self.lbl_status.config(text=f"Démarrage de {svc['name']}...")
            self.update_badge(svc["name"], "starting")

            # Si le port écoute déjà (ex: relance de l'app), inutile de recréer le process
            if not check_port(svc["port"]):
                proc = subprocess.Popen(
                    f'cmd /k "{svc["cmd"]}"',
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                self.processes.append(proc)

            # Attente active que le socket TCP réponde
            max_retries = 30  # 30 secondes max par service
            is_ready = False
            for _ in range(max_retries):
                if check_port(svc["port"]):
                    is_ready = True
                    break
                time.sleep(1)

            if is_ready:
                self.update_badge(svc["name"], "ready")
                progress_val += 1
                self.progress["value"] = progress_val
            else:
                self.update_badge(svc["name"], "failed")
                self.lbl_status.config(
                    text=f"Erreur : Délai dépassé pour joindre le port {svc['port']}."
                )
                return

        # Tous les services répondent
        self.lbl_status.config(text="Tous les serveurs sont actifs et synchronisés !")
        self.btn_open.config(
            text="🚀 Ouvrir SilaLink CRM",
            fg="#FFFFFF",
            bg="#2563EB",
            activeforeground="#FFFFFF",
            activebackground="#1D4ED8",
            state="normal",
            cursor="hand2",
        )

    def open_dashboard(self):
        webbrowser.open("http://localhost:5173")

    def shutdown_all(self):
        self.lbl_status.config(text="Fermeture forcée des services locaux...")
        # Arrêt des processus Node et Python
        subprocess.run(
            ["taskkill", "/F", "/IM", "node.exe"],
            capture_output=True,
            shell=True,
        )
        subprocess.run(
            ["taskkill", "/F", "/IM", "python.exe"],
            capture_output=True,
            shell=True,
        )
        self.destroy()


if __name__ == "__main__":
    app = SilaLinkLauncherApp()
    app.mainloop()
