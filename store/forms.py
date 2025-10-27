from django import forms
from django.forms.models import inlineformset_factory
from .models import Product, Category, ProductVariant, ShopConfiguration  # Retiré Order/OrderItem

# Importation externe des modèles de l'application "orders"
from orders.models import Order  # <-- NOUVEAU/CORRIGÉ : Importation explicite de Order
from decimal import Decimal  # Assurez-vous que Decimal est importé si vous utilisez des champs monétaires


# =========================================================================
# 1. Formulaire Principal du Produit
# =========================================================================

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category',
            'name',
            'slug',
            'description',
            'price',
            'is_active',
            'image',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'is_active': forms.CheckboxInput(
                attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500'}
            ),
        }

    def clean_price(self):
        """Assure que le prix est positif."""
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError("Le prix ne peut pas être négatif.")
        return price


# =========================================================================
# 2. FormSet pour les Variantes (Tailles et Stock)
# =========================================================================

ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    fields=('size', 'stock'),
    extra=1,
    can_delete=True
)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug']

        widgets = {
            'slug': forms.TextInput(attrs={'readonly': 'readonly'})
        }


# Formulaire pour la mise à jour du statut dans l'administration
class OrderStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Order  # <-- CIBLE LE BON MODÈLE (orders.Order)
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-caramel focus:ring focus:ring-caramel focus:ring-opacity-50'})
        }


# =========================================================================
# 4. Formulaire de Commande (Utilisé par store/views.py::checkout)
# =========================================================================
class OrderForm(forms.ModelForm):
    # Nous ne déclarons pas les champs explicitement ici pour laisser ModelForm
    # les générer automatiquement, assurant ainsi la cohérence avec le modèle.

    class Meta:
        model = Order
        # Ces noms doivent correspondre aux attributs 'name' du template
        fields = ['full_name', 'phone_number', 'address_line_1']

        labels = {
            'full_name': 'Nom complet',
            'phone_number': 'Téléphone',
            'address_line_1': 'Adresse de livraison',
        }


class ShopConfigurationForm(forms.ModelForm):
    class Meta:
        model = ShopConfiguration
        fields = ['contact_email', 'contact_phone']
        widgets = {
            'contact_email': forms.EmailInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-[#D29C6B] focus:ring-[#D29C6B]'}),
            'contact_phone': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-[#D29C6B] focus:ring-[#D29C6B]'}),
        }
