from crm_api import get_all_prospects_df, get_prospects_by_status_df

print("=== TEST 1 : Récupération de tous les prospects ===")
try:
    df_all = get_all_prospects_df()
    print(df_all[['id', 'entreprise', 'statut', 'updated_at']])
except Exception as e:
    print(f"[Erreur] Échec du Test 1 : {e}")

print("\n=== TEST 2 : Filtrage par statut (BROUILLON_CREE) ===")
try:
    df_brouillons = get_prospects_by_status_df('BROUILLON_CREE')
    print(f"Nombre de brouillons trouvés : {len(df_brouillons)}")
except Exception as e:
    print(f"[Erreur] Échec du Test 2 : {e}")
