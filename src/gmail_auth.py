import os
import base64
from email.message import EmailMessage
import google.auth.transport.requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

# CORRECTION CRITIQUE : Modification du scope pour autoriser la création de brouillons
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = google.oauth2.credentials.Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def create_gmail_draft(to, subject, body):
    """
    Crée un brouillon dans Gmail.
    """
    service = get_gmail_service()
    
    message = EmailMessage()
    message.set_content(body)
    message['To'] = to
    message['Subject'] = subject
    
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'message': {'raw': encoded_message}}
    
    try:
        draft = service.users().drafts().create(userId="me", body=create_message).execute()
        return draft
    except Exception as error:
        print(f"[ERREUR API Gmail] Échec de création du brouillon : {error}")
        return None

def send_gmail_email(to, subject, body):
    """
    Fonction originelle conservée pour historique.
    """
    service = get_gmail_service()
    
    message = EmailMessage()
    message.set_content(body)
    message['To'] = to
    message['Subject'] = subject
    
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'raw': encoded_message}
    
    try:
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        print(f"E-mail envoyé avec succès à {to}! ID: {sent_message['id']}")
        return sent_message
    except Exception as error:
        print(f"Erreur lors de l'envoi : {error}")
        return None

if __name__ == '__main__':
    service = get_gmail_service()
    print("Authentification Gmail réussie !")
