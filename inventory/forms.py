from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator

from .models import Category, Product, Supplier

CTRL = {"class": "form-control"}


class AssignProductForm(forms.Form):
    """Port of the Flask AssignProductForm (choices load lazily from the DB)."""

    categories = forms.ModelChoiceField(queryset=Category.objects.all(), label="Επιλογή Κατηγορίας",
                                        widget=forms.Select(attrs={"class": "categories"}))
    suppliers = forms.ModelChoiceField(queryset=Supplier.objects.all(), label="Επιλογή Προμηθευτή",
                                       widget=forms.Select(attrs={"class": "suppliers"}))


class CategoryForm(forms.Form):
    category_type = forms.CharField(label="Κατηγορία", max_length=100)


def _image_field():
    return forms.FileField(
        label="Αρχείο εικόνας", required=False, widget=forms.FileInput(attrs=CTRL),
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
    )


class _ProductFormBase(forms.Form):
    barcode = forms.CharField(label="Barcode", max_length=255, widget=forms.TextInput(attrs=CTRL))
    desc = forms.CharField(label="Περιγραφή προϊόντος", max_length=100, widget=forms.TextInput(attrs=CTRL))
    price = forms.IntegerField(label="Τιμή προϊόντος", min_value=0, widget=forms.NumberInput(attrs=CTRL))
    stock = forms.IntegerField(label="Ποσότητα", min_value=0, widget=forms.NumberInput(attrs=CTRL))
    categories = forms.ModelChoiceField(label="Κατηγορία", queryset=Category.objects.order_by("cat_type"),
                                        required=False, empty_label="Χωρίς κατηγορία",
                                        widget=forms.Select(attrs=CTRL))
    suppliers = forms.ModelChoiceField(label="Προμηθευτής", queryset=Supplier.objects.order_by("name"),
                                       required=False, empty_label="Επιλέξτε προμηθευτή",
                                       widget=forms.Select(attrs=CTRL))
    image = _image_field()

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > settings.UPLOAD_MAX_BYTES:
            raise forms.ValidationError("Το αρχείο είναι πολύ μεγάλο (max 16MB)")
        return image


class ProductRegistrationForm(_ProductFormBase):
    pass


class ProductEditForm(_ProductFormBase):
    def __init__(self, *args, product=None, **kwargs):
        self.product = product
        super().__init__(*args, **kwargs)

    def clean_barcode(self):
        barcode = self.cleaned_data["barcode"]
        clash = Product.objects.filter(barcode=barcode)
        if self.product:
            clash = clash.exclude(pk=self.product.pk)
        if clash.exists():
            raise forms.ValidationError("Το προϊόν υπάρχει ήδη")
        return barcode


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "email", "phone"]
        labels = {"name": "Name", "email": "Email", "phone": "Phone"}
        widgets = {
            "name": forms.TextInput(attrs=CTRL),
            "email": forms.EmailInput(attrs=CTRL),
            "phone": forms.TextInput(attrs=CTRL),  # text, not int: keeps leading zeros
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["phone"].required = True

    def clean_name(self):
        name = self.cleaned_data["name"]
        clash = Supplier.objects.filter(name=name)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("Ο προμηθευτής υπάρχει ήδη")
        return name
