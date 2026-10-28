import json

from django.contrib import messages
from django.db import DatabaseError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..filters import SupplierFilterForm
from ..forms import SupplierForm
from ..models import Product, Supplier
from .categories import group_detail_context, group_list_context


def supplier_list(request, current_view="list"):
    return render(request, "inventory/suppliers/index.html", {
        **group_list_context(request, SupplierFilterForm, Supplier.objects.all(), current_view),
        "unassigned": Product.objects.filter(supplier__isnull=True).count(),
    })


def supplier_products(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    products = supplier.products.select_related("category").order_by("id")
    return render(request, "inventory/suppliers/products.html",
                  {"supplier": supplier, **group_detail_context(request, products)})


def supplier_register(request):
    form = SupplierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Ο προμηθευτής προστέθηκε")
        return redirect("dashboard")
    return render(request, "inventory/suppliers/register.html", {"form": form})


def supplier_edit(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Supplier updated successfully!")
        return redirect("dashboard")
    return render(request, "inventory/suppliers/edit.html", {"form": form, "supplier": supplier})


@require_POST
def supplier_delete(request):
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        data = None
    if not data:
        return JsonResponse({"status": "error", "message": "Could not read data"}, status=400)
    supplier = Supplier.objects.filter(name=data.get("name", "")).first()
    if not supplier:
        return JsonResponse({"status": "error", "message": "Supplier not found"}, status=404)
    try:
        supplier.delete()
    except DatabaseError as exc:
        print(f"[ERROR]: {exc}")
        messages.error(request, "Πρόβλημα κατά την διαδικασία")
        return JsonResponse({"status": "error", "message": "Operation could not be completed"}, status=400)
    messages.success(request, "Επιτυχης διαγραφη")
    return JsonResponse({"status": "success", "message": "Successfull operation"})
