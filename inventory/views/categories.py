import json

from django.contrib import messages
from django.db import DatabaseError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..filters import CategoryFilterForm
from ..forms import CategoryForm
from ..models import Category, Product, Supplier
from ..stock import filter_by_status, query_without_page, status_chips, stock_totals, with_stock_stats
from ..utils import paginate

GROUPS_PER_PAGE = 24


def group_list_context(request, form_class, groups, current_view):
    filter_form = form_class(request.GET)
    active_filters = filter_form.active_filters(request)
    items, page, pages, total = paginate(filter_form.apply(with_stock_stats(groups)),
                                         request.GET.get("page", 1), GROUPS_PER_PAGE)
    return {
        "groups": items,
        "page": page,
        "pages": pages,
        "page_numbers": range(1, pages + 1),
        "total": total,
        "row_offset": (page - 1) * GROUPS_PER_PAGE,
        "current_view": "cards" if current_view == "cards" else "list",
        "query_string": query_without_page(request),
        "filter_form": filter_form,
        "active_filters": active_filters,
        "filter_count": len(active_filters) + filter_form.sort_is_custom,
        "is_filtered": bool(active_filters),
    }


def group_detail_context(request, products):
    status = request.GET.get("status", "")
    totals = stock_totals(products)
    filtered = filter_by_status(products, status)
    return {
        "products": filtered,
        "filtered_value": stock_totals(filtered)["stock_value"] if status else totals["stock_value"],
        "totals": totals,
        "total": totals["products"],
        "status_chips": status_chips(request, totals, status),
        "status": status,
    }


def categories(request, current_view="list"):
    return render(request, "inventory/categories/index.html", {
        **group_list_context(request, CategoryFilterForm, Category.objects.all(), current_view),
        "uncategorized": Product.objects.filter(category__isnull=True).count(),
    })


def category_info(request, cat_id):
    category = Category.objects.filter(pk=cat_id).first()
    if not category:
        messages.error(request, "Η κατηγορία δεν βρέθηκε")
        return redirect("categories", "list")
    products = category.products.select_related("supplier").order_by("id")
    return render(request, "inventory/categories/info.html",
                  {"category": category, **group_detail_context(request, products)})


@require_POST
def category_delete(request):
    category = Category.objects.filter(pk=request.POST.get("cat_id") or None).first()
    if not category:
        messages.error(request, "Η κατηγορία δεν βρέθηκε")
        return redirect("categories", "list")
    try:
        category.delete()  # products keep existing; their category is set to NULL
        messages.success(request, "Η κατηγορία διαγραφήκε")
    except DatabaseError as exc:
        messages.error(request, "Αποτυχία διαγραφής")
        print(f"[ERROR]: {exc}")
    return redirect("categories", "list")


def category_edit(request, id):
    category = Category.objects.filter(pk=id).first()
    if not category:
        messages.error(request, "Η κατηγορία δεν βρέθηκε")
        return redirect("categories", "list")
    form = CategoryForm(request.POST or None, initial={"category_type": category.cat_type})
    if request.method == "POST" and form.is_valid():
        category.cat_type = form.cleaned_data["category_type"]
        category.save()
        return redirect("categories", "list")
    return render(request, "inventory/categories/edit.html", {"category": category, "form": form})


def category_register(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        Category.objects.create(cat_type=form.cleaned_data["category_type"])
        messages.success(request, "Η κατηγορία προστέθηκε")
        return redirect("categories", "list")
    return render(request, "inventory/categories/register.html", {"form": form})


@require_POST
def category_get(request):
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        data = None
    if not data:
        return JsonResponse({"status": "error", "message": "Could not read data"}, status=400)
    category = Category.objects.filter(pk=data.get("category_id")).first()
    payload = {"id": category.id, "cat_type": category.cat_type} if category else None
    return JsonResponse({"status": "success", "category": payload})


@require_POST
def category_assign(request):
    barcodes = [b.strip() for b in request.POST.get("barcodes", "").split(",") if b.strip()]
    category_id = request.POST.get("categories")
    supplier_id = request.POST.get("suppliers")

    if not category_id:
        messages.warning(request, "Δεν επιλέξατε κατηγορία!")
        return redirect("dashboard")
    if not supplier_id:
        messages.warning(request, "Δεν επιλέξατε προμηθευτή!")
        return redirect("dashboard")

    category = Category.objects.filter(pk=category_id).first() if category_id.isdigit() else None
    supplier = Supplier.objects.filter(pk=supplier_id).first() if supplier_id.isdigit() else None
    if not category:
        messages.error(request, "Η κατηγορία δεν βρέθηκε!")
        return redirect("dashboard")
    if not supplier:
        messages.error(request, "Ο προμηθευτής δεν βρέθηκε!")
        return redirect("dashboard")

    products = Product.objects.filter(barcode__in=barcodes)
    if not products.exists():
        messages.warning(request, "Δεν βρέθηκαν προϊόντα για ενημέρωση.")
        return redirect("dashboard")
    try:
        products.update(category=category, supplier=supplier)
    except DatabaseError as exc:
        print(f"[ERROR]: {exc}")
        messages.error(request, "Αποτυχία διαδικασίας καταχώρησης")
        return redirect("dashboard")
    messages.success(request, "Επιτυχής καταχώρηση προϊόντων")
    return redirect("dashboard")
