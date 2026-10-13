import io
import json
import shutil
import tempfile
from pathlib import Path

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Role, User
from .models import Category, Product, Supplier

TMP_MEDIA = tempfile.mkdtemp()
MD5_OF_1 = "c4ca4238a0b923820dcc509a6f75849b"  # same shape as the hash in the Flask dump
SHA256_OF_PW = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # sha256("password")


def png(name="x.png"):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=TMP_MEDIA, ALLOWED_HOSTS=["testserver"])
class AppTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.admin_role = Role.objects.create(role="admin")
        self.user_role = Role.objects.create(role="user")
        # legacy users exactly as stored by the Flask app (unsalted hex digests)
        User.objects.create(username="legacy_md5", password=MD5_OF_1)
        User.objects.create(username="legacy_sha", password=SHA256_OF_PW, role=self.user_role)
        self.c = Client()
        assert self.c.login(username="legacy_md5", password="1")

    # ---------- auth ----------
    def test_legacy_hashes_login_and_get_upgraded(self):
        self.assertTrue(User.objects.get(username="legacy_md5").password.startswith("pbkdf2_sha256$"))
        c = Client()
        self.assertFalse(c.login(username="legacy_sha", password="wrong"))
        self.assertTrue(c.login(username="legacy_sha", password="password"))
        self.assertTrue(User.objects.get(username="legacy_sha").password.startswith("pbkdf2_sha256$"))
        self.assertTrue(Client().login(username="legacy_sha", password="password"))  # now via PBKDF2

    def test_anonymous_is_redirected_everywhere(self):
        anon = Client()
        for name, args in [("dashboard", []), ("category_list", []), ("supplier_list", []),
                           ("product_list", ["list"]), ("reset_password", [])]:
            r = anon.get(reverse(name, args=args))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn("/login", r["Location"], name)
        for url in ["/product/delete", "/supplier/delete", "/filters"]:
            self.assertEqual(anon.post(url, "{}", content_type="application/json").status_code, 302)
        self.assertEqual(anon.get("/login").status_code, 200)

    def test_login_page_and_bad_login_message(self):
        r = Client().post("/login", {"username": "legacy_md5", "password": "nope"})
        self.assertContains(r, "Τα στοιχεία σύνδεσης είναι λάθος")
        r = self.c.get("/login")
        self.assertRedirects(r, "/dashboard", fetch_redirect_response=False)

    def test_logout_is_post_only(self):
        self.assertEqual(self.c.get("/logout").status_code, 405)
        self.assertEqual(self.c.post("/logout").status_code, 302)
        self.assertEqual(self.c.get("/dashboard").status_code, 302)

    def test_password_reset_rules(self):
        r = self.c.post("/reset-password", {"username": "legacy_sha", "password": "a", "password_confirm": "a"})
        self.assertContains(r, "μόνο τον δικό σας")  # non-admin cannot reset someone else
        r = self.c.post("/reset-password", {"username": "legacy_md5", "password": "a", "password_confirm": "b"})
        self.assertContains(r, "δεν ταιριαζουν")
        r = self.c.post("/reset-password", {"username": "legacy_md5", "password": "newpw", "password_confirm": "newpw"})
        self.assertRedirects(r, "/login", fetch_redirect_response=False)
        self.assertTrue(Client().login(username="legacy_md5", password="newpw"))

    # ---------- dashboard ----------
    def test_dashboard_numbers_and_chart_json(self):
        cat = Category.objects.create(cat_type="C1")
        sup = Supplier.objects.create(name="S1")
        Product.objects.create(barcode="1", price=5, stock=3, category=cat, supplier=sup)
        Product.objects.create(barcode="2", price=2, stock=1)
        r = self.c.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["total_products"], 2)
        self.assertEqual(r.context["total_stock_value"], 17)
        self.assertEqual(r.context["category_data"], {"labels": ["C1"], "values": [1]})
        self.assertContains(r, 'id="category-data"')
        self.assertContains(r, 'name="csrf-token"')

    def test_filters_endpoints(self):
        r = self.c.post("/filters", json.dumps({"barcode": "9"}), content_type="application/json")
        self.assertEqual(r.json()["filters"]["sort"], "date_updated")
        self.assertEqual(self.c.session["filters"]["barcode"], "9")
        self.c.post("/clear-filters")
        self.assertNotIn("filters", self.c.session)

    # ---------- categories ----------
    def test_category_crud(self):
        r = self.c.post("/category/register-category", {"category_type": "Φάρμακα"})
        self.assertRedirects(r, "/category/list", fetch_redirect_response=False)
        cat = Category.objects.get()
        Product.objects.create(barcode="p1", category=cat)
        r = self.c.get("/category/list")
        self.assertContains(r, "Φάρμακα")
        self.assertEqual(r.context["categories"][0].product_count, 1)
        self.assertContains(self.c.get(f"/category/info/{cat.id}"), "p1")
        self.assertEqual(self.c.get("/category/info/999").status_code, 302)
        self.assertContains(self.c.get(f"/category/edit/{cat.id}"), "Φάρμακα")
        self.c.post(f"/category/edit/{cat.id}", {"category_type": "Νέα"})
        cat.refresh_from_db(); self.assertEqual(cat.cat_type, "Νέα")
        self.assertEqual(self.c.get("/category/delete", {"cat_id": cat.id}).status_code, 405)
        self.c.post("/category/delete", {"cat_id": cat.id})
        self.assertFalse(Category.objects.exists())
        self.assertIsNone(Product.objects.get().category)  # product survives, like SQLAlchemy backref

    def test_assign_products(self):
        cat, sup = Category.objects.create(cat_type="A"), Supplier.objects.create(name="S")
        Product.objects.create(barcode="b1"); Product.objects.create(barcode="b2")
        self.c.post("/category/assign_product", {"barcodes": "b1, b2", "categories": cat.id, "suppliers": sup.id})
        self.assertEqual(Product.objects.filter(category=cat, supplier=sup).count(), 2)
        r = self.c.post("/category/get-categories", json.dumps({"category_id": cat.id}), content_type="application/json")
        self.assertEqual(r.json()["category"]["cat_type"], "A")

    # ---------- suppliers ----------
    def test_supplier_crud(self):
        r = self.c.post("/supplier/register", {"name": "Acme", "email": "a@b.gr", "phone": "0301234567"})
        self.assertRedirects(r, "/dashboard", fetch_redirect_response=False)
        sup = Supplier.objects.get()
        self.assertEqual(sup.phone, "0301234567")  # leading zero preserved (Flask IntegerField dropped it)
        r = self.c.post("/supplier/register", {"name": "Acme", "email": "a@b.gr", "phone": "1"})
        self.assertContains(r, "υπάρχει ήδη")
        Product.objects.create(barcode="p", supplier=sup)
        self.assertContains(self.c.get("/supplier/"), "Acme")
        self.assertContains(self.c.get(f"/supplier/{sup.id}/products"), "p")
        self.assertEqual(self.c.get("/supplier/999/products").status_code, 404)
        self.assertContains(self.c.get(f"/supplier/{sup.id}/edit"), "Acme")
        self.c.post(f"/supplier/{sup.id}/edit", {"name": "Acme2", "email": "a@b.gr", "phone": "5"})
        sup.refresh_from_db(); self.assertEqual(sup.name, "Acme2")
        r = self.c.post("/supplier/delete", json.dumps({"name": "Acme2"}), content_type="application/json")
        self.assertEqual(r.json()["status"], "success")
        self.assertIsNone(Product.objects.get().supplier)

    # ---------- products ----------
    def test_product_register_edit_delete_with_image_and_qr(self):
        cat, sup = Category.objects.create(cat_type="A"), Supplier.objects.create(name="S")
        data = {"barcode": "5205344212071", "desc": "χαρτοσημο", "price": 0, "stock": 3,
                "categories": cat.id, "suppliers": sup.id, "image": png("pic.png")}
        r = self.c.post("/product/register", data)
        self.assertRedirects(r, "/product/products/list", fetch_redirect_response=False)
        p = Product.objects.get()
        self.assertEqual((p.price, p.stock, p.category, p.supplier), (0, 3, cat, sup))  # price 0 allowed
        self.assertTrue(p.image.startswith("5205344212071_pic"))
        self.assertTrue((Path(TMP_MEDIA) / "uploads" / p.image).exists())

        # duplicate barcode
        data["image"] = png()
        r = self.c.post("/product/register", data)
        self.assertEqual(Product.objects.count(), 1)

        # bad extension rejected
        bad = {**data, "barcode": "zzz", "image": SimpleUploadedFile("evil.php", b"x")}
        self.assertContains(self.c.post("/product/register", bad), "text-danger")

        # edit GET: QR generated, image + form shown
        r = self.c.get(f"/product/edit/{p.barcode}")
        self.assertEqual(r.status_code, 200)
        self.assertTrue((Path(TMP_MEDIA) / "qrcodes" / f"{p.barcode}.png").exists())
        self.assertContains(r, f"/media/uploads/{p.image}")
        self.assertEqual(self.c.get("/product/edit/nope").status_code, 302)

        # edit POST: new image replaces and removes old one; date_updated moves
        old_image, before = p.image, p.date_updated
        r = self.c.post(f"/product/edit/{p.barcode}", {**data, "desc": "new", "price": 7, "image": png("new.png")})
        self.assertRedirects(r, "/dashboard", fetch_redirect_response=False)
        p.refresh_from_db()
        self.assertEqual((p.desc, p.price), ("new", 7))
        self.assertNotEqual(p.image, old_image)
        self.assertFalse((Path(TMP_MEDIA) / "uploads" / old_image).exists())
        self.assertGreaterEqual(p.date_updated, before)

        # served media requires login, and works when logged in
        self.assertEqual(self.c.get(f"/media/uploads/{p.image}").status_code, 200)
        self.assertEqual(Client().get(f"/media/uploads/{p.image}").status_code, 302)

        # JSON delete (what products.js does)
        r = self.c.post("/product/delete", json.dumps({"barcodes": [p.barcode]}), content_type="application/json")
        self.assertEqual(r.json()["status"], "success")
        self.assertFalse(Product.objects.exists())
        self.assertEqual(self.c.post("/product/delete", "not json", content_type="application/json").status_code, 400)

    def test_edit_barcode_uniqueness(self):
        Product.objects.create(barcode="a"); b = Product.objects.create(barcode="b")
        r = self.c.post("/product/edit/b", {"barcode": "a", "desc": "d", "price": 1, "stock": 1})
        self.assertContains(r, "υπάρχει ήδη")
        b.refresh_from_db(); self.assertEqual(b.barcode, "b")

    def test_product_list_and_cards_pagination(self):
        for i in range(23):
            Product.objects.create(barcode=f"b{i:02d}", desc=f"d{i}", price=i, stock=1)
        r = self.c.get("/product/products/list")
        self.assertEqual((len(r.context["products"]), r.context["pages"], r.context["total"]), (10, 3, 23))
        r = self.c.get("/product/products/list?page=3")
        self.assertEqual(len(r.context["products"]), 3)
        self.assertContains(r, "<td>21</td>", html=True)  # continuous row numbering across pages
        self.assertContains(self.c.get("/product/products/list?page=2"), 'href="?page=3"')
        r = self.c.get("/product/products/cards")
        self.assertEqual((len(r.context["products"]), r.context["pages"]), (6, 4))
        self.assertContains(r, "product_cards.css")
        self.assertEqual(r.content.decode().count("<html"), 1)  # no nested documents (a Flask quirk)
        self.assertEqual(self.c.get("/product/products/list?page=abc").status_code, 200)

    def test_empty_states_and_menu(self):
        for url in ["/category/list", "/supplier/", "/product/products/list", "/product/products/cards"]:
            r = self.c.get(url)
            self.assertEqual(r.status_code, 200, url)
        self.assertContains(self.c.get("/product/products/list"), "Αποσύνδεση")
        self.assertContains(self.c.get("/product/products/list"), "legacy_md5")

    def test_csrf_is_enforced(self):
        c = Client(enforce_csrf_checks=True)
        c.login(username="legacy_md5", password="newpw-not-set") or c.force_login(User.objects.get(username="legacy_md5"))
        self.assertEqual(c.post("/product/delete", "{}", content_type="application/json").status_code, 403)
