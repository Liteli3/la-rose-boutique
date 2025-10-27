
# 🌹 LA ROSE BOUTIQUE 🌹

**La Rose Boutique** est une application e-commerce minimaliste et robuste développée avec le framework Django. Ce projet met l'accent sur une gestion de catalogue claire, une expérience utilisateur fluide et une administration simplifiée.

---

## 💻 FONCTIONNALITÉS CLÉS

### 1. Expérience Utilisateur (Front-end)

Le client dispose d'un parcours d'achat complet et optimisé :

* **Catalogue Interactif :** Parcourez facilement les produits sur la page `/boutique/`.
* **Gestion des Variantes :** Possibilité d'ajouter des produits au panier en sélectionnant la **taille (variante)** souhaitée.
* **Panier Persistant :** Le contenu du panier est conservé entre les sessions (via les sessions Django) pour une expérience d'achat ininterrompue.
* **Processus de Commande (Checkout) :** Flux complet et sécurisé pour la saisie des informations de livraison, menant à une page de confirmation détaillée.
* **Design Responsive :** L'ensemble du site est optimisé pour les téléphones, tablettes et ordinateurs de bureau.

### 2. Administration et Logistique (Back-end)

L'interface d'administration offre tous les outils nécessaires à la gestion quotidienne de la boutique :

* **Tableau de Bord Centralisé :** Accès rapide au **Dashboard Administration** via l'URL `/admin/` pour une vue d'ensemble.
* **Gestion du Catalogue (CRUD) :** L'administrateur peut créer, lire, mettre à jour et supprimer les produits via la vue dédiée `/admin/products/`.
* **Stock Avancé :** Gestion précise du **Stock par Variante (taille)**. Le stock est automatiquement mis à jour dans l'interface lorsque les variantes sont modifiées.
* **Décrémentation Automatique :** Le stock est **automatiquement réduit** après chaque commande client réussie, garantissant la précision des inventaires.
* **Gestion des Commandes :** Vue détaillée des commandes (liste et détail) via `/admin/orders/`, permettant de suivre l'état de chaque achat.
* **Configuration de la Boutique :** Un module dédié permet de mettre à jour les informations de contact (email, téléphone) de la boutique.

---

## 🛠️ INSTRUCTIONS DE DÉPLOIEMENT

### 1. Préparation de l'Environnement

1.  **Cloner le dépôt :**
    ```bash
    git clone [URL_DE_VOTRE_DEPOT]
    cd la_rose_boutique/
    ```
2.  **Créer et Activer l'Environnement Virtuel :**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Sous Linux/macOS
    .\.venv\Scripts\activate   # Sous Windows
    ```
3.  **Installer les dépendances :**
    *(Un fichier `requirements.txt` contenant toutes les dépendances de Django et autres est nécessaire ici. N'oubliez pas de le générer !)*
    ```bash
    pip install -r requirements.txt
    ```

### 2. Configuration et Lancement

1.  **Variables d'Environnement :** Assurez-vous que votre environnement de déploiement (Heroku, AWS, etc.) ou votre fichier `.env` contient les variables de sécurité :
    * `SECRET_KEY` (doit être différente de celle de développement).
    * `DEBUG_MODE=False` (en production).
    * Mettez à jour `ALLOWED_HOSTS` dans `settings.py` avec le nom de domaine de la boutique.

2.  **Migrations :**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

3.  **Collecte des Fichiers Statiques :**
    ```bash
    python manage.py collectstatic
    ```

4.  **Créer un Utilisateur Administrateur :**
    ```bash
    python manage.py createsuperuser
    ```

Le projet est maintenant prêt à être servi par un serveur WSGI (comme Gunicorn) et un proxy inverse (comme Nginx) en production.

---




