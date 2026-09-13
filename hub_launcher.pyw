import os
import sys
import socket
import subprocess
import time
import requests
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import webview
import ctypes

# Chemins dynamiques gérant à la fois le mode script brut et l'exécutable PyInstaller gelé
if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

OMNIROUTE_DIR = os.path.join(ROOT_DIR, "OmniRoute")
OMNIROUTE_STANDALONE_DIR = os.path.join(OMNIROUTE_DIR, ".build", "next", "standalone")
BACKEND_DIR = os.path.join(ROOT_DIR, "src")
FRONTEND_DIR = os.path.join(ROOT_DIR, "silalink-frontend")
VENV_ACTIVATE = os.path.join(ROOT_DIR, "venv", "Scripts", "activate.bat")
ICON_PATH = os.path.join(ROOT_DIR, "silalink.ico")

def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(s.getsockname()[1])

def is_port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0

class SplashScreen:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SilaLink CRM - Initialisation")
        self.root.geometry("600x600")
        self.root.configure(bg="#0f172a")
        
        try:
            self.root.iconbitmap(ICON_PATH)
        except Exception:
            pass
        
        x = (self.root.winfo_screenwidth() - 600) // 2
        y = (self.root.winfo_screenheight() - 600) // 2
        self.root.geometry(f"600x600+{x}+{y}")
        self.root.overrideredirect(True)
        
        # Titre fixe avec la couleur du sablier (orange/jaune)
        self.title_label = tk.Label(self.root, text="SilaLink CRM", font=("Segoe UI", 26, "bold"), fg="#eab308", bg="#0f172a")
        self.title_label.pack(pady=(30, 0))
        
        tk.Label(self.root, text="Démarrage des services locaux...", font=("Segoe UI", 11), fg="#94a3b8", bg="#0f172a").pack(pady=(5, 10))
        
        # --- ANIMATION CENTRALE MODERNE (Haute Qualité) ---
        self.spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_idx = 0
        self.spinner_label = tk.Label(self.root, text=self.spinner_frames[0], font=("Consolas", 65), fg="#38bdf8", bg="#0f172a")
        self.spinner_label.pack(pady=5)
        # --------------------------------------------------

        self.steps_frame = tk.Frame(self.root, bg="#0f172a")
        self.steps_frame.pack(fill="x", padx=40, pady=5)
        
        self.step_labels = {}
        steps = [
            ("omniroute", "Démarrage du proxy OmniRoute AI (Port 3000)"),
            ("backend", "Lancement du serveur Backend FastAPI"),
            ("frontend", "Initialisation de l'interface utilisateur")
        ]
        
        for key, text in steps:
            row = tk.Frame(self.steps_frame, bg="#0f172a")
            row.pack(fill="x", pady=6)
            lbl_icon = tk.Label(row, text="⏳", font=("Segoe UI", 13), fg="#eab308", bg="#0f172a", width=3)
            lbl_icon.pack(side="left")
            tk.Label(row, text=text, font=("Segoe UI", 11, "bold"), fg="#cbd5e1", bg="#0f172a").pack(side="left")
            self.step_labels[key] = lbl_icon

        self.tips = [
            "💡 Astuce : Importez vos prospects en un clic via un fichier CSV.",
            "💡 Astuce : OmniRoute optimise vos requêtes IA en arrière-plan.",
            "💡 Astuce : Personnalisez vos pitchs commerciaux grâce à l'IA.",
            "💡 Astuce : Le tableau de bord s'actualise en temps réel.",
            "💡 Astuce : SilaLink fonctionne entièrement en local pour votre sécurité."
        ]
        self.tip_index = 0
        self.tip_label = tk.Label(self.root, text=self.tips[0], font=("Segoe UI", 12, "bold", "italic"), fg="#fef08a", bg="#0f172a")
        self.tip_label.pack(pady=(15, 10))

        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar", thickness=8, background="#38bdf8", troughcolor="#1e293b")
        
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=520, mode="determinate", maximum=100)
        self.progress.pack(pady=5)
        
        self.start_time = time.time()
        self.estimated_time = 25.0
        self.timer_running = True
        self.timer_label = tk.Label(self.root, text="Chargement : 0%  |  Temps écoulé : 0.0s  |  Estimé : ~25s", font=("Consolas", 10, "bold"), fg="#cbd5e1", bg="#0f172a")
        self.timer_label.pack(pady=(5, 10))
        
        self.log_widget = scrolledtext.ScrolledText(self.root, height=5, width=65, bg="#020617", fg="#f87171", font=("Consolas", 8))
        self.log_widget.pack(pady=5)
        self.log_widget.pack_forget()

        self.is_success = False
        self.final_url = ""

        self.update_timer()
        self.animate_spinner()
        self.rotate_tips()

    def animate_spinner(self):
        if not self.timer_running: return
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
        self.spinner_label.config(text=self.spinner_frames[self.spinner_idx])
        self.root.after(80, self.animate_spinner) # 80ms par frame pour une rotation fluide

    def rotate_tips(self):
        if not self.timer_running: return
        self.tip_index = (self.tip_index + 1) % len(self.tips)
        self.tip_label.config(text=self.tips[self.tip_index])
        self.root.after(3500, self.rotate_tips)

    def update_timer(self):
        if self.timer_running:
            elapsed = time.time() - self.start_time
            progress_val = min((elapsed / self.estimated_time) * 100, 95)
            self.progress["value"] = progress_val
            
            self.timer_label.config(text=f"Chargement : {int(progress_val)}%  |  Temps écoulé : {elapsed:.1f}s  |  Estimé : ~{int(self.estimated_time)}s")
            self.root.after(100, self.update_timer)

    def update_step(self, key, state):
        if state == "success":
            self.step_labels[key].config(text="✔️", fg="#22c55e")
        elif state == "error":
            self.step_labels[key].config(text="❌", fg="#ef4444")

    def show_error(self, message):
        self.timer_running = False
        self.progress.stop()
        self.progress.pack_forget()
        self.tip_label.pack_forget()
        self.spinner_label.pack_forget()
        self.log_widget.pack(pady=5, padx=30, fill="both")
        self.log_widget.insert(tk.END, f"[ERREUR CRITIQUE]\n{message}")
        self.log_widget.config(state=tk.DISABLED)
        tk.Button(self.root, text="Fermer", bg="#ef4444", fg="white", font=("Segoe UI", 10, "bold"), command=self.root.destroy).pack(pady=5)

