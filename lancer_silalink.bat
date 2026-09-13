@echo off
TITLE SilaLink - Surveillance et Lancement Automatique
echo ========================================================
echo [1/4] Lancement d'Omniroute...
start /min cmd /c "omniroute start"

:: Attente de 5 secondes pour laisser le temps à Omniroute de démarrer
timeout /t 5 /nobreak >nul

echo [2/4] Test de connexion et authentification Omniroute...
curl -s -X POST "http://localhost:20128/login" -H "Content-Type: application/json" -d "{\"password\":\"    \"}" >nul
if %errorlevel% neq 0 (
    echo [ATTENTION] Impossible de joindre Omniroute sur le port 20128 !
) else (
    echo [OK] Omniroute est actif et connecte.
)

echo [3/4] Démarrage du backend FastAPI (Uvicorn)...
cd /d "C:\Users\USER\Desktop\prototype B2B - Modernisation\src"
call "..\venv\Scripts\activate"
start /min cmd /c "uvicorn main:app --host 127.0.0.1 --port 8000"

:: Attente de 3 secondes pour l'initialisation de FastAPI
timeout /t 3 /nobreak >nul

:: Test de santé de l'API FastAPI
echo Verification de la reponse du serveur FastAPI...
curl -s "http://127.0.0.1:8000/health" >nul
if %errorlevel% neq 0 (
    echo [ERREUR] Le serveur FastAPI ne repond pas sur le port 8000 !
    echo Verifiez s'il y a un conflit ou une erreur dans main.py.
) else (
    echo [OK] FastAPI repond correctement.
    echo [4/4] Ouverture de Swagger UI dans le navigateur...
    start http://127.0.0.1:8000/docs
)

echo ========================================================
echo Processus de verification termine.
echo ========================================================
pause