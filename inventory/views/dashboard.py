import json

from django.db.models import Count, ExpressionWrapper, F, IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from ..models import LOW_STOCK_THRESHOLD, Category, Product, Supplier

TOP_GROUPS = 8
REORDER_LIST_SIZE = 10

STOCK_VALUE = ExpressionWrapper(
    Coalesce(F("price"), Value(0)) * Coalesce(F("stock"), Value(0)), output_field=IntegerField()
)
OUT_OF_STOCK = Q(stock__isnull=True) | Q(stock__lte=0)
LOW_STOCK = Q(stock__gt=0, stock__lt=LOW_STOCK_THRESHOLD)
IN_STOCK = Q(stock__gte=LOW_STOCK_THRESHOLD)


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


def _stock_value_by(fk, label_field, empty_label):
    """Stock value and product count per group, largest first; the tail is folded into 'Λοιπά'."""
    rows = list(
        Product.objects.values(fk, label_field)
        .annotate(value=Coalesce(Sum(STOCK_VALUE), 0), count=Count("id"))
        .order_by("-value", "-count")
    )
    if len(rows) > TOP_GROUPS:
        head, tail = rows[:TOP_GROUPS - 1], rows[TOP_GROUPS - 1:]
        rows = head + [{fk: None, label_field: "Λοιπά",
                        "value": sum(r["value"] for r in tail), "count": sum(r["count"] for r in tail)}]
    return {
        "labels": [r[label_field] or (empty_label if r[fk] is None else f"#{r[fk]}") for r in rows],
        "values": [r["value"] for r in rows],
        "counts": [r["count"] for r in rows],
    }


def dashboard(request):
    totals = Product.objects.aggregate(
        products=Count("id"),
        stock_value=Coalesce(Sum(STOCK_VALUE), 0),
        in_stock=Count("id", filter=IN_STOCK),
        low_stock=Count("id", filter=LOW_STOCK),
        out_of_stock=Count("id", filter=OUT_OF_STOCK),
    )
    reorder_products = (
        Product.objects.filter(OUT_OF_STOCK | LOW_STOCK)
        .select_related("supplier")
        .order_by(F("stock").asc(nulls_first=True), "desc")[:REORDER_LIST_SIZE]
    )
    return render(request, "inventory/dashboard.html", {
        "total_products": totals["products"],
        "total_categories": Category.objects.count(),
        "total_suppliers": Supplier.objects.count(),
        "total_stock_value": totals["stock_value"],
        "low_stock_count": totals["low_stock"],
        "out_of_stock_count": totals["out_of_stock"],
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
        "reorder_products": reorder_products,
        "reorder_total": totals["low_stock"] + totals["out_of_stock"],
        "stock_status_data": {
            "labels": ["Διαθέσιμο", "Περιορισμένο", "Εξαντλημένο"],
            "values": [totals["in_stock"], totals["low_stock"], totals["out_of_stock"]],
        },
        "category_data": _stock_value_by("category", "category__cat_type", "Χωρίς κατηγορία"),
        "supplier_data": _stock_value_by("supplier", "supplier__name", "Χωρίς προμηθευτή"),
    })