def pipeline_lancement(splash):
    CREATE_NO_WINDOW = 0x08000000
    
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0

    port_omniroute = 3000
    port_fastapi = get_free_port()
    port_frontend = get_free_port()

    config_js_path = os.path.join(FRONTEND_DIR, "public", "config.js")
    os.makedirs(os.path.dirname(config_js_path), exist_ok=True)
    with open(config_js_path, "w", encoding="utf-8") as f:
        f.write(f"window.API_URL = 'http://127.0.0.1:{port_fastapi}';\n")

    # 1. Démarrage OmniRoute
    try:
        cmd_omni = 'node server.js'
        target_dir = OMNIROUTE_STANDALONE_DIR
        if not os.path.exists(target_dir):
            target_dir = OMNIROUTE_DIR

        subprocess.Popen(
            f'cmd.exe /c "{cmd_omni}"',
            cwd=target_dir,
            shell=True,
            creationflags=CREATE_NO_WINDOW,
            startupinfo=startupinfo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        omniroute_ready = False
        for _ in range(150):
            if is_port_listening(port_omniroute):
                omniroute_ready = True
                break
            time.sleep(0.3)
            
        if not omniroute_ready:
            raise Exception(f"OmniRoute standalone n'a pas répondu sur le port {port_omniroute} après 45s.")
            
        splash.root.after(0, lambda: splash.update_step("omniroute", "success"))
    except Exception as e:
        splash.root.after(0, lambda: splash.update_step("omniroute", "error"))
        splash.root.after(0, lambda: splash.show_error(f"Échec OmniRoute:\n{str(e)}"))
        return

    # 2. Démarrage FastAPI
    try:
        cmd_api = f'call "{VENV_ACTIVATE}" && set OMNIROUTE_PORT={port_omniroute}&& uvicorn main:app --host 127.0.0.1 --port {port_fastapi}'
        subprocess.Popen(
            f'cmd.exe /c "{cmd_api}"',
            cwd=BACKEND_DIR,
            shell=True,
            creationflags=CREATE_NO_WINDOW,
            startupinfo=startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        fastapi_ready = False
        for _ in range(60):
            try:
                if requests.get(f"http://127.0.0.1:{port_fastapi}/health", timeout=0.5).status_code == 200:
                    fastapi_ready = True
                    break
            except Exception:
                pass
            time.sleep(0.2)
            
        if not fastapi_ready:
            raise Exception("FastAPI a démarré mais l'endpoint n'a pas répondu dans le délai imparti.")
            
        splash.root.after(0, lambda: splash.update_step("backend", "success"))
    except Exception as e:
        splash.root.after(0, lambda: splash.update_step("backend", "error"))
        splash.root.after(0, lambda: splash.show_error(f"Échec Backend FastAPI:\n{str(e)}"))
        return

    # 3. Démarrage Frontend Vite
    try:
        cmd_front = f'npm.cmd run dev -- --host 127.0.0.1 --port {port_frontend} --strictPort'
        subprocess.Popen(
            f'cmd.exe /c "{cmd_front}"',
            cwd=FRONTEND_DIR,
            shell=True,
            creationflags=CREATE_NO_WINDOW,
            startupinfo=startupinfo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        frontend_ready = False
        for _ in range(60):
            if is_port_listening(port_frontend):
                frontend_ready = True
                break
            time.sleep(0.2)
            
        if not frontend_ready:
            raise Exception(f"Le serveur Frontend n'a pas répondu sur le port {port_frontend}.")
            
        splash.root.after(0, lambda: splash.update_step("frontend", "success"))
    except Exception as e:
        splash.root.after(0, lambda: splash.update_step("frontend", "error"))
        splash.root.after(0, lambda: splash.show_error(f"Échec Frontend Vite:\n{str(e)}"))
        return

    # Fin avec succès
    splash.timer_running = False
    splash.root.after(0, lambda: splash.progress.config(value=100))
    splash.root.after(0, lambda: splash.timer_label.config(text="Chargement : 100%  |  Lancement de SilaLink...", fg="#22c55e"))
    
    time.sleep(1.2)
    splash.final_url = f"http://127.0.0.1:{port_frontend}"
    splash.is_success = True
    splash.root.after(0, splash.root.destroy)

if __name__ == "__main__":
    try:
        myappid = 'silalink.crm.desktop.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    splash = SplashScreen()
    threading.Thread(target=pipeline_lancement, args=(splash,), daemon=True).start()
    splash.root.mainloop()
    
    if splash.is_success and splash.final_url:
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(os.path.dirname(sys.executable), "silalink.ico")
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "silalink.ico")

        webview.create_window(
            title="SiLaLinK CRM — Application Desktop",
            url=splash.final_url,
            width=1280,
            height=800,
            min_size=(1024, 720),
            confirm_close=True
        )
        webview.start(icon=ICON_PATH)
        
        CREATE_NO_WINDOW = 0x08000000
        subprocess.run("taskkill /F /IM node.exe", shell=True, creationflags=CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run("taskkill /F /IM python.exe", shell=True, creationflags=CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)