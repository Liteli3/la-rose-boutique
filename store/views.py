
"""Ici on a créer une vue qui gérera la logique de la page de
la boutique et qui lui enverra les données des articles."""

# Mettez à jour vos imports en haut de views.py
# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import Product, ProductVariant, Category, ShopConfiguration
from decimal import Decimal
from django.db.models import F, Sum, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.forms.models import inlineformset_factory
from .forms import ProductAdminForm, ProductVariantFormSet, CategoryForm, OrderForm
from orders.views import is_staff_user
from orders.models import Order, OrderItem # <-- LIGNE CRITIQUE AJOUTÉE


# Page d'accueil (inchangée)
def home(request):
    return render(request, 'home.html')


# Contenu de store/views.py - Fonction store (Corrigée)

def store(request):  # category_slug=None est retiré ici pour correspondre à l'URL simple
    """
    Affiche la boutique, en appliquant un filtre par catégorie ou une recherche.
    Les filtres sont gérés via les paramètres GET (category_slug et q).
    """
    products = Product.objects.filter(is_active=True).order_by('name')
    current_category = None

    # Correction majeure : 'q' est pour la recherche, 'category_slug' pour le filtre.
    category_slug = request.GET.get('category_slug')
    search_query = request.GET.get('q')  # Correctement lié au champ de recherche textuelle

    # 1. GESTION DU FILTRAGE PAR CATÉGORIE
    # 'all' est la valeur que nous utilisons pour réinitialiser le filtre
    if category_slug and category_slug not in ['', 'all']:
        # Tente de récupérer la catégorie par son slug
        current_category = get_object_or_404(Category, slug=category_slug)

        # Filtre les produits pour n'afficher que ceux de cette catégorie
        products = products.filter(category=current_category)

    # 2. GESTION DE LA RECHERCHE PAR MOT-CLÉ
    if search_query:
        # Utilisation de Q object pour chercher dans plusieurs champs
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # 3. Récupérer TOUTES les catégories actives pour le template
    categories = Category.objects.all().order_by('name')

    # 4. Récupération de la configuration de la boutique (inchangée)
    shop_config, created = ShopConfiguration.objects.get_or_create(pk=1)

    context = {
        'products': products,
        'categories': categories,  # Liste pour le menu de gauche
        'current_category': current_category,  # Pour mettre en évidence la catégorie sélectionnée
        'search_query': search_query,  # Pour maintenir le terme dans la barre de recherche
        'shop_config': shop_config,  # Configuration de la boutique
    }

    return render(request, 'store.html', context)


# ATTENTION : La vue attend maintenant l'ID de la VARIANTE

