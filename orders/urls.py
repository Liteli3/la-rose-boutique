from django.urls import path
from . import views

urlpatterns = [
    # ... autres URLs orientées utilisateur (checkout, confirmation, etc.)

    # =========================================================================
    # Admin URLs
    # =========================================================================

    # Dashboard URL: /admin/
    path('admin/', views.admin_dashboard, name='admin_dashboard'),

    # List URL: /admin/orders/
    path('admin/orders/', views.admin_order_list, name='admin_order_list'),

    # Detail URL: /admin/orders/1/
    path('admin/orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),

    # URL de suppression
    path('admin/orders/delete/<int:order_id>/', views.admin_order_delete, name='admin_order_delete'),

]

