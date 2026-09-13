from crm_api import get_all_prospects_df, update_prospect_status, import_prospects_from_csv
import streamlit as st
import time
from crm_api import get_all_prospects_df, update_prospect_status
from agent import process_prospects_pipeline

# Cycle de vie du prospect (identique à crm_api.py)
STATUS_LIST = ['EN ATTENTE', 'BROUILLON_CREE', 'ENVOYE', 'REPONDU', 'QUALIFIE']

st.set_page_config(page_title="SilaLink CRM", layout="wide")
st.title("Tableau de bord Prospection - SilaLink")

# --- SECTION 1 : PILOTAGE INTERACTIF ---
st.subheader("Contrôle du Pipeline IA")

if st.button("Lancer la génération IA", type="primary"):
    with st.spinner("Génération des brouillons par le LLM (Ollama) en cours..."):
        try:
            resultats = process_prospects_pipeline()
            if resultats is not None:
                st.success(f"Génération terminée : {resultats['success']} brouillons, {resultats['errors']} erreurs, {resultats['skipped']} ignorés.")
            else:
                st.warning("Aucune métrique retournée. Vérifiez le retour de process_prospects_pipeline().")
            time.sleep(2)
        except Exception as e:
            st.error(f"Erreur d'exécution : {str(e)}")
            time.sleep(3)
    st.rerun()

st.divider()

# --- SECTION 2 : VISUALISATION DES DONNÉES ---
try:
    df = get_all_prospects_df()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Prospects", len(df))
    col2.metric("Brouillons Créés", len(df[df['statut'] == 'BROUILLON_CREE']))
    col3.metric("En Attente", len(df[df['statut'] == 'EN ATTENTE']))
    
    st.subheader("Pipeline Commercial")
    st.dataframe(df, width='stretch')
    st.divider()

    # --- SECTION 4 : INGESTION DE DONNÉES ---
    st.subheader("Importation de nouveaux prospects")
    
    uploaded_file = st.file_uploader("Importer un fichier prospects.csv", type=["csv"])
    
    if uploaded_file is not None:
        if st.button("Lancer l'importation", type="secondary"):
            with st.spinner("Analyse et insertion sécurisée en cours..."):
                try:
                    metrics = import_prospects_from_csv(uploaded_file)
                    st.success(f"Import terminé : {metrics['added']} ajoutés, {metrics['duplicates']} doublons ignorés, {metrics['errors']} rejets.")
                    time.sleep(2.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Échec de l'importation : {str(e)}")
    st.divider()
    

    # --- SECTION 3 : GESTION MANUELLE (CRM) ---
    st.subheader("Mise à jour d'un prospect")
    
    if not df.empty:
        # 1. Sélection ciblée : Concaténation de l'ID, de l'entreprise et du contact pour la lisibilité
        prospect_options = df.apply(lambda row: f"{row['id']} - {row['entreprise']} ({row['contact']})", axis=1).tolist()
        selected_option = st.selectbox("Sélectionner un prospect :", prospect_options)
        
        # Extraction de l'ID de la chaîne de caractères
        selected_id = int(selected_option.split(" - ")[0])
        prospect_data = df[df['id'] == selected_id].iloc[0]
        
        # Affichage des métadonnées du prospect sélectionné
        st.caption(f"Email : {prospect_data['email']} | Statut actuel : {prospect_data['statut']} | Dernière mise à jour : {prospect_data['updated_at']}")
        
        # 2. Formulaire de mise à jour
        col_select, col_btn = st.columns([3, 1])
        with col_select:
            # Détermination de l'index du statut actuel pour l'afficher par défaut
            try:
                default_index = STATUS_LIST.index(prospect_data['statut'])
            except ValueError:
                default_index = 0
                
            new_status = st.selectbox("Nouveau statut :", STATUS_LIST, index=default_index)
            
        with col_btn:
            st.write("") # Alignement vertical
            st.write("")
            if st.button("Mettre à jour le statut"):
                if new_status == prospect_data['statut']:
                    st.info("Le statut sélectionné est identique au statut actuel.")
                else:
                    # 3. Connexion Backend et Actualisation
                    success = update_prospect_status(selected_id, new_status)
                    if success:
                        st.success(f"Mise à jour réussie : ID {selected_id} -> {new_status}")
                        time.sleep(1) # Laisse le temps à l'utilisateur de lire le message
                        st.rerun()    # Rafraîchissement forcé de l'état de l'interface
                    else:
                        st.error("Échec : La base de données n'a pas pu être mise à jour.")
    else:
        st.info("La base de données est vide. Aucun prospect à modifier.")

except Exception as e:
    st.error(f"Impossible de lire la base de données : {str(e)}")
