#!/bin/bash
# Lancer le serveur ollama
nohup ollama serve &

# Attendre que le serveur soit prêt
sleep 5

# Télécharger les modèles
# ollama pull gemma:2b
models=("gemma:2b" "deepseek-r1:1.5b" "llama3.2:1b")

for model in "${models[@]}"; do
    ollama pull "$model"
done

# Démarrer le processus principal (par exemple le serveur)
tail -f /dev/null