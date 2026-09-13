import os
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Ce "scope" donne l'autorisation de créer et gérer des brouillons
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

def get_gmail_service():
    """Gère l'authentification OAuth2 avec Google et retourne le service Gmail."""
    creds = None
    # Vérifie si on a déjà un token d'accès sauvegardé
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
    # Si aucun token valide, on lance le flux d'authentification
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # Ouvre le navigateur pour demander l'autorisation à l'utilisateur
            creds = flow.run_local_server(port=0)
        # Sauvegarde le token pour la prochaine fois
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)

def create_gmail_draft(service, to_email, subject, message_text):
    """Crée un brouillon dans Gmail et retourne son identifiant unique."""
    message = EmailMessage()
    message.set_content(message_text)
    message['To'] = to_email
    message['Subject'] = subject

    # Encodage requis par l'API Gmail
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'message': {'raw': encoded_message}}
    
    draft = service.users().drafts().create(userId="me", body=create_message).execute()
    return draft['id']

def delete_gmail_draft(service, draft_id: str):
    """
    Supprime un brouillon dans Gmail en utilisant son draft_id.
    """
    try:
        service.users().drafts().delete(userId='me', id=draft_id).execute()
        return True
    except Exception as e:
        print(f"Erreur lors de la suppression du brouillon Gmail {draft_id}: {str(e)}")
        raise e