def add_to_cart(request):
    """
    Ajoute un produit (variante) au panier et retourne une réponse JSON
    pour la mise à jour asynchrone du compteur de panier.
    """
    # Accepte uniquement les requêtes POST
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

    # 1. Récupère l'ID de la variante
    variant_id = request.POST.get('variant_id')

    if not variant_id:
        return JsonResponse({'success': False, 'error': "Erreur: Aucune taille n'a été sélectionnée."}, status=400)

    try:
        # Récupère l'objet ProductVariant
        variant = get_object_or_404(ProductVariant, id=variant_id)
    except Exception:
        return JsonResponse({'success': False, 'error': "Variante de produit introuvable."}, status=404)

    # Vérification du stock
    if variant.stock < 1:
        return JsonResponse({
            'success': False,
            'error': f"Désolé, la taille {variant.size} pour '{variant.product.name}' est en rupture de stock."
        }, status=400)

    # 2. Mise à jour du Panier (logique inchangée)
    cart = request.session.get('cart', {})
    if not isinstance(cart, dict):
        cart = {}  # Réinitialisation en cas de corruption

    # -------------------------------------------------------------
    # CORRECTION MAJEURE: Clé du panier = ID_Produit-ID_Variante
    # -------------------------------------------------------------
    # Ancienne clé: str(variant.id)
    cart_key = f"{variant.product.id}-{variant.id}"
    current_quantity = cart.get(cart_key, {}).get('quantity', 0)

    # Vérification du stock si ajout de la quantité
    if current_quantity + 1 > variant.stock:
        return JsonResponse({
            'success': False,
            'error': f"Stock insuffisant. {variant.stock} unités restantes pour la taille {variant.size}."
        }, status=400)

    # Stockage des données du panier
    if cart_key not in cart:
        cart[cart_key] = {
            'product_id': str(variant.product.id),
            'variant_id': variant.id,
            'name': variant.product.name,
            'size': variant.size,
            'price': float(variant.product.price),
            'quantity': 1,
        }
        # REMARQUE : L'entrée 'variant_id' stockée est redondante si la clé est bonne, mais on la garde.
    else:
        cart[cart_key]['quantity'] += 1

    # 3. DÉCRÉMENTATION/GESTION DU STOCK EN BASE DE DONNÉES
    # =========================================================
    # LIGNES SUPPRIMÉES : Le stock NE DOIT PAS être décrémenté ici.
    # Il est décrémenté uniquement dans la fonction checkout() après paiement.
    # variant.stock = F('stock') - 1
    # variant.save(update_fields=['stock'])
    # =========================================================

    # 4. Sauvegarde de la session
    request.session['cart'] = cart
    request.session.modified = True

    # 5. Calcul de la nouvelle quantité totale
    total_quantity = sum(item.get('quantity', 0) for item in cart.values() if isinstance(item, dict))

    # 6. Retour de la réponse JSON au client
    return JsonResponse({
        'success': True,
        'message': f"'{variant.product.name}' (Taille: {variant.size}) ajouté au panier.",
        'new_cart_quantity': total_quantity  # Nouvelle quantité pour l'indicateur
    })




def cart(request):
    """
    Affiche le contenu du panier.
    """
    cart = request.session.get('cart', {})
    if not isinstance(cart, dict):
        request.session['cart'] = {}
        request.session.modified = True
        cart = {}

    items = []
    total_price = Decimal('0.00')
    total_quantity = 0

    # Étape 1 : Collecte de tous les IDs de variantes pour une requête en vrac
    variant_ids = [item['variant_id'] for item in cart.values() if isinstance(item, dict) and 'variant_id' in item]

    # Étape 2 : Récupérer toutes les variantes, ainsi que les produits associés (select_related)
    variants = ProductVariant.objects.filter(id__in=variant_ids).select_related('product').in_bulk(variant_ids)

    # Étape 3 : Parcourir le panier de session et construire la liste des items
    for key, item in cart.items():
        if not isinstance(item, dict):
            continue

        variant_id = item.get('variant_id')
        quantity = item.get('quantity')
        price = item.get('price')

        # Si les données ne sont pas valides OU si la variante n'existe plus en base, on passe
        if not variant_id or variant_id not in variants or not isinstance(quantity, int) or not isinstance(price, (
        float, Decimal, int)):
            continue

        variant = variants[variant_id]
        product = variant.product

        # CONVERSION DU PRIX EN DECIMAL pour les calculs robustes
        item_price_decimal = Decimal(str(price))

        # Attacher les objets et informations clés pour le template
        item['product'] = product
        item['variant'] = variant  # Ajout de l'objet variant
        item['image_url'] = product.image.url if product.image else None  # Ajout de l'URL de l'image

        # Le prix est stocké dans l'item de session, mais on recalcule le total de ligne
        item_total = quantity * item_price_decimal

        # CHANGEMENT 1 : PASSER item_total comme Decimal, pas comme une chaîne
        item['total'] = item_total

        total_price += item_total
        total_quantity += quantity

        # Ajouter le key qui est l'ID de la variante
        item['key'] = key
        items.append(item)

    context = {
        'items': items,
        # CHANGEMENT 2 : PASSER total_price comme Decimal, pas comme une chaîne
        'cart_total_price': total_price,
        'cart_total_quantity': total_quantity,
    }
    return render(request, 'cart.html', context)


