import csv
import re
import logging
from io import StringIO
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = 'prospects_test.db'

# Cycle de vie strict du prospect (Pipeline commercial)
VALID_STATUSES = [
    'EN ATTENTE',      # Import initial
    'BROUILLON_CREE',  # Traité par le LLM
    'ENVOYE',          # Validation manuelle effectuée
    'REPONDU',         # Interaction du prospect
    'QUALIFIE'         # Opportunité commerciale confirmée
]

def upgrade_crm_schema():
    """
    Met à jour la table SQLite existante pour inclure la traçabilité temporelle.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE prospects ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
        conn.commit()
        print("[CRM] Schéma mis à jour : Colonne 'updated_at' ajoutée.")
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()

def get_all_prospects_df():
    """Récupère l'intégralité du pipeline sous forme de DataFrame Pandas."""
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT * FROM prospects ORDER BY updated_at DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_prospects_by_status_df(status):
    """Récupère un sous-ensemble de prospects filtré par statut."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Statut invalide. Utilisez l'un de ces statuts : {VALID_STATUSES}")
        
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT * FROM prospects WHERE statut = ?"
    df = pd.read_sql_query(query, conn, params=(status,))
    conn.close()
    return df

def update_prospect_status(prospect_id, new_status, draft_id=None):
    """
    Modifie le statut d'un prospect. Si draft_id est fourni, met également à jour l'ID du brouillon.
    """
    if new_status not in VALID_STATUSES:
        print(f"[Erreur CRM] Rejet de la mise à jour : Le statut '{new_status}' n'est pas reconnu.")
        return False

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if draft_id:
        cursor.execute("""
            UPDATE prospects 
            SET statut = ?, updated_at = ?, brouillon = ?
            WHERE id = ?
        """, (new_status, current_time, str(draft_id), prospect_id))
    else:
        cursor.execute("""
            UPDATE prospects 
            SET statut = ?, updated_at = ?
            WHERE id = ?
        """, (new_status, current_time, prospect_id))
        
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if rows_affected > 0:
        return True
    else:
        print(f"[Erreur CRM] Aucun prospect trouvé avec l'ID {prospect_id}.")
        return False

def validate_email_strict(email):
    """Valide le format de l'adresse e-mail via regex."""
    if not email: return False
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email.strip()) is not None

def import_prospects_from_csv(uploaded_file):
    """
    Importe un fichier CSV via Pandas avec contrainte d'unicité SQL native.
    """
    added_count = 0
    duplicate_count = 0
    error_count = 0
    
    try:
        df_import = pd.read_csv(uploaded_file, encoding='utf-8-sig', sep=None, engine='python')
    except Exception:
        try:
            uploaded_file.seek(0)
            df_import = pd.read_csv(uploaded_file, encoding='latin-1', sep=None, engine='python')
        except Exception as e:
            logging.error(f"[Upload] Erreur critique de lecture du fichier : {str(e)}")
            raise ValueError("Impossible de lire le fichier CSV. Vérifiez son encodage.")

    # Normalisation des entêtes de colonnes
    df_import.columns = [col.strip().lower() for col in df_import.columns]
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for index, row in df_import.iterrows():
        row_num = index + 2
        entreprise = str(row.get('company_name', row.get('entreprise', ''))).strip()
        contact = str(row.get('contact_name', row.get('contact', ''))).strip()
        role = str(row.get('role', '')).strip()
        email = str(row.get('email', '')).strip()
        contexte_metier = str(row.get('context', row.get('contexte_metier', ''))).strip()
        solution = str(row.get('custom_solution', row.get('solution', ''))).strip()
        
        # 1. Validation des champs obligatoires
        if not entreprise or entreprise == 'nan' or not contact or contact == 'nan' or not solution or solution == 'nan' or not email or email == 'nan':
            logging.error(f"[Upload - Ligne {row_num}] Rejet : Champs obligatoires manquants.")
            error_count += 1
            continue
            
        # 2. Validation stricte de l'e-mail
        if not validate_email_strict(email):
            logging.error(f"[Upload - Ligne {row_num}] Rejet : E-mail invalide '{email}'.")
            error_count += 1
            continue
            
        # 3. Insertion en base sécurisée par la contrainte SQL UNIQUE sur l'e-mail
        try:
            cursor.execute('''
                INSERT INTO prospects (entreprise, contact, role, email, contexte_metier, solution, statut)
                VALUES (?, ?, ?, ?, ?, ?, 'EN ATTENTE')
            ''', (entreprise, contact, role, email, contexte_metier, solution))
            added_count += 1
        except sqlite3.IntegrityError:
            # Capturé nativement par la contrainte UNIQUE SQL si l'email existe déjà
            duplicate_count += 1
        
    conn.commit()
    conn.close()
    
    return {"added": added_count, "duplicates": duplicate_count, "errors": error_count}
