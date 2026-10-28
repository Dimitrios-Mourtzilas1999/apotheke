"""GET-parameter filter forms for the products, categories and suppliers list pages."""
from django import forms
from django.db.models import F, Q

from .models import Category, Supplier
from .stock import STATUS_FILTERS, STOCK_VALUE

STATUS_CHOICES = [
    ("", "Όλα"),
    ("reorder", "Προς παραγγελία (περιορισμένο ή εξαντλημένο)"),
    ("low", "Περιορισμένο"),
    ("out", "Εξαντλημένο"),
    ("in", "Διαθέσιμο"),
]
ORDER_CHOICES = [("asc", "Αύξουσα"), ("desc", "Φθίνουσα")]


def _number(label, col=6, **kwargs):
    field = forms.IntegerField(label=label, required=False, **kwargs)
    field.col = col
    return field


def _choice(label, choices, col=6):
    field = forms.ChoiceField(label=label, choices=choices, required=False)
    field.col = col
    return field


class ListFilterForm(forms.Form):
    """Base class: unbound defaults, Bootstrap widgets, active-filter tags."""

    sort_fields = {}
    default_sort = ""
    default_order = "asc"
    ranges = ()  # (min_field, max_field, lookup)

    def __init__(self, data=None, **kwargs):
        super().__init__(data if data is not None else {}, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css)

    def clean(self):
        cleaned = super().clean()
        for low, high, _ in self.ranges:
            lo, hi = cleaned.get(low), cleaned.get(high)
            if lo is not None and hi is not None and lo > hi:
                self.add_error(high, "Η μέγιστη τιμή πρέπει να είναι ≥ της ελάχιστης.")
                cleaned.pop(low, None)
        return cleaned

    @property
    def values(self):
        self.is_valid()
        return getattr(self, "cleaned_data", {})

    def _apply_ranges(self, queryset):
        v = self.values
        for low, high, lookup in self.ranges:
            if v.get(low) is not None:
                queryset = queryset.filter(**{f"{lookup}__gte": v[low]})
            if v.get(high) is not None:
                queryset = queryset.filter(**{f"{lookup}__lte": v[high]})
        return queryset

    def _apply_sort(self, queryset, tiebreak):
        v = self.values
        expr = self.sort_fields.get(v.get("sort") or self.default_sort)
        if expr is None:
            return queryset.order_by(tiebreak)
        descending = (v.get("order") or self.default_order) == "desc"
        ordering = expr.desc(nulls_last=True) if descending else expr.asc(nulls_first=True)
        return queryset.order_by(ordering, tiebreak)

    def active_filters(self, request):
        """Tags for every non-default filter, each with a link that removes it."""
        tags = []
        v = self.values
        for name, field in self.fields.items():
            if name in ("sort", "order"):
                continue
            value = v.get(name)
            if value in (None, ""):
                continue
            if isinstance(field, forms.ChoiceField):
                value = dict(field.choices).get(value, value)
            params = request.GET.copy()
            for key in (name, "page"):
                params.pop(key, None)
            tags.append({"label": field.label, "value": value,
                         "remove_url": f"?{params.urlencode()}" if params else request.path})
        return tags

    @property
    def sort_is_custom(self):
        v = self.values
        return bool(v.get("sort") and v["sort"] != self.default_sort) or (
            bool(v.get("order")) and v["order"] != self.default_order)


