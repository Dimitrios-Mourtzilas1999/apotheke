from django.db import models
from django.utils import timezone


class Category(models.Model):
    cat_type = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "category"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.cat_type or f"Category {self.pk}"


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "suppliers"

    def __str__(self):
        return self.name


class Product(models.Model):
    barcode = models.CharField(max_length=255, unique=True)
    desc = models.CharField(max_length=100, blank=True, default="")
    stock = models.IntegerField(null=True, blank=True, default=0)
    price = models.IntegerField(null=True, blank=True, default=0)
    image = models.CharField(max_length=255, null=True, blank=True)   # filename, as in Flask
    qr_code = models.CharField(max_length=255, null=True, blank=True)
    date_created = models.DateTimeField(null=True, blank=True, default=timezone.now)
    # Flask: default=datetime.now only (no onupdate). auto_now makes "updated" actually update.
    date_updated = models.DateTimeField(null=True, blank=True, auto_now=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL,
                                 db_column="cat_id", related_name="products")
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.SET_NULL,
                                 db_column="supplier_id", related_name="products")

    class Meta:
        db_table = "product"

    def __str__(self):
        return f"{self.barcode} - {self.desc}"

    def to_dict(self):
        return {
            "id": self.id,
            "barcode": self.barcode,
            "desc": self.desc,
            "stock": self.stock,
            "price": self.price,
            "category": self.category.cat_type if self.category else None,
            "date_updated": self.date_updated.strftime("%Y-%m-%d") if self.date_updated else None,
        }

    @property
    def image_url(self):
        if self.image:
            return f"/media/uploads/{self.image}"
        return None

    @property
    def stock_status(self):
        if self.stock is None or self.stock == 0:
            return "out_of_stock"
        elif self.stock < 10:
            return "low_stock"
        else:
            return "in_stock"

    @property
    def stock_status_label(self):
        if self.stock is None or self.stock == 0:
            return "Εξαντλημένο"
        elif self.stock < 10:
            return "Περιορισμένο"
        else:
            return "Διαθέσιμο"
