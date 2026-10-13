import json

from django.db.models import Count, ExpressionWrapper, F, IntegerField, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from ..models import Category, Product, Supplier


@require_POST
def filters(request):
    try:
        data = json.loads(request.body or b"{}") or {}
    except json.JSONDecodeError:
        data = {}
    request.session["filters"] = {
        "barcode": data.get("barcode") or None,
        "category": data.get("category") or None,
        "supplier": data.get("supplier") or None,
        "sort": data.get("sort") or "date_updated",
        "order": data.get("order") or "desc",
    }
    return JsonResponse({"status": "success", "filters": request.session["filters"]})


@require_POST
def clear_filters(request):
    request.session.pop("filters", None)
    return JsonResponse({"status": "success"})


def dashboard(request):
    stock_value = Product.objects.aggregate(
        v=Sum(ExpressionWrapper(F("price") * F("stock"), output_field=IntegerField()))
    )["v"] or 0
    categories = Category.objects.annotate(n=Count("products")).values_list("cat_type", "n")
    suppliers = Supplier.objects.annotate(n=Count("products")).values_list("name", "n")
    return render(request, "inventory/dashboard.html", {
        "total_products": Product.objects.count(),
        "total_categories": Category.objects.count(),
        "total_suppliers": Supplier.objects.count(),
        "total_stock_value": stock_value,
        "category_data": {"labels": [c[0] for c in categories], "values": [c[1] for c in categories]},
        "supplier_data": {"labels": [s[0] for s in suppliers], "values": [s[1] for s in suppliers]},
    })
