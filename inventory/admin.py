from django.contrib import admin
from .models import Category, Product, Supplier

admin.site.register(Category)
admin.site.register(Supplier)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("barcode", "desc", "stock", "price", "category", "supplier", "date_updated")
    search_fields = ("barcode", "desc")
    list_filter = ("category", "supplier")
