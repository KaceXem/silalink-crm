import requests

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("--- 1. Vérification du statut de l'API ---")
    health = requests.get(f"{BASE_URL}/health")
    print(health.json())

    print("\n--- 2. Récupération des prospects ---")
    response = requests.get(f"{BASE_URL}/prospects")
    
    # Sécurité : on vérifie que le serveur a bien répondu avec un succès (200)
    if response.status_code != 200:
        print(f"ÉCHEC DU SERVEUR (Code {response.status_code}) : {response.text}")
        return

    prospects = response.json()
    print(f"Nombre de prospects dans la base sandbox : {len(prospects)}")

    if prospects:
        target_id = prospects[0]["id"]
        print(f"\n--- 3. Test de génération de pitch pour le prospect ID {target_id} ---")
        gen_response = requests.post(f"{BASE_URL}/prospects/{target_id}/generate")
        
        if gen_response.status_code != 200:
            print(f"ERREUR IA (Code {gen_response.status_code}) : {gen_response.text}")
        else:
            print(gen_response.json())
    else:
        print("\nAucun prospect disponible pour tester la génération IA. Importez un CSV d'abord.")

if __name__ == "__main__":
    run_tests()
