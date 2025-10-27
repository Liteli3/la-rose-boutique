from django.contrib import admin
from .models import Product, ProductVariant  # Importation locale
from orders.models import Order, OrderItem


# =========================================================================
# 1. Administration des COMMANDES (Order & OrderItem)
# =========================================================================

class OrderItemInline(admin.TabularInline):
    """Permet de voir les articles d'une commande directement dans la page Order."""
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0  # Ne pas afficher de lignes vides par défaut


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Personnalisation de l'affichage du modèle Order."""
    list_display = ['id', 'full_name', 'email', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['full_name', 'email', 'payment_id']
    inlines = [OrderItemInline]
    readonly_fields = ['total_price', 'created_at', 'updated_at', 'payment_id']

    actions = ['mark_order_completed']

    def mark_order_completed(self, request, queryset):
        queryset.update(status='Completed')
        self.message_user(request, f"{queryset.count()} commandes ont été marquées comme Complétées.")

    mark_order_completed.short_description = "Marquer comme Complétée (Payée/Livrée)"


# =========================================================================
# 3. Administration des PRODUITS (Product & ProductVariant)
# =========================================================================

class ProductVariantInline(admin.TabularInline):
    """Permet de gérer les tailles/stock directement dans la page du produit."""
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # CORRECTION: Remplacer 'stock' par la propriété 'total_stock' du modèle
    list_display = ['id', 'name', 'price', 'total_stock', 'is_active']
    list_filter = ['is_active', 'category']
    search_fields = ['name', 'description']
    inlines = [ProductVariantInline]  # AJOUT : Pour gérer les variantes directement
    prepopulated_fields = {'slug': ('name',)}  # AJOUT : Pour aider à la création du slug

# NOTE : OrderItem est inclus via l'inline dans OrderAdmin, il n'a pas besoin d'être enregistré séparément.
