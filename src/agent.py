import os
import csv
import json
import time
import sqlite3
import logging
import re
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from gmail_auth import create_gmail_draft

# Importation de l'interface CRM
from crm_api import upgrade_crm_schema, update_prospect_status

# Chargement des variables d'environnement
load_dotenv()

# Configuration de la journalisation structurée (Console INFO + Fichier ERROR.log)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('error.log', encoding='utf-8')
    ]
)

# Configuration du client OpenAI pointant vers l'instance locale / Omniroute
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:20128/v1"),
    api_key=os.getenv("OMNIROUTE_API_KEY", "dummy-token")
)

DB_NAME = 'prospects_test.db'

def validate_email_strict(email):
    """
    Validation stricte du format de l'adresse e-mail à l'aide d'une expression régulière robuste.
    """
    if not email:
        return False
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email.strip()) is not None

def init_database_with_strict_filtering(csv_path='prospects.csv'):
    """
    Initialise la base de données SQLite avec la contrainte UNIQUE sur l'email
    et applique le filtrage amont rigoureux lors de l'import initial.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # CONTRAINTE D'UNICITÉ SQL SUR LA COLONNE EMAIL
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
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Vérification si la base est vide pour lancer l'import initial filtré
    cursor.execute('SELECT COUNT(*) FROM prospects')
    count = cursor.fetchone()[0]
    
    inserted_count = 0
    rejected_count = 0
    
    if count == 0 and os.path.exists(csv_path):
        logging.info(f"Base de données vide. Import et filtrage amont depuis {csv_path}...")
        with open(csv_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row_index, row in enumerate(reader, start=2):
                entreprise = row.get('company_name', '').strip()
                contact = row.get('contact_name', '').strip()
                role = row.get('role', '').strip()
                email = row.get('email', '').strip()
                contexte_metier = row.get('context', '').strip()
                solution = row.get('custom_solution', '').strip()
                
                # 1. Contrôle des champs obligatoires
                if not entreprise or not contact or not solution or not email:
                    err_msg = f"[Rejet Amont - Ligne {row_index}] Email: '{email}' | Motif: Champs obligatoires manquants"
                    logging.error(err_msg)
                    rejected_count += 1
                    continue
                
                # 2. Validation stricte des e-mails par Regex
                if not validate_email_strict(email):
                    err_msg = f"[Rejet Amont - Ligne {row_index}] Email: '{email}' | Motif: Format d'adresse e-mail invalide"
                    logging.error(err_msg)
                    rejected_count += 1
                    continue
                
                # 3. Insertion sécurisée par la contrainte UNIQUE SQL
                try:
                    cursor.execute('''
                        INSERT INTO prospects (entreprise, contact, role, email, contexte_metier, solution, statut)
                        VALUES (?, ?, ?, ?, ?, ?, 'EN ATTENTE')
                    ''', (entreprise, contact, role, email, contexte_metier, solution))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    logging.warning(f"[Doublon SQL - Ligne {row_index}] L'e-mail '{email}' existe déjà.")
                    rejected_count += 1
                    
            conn.commit()
        logging.info(f"Import initial terminé. {inserted_count} prospects insérés, {rejected_count} rejetés.")
    
    conn.close()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((json.JSONDecodeError, ValueError, Exception)),
    reraise=True
)
def generate_personalized_pitch_with_retry(entreprise, contact, role, contexte_metier, solution):
    """
    Génère le pitch commercial via le LLM avec une structure JSON stricte et réessais automatiques.
    """
    prompt = f"""
    Tu es EL HOUAT AHMED BELKACEM LADJEL, courtier agro-industrie chez SilaLink.
    Rédige un e-mail de prospection B2B ultra-personnalisé.
    
    Destinataire : {contact}, {role} chez {entreprise}.
    Contexte connu sur eux : {contexte_metier}.
    Solution / Produit proposé : {solution}.
    
    Règles strictes :
    1. Salutation : "Bonjour {contact},"
    2. Utilise le 'Contexte connu' dès la première phrase.
    3. Présente l'avantage de la solution proposée.
    4. Appel à l'action : Propose un appel de 10 min.
    5. Signature : 
       Cordialement,
       EL HOUAT AHMED BELKACEM LADJEL | SilaLink
    
    Réponds uniquement avec ce JSON :
    {{
      "subject": "Objet court et percutant...",
      "body": "Corps de l'e-mail..."
    }}
    """
    
    response = client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        timeout=30
    )
    
    content = response.choices[0].message.content
    data = json.loads(content)
    
    if "subject" not in data or "body" not in data:
        raise ValueError("Le JSON retourné ne contient pas les clés 'subject' ou 'body'.")
        
    return data

def process_prospects_pipeline():
    """
    Orchestre l'initialisation filtrée, la lecture de SQLite, les appels LLM, 
    la création de brouillons et le rapport final avec journalisation structurée.
    """
    init_database_with_strict_filtering()
    upgrade_crm_schema()
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM prospects WHERE statut = 'EN ATTENTE'")
    prospects = cursor.fetchall()
    
    success_count = 0
    llm_error_count = 0
    skipped_count = 0
    
    logging.info(f"Début du traitement du pipeline pour {len(prospects)} prospects en attente...")
    
    for row in prospects:
        prospect_id = row['id']
        entreprise = row['entreprise']
        contact = row['contact']
        role = row['role']
        email = row['email']
        contexte_metier = row['contexte_metier']
        solution = row['solution']
        
        logging.info(f"Traitement ID {prospect_id} : {contact} ({email}) chez {entreprise}")
        
        try:
            pitch = generate_personalized_pitch_with_retry(entreprise, contact, role, contexte_metier, solution)
        except Exception as e:
            err_msg = f"ID {prospect_id} ({email}) : Échec persistant LLM/JSON après réessais. Erreur : {str(e)}"
            logging.error(err_msg)
            llm_error_count += 1
            time.sleep(2)
            continue
            
        draft = create_gmail_draft(to=email, subject=pitch['subject'], body=pitch['body'])
        if draft:
            draft_id = draft['id']
            logging.info(f"Brouillon Gmail créé avec succès (ID: {draft_id}) pour le prospect ID {prospect_id}.")
            update_prospect_status(prospect_id, 'BROUILLON_CREE', draft_id)
            success_count += 1
        else:
            err_msg = f"ID {prospect_id} ({email}) : Impossible de créer le brouillon via l'API Gmail."
            logging.error(err_msg)
            
        time.sleep(2)
        
    conn.close()
    
    logging.info("="*50)
    logging.info("RAPPORT DE FIN D'EXÉCUTION DU PIPELINE DE PROSPECTION")
    logging.info(f"* Succès (Brouillons créés) : {success_count}")
    logging.info(f"* Erreurs LLM rencontrées   : {llm_error_count}")
    logging.info("="*50)
    
    return {"success": success_count, "errors": llm_error_count, "skipped": skipped_count}

if __name__ == "__main__":
    process_prospects_pipeline()
