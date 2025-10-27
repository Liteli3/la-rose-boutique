from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from .models import Order, OrderItem
# Assurez-vous d'importer les modèles nécessaires de 'store'
from store.models import Product, ShopConfiguration
from store.forms import ShopConfigurationForm

User = get_user_model()


# Fonction utilitaire pour vérifier si l'utilisateur est un admin/staff
def is_staff_user(user):
    """Vérifie si l'utilisateur est actif et membre du staff (admin)."""
    return user.is_active and user.is_staff


# =========================================================================
# Vues d'Administration des Commandes
# =========================================================================

@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def admin_dashboard(request):
    """Vue pour le tableau de bord principal de l'administration et la gestion de la configuration."""

    # 1. Récupérer l'unique enregistrement de configuration
    config, created = ShopConfiguration.objects.get_or_create(pk=1)

    # 2. Gérer la soumission du formulaire de configuration
    if request.method == 'POST':
        # Crée une instance du formulaire en le liant aux données POST et à l'objet 'config'
        config_form = ShopConfigurationForm(request.POST, instance=config)

        if config_form.is_valid():
            config_form.save()
            messages.success(request, "Les informations de contact ont été mises à jour avec succès.")
            return redirect('admin_dashboard')  # Redirige pour éviter la double soumission
        else:
            messages.error(request, "Erreur lors de la mise à jour des informations de contact.")
    else:
        # Créer le formulaire avec les données existantes
        config_form = ShopConfigurationForm(instance=config)

    # 3. Récupération des statistiques clés (comme avant)
    try:
        # ... (votre code existant pour les statistiques)
        pending_orders_count = Order.objects.filter(status='PENDING').count()
        total_revenue = Order.objects.filter(status='COMPLETED').aggregate(Sum('total_price'))[
                            'total_price__sum'] or 0.00
        active_products_count = Product.objects.filter(is_active=True).count()
        total_users_count = User.objects.count()
    except Exception:
        pending_orders_count = 0
        total_revenue = 0.00
        active_products_count = 0
        total_users_count = 0

    # 4. Préparer le contexte
    context = {
        'pending_orders_count': pending_orders_count,
        'total_revenue': round(total_revenue, 2),
        'active_products_count': active_products_count,
        'total_users_count': total_users_count,
        'config_form': config_form,  # AJOUT du formulaire de configuration
    }
    return render(request, 'orders/admin_dashboard.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def admin_order_list(request):
    """Vue pour afficher la liste de toutes les commandes pour l'administrateur avec filtrage et débogage."""
    status_filter_display = request.GET.get('status')

    # CRÉATION DU DICTIONNAIRE DE TRADUCTION INVERSE (nécessite ORDER_STATUS_CHOICES du modèle Order)
    # Ex: {'EN ATTENTE DE PAIEMENT': 'PENDING', 'EN COURS DE TRAITEMENT': 'PROCESSING', ...}

    # Assurez-vous que le modèle Order a la constante ORDER_STATUS_CHOICES
    STATUS_MAPPING = {display.upper(): code for code, display in Order.ORDER_STATUS_CHOICES}

    orders_query = Order.objects.get_queryset().order_by('-created_at')

    # Récupère TOUTES les commandes existantes pour le compteur 'Toutes'
    total_orders = orders_query.count()

    # Applique le filtre si un statut est spécifié
    if status_filter_display:
        # 1. Trouve le code DB correspondant au nom affiché (en majuscules)
        #    Ex: 'EN ATTENTE DE PAIEMENT' -> 'PENDING'
        status_code = STATUS_MAPPING.get(status_filter_display.upper())

        # 2. Si un code valide est trouvé, on filtre
        if status_code:
            orders_query = orders_query.filter(status=status_code)

        # NOTE : Si status_filter_display est 'TOUTES', status_code sera None, donc le filtre n'est pas appliqué.

    # Exécution de la QuerySet pour le contexte
    orders = list(orders_query)

    # =======================================================
    # LIGNES DE DÉBOGAGE MISES À JOUR
    # =======================================================
    print("--- DÉBOGAGE ADMIN ORDERS (orders/views.py) ---")
    print(f"Filtre reçu (Display): {status_filter_display}")
    if status_filter_display and status_filter_display != 'TOUTES':
        print(f"Filtre appliqué (Code DB): {status_code}")
    print(f"Compteur total (DB - FINAL): {total_orders}")
    print(f"Nombre de commandes dans 'orders' après application du filtre: {len(orders)}")
    if orders:
        print(f"Détails de la dernière commande trouvée: ID {orders[0].id}, Statut: {orders[0].status}")
    print("-----------------------------------")
    # =======================================================

    context = {
        'orders': orders,
        'total_orders': total_orders,
    }
    return render(request, 'orders/order_list.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def admin_order_detail(request, order_id):
    """Vue pour afficher les détails d'une commande spécifique et gérer la mise à jour du statut."""
    order = get_object_or_404(Order, id=order_id)

    # Logique pour gérer la soumission du formulaire de mise à jour du statut
    if request.method == 'POST':
        new_status = request.POST.get('status')

        # Vérification simple pour s'assurer que le nouveau statut est valide
        valid_statuses = [key for key, value in order.ORDER_STATUS_CHOICES]

        if new_status and new_status in valid_statuses:
            order.status = new_status
            order.save()
            messages.success(request,
                             f"Le statut de la commande #{order.id} a été mis à jour à '{order.get_status_display()}'.")
        else:
            messages.error(request, "Erreur : Le statut fourni n'est pas valide.")

        return redirect('admin_order_detail', order_id=order.id)

    # Logique pour l'affichage de la page (GET)
    order_items = OrderItem.objects.filter(order=order)

    context = {
        'order': order,
        'order_items': order_items,
        # On passe les choix de statut pour le menu déroulant du template
        # Ceci suppose que ORDER_STATUS_CHOICES est défini dans orders/models.py
        'ORDER_STATUS_CHOICES': Order.ORDER_STATUS_CHOICES,
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def admin_order_delete(request, order_id):
    """
    Vue pour supprimer une commande. Nécessite une requête POST.
    """
    order = get_object_or_404(Order, id=order_id)

    # Exiger la méthode POST pour la suppression (sécurité)
    if request.method == 'POST':
        # Optionnel: vérification des permissions plus strictes si vous en avez (ex: is_superuser)

        # Suppression de la commande
        order.delete()

        messages.success(request, f"La commande #{order_id} a été supprimée avec succès.")
        return redirect('admin_order_list')

    messages.error(request, "Requête non valide pour la suppression. Utilisez un formulaire POST.")
    return redirect('admin_order_list')