class ProductFilterForm(ListFilterForm):
    q = forms.CharField(label="Αναζήτηση", required=False,
                        widget=forms.TextInput(attrs={"placeholder": "Κωδικός ή περιγραφή…"}))
    q.col = 12
    category = _choice("Κατηγορία", [])
    supplier = _choice("Προμηθευτής", [])
    status = _choice("Κατάσταση αποθέματος", STATUS_CHOICES)
    image = _choice("Εικόνα", [("", "Όλα"), ("yes", "Με εικόνα"), ("no", "Χωρίς εικόνα")])
    stock_min = _number("Απόθεμα από")
    stock_max = _number("Απόθεμα έως")
    price_min = _number("Τιμή από (€)", min_value=0)
    price_max = _number("Τιμή έως (€)", min_value=0)
    sort = _choice("Ταξινόμηση", [("id", "Σειρά καταχώρησης"), ("desc", "Περιγραφή"), ("stock", "Απόθεμα"),
                                  ("price", "Τιμή"), ("value", "Αξία αποθέματος"),
                                  ("date_updated", "Τελευταία ενημέρωση")])
    order = _choice("Σειρά", ORDER_CHOICES)

    sort_fields = {"id": F("id"), "desc": F("desc"), "stock": F("stock"), "price": F("price"),
                   "value": F("value"), "date_updated": F("date_updated")}
    default_sort = "id"
    ranges = (("stock_min", "stock_max", "stock"), ("price_min", "price_max", "price"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = [("", "Όλες"), ("none", "Χωρίς κατηγορία")] + [
            (str(c.id), c.cat_type or f"#{c.id}") for c in Category.objects.order_by("cat_type")]
        self.fields["supplier"].choices = [("", "Όλοι"), ("none", "Χωρίς προμηθευτή")] + [
            (str(s.id), s.name) for s in Supplier.objects.order_by("name")]

    def apply(self, queryset, include_status=True):
        v = self.values
        if v.get("q"):
            queryset = queryset.filter(Q(barcode__icontains=v["q"]) | Q(desc__icontains=v["q"]))
        for field in ("category", "supplier"):
            if v.get(field) == "none":
                queryset = queryset.filter(**{f"{field}__isnull": True})
            elif v.get(field):
                queryset = queryset.filter(**{f"{field}_id": int(v[field])})
        if v.get("image") == "yes":
            queryset = queryset.exclude(image__isnull=True).exclude(image="")
        elif v.get("image") == "no":
            queryset = queryset.filter(Q(image__isnull=True) | Q(image=""))
        if include_status and v.get("status"):
            queryset = queryset.filter(STATUS_FILTERS[v["status"]])
        queryset = self._apply_ranges(queryset)
        return self._apply_sort(queryset.annotate(value=STOCK_VALUE), "id")


HEALTH_FILTERS = {
    "reorder": Q(reorder__gt=0),
    "out": Q(out_of_stock__gt=0),
    "healthy": Q(product_count__gt=0, reorder=0),
    "empty": Q(product_count=0),
}


class GroupFilterForm(ListFilterForm):
    """Categories and suppliers, annotated by `stock.with_stock_stats`."""

    q = forms.CharField(label="Αναζήτηση", required=False,
                        widget=forms.TextInput(attrs={"placeholder": "Όνομα…"}))
    q.col = 12
    health = _choice("Κατάσταση αποθέματος", [
        ("", "Όλες"), ("reorder", "Με προϊόντα προς παραγγελία"), ("out", "Με εξαντλημένα προϊόντα"),
        ("healthy", "Όλα τα προϊόντα διαθέσιμα"), ("empty", "Χωρίς προϊόντα")], col=12)
    products_min = _number("Προϊόντα από", min_value=0)
    products_max = _number("Προϊόντα έως", min_value=0)
    value_min = _number("Αξία από (€)", min_value=0)
    value_max = _number("Αξία έως (€)", min_value=0)
    sort = _choice("Ταξινόμηση", [("name", "Όνομα"), ("reorder", "Προς παραγγελία"),
                                  ("value", "Αξία αποθέματος"), ("products", "Πλήθος προϊόντων")])
    order = _choice("Σειρά", ORDER_CHOICES)

    name_field = "cat_type"
    search_fields = ("cat_type",)
    default_sort = "name"
    ranges = (("products_min", "products_max", "product_count"), ("value_min", "value_max", "stock_value"))

    @property
    def sort_fields(self):
        return {"name": F(self.name_field), "reorder": F("reorder"),
                "value": F("stock_value"), "products": F("product_count")}

    def apply(self, queryset):
        v = self.values
        if v.get("q"):
            search = Q()
            for field in self.search_fields:
                search |= Q(**{f"{field}__icontains": v["q"]})
            queryset = queryset.filter(search)
        if v.get("health"):
            queryset = queryset.filter(HEALTH_FILTERS[v["health"]])
        queryset = self._apply_ranges(queryset)
        return self._apply_sort(queryset, self.name_field)


class CategoryFilterForm(GroupFilterForm):
    pass


class SupplierFilterForm(GroupFilterForm):
    contact = _choice("Στοιχεία επικοινωνίας", [
        ("", "Όλοι"), ("complete", "Με email και τηλέφωνο"), ("no_email", "Χωρίς email"),
        ("no_phone", "Χωρίς τηλέφωνο")], col=12)

    name_field = "name"
    search_fields = ("name", "email", "phone")
    field_order = ["q", "health", "contact"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["q"].widget.attrs["placeholder"] = "Όνομα, email ή τηλέφωνο…"

    def apply(self, queryset):
        missing = {"email": Q(email__isnull=True) | Q(email=""), "phone": Q(phone__isnull=True) | Q(phone="")}
        contact = self.values.get("contact")
        if contact == "complete":
            queryset = queryset.exclude(missing["email"]).exclude(missing["phone"])
        elif contact == "no_email":
            queryset = queryset.filter(missing["email"])
        elif contact == "no_phone":
            queryset = queryset.filter(missing["phone"])
        return super().apply(queryset)
