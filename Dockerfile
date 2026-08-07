FROM node:18-alpine AS build

WORKDIR /app

# Copier package.json et package-lock.json
COPY package*.json ./

# Installer les dépendances
RUN npm install

# Copier le code source
COPY . .

# Create dynamic version file before build
# This creates src/version.js with a new timestamp or Git commit hash each build
ARG BUILD_VERSION
RUN echo "export const APP_VERSION = '${BUILD_VERSION:-$(date +%Y.%m.%d-%H%M%S)}';" > src/version.js

COPY template/background.png /app/template/background.png
COPY template/person.png /app/template/person.png

# Construire l'application
RUN npm run build

# Stage de production avec Python et Flask
FROM python:3.9-alpine

WORKDIR /app

# Python 3.9 inclut déjà SQLite, pas besoin d'installation séparée

# Installer les dépendances Python
RUN pip install flask flask-cors pyjwt Pillow requests flask-limiter redis pyotp qrcode[pil] numpy

# Copier les fichiers construits depuis le stage de build
COPY --from=build /app/dist ./dist

# Copier le backend Python
COPY server.py auth.py auth_routes.py image_metrics.py operagallery_service.py operagallery_integration.py image_quality_checker.py email_service.py totp_service.py migrate_totp.py filemaker_cache_service.py search_operacrm_corrected.py operacrm_service.py artist_indexer.py start_indexer.py quick_fallback.py crm_api.py filemaker_service.py certificate_service.py fm_client.py ./

# Copier les fichiers CSV nécessaires
COPY ../images_catalog.csv ./
COPY ../list-url-id.csv ./
COPY image_processor.py ./

# Créer le répertoire pour la base de données
RUN mkdir -p /app/data

# Exposer le port
EXPOSE 5001

# Définir les variables d'environnement
ENV FLASK_APP=server.py
ENV FLASK_ENV=production

# Démarrer le serveur Flask
CMD ["python", "server.py"]
