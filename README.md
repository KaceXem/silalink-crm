# SilaLink CRM — Plateforme de Prospection B2B

## 1. Vision et Objectif
SilaLink CRM est une solution logicielle B2B conçue pour automatiser et hyper-personnaliser les campagnes d'acquisition. Le système couvre le flux complet : de l'importation de fichiers CSV à la génération de pitchs via l'intelligence artificielle, jusqu'à l'injection directe des brouillons dans la messagerie Gmail du commercial.

## 2. Architecture Technique
Le système s'articule autour de trois micro-services interconnectés, supervisés par un orchestrateur local gérant l'allocation dynamique des ports TCP (Service Discovery) pour éliminer les conflits.

*   **Frontend (Interface Web) :** React, TypeScript, Vite, Axios.
*   **Backend (Logique & Données) :** Python, FastAPI, Pandas (parsing CSV).
*   **Base de Données :** SQLite embarquée (`prospects_test.db`).
*   **Proxy Inférence IA :** OmniRoute (environnement Node.js).
*   **Orchestration Windows :** Application graphique Tkinter (`hub_launcher.py`) exécutée en mode silencieux via VBScript (`SilaLink Hub.vbs`).

## 3. Prérequis et Dépendances
*Hypothèse : Les environnements de base sont déjà installés sur la machine hôte.*
*   **Python 3.x** avec un environnement virtuel configuré (`venv`).
*   **Node.js** (requis pour Vite et OmniRoute).
*   **API Google Workspace** (Tokens de connexion actifs pour `gmail_service.py`).
*   **Clé API OmniRoute** valide (doit être configurée dans le backend, idéalement via variable d'environnement).

## 4. Démarrage et Utilisation
Le système est conçu pour être lancé via un point d'entrée unique qui gère l'injection des variables d'environnement (`VITE_API_URL`, `OMNIROUTE_PORT`).

1. Lancer le raccourci **`SilaLink Hub.vbs`**.
2. L'interface de supervision teste l'ouverture des sockets dynamiques en tâche de fond (processus masqués `CREATE_NO_WINDOW`).
3. Attendre que les trois indicateurs passent au statut **OPÉRATIONNEL**.
4. Cliquer sur **Ouvrir SilaLink CRM** pour accéder à l'interface sur le port dynamique généré.
5. **Arrêt :** Utiliser exclusivement le bouton d'arrêt du Hub pour garantir la fermeture des processus orphelins (node.exe, python.exe).

## 5. Limites connues et Sécurité
*   Les clés d'API (OmniRoute, Google) ne doivent pas être exposées en clair dans les fichiers source lors d'un déploiement en production.
*   Le système de nettoyage des ports `taskkill` ferme tous les processus `node.exe` et `python.exe` de l'utilisateur de manière indiscriminée à la fermeture du Hub.