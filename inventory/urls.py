"""URL paths are identical to the Flask app so the existing JS keeps working."""
from django.urls import path

from .views import categories, dashboard, products, suppliers

urlpatterns = [
    path("dashboard", dashboard.dashboard, name="dashboard"),
    path("filters", dashboard.filters, name="filters"),
    path("clear-filters", dashboard.clear_filters, name="clear_filters"),

    path("category/list", categories.category_list, name="category_list"),
    path("category/info/<int:cat_id>", categories.category_info, name="category_info"),
    path("category/delete", categories.category_delete, name="category_delete"),
    path("category/edit/<int:id>", categories.category_edit, name="category_edit"),
    path("category/register-category", categories.category_register, name="category_register"),
    path("category/get-categories", categories.category_get, name="category_get"),
    path("category/assign_product", categories.category_assign, name="category_assign"),

    path("product/products/<str:view>", products.product_list, name="product_list"),
    path("product/register", products.product_register, name="product_register"),
    path("product/edit/<str:barcode>", products.product_edit, name="product_edit"),
    path("product/delete", products.product_delete, name="product_delete"),

    path("supplier/", suppliers.supplier_list, name="supplier_list"),
    path("supplier/<int:supplier_id>/products", suppliers.supplier_products, name="supplier_products"),
    path("supplier/register", suppliers.supplier_register, name="supplier_register"),
    path("supplier/<int:supplier_id>/edit", suppliers.supplier_edit, name="supplier_edit"),
    path("supplier/delete", suppliers.supplier_delete, name="supplier_delete"),
]