# Mise à jour d'un article dans le panier (utilise la KEY complète)
def update_cart_quantity(request, key):
    """
    Met à jour la quantité d'un item du panier.
    Vérifie le stock réel SANS le modifier en base.
    """
    # Assurez-vous d'avoir bien importé Decimal en haut du fichier views.py :
    from decimal import Decimal
    # Assurez-vous d'avoir importé ProductVariant du modèle store :
    from store.models import ProductVariant # À ajuster si ProductVariant est ailleurs

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

    # CORRECTION CRUCIALE : Le séparateur de clé est le tiret ('-'), pas l'underscore ('_').
    key_parts = key.split('-')

    if len(key_parts) < 2:
        # Si la clé est simple (ex: '5'), on utilise la clé entière comme ID de variante (si elle est l'ID).
        variant_id_str = key
    else:
        # Si la clé est complexe (ex: '5-2'), l'ID de variante est la deuxième partie ('2').
        variant_id_str = key_parts[1]

    try:
        # Tente de convertir l'ID de variante pour la recherche.
        variant_id = int(variant_id_str)
        # La quantité vient de la requête POST
        new_quantity = int(request.POST.get('quantity', 0))
    except ValueError:
        # Ceci est le message que vous recevez si 'variant_id_str' n'est pas un nombre.
        return JsonResponse({'success': False, 'error': 'Données invalides pour la mise à jour.'}, status=400)

    cart = request.session.get('cart', {})

    if key not in cart:
        return JsonResponse({'success': False, 'error': 'Article non trouvé dans le panier.'}, status=404)

    # 1. Récupération de la variante et vérification du stock
    try:
        variant = ProductVariant.objects.get(id=variant_id)
        # Le stock disponible est le stock réel en base
        available_stock = variant.stock
    except ProductVariant.DoesNotExist:
        del cart[key]
        request.session.modified = True
        return JsonResponse({'success': False, 'error': 'Variante introuvable. Article retiré du panier.'}, status=404)

    # -----------------------------------------------------------
    # GESTION DE LA QUANTITÉ ET VÉRIFICATION
    # -----------------------------------------------------------

    item_removed = False

    # 1. Si la quantité est réduite à zéro : suppression
    if new_quantity <= 0:
        del cart[key]
        item_removed = True
        new_quantity = 0

    # 2. Si la nouvelle quantité dépasse le stock disponible
    elif new_quantity > available_stock:
        # Bloquer la mise à jour si la nouvelle quantité est > stock disponible
        max_quantity = available_stock
        cart[key]['quantity'] = max_quantity
        new_quantity = max_quantity

        request.session.modified = True
        # Retourner une erreur avec la nouvelle quantité corrigée (limitée par le stock)
        return JsonResponse({
            'success': False,
            'error': f"Stock insuffisant. Maximum disponible : {max_quantity} unités.",
            'new_quantity': new_quantity,
        }, status=400)

    # 3. Mise à jour normale de la quantité
    else:
        cart[key]['quantity'] = new_quantity
        item_removed = False

    # AUCUNE MODIFICATION DU STOCK EN BASE DE DONNÉES

    # Sauvegarde de la session
    request.session.modified = True

    # 2. Recalcul des totaux globaux et de la ligne
    # Utilisation de Decimal pour la précision des calculs d'argent
    total_price_decimal = Decimal('0.00')
    total_quantity = 0
    new_subtotal_decimal = Decimal('0.00')

    for item_key, item in cart.items():
        # Conversion du prix et de la quantité en Decimal
        try:
            # Sécurité: le prix est stocké dans la session, on le convertit en Decimal
            price = Decimal(str(item.get('price', '0.00')))
        except:
            price = Decimal('0.00')

        quantity = item.get('quantity', 0)

        # Calcul du total de la ligne
        item_total = price * Decimal(quantity)
        total_price_decimal += item_total
        total_quantity += quantity

        if item_key == key:
            new_subtotal_decimal = item_total

    if item_removed:
        new_subtotal_decimal = Decimal('0.00')

    # 3. Retour de la réponse JSON pour l'AJAX
    return JsonResponse({
        'success': True,
        'new_quantity': new_quantity,
        # Formatage des Decimal en chaîne de caractères avec 2 décimales pour l'affichage JS
        'new_subtotal': f"{new_subtotal_decimal:.2f}",
        'total': f"{total_price_decimal:.2f}",
        'cart_quantity': total_quantity
    })


