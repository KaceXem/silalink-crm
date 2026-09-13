import os
import re
import sqlite3
import appdirs  # <-- Ajout de la bibliothèque pour la gestion sécurisée des dossiers
from datetime import datetime
from typing import Optional
from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import requests

from gmail_service import get_gmail_service, create_gmail_draft, delete_gmail_draft

# ==========================================
# CONFIGURATION & CONSTANTES
# ==========================================
OMNIRUTE_API_KEY = "sk-de8ce7dc6dc32d2e-875f34-6b667bd4"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "silalink-frontend", "dist"))

# --- REDIRECTION SÉCURISÉE DE LA BASE DE DONNÉES (AppData) ---
app_name = "SilaLinkCRM"
data_dir = appdirs.user_data_dir(app_name)
os.makedirs(data_dir, exist_ok=True) # Crée le dossier utilisateur s'il n'existe pas
DB_NAME = os.path.join(data_dir, 'prospects_test.db')
# -------------------------------------------------------------

VALID_STATUSES = [
    'EN ATTENTE',
    'BROUILLON_CREE',
    'ENVOYE',
    'REPONDU',
    'QUALIFIE'
]

# ==========================================
# INSTANCIATION DE L'APPLICATION FASTAPI
# ==========================================
app = FastAPI(
    title="SilaLink CRM API",
    description="Backend de modernisation pour le CRM B2B SilaLink",
    version="2.0.0"
)

# Configuration CORS globale
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# BASE DE DONNÉES & UTILITAIRES
# ==========================================
def init_test_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entreprise TEXT NOT NULL,
            contact TEXT NOT NULL,
            role TEXT,
            email TEXT UNIQUE NOT NULL,
            contexte_metier TEXT,
            solution TEXT NOT NULL,
            statut TEXT DEFAULT 'EN ATTENTE',
            brouillon TEXT,
            pitch_genere TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        cursor.execute("ALTER TABLE prospects ADD COLUMN pitch_genere TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_test_db()

def validate_email_strict(email: str) -> bool:
    if not email:
        return False
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email.strip()) is not None


# ==========================================
# ROUTES API REST
# ==========================================

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Bienvenue sur l'API de SilaLink - Architecture FastAPI dynamique"
    }

@app.get("/health")
def health_check():
    return {"database": DB_NAME, "mode": "sandbox"}

@app.get("/prospects")
def get_prospects():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prospects ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'accès à la base de données : {str(e)}")

@app.get("/prospects/{prospect_id}")
def get_prospect_by_id(prospect_id: int):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,))
    prospect = cursor.fetchone()
    conn.close()
    
    if not prospect:
        raise HTTPException(status_code=404, detail=f"Prospect ID {prospect_id} introuvable.")
    
    return dict(prospect)

@app.post("/prospects/import")
async def import_prospects(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        try:
            df_import = pd.read_csv(BytesIO(contents), encoding='utf-8-sig', sep=None, engine='python')
        except Exception:
            df_import = pd.read_csv(BytesIO(contents), encoding='latin-1', sep=None, engine='python')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Impossible de lire le fichier CSV : {str(e)}")

    df_import.columns = [col.strip().lower() for col in df_import.columns]

    added_count = 0
    duplicate_count = 0
    error_count = 0

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    for _, row in df_import.iterrows():
        entreprise = str(row.get('company_name', row.get('entreprise', ''))).strip()
        contact = str(row.get('contact_name', row.get('contact', ''))).strip()
        role = str(row.get('role', '')).strip()
        email = str(row.get('email', '')).strip()
        contexte_metier = str(row.get('context', row.get('contexte_metier', ''))).strip()
        solution = str(row.get('custom_solution', row.get('solution', ''))).strip()

        if not entreprise or entreprise == 'nan' or not contact or contact == 'nan' or not solution or solution == 'nan' or not email or email == 'nan':
            error_count += 1
            continue

        if not validate_email_strict(email):
            error_count += 1
            continue

        try:
            cursor.execute('''
                INSERT INTO prospects (entreprise, contact, role, email, contexte_metier, solution, statut)
                VALUES (?, ?, ?, ?, ?, ?, 'EN ATTENTE')
            ''', (entreprise, contact, role, email, contexte_metier, solution))
            added_count += 1
        except sqlite3.IntegrityError:
            duplicate_count += 1

    conn.commit()
    conn.close()

    return {
        "filename": file.filename,
        "added": added_count,
        "duplicates": duplicate_count,
        "errors": error_count
    }

@app.patch("/prospects/{prospect_id}/status")
def update_status(prospect_id: int, new_status: str = Form(...), draft_id: Optional[str] = Form(None)):
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Choisissez parmi : {VALID_STATUSES}")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if draft_id:
        cursor.execute("""
            UPDATE prospects 
            SET statut = ?, updated_at = ?, brouillon = ?
            WHERE id = ?
        """, (new_status, current_time, draft_id, prospect_id))
    else:
        cursor.execute("""
            UPDATE prospects 
            SET statut = ?, updated_at = ?
            WHERE id = ?
        """, (new_status, current_time, prospect_id))

    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()

    if rows_affected == 0:
        raise HTTPException(status_code=404, detail=f"Aucun prospect trouvé avec l'ID {prospect_id}.")

    return {
        "success": True,
        "prospect_id": prospect_id,
        "new_status": new_status,
        "draft_id": draft_id,
        "updated_at": current_time
    }

@app.post("/prospects/{prospect_id}/generate")
def generate_prospect_pitch(prospect_id: int):
    """
    Génère le pitch commercial via le proxy LLM OmniRoute, 
    crée un brouillon Gmail et persiste le résultat en base SQLite.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,))
    prospect = cursor.fetchone()
    
    if not prospect:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Prospect ID {prospect_id} introuvable.")
        
    prompt = (
        f"Rédige uniquement le corps d'un e-mail de prospection commerciale professionnel "
        f"à l'attention de {prospect['contact']} ({prospect['role']}) chez {prospect['entreprise']}. "
        f"Contexte métier : {prospect['contexte_metier']}. "
        f"Solution à proposer : {prospect['solution']}. "
        f"Règles strictes et absolues : "
        f"1. Ne mets PAS le nom ou le poste du destinataire au début du message. Commence directement par la formule de civilité (ex: 'Madame Marchand,'). "
        f"2. N'écris JAMAIS les mots 'Objet :', 'Sujet :' ou l'intitulé de l'objet dans le corps du texte. "
        f"3. N'utilise AUCUN formatage Markdown (pas d'étoiles **). "
        f"4. Termine obligatoirement par la signature exacte suivante :\n"
        f"EL HOUAT Ahmed Belkacem Ladjel\n"
        f"Product Engineer\n"
        f"SiLaLinK\n"
        f"Tél : +213549461738\n"
        f"Email : Kacemelhaoute2@gmail.com"
    )
    
    omniroute_port = os.getenv("OMNIROUTE_PORT", "20128")
    omniroute_url = f"http://127.0.0.1:{omniroute_port}/v1/chat/completions"

    try:
        response = requests.post(
            omniroute_url,
            headers={
                "Authorization": f"Bearer {OMNIRUTE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "auto",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60
        )
        
        if response.status_code == 200:
            res_json = response.json()
            pitch_content = res_json['choices'][0]['message']['content']
        else:
            pitch_content = f"Erreur de l'API LLM ({response.status_code}) : {response.text}"
            
    except Exception as e:
        pitch_content = f"Pitch généré en mode hors-ligne. Détail de l'erreur : {str(e)}"

    try:
        gmail_service = get_gmail_service()
        sujet_email = f"Optimisation de vos approvisionnements - {prospect['entreprise']}"
        draft_id = create_gmail_draft(
            service=gmail_service,
            to_email=prospect['email'],
            subject=sujet_email,
            message_text=pitch_content
        )
    except Exception as e:
        draft_id = f"erreur-gmail-{abs(hash(prospect['email']))}"
        print(f"Erreur d'accès à l'API Gmail : {str(e)}")

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        UPDATE prospects 
        SET statut = 'BROUILLON_CREE', brouillon = ?, pitch_genere = ?, updated_at = ?
        WHERE id = ?
    """, (draft_id, pitch_content, current_time, prospect_id))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "prospect_id": prospect_id,
        "entreprise": prospect["entreprise"],
        "draft_id": draft_id,
        "pitch_genere": pitch_content,
        "nouveau_statut": "BROUILLON_CREE",
        "updated_at": current_time
    }

