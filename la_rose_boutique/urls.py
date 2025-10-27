"""
URL configuration for la_rose_boutique project.
...
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 🚨 AUTHENTIFICATION : Doit toujours être là 🚨
    path('accounts/', include('django.contrib.auth.urls')),

    # 1. Django Admin par défaut : Mieux de le laisser en premier ou à un chemin unique.
    path('django-admin/', admin.site.urls),

    # 2. URLs des COMMANDES (Orders) : Souvent les chemins plus spécifiques (e.g. /checkout/, /admin/orders/)
    # Mieux d'inclure les orders avant le store pour les chemins admin/ spécifiques
    path('', include('orders.urls')),

    # 3. URLs de la BOUTIQUE (Store) : Le chemin de l'application cliente.
    # On la place en dernière pour s'assurer que les chemins plus spécifiques (orders, admin, accounts)
    # sont trouvés d'abord.
    path('', include('store.urls')),
]

# Ajoutez ces deux lignes, pour que django recuperes les fichiers media quand il est en mode developement (debug)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