# Suppression d'un article du panier (utilise la KEY complète)
def remove_from_cart(request, key):
    """
    Retire un article du panier. Le stock N'EST PAS ré-incrémenté ici.
    """
    if request.method == 'POST':
        cart = request.session.get('cart', {})

        if key in cart:
            try:
                # 1. Suppression de l'article du panier
                del cart[key]
                request.session['cart'] = cart
                request.session.modified = True

                # 2. Recalcul des totaux
                total_price = sum(
                    Decimal(str(item.get('quantity', 0))) * Decimal(str(item.get('price', 0)))
                    for item in cart.values() if isinstance(item, dict)
                )
                cart_quantity = sum(item.get('quantity', 0) for item in cart.values() if isinstance(item, dict))

                return JsonResponse({
                    'success': True,
                    'total': f"{total_price:.2f}",
                    'cart_quantity': cart_quantity,
                    'key': key
                })

            except Exception as e:
                return JsonResponse({'success': False, 'error': f'Erreur interne: {e}'}, status=500)

        return JsonResponse({'success': False, 'error': 'Clé de panier invalide'}, status=404)

    return JsonResponse({'success': False, 'error': 'Méthode invalide'}, status=405)


# =====================================================================================
# VUE : Commander (Checkout)
# =====================================================================================