@app.put("/prospects/{prospect_id}/pitch")
def update_prospect_pitch(prospect_id: int, payload: dict):
    """
    Met à jour le texte du pitch en base et met à jour le brouillon Gmail associé.
    """
    nouveau_texte = payload.get("pitch_genere")
    if not nouveau_texte:
        raise HTTPException(status_code=400, detail="Le contenu du pitch est requis.")

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,))
    prospect = cursor.fetchone()
    
    if not prospect:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Prospect ID {prospect_id} introuvable.")

    draft_id = prospect['brouillon']
    
    try:
        if draft_id and not draft_id.startswith("erreur-gmail"):
            gmail_service = get_gmail_service()
            try:
                delete_gmail_draft(gmail_service, draft_id)
            except Exception:
                pass
            sujet_email = f"Optimisation de vos approvisionnements - {prospect['entreprise']}"
            draft_id = create_gmail_draft(
                service=gmail_service,
                to_email=prospect['email'],
                subject=sujet_email,
                message_text=nouveau_texte
            )
    except Exception as e:
        print(f"Erreur lors de la mise à jour du brouillon Gmail : {str(e)}")

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE prospects 
        SET pitch_genere = ?, brouillon = ?, updated_at = ?
        WHERE id = ?
    """, (nouveau_texte, draft_id, current_time, prospect_id))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Pitch et brouillon mis à jour avec succès."}

@app.delete("/prospects/{prospect_id}/draft")
def delete_prospect_draft(prospect_id: int):
    """
    Supprime le brouillon dans Gmail et repasse le statut du prospect à 'EN ATTENTE'.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,))
    prospect = cursor.fetchone()
    
    if not prospect:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Prospect ID {prospect_id} introuvable.")

    draft_id = prospect['brouillon']
    
    try:
        if draft_id and not draft_id.startswith("erreur-gmail"):
            gmail_service = get_gmail_service()
            delete_gmail_draft(gmail_service, draft_id)
    except Exception as e:
        print(f"Erreur suppression brouillon Gmail : {str(e)}")

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE prospects 
        SET statut = 'EN ATTENTE', brouillon = NULL, pitch_genere = NULL, updated_at = ?
        WHERE id = ?
    """, (current_time, prospect_id))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Brouillon supprimé de Gmail et prospect réinitialisé."}

@app.delete("/prospects/{prospect_id}")
def delete_prospect(prospect_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM prospects WHERE id = ?", (prospect_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail=f"Prospect ID {prospect_id} introuvable.")
    
    return {
        "success": True,
        "message": f"Prospect {prospect_id} supprimé avec succès."
    }

# ==========================================
# SERVING REACT FRONTEND (PLUGGED AT THE END)
# ==========================================
if os.path.exists(FRONTEND_DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_react_app(full_path: str):
        file_path = os.path.join(FRONTEND_DIST_DIR, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST_DIR, "index.html"))