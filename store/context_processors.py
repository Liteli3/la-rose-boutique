# Importation de Order depuis l'application 'orders' où il est correctement défini
from orders.models import Order # <-- LIGNE CRITIQUE MODIFIÉE


def cart_processor(request):
    """
    Rend le contenu du panier (nombre d'articles et contenu) disponible
    dans le contexte de tous les templates.
    """
    cart = request.session.get('cart', {})

    # 1. Assurer la robustesse contre les sessions corrompues
    if not isinstance(cart, dict):
        cart = {}

    total_quantity = 0

    # Calculer la quantité totale d'articles (pas de variantes, mais d'unités)
    for item in cart.values():
        if isinstance(item, dict) and 'quantity' in item:
            total_quantity += item.get('quantity', 0)

    return {
        'cart_total_quantity': total_quantity,
        # Optionnellement, exposer le panier complet si besoin dans le template
        'cart_content': cart
    }