def checkout(request):
    # Assurez-vous que l'utilisateur est authentifié et que le panier n'est pas vide
    if not request.session.get('cart', {}):
        messages.warning(request, "Votre panier est vide. Ajoutez des articles avant de commander.")
        return redirect('store')

    # Récupérer les items du panier (nécessaires pour le calcul)
    cart = request.session.get('cart', {})
    sub_total = Decimal('0.00')
    items_in_cart = 0
    products_with_variants = {}

    # 1. Calculer les totaux et valider les quantités
    for key, item_data in cart.items():
        key_parts = key.split('-')
        product_id = key_parts[0]
        variant_id = key_parts[1] if len(key_parts) > 1 else None

        try:
            product = Product.objects.get(pk=product_id)
            variant = None
            if variant_id and variant_id != 'None':
                variant = ProductVariant.objects.get(pk=variant_id, product=product)

            # 🚨 POINT DE CONTRÔLE CRITIQUE : Si un variant est requis, il doit exister.
            # On assume que tout article dans le panier est soit un variant, soit un produit
            # qui doit avoir des variants. Si variant_id est donné, variant doit être trouvé.
            if variant_id and variant_id != 'None' and not variant:
                raise ProductVariant.DoesNotExist(f"Variante ID {variant_id} non trouvée.")

            quantity = int(item_data['quantity'])
            price = Decimal(item_data['price'])

            sub_total += quantity * price
            items_in_cart += quantity

            products_with_variants[key] = {
                'product': product,
                'variant': variant,
                'quantity': quantity,
                'price': price,
                'name': product.name + (f" ({variant.size})" if variant else '')
            }

        except Product.DoesNotExist:
            del cart[key]
            request.session.modified = True
            messages.error(request, f"Le produit avec la clé {key} n'existe plus et a été retiré du panier.")
            return redirect('cart')

        except ProductVariant.DoesNotExist:
            # Cette exception gère aussi le cas où la variante est requise mais manquante
            del cart[key]
            request.session.modified = True
            messages.error(request,
                           f"La variante spécifiée pour le produit {product.name} n'existe plus et a été retirée du panier.")
            return redirect('cart')
        except ValueError:
            del cart[key]
            request.session.modified = True
            messages.error(request, f"Erreur de données pour le produit {product.name}. Article retiré.")
            return redirect('cart')

    # 2. Calculer les coûts supplémentaires
    shipping_cost = Decimal('10.00')
    tax_rate = Decimal('0.16')
    tax = round(sub_total * tax_rate, 2)
    total_price_incl_all = sub_total + shipping_cost + tax

    # Initialiser le formulaire pour la méthode GET ou en cas d'échec POST
    form = OrderForm()

    # 3. Traiter la soumission du formulaire
    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            # Nettoyage des données (Champs harmonisés)
            full_name = form.cleaned_data['full_name']
            phone_number = form.cleaned_data['phone_number']
            address_line_1 = form.cleaned_data['address_line_1']

            # Récupérer le champ du template qui n'est pas dans OrderForm
            payment_method = request.POST.get('payment_method', 'Cash')

            # Déterminer l'email (même logique)
            customer_email = request.user.email if request.user.is_authenticated else "email_non_fourni@exemple.com"

            try:
                # Créer l'enregistrement Order
                new_order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None, # Permet à l'utilisateur d'être NULL si non connecté
                    full_name=full_name,
                    phone_number=phone_number,
                    address_line_1=address_line_1,

                    # Nouveaux champs requis (Valeurs par défaut)
                    address_line_2="",
                    city="Kinshasa",
                    postal_code="00243",
                    country="RDC",

                    email=customer_email,
                    payment_method=payment_method,

                    # Totaux financiers
                    total_price=sub_total,
                    shipping_cost=shipping_cost,
                    tax=tax,
                )

                # 4. Créer les OrderItems
                for key, data in products_with_variants.items():
                    product = data['product']
                    variant = data['variant']

                    size = variant.size if variant else None
                    #color = variant.color if variant else None  # Assurez-vous que ProductVariant a un champ 'color' si nécessaire, sinon retirez ceci.

                    color_to_save = None

                    OrderItem.objects.create(
                        order=new_order,
                        product=product,
                        product_name=data['name'],
                        quantity=data['quantity'],
                        price=data['price'],
                        size=size,
                        color=color_to_save,
                    )

                    # -----------------------------------------------------------
                    # CORRECTION MAJEURE: Décrémenter le stock UNIQUEMENT sur la VARIANT
                    # -----------------------------------------------------------
                    if variant:
                        # Décrémenter le stock de la variante
                        variant.stock = F('stock') - data['quantity']
                        variant.save()  # Le problème est résolu ici
                    else:
                        # Si le produit n'a pas de variante, la transaction NE DEVRAIT PAS arriver ici
                        # ou cela signifie que le produit n'a pas de stock traçable.
                        # Pour éviter l'erreur "field 'stock' does not exist", nous allons ignorer la décrémentation
                        # pour le produit parent, mais c'est un risque si votre logique de panier est imparfaite.
                        # Mieux vaut Logguer une alerte si cela arrive, car la vente ne devrait pas être possible.
                        print(
                            f"ALERTE: Commande #{new_order.id}: Article {product.name} sans variante ignoré pour la décrémentation de stock (pas de champ 'stock' sur Product).")
                        # messages.warning(request, f"Attention: Le stock de {product.name} n'a pas été mis à jour.")

                # 5. Vider le panier après succès
                request.session['cart'] = {}
                request.session.modified = True

                # 6. Rediriger vers la page de confirmation
                return redirect('confirmation', order_id=new_order.id)

            except Exception as e:
                # Cette exception capture aussi l'erreur si F('stock') échoue ou si le stock tombe en négatif (non géré ici)
                messages.error(request,
                               f"Une erreur s'est produite lors de l'enregistrement de votre commande. Veuillez réessayer. Détail: {e}")
                print(f"Erreur à la création de la commande: {e}")

        # SI LE FORMULAIRE N'EST PAS VALIDE :
        else:
            print("--- ERREUR DE VALIDATION DU FORMULAIRE DE COMMANDE ---")
            print(form.errors)
            print("-----------------------------------------------------")
            # Le formulaire non valide est conservé dans 'form' pour être affiché

    # 4. Afficher le formulaire (GET ou POST invalide)
    else:
        # Si méthode GET (première visite), pré-remplir le formulaire
        initial_data = {
            # Utilisation des noms de champs du modèle pour l'initialisation
            'full_name': request.user.get_full_name() if request.user.is_authenticated else '',
            # Le reste des champs initialisés (phone_number, etc.) doit aussi être conditionnel
            'phone_number': getattr(request.user, 'phone_number', '') if request.user.is_authenticated else '',
        }
        form = OrderForm(initial=initial_data)

    context = {
        'form': form,
        'cart_items': products_with_variants.values(),
        'sub_total': sub_total,
        'shipping_cost': shipping_cost,
        'tax': tax,
        'total_price_incl_all': total_price_incl_all,
        'items_in_cart': items_in_cart,
    }

    return render(request, 'checkout.html', context)


