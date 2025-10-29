import os
from django.contrib.auth import get_user_model

USERNAME = 'life'
EMAIL = 'simonpierrelife54@gmail.com'
PASSWORD = 'benjamin22'
# -----------------------------

User = get_user_model()

if not User.objects.filter(username=USERNAME).exists():
    print(f'Création du compte administrateur : {USERNAME}')
    User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
else:
    print(f'Le compte administrateur {USERNAME} existe déjà.')