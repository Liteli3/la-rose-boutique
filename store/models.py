from django.db import models
from django.db.models import Sum  # NOUVEL IMPORT : Pour calculer la somme du stock
from django.utils.text import slugify


# NOUVEAU/RÉINTÉGRÉ : Modèle pour les catégories
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def save(self, *args, **kwargs):
        # Génère automatiquement le slug à partir du nom s'il n'est pas défini
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# Modèle pour un article de la boutique (contient les informations générales)
class Product(models.Model):
    # NOUVEAUX CHAMPS ESSENTIELS AJOUTÉS
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Actif / Visible")  # État visible/invisible

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def save(self, *args, **kwargs):
        # Génère automatiquement le slug à partir du nom s'il n'est pas défini
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    # PROPRIÉTÉS DE STOCK AJOUTÉES/CORRIGÉES
    @property
    def total_stock(self):
        """Calcule la somme du stock de toutes les variantes disponibles de ce produit (via DB aggregation)."""
        # Utilisation de .aggregate pour une meilleure performance
        return self.variants.filter(stock__gt=0).aggregate(Sum('stock'))['stock__sum'] or 0

    @property
    def is_available(self):
        """Retourne True si le produit a un stock total (toutes variantes confondues) > 0."""
        # Vérifie si le stock total est supérieur à zéro
        return self.total_stock > 0

    def __str__(self):
        return self.name


# NOUVEAU MODÈLE : Gestion des variantes par taille
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=50, verbose_name="Taille")  # Ex: 46, 48, 50, S, M, L
    stock = models.IntegerField(default=0, verbose_name="Stock disponible")

    class Meta:
        # Assure qu'on ne peut pas avoir deux fois la même taille pour le même produit
        unique_together = ('product', 'size')
        verbose_name = "Variante d'Article"
        verbose_name_plural = "Variantes d'Articles"

    def __str__(self):
        return f"{self.product.name} - {self.size} (Stock: {self.stock})"


# ==========================================================
# NOUVEAU MODÈLE : Configuration de la Boutique (Email/Téléphone)
# ==========================================================
class ShopConfiguration(models.Model):
    """Stocke les informations générales de la boutique (email, téléphone)."""
    contact_email = models.EmailField(max_length=254, default='contact@laroseboutique.com',
                                      verbose_name="Email de contact")
    contact_phone = models.CharField(max_length=20, default='+33123456789',
                                     verbose_name="Numéro de téléphone (WhatsApp)")

    class Meta:
        verbose_name = "Configuration de la Boutique"
        verbose_name_plural = "Configurations de la Boutique"

    def __str__(self):
        return "Paramètres de la Boutique"

    # Empêcher la création de plus d'un objet (Singleton Pattern)
    def save(self, *args, **kwargs):
        if not self.pk and ShopConfiguration.objects.exists():
            # Ne permet l'enregistrement que si aucun objet n'existe déjà
            raise Exception("Il ne peut y avoir qu'une seule configuration de boutique.")
        return super(ShopConfiguration, self).save(*args, **kwargs)

# NOTE: La partie suivante semble être un reste de code pour OrderItem et n'a pas été incluse dans la mise à jour :
# def __str__(self):
#     size_info = f" ({self.variant.size})" if self.variant else ""
#     return f"{self.quantity} x {self.product.name}{size_info}"
# J'ai ignoré ce bloc qui semblait incomplet et mal placé.
