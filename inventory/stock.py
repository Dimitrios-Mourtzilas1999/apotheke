"""Stock-health aggregates and filters shared by the dashboard, list pages and API."""
from django.db.models import Count, ExpressionWrapper, F, IntegerField, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import IN_STOCK, LOW_STOCK, NEEDS_REORDER, OUT_OF_STOCK

STOCK_VALUE = ExpressionWrapper(
    Coalesce(F("price"), Value(0)) * Coalesce(F("stock"), Value(0)), output_field=IntegerField()
)

STATUS_FILTERS = {
    "reorder": NEEDS_REORDER,
    "low": LOW_STOCK,
    "out": OUT_OF_STOCK,
    "in": IN_STOCK,
}

STATUS_CHIPS = [
    ("", "Όλα", "all", "products"),
    ("reorder", "Προς παραγγελία", "reorder", "reorder"),
    ("low", "Περιορισμένο", "low_stock", "low_stock"),
    ("out", "Εξαντλημένα", "out_of_stock", "out_of_stock"),
    ("in", "Διαθέσιμα", "in_stock", "in_stock"),
]


def _related(q, prefix):
    """Rewrite a Product Q (e.g. LOW_STOCK) so it can filter through a reverse relation."""
    clone = Q(*[_related(c, prefix) if isinstance(c, Q) else (f"{prefix}__{c[0]}", c[1]) for c in q.children])
    clone.connector, clone.negated = q.connector, q.negated
    return clone


def stock_totals(products):
    totals = products.aggregate(
        products=Count("id"),
        stock_value=Coalesce(Sum(STOCK_VALUE), 0),
        in_stock=Count("id", filter=IN_STOCK),
        low_stock=Count("id", filter=LOW_STOCK),
        out_of_stock=Count("id", filter=OUT_OF_STOCK),
    )
    totals["reorder"] = totals["low_stock"] + totals["out_of_stock"]
    return totals


def with_stock_stats(groups, relation="products"):
    """Annotate Category/Supplier rows with the same figures `stock_totals` gives for products."""
    value = ExpressionWrapper(
        Coalesce(F(f"{relation}__price"), Value(0)) * Coalesce(F(f"{relation}__stock"), Value(0)),
        output_field=IntegerField(),
    )
    return groups.annotate(
        product_count=Count(relation),
        stock_value=Coalesce(Sum(value), 0),
        in_stock=Count(relation, filter=_related(IN_STOCK, relation)),
        low_stock=Count(relation, filter=_related(LOW_STOCK, relation)),
        out_of_stock=Count(relation, filter=_related(OUT_OF_STOCK, relation)),
    ).annotate(reorder=F("low_stock") + F("out_of_stock"))


def filter_by_status(products, status):
    predicate = STATUS_FILTERS.get(status)
    return products.filter(predicate) if predicate is not None else products


def status_chips(request, totals, current):
    """Filter links with counts; they keep the other query params and reset the page."""
    chips = []
    for key, label, tone, total_key in STATUS_CHIPS:
        params = request.GET.copy()
        params.pop("page", None)
        params.pop("status", None)
        if key:
            params["status"] = key
        chips.append({
            "key": key, "label": label, "tone": tone, "count": totals[total_key],
            "url": f"?{params.urlencode()}" if params else request.path,
            "active": current == key,
        })
    return chips


def query_without_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()
