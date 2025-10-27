
from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders' # C'est le nom de l'application (l'étiquette)
    verbose_name = 'Gestion des Commandes' # Nom convivial pour l'Admin Django
