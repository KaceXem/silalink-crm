import re
import requests
from bs4 import BeautifulSoup

def search_companies(query, max_results=3):
    """
    Simule une recherche en ligne pour trouver des entreprises cibles.
    Pour une vraie production, utilisez une API de recherche (ex: SerpAPI, Google Custom Search).
    """
    print(f"Recherche en cours pour : {query}...")
    
    # Exemple de sites d'entreprises simulés pour le prototype B2B
    mock_results = [
        {"name": "TechNova Solutions", "url": "https://example.com/contact"},
        {"name": "Global Logistics Corp", "url": "https://example.org/about-us"}
    ]
    
    return mock_results[:max_results]

def extract_emails_from_url(url):
    """
    Visite une URL et extrait les adresses e-mail trouvées sur la page.
    """
    emails = set()
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Expression régulière pour trouver des e-mails
            email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
            found = re.findall(email_pattern, response.text)
            for email in found:
                # Filtrer les faux e-mails (extensions d'images, scripts, etc.)
                if not any(ext in email.lower() for ext in ['.png', '.jpg', '.gif', '.css', '.js']):
                    emails.add(email)
    except Exception as e:
        print(f"Erreur lors du scraping de {url}: {e}")
    
    return list(emails)

def get_b2b_prospects(query):
    """
    Fonction principale combinant recherche et extraction d'e-mails.
    """
    prospects = []
    companies = search_companies(query)
    
    for comp in companies:
        emails = extract_emails_from_url(comp["url"])
        prospects.append({
            "company_name": comp["name"],
            "url": comp["url"],
            "emails": emails if emails else ["contact@example.com"] # Fallback de secours
        })
        
    return prospects

if __name__ == "__main__":
    # Test du scraper
    results = get_b2b_prospects("SaaS B2B logistique")
    print("Résultats du scraping :", results)
