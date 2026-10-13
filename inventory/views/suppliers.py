import json

from django.contrib import messages
from django.db import DatabaseError
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import SupplierForm
from ..models import Supplier


def supplier_list(request):
    suppliers = Supplier.objects.annotate(product_count=Count("products")).order_by("name")
    return render(request, "inventory/suppliers/index.html", {"suppliers": suppliers})


def supplier_products(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id)
    products = supplier.products.select_related("category").order_by("id")
    return render(request, "inventory/suppliers/products.html", {"supplier": supplier, "products": products})


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
