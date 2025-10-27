# -*- coding: utf-8 -*-

from django.db import models
from store.models import Product  # Importez le modèle Product depuis l'application 'store'
from django.contrib.auth import get_user_model
from decimal import Decimal  # Pour une gestion précise de l'argent

User = get_user_model()


# =========================================================================
# AJOUT : Manager d'objets explicite pour l'ordre
# =========================================================================
class OrderManager(models.Manager):
    """
    Manager personnalisé pour s'assurer que les requêtes
    lisent correctement la table.
    """
    def get_queryset(self):
        # Utiliser la méthode par défaut
        return super().get_queryset()
# =========================================================================


class Order(models.Model):
    # AJOUT : Assigne le manager explicite
    objects = OrderManager()

    # Choix de statut que nous utilisons dans orders/views.py et order_detail.html
    ORDER_STATUS_CHOICES = (
        ('Pending', 'En Attente de Paiement'),
        ('Processing', 'En Cours de Traitement'),
        ('Shipped', 'Expédiée'),
        ('Completed', 'Livrée/Payée'),
        ('Cancelled', 'Annulée'),
    )

    # Liens
    user = models.ForeignKey(User, related_name='orders', on_delete=models.SET_NULL, null=True, blank=True)

    # Informations de commande
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='Pending')

    # Informations de livraison et paiement
    full_name = models.CharField(max_length=250)
    email = models.EmailField(max_length=250)
    phone_number = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=250)
    address_line_2 = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    # Totaux financiers
    # Utiliser DecimalField pour stocker l'argent de manière précise
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Paiement
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_id = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Commande'
        verbose_name_plural = 'Commandes'

    def __str__(self):
        return f"Order {self.id} - {self.full_name}"

    def get_total(self):
        """Calcule le prix total incluant la livraison et les taxes."""
        return self.total_price + self.shipping_cost + self.tax

    def get_sub_total(self):
        """Retourne uniquement le prix total des articles (sans livraison ni taxes)."""
        return self.total_price


class OrderItem(models.Model):
    # Liens
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.SET_NULL, null=True)

    # Détails de l'article au moment de la commande
    product_name = models.CharField(max_length=250)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Prix unitaire au moment de l'achat
    size = models.CharField(max_length=50, blank=True, null=True)  # Si vous avez des tailles
    color = models.CharField(max_length=50, blank=True, null=True)  # Si vous avez des couleurs

    class Meta:
        verbose_name = 'Article de Commande'
        verbose_name_plural = 'Articles de Commande'

    def __str__(self):
        return f"{self.quantity} x {self.product_name} in Order {self.order.id}"

    def get_cost(self):
        return self.price * self.quantity


