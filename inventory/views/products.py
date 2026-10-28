import json

from django.contrib import messages
from django.db import DatabaseError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..forms import ProductEditForm, ProductRegistrationForm
from ..filters import ProductFilterForm
from ..models import Product
from ..stock import query_without_page, status_chips, stock_totals
from ..utils import delete_product_image, make_qr_code, paginate, save_product_image


def product_list(request, view):
    view = "list" if view == "list" else "cards"
    per_page = 10 if view == "list" else 6
    filter_form = ProductFilterForm(request.GET)
    base = Product.objects.select_related("category", "supplier")
    chips = status_chips(request, stock_totals(filter_form.apply(base, include_status=False)),
                         filter_form.values.get("status", ""))
    queryset = filter_form.apply(base)
    totals = stock_totals(queryset)

    items, page, pages, total = paginate(queryset, request.GET.get("page", 1), per_page)
    active_filters = filter_form.active_filters(request)
    return render(request, "inventory/products/index.html", {
        "products": items, "page": page, "pages": pages, "page_numbers": range(1, pages + 1),
        "total": total, "per_page": per_page, "current_view": view,
        "row_offset": (page - 1) * per_page,
        "status_chips": chips, "totals": totals, "filtered_value": totals["stock_value"],
        "query_string": query_without_page(request), "status": filter_form.values.get("status", ""),
        "filter_form": filter_form, "active_filters": active_filters,
        "filter_count": len(active_filters) + filter_form.sort_is_custom,
        "is_filtered": bool(active_filters),
    })


def product_register(request):
    form = ProductRegistrationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        if Product.objects.filter(barcode=cd["barcode"]).exists():
            messages.error(request, "Το προϊόν υπάρχει ήδη")
            return redirect("product_list", view="list")
        image_name = save_product_image(cd["image"], cd["barcode"]) if cd.get("image") else None
        try:
            Product.objects.create(
                barcode=cd["barcode"], desc=cd["desc"], stock=cd["stock"], price=cd["price"],
                image=image_name, category=cd["categories"], supplier=cd["suppliers"],
            )
        except DatabaseError as exc:
            delete_product_image(image_name)
            messages.error(request, f"Σφάλμα κατά την καταχώρηση: {exc}")
        else:
            messages.success(request, "Το προϊόν καταχωρήθηκε επιτυχώς!")
            return redirect("product_list", view="list")
    return render(request, "inventory/products/register.html", {"form": form})


def product_edit(request, barcode):
    product = Product.objects.select_related("category", "supplier").filter(barcode=barcode).first()
    if not product:
        messages.error(request, "Δεν βρέθηκε το προϊόν")
        return redirect("dashboard")

    if request.method == "POST":
        form = ProductEditForm(request.POST, request.FILES, product=product)
        if form.is_valid():
            cd = form.cleaned_data
            old_image = product.image
            if cd.get("image"):
                product.image = save_product_image(cd["image"], cd["barcode"])
            product.barcode, product.desc = cd["barcode"], cd["desc"]
            product.stock, product.price = cd["stock"], cd["price"]
            product.category, product.supplier = cd["categories"], cd["suppliers"]
            try:
                product.save()  # date_updated refreshes automatically
            except DatabaseError as exc:
                messages.error(request, f"Πρόβλημα κατά την ενημερωση: {exc}")
            else:
                if cd.get("image") and old_image != product.image:
                    delete_product_image(old_image)
                messages.success(request, "Το προϊόν ενημερωθηκε")
                return redirect("dashboard")
    else:
        form = ProductEditForm(product=product, initial={
            "barcode": product.barcode, "desc": product.desc, "price": product.price,
            "stock": product.stock, "categories": product.category_id, "suppliers": product.supplier_id,
        })

    return render(request, "inventory/products/edit.html", {
        "form": form, "product": product, "qr_filename": make_qr_code(product.barcode),
    })


@require_POST
def product_delete(request):
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        data = None
    if not data:
        return JsonResponse({"status": "error", "message": "Could not read data"}, status=400)
    barcodes = data.get("barcodes", [])
    try:
        Product.objects.filter(barcode__in=barcodes).delete()
    except DatabaseError as exc:
        print(f"[ERROR]: {exc}")
        messages.error(request, "Πρόβλημα κατά την διαδικασία")
        return JsonResponse({"status": "error", "message": "Operation could not be completed"}, status=400)
    messages.success(request, "Επιτυχης διαγραφη")
    return JsonResponse({"status": "success", "message": "Successfull operation"})