# La vue doit accepter l'order_id passé par l'URL
def confirmation(request, order_id):
    # Utiliser get_object_or_404 pour récupérer la commande ou retourner une 404
    # S'il y a une erreur ou si l'ID n'existe pas, l'utilisateur ne verra pas la page
    order = get_object_or_404(Order, id=order_id)

    context = {
        'order': order,
    }
    return render(request, 'confirmation.html', context)


# =========================================================================
# Vues d'Administration du Catalogue
# =========================================================================

@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def admin_product_create(request):
    """
    Vue pour la création d'un nouveau produit par l'administrateur.
    """
    if request.method == 'POST':
        # Instancie le formulaire avec les données POST et les fichiers (pour l'image)
        form = ProductAdminForm(request.POST, request.FILES)
        if form.is_valid():
            # L'enregistrement est géré par le ModelForm
            product = form.save()
            messages.success(request, f"Le produit '{product.name}' a été créé avec succès.")

            # Redirection vers la liste des produits admin (que nous allons créer juste après)
            return redirect('admin_product_list')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = ProductAdminForm()

    context = {
        'form': form,
        'action_type': 'Créer',
    }
    return render(request, 'store/admin_product_form.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def admin_product_list(request):
    """
    Affiche la liste de tous les produits pour l'administration, avec filtres et recherche.
    """
    # 1. Récupération des paramètres de filtrage et de recherche
    category_id = request.GET.get('category')
    search_query = request.GET.get('q')

    # 2. Construction de la QuerySet de base
    products = Product.objects.all().prefetch_related('variants')

    # 3. Application du filtre par catégorie
    if category_id:
        products = products.filter(category__id=category_id)

    # 4. Application du filtre de recherche (Nom et Description)
    if search_query:
        # Utilisation de Q object pour combiner les conditions avec OR (|)
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # 5. Annotation et tri (calcul du stock total)
    products = products.annotate(
        # total_variant_stock est le nom du champ qui sera utilisé dans le template
        total_variant_stock=Sum('variants__stock')
    ).order_by('-id')

    # 6. Récupérer toutes les catégories pour le sélecteur
    categories = Category.objects.all().order_by('name')

    context = {
        'products': products,
        'categories': categories,  # Pour la liste déroulante
        'selected_category': category_id,  # Pour maintenir la sélection
        'search_query': search_query,  # Pour pré-remplir la barre de recherche
    }
    return render(request, 'store/admin_product_list.html', context)


# =========================================================================
# 1. FONCTION admin_order_list et admin_order_detail ont été supprimé pour raison de débogage
# =========================================================================



@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def admin_product_edit(request, product_id):
    """
    Vue pour l'édition d'un produit existant et de ses variantes (stock/taille).
    """
    product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        form = ProductAdminForm(request.POST, request.FILES, instance=product)
        formset = ProductVariantFormSet(request.POST, request.FILES, instance=product)  # Gestion des données POST

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()  # Sauvegarde toutes les variantes
            messages.success(request, f"Le produit '{product.name}' et ses variantes ont été mis à jour avec succès.")
            return redirect('admin_product_list')
        else:
            # Si un des deux n'est pas valide, on signale l'erreur
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire ou les variantes.")
    else:
        form = ProductAdminForm(instance=product)
        formset = ProductVariantFormSet(instance=product)  # Initialisation avec les données existantes

    context = {
        'form': form,
        'formset': formset,  # Ajout du formset au contexte
        'action_type': 'Modifier',
        'product': product,
    }
    return render(request, 'store/admin_product_form.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def admin_product_delete(request, product_id):
    """
    Vue pour la suppression d'un produit.
    """
    product = get_object_or_404(Product, pk=product_id)

    # Nous pourrions mettre une confirmation POST ici, mais pour l'instant, faisons la suppression directe pour la simplicité
    # Note: En production, il est CRUCIAL d'utiliser un formulaire POST/une confirmation.

    product_name = product.name
    product.delete()

    messages.success(request, f"Le produit '{product_name}' a été supprimé avec succès du catalogue.")
    return redirect('admin_product_list')


# =========================================================================
# VUES DE GESTION DES CATÉGORIES (POUR POP-UP ADMIN)
# =========================================================================

@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def manage_category(request, category_id=None):
    """
    Vue pour créer OU modifier une catégorie dans un pop-up.
    - Si category_id est None: Mode Création.
    - Si category_id est fourni: Mode Édition.
    """
    category = None
    if category_id:
        # En mode édition, on récupère la catégorie existante
        category = get_object_or_404(Category, pk=category_id)
        # S'assure que le pop-up s'appelle pour l'édition et non la création
        action_title = "Modifier la Catégorie"
        success_message = f"La catégorie '{category.name}' a été mise à jour avec succès."
    else:
        # Mode Création
        action_title = "Créer une Catégorie"
        success_message = "La nouvelle catégorie a été créée avec succès."

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            new_category = form.save()
            # Afficher un message Django
            messages.success(request, success_message)

            # Script pour fermer le pop-up et mettre à jour le champ parent.
            # (Identique à l'implémentation initiale pour la création)
            return HttpResponse(
                f'<script type="text/javascript">opener.dismissAddAnotherPopup(window, "{new_category.id}", "{new_category.name}");</script>'
            )
        else:
            messages.error(request, "Veuillez corriger les erreurs de formulaire.")
    else:
        # Initialisation du formulaire (vide ou pré-rempli)
        form = CategoryForm(instance=category)

    context = {
        'form': form,
        'is_popup': True,
        'category': category,  # Ajout de l'objet category pour le template
        'action_title': action_title,
    }
    return render(request, 'store/category_form.html', context)


@login_required
@user_passes_test(is_staff_user, login_url='/admin/login/')
def delete_category(request, category_id):
    """
    Vue pour supprimer une catégorie (utilisée par le template pop-up).
    """
    category = get_object_or_404(Category, pk=category_id)

    if request.method == 'POST':
        category_name = category.name
        # Note: En production, il est crucial d'ajouter ici une logique de vérification
        # pour s'assurer qu'aucun produit n'est associé avant la suppression.
        # Si vous utilisez `on_delete=models.SET_NULL` sur Product.category, cela passera.
        # Sinon, cela lèvera une erreur `IntegrityError` si des produits sont liés.

        category.delete()
        messages.success(request, f"La catégorie '{category_name}' a été supprimée avec succès.")

        # Script pour fermer le pop-up, sans mettre à jour le champ parent car l'élément n'existe plus.
        # Le champ parent devra être rechargé par l'utilisateur (ou une mise à jour plus complexe).
        return HttpResponse(
            f'<script type="text/javascript">window.close();</script>'
        )

    # Si GET, on redirige vers l'édition (cela ne devrait pas arriver)
    messages.error(request, "Méthode non autorisée. Utilisez le formulaire de suppression.")
    return redirect('manage_category', category_id=category_id)


# =========================================================================
# VUE AJAX POUR LE POLLING DU STOCK EN TEMPS RÉEL (Modifiée pour supporter l'admin)
# =========================================================================

def get_all_variant_stocks(request):
    """
    Renvoie les données de stock adaptées à la requête (par variante OU agrégées par produit).
    - Par défaut (pas de paramètre `admin`): retourne {variant_id: stock} (pour la boutique front-end)
    - Avec paramètre `admin=true`: retourne {product_id: total_stock} (pour l'admin/catalogue)
    """
    is_admin_request = request.GET.get('admin') == 'true'

    if is_admin_request:
        # Stock agrégé par PRODUIT (pour la page admin_product_list)
        product_stocks = ProductVariant.objects.filter(
            product__is_active=True
        ).values('product_id').annotate(
            total_stock=Sum('stock')
        )

        # Construction du dictionnaire {product_id: total_stock}
        stock_data = {
            item['product_id']: item['total_stock']
            for item in product_stocks
        }

    else:
        # Stock par VARIANTE (pour la page store/boutique)
        active_variants = ProductVariant.objects.filter(
            product__is_active=True
        ).values('id', 'stock')

        # Construction d'un dictionnaire {variant_id: stock}
        stock_data = {
            item['id']: item['stock']
            for item in active_variants
        }

    return JsonResponse({'stocks': stock_data})
