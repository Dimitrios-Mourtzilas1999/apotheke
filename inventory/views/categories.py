import json

from django.contrib import messages
from django.db import DatabaseError
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..forms import CategoryForm
from ..models import Category, Product, Supplier


def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products")).order_by("cat_type")
    return render(request, "inventory/categories/index.html", {"categories": categories})


def category_info(request, cat_id):
    category = Category.objects.filter(pk=cat_id).first()
    if not category:
        messages.error(request, "Η κατηγορία δεν βρέθηκε")
        return redirect("category_list")
    products = category.products.all().order_by("id")
    return render(request, "inventory/categories/info.html",
                  {"category": category, "products": products, "total": products.count()})


@require_POST
def category_delete(request):
    category = Category.objects.filter(pk=request.POST.get("cat_id") or None).first()
    if not category:
        messages.error(request, "Η κατηγορία δεν βρέθηκε")
        return redirect("category_list")
    try:
        category.delete()  # products keep existing; their category is set to NULL
        messages.success(request, "Η κατηγορία διαγραφήκε")
    except DatabaseError as exc:
        messages.error(request, "Αποτυχία διαγραφής")
        print(f"[ERROR]: {exc}")
    return redirect("category_list")


def category_edit(request, id):
    category = Category.objects.filter(pk=id).first()
    if not category:
        messages.error(request, "Η κατηγορία δεν βρέθηκε")
        return redirect("category_list")
    form = CategoryForm(request.POST or None, initial={"category_type": category.cat_type})
    if request.method == "POST" and form.is_valid():
        category.cat_type = form.cleaned_data["category_type"]
        category.save()
        return redirect("category_list")
    return render(request, "inventory/categories/edit.html", {"category": category, "form": form})


def category_register(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        Category.objects.create(cat_type=form.cleaned_data["category_type"])
        messages.success(request, "Η κατηγορία προστέθηκε")
        return redirect("category_list")
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
