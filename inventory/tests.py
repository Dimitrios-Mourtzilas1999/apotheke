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
        self.assertEqual(r.context["category_data"],
                         {"labels": ["C1", "Χωρίς κατηγορία"], "values": [15, 2], "counts": [1, 1]})
        self.assertContains(r, 'id="category-data"')
        self.assertContains(r, 'name="csrf-token"')

    def test_dashboard_stock_status_and_reorder_list(self):
        Product.objects.create(barcode="in", stock=10, price=1)
        Product.objects.create(barcode="low", desc="Low", stock=3, price=None)
        Product.objects.create(barcode="zero", stock=0, price=4)
        Product.objects.create(barcode="none", stock=None, price=4)
        r = self.c.get("/dashboard")
        self.assertEqual(r.context["total_stock_value"], 10)
        self.assertEqual(r.context["stock_status_data"]["values"], [1, 1, 2])
        self.assertEqual((r.context["low_stock_count"], r.context["out_of_stock_count"]), (1, 2))
        self.assertEqual([p.barcode for p in r.context["reorder_products"]], ["none", "zero", "low"])
        self.assertContains(r, '/product/edit/low')

    def test_stock_health_is_consistent_across_views(self):
        Product.objects.create(barcode="neg", stock=-1)
        Product.objects.create(barcode="zero", stock=0)
        Product.objects.create(barcode="none", stock=None)
        Product.objects.create(barcode="low", stock=3)
        Product.objects.create(barcode="ok", stock=10)
        self.assertEqual(Product.objects.get(barcode="neg").stock_status, "out_of_stock")
        summary = self.c.get("/api/stock-summary").json()["results"]
        self.assertEqual((summary["summary"]["low_stock"], summary["summary"]["out_of_stock"]), (1, 3))
        self.assertEqual([p["barcode"] for p in summary["low_stock_products"]], ["none", "neg", "zero", "low"])
        r = self.c.get("/dashboard")
        self.assertEqual((r.context["low_stock_count"], r.context["out_of_stock_count"]), (1, 3))
        statuses = {p.barcode: p.stock_status for p in Product.objects.all()}
        self.assertEqual(sorted(b for b, s in statuses.items() if s == "out_of_stock"), ["neg", "none", "zero"])

    def _stock_fixture(self):
        self.cat_a = Category.objects.create(cat_type="Alpha")
        self.cat_b = Category.objects.create(cat_type="Beta")
        Category.objects.create(cat_type="Empty")
        self.sup_a = Supplier.objects.create(name="Acme", email="a@x.gr", phone="1")
        self.sup_b = Supplier.objects.create(name="Bolt")
        Product.objects.create(barcode="ok", desc="Aspirin", stock=20, price=5, category=self.cat_a, supplier=self.sup_a)
        Product.objects.create(barcode="low", desc="Bandage", stock=3, price=10, category=self.cat_a, supplier=self.sup_b)
        Product.objects.create(barcode="zero", desc="Cream", stock=0, price=7, category=self.cat_b, supplier=self.sup_b)
        Product.objects.create(barcode="none", desc="Drops", stock=None, price=2, image="none.png")

    def test_product_filters(self):
        self._stock_fixture()
        url = "/product/products/list"
        barcodes = lambda r: [p.barcode for p in r.context["products"]]
        self.assertEqual(barcodes(self.c.get(url, {"status": "reorder"})), ["low", "zero", "none"])
        self.assertEqual(barcodes(self.c.get(url, {"status": "out"})), ["zero", "none"])
        self.assertEqual(barcodes(self.c.get(url, {"q": "band"})), ["low"])
        self.assertEqual(barcodes(self.c.get(url, {"category": "none"})), ["none"])
        self.assertEqual(barcodes(self.c.get(url, {"supplier": self.sup_b.id})), ["low", "zero"])
        self.assertEqual(barcodes(self.c.get(url, {"image": "yes"})), ["none"])
        self.assertEqual(barcodes(self.c.get(url, {"price_min": 5, "price_max": 7})), ["ok", "zero"])
        self.assertEqual(barcodes(self.c.get(url, {"stock_max": 3})), ["low", "zero"])
        self.assertEqual(barcodes(self.c.get(url, {"sort": "value", "order": "desc"})), ["ok", "low", "zero", "none"])

        r = self.c.get(url, {"supplier": self.sup_b.id, "status": "low"})
        chips = {c["key"]: c["count"] for c in r.context["status_chips"]}
        self.assertEqual((chips[""], chips["reorder"], chips["low"], chips["out"]), (2, 2, 1, 1))
        self.assertEqual(r.context["filtered_value"], 30)
        self.assertEqual(r.context["filter_count"], 2)
        self.assertContains(r, 'id="filterModal"')
        self.assertContains(r, "Προμηθευτής: <strong>Bolt</strong>", html=False)

        r = self.c.get(url, {"price_min": 9, "price_max": 1})
        self.assertIn("price_max", r.context["filter_form"].errors)
        self.assertEqual(len(r.context["products"]), 4)  # an invalid range is dropped as a whole
        self.assertContains(r, "data-open-on-load")

    def test_filters_survive_pagination(self):
        for i in range(12):
            Product.objects.create(barcode=f"p{i:02d}", stock=1, price=1)
        r = self.c.get("/product/products/list", {"status": "low", "page": 1})
        self.assertContains(r, 'href="?status=low&amp;page=2"')
        self.assertContains(r, "/product/products/cards?status=low")

    def test_category_list_stats_and_filters(self):
        self._stock_fixture()
        r = self.c.get("/category/list")
        stats = {c.cat_type: (c.product_count, c.stock_value, c.low_stock, c.out_of_stock, c.reorder)
                 for c in r.context["groups"]}
        self.assertEqual(stats, {"Alpha": (2, 130, 1, 0, 1), "Beta": (1, 0, 0, 1, 1), "Empty": (0, 0, 0, 0, 0)})
        self.assertEqual(r.context["uncategorized"], 1)
        names = lambda params: [c.cat_type for c in self.c.get("/category/list", params).context["groups"]]
        self.assertEqual(names({"health": "out"}), ["Beta"])
        self.assertEqual(names({"health": "empty"}), ["Empty"])
        self.assertEqual(names({"health": "reorder", "sort": "value", "order": "desc"}), ["Alpha", "Beta"])
        self.assertEqual(names({"q": "alp"}), ["Alpha"])
        self.assertEqual(names({"products_min": 1, "value_max": 50}), ["Beta"])
        self.assertContains(self.c.get("/category/list", {"q": "zzz"}), "Καμία κατηγορία δεν ταιριάζει")

    def test_supplier_list_stats_and_filters(self):
        self._stock_fixture()
        r = self.c.get("/supplier/")
        stats = {s.name: (s.product_count, s.stock_value, s.reorder) for s in r.context["groups"]}
        self.assertEqual(stats, {"Acme": (1, 100, 0), "Bolt": (2, 30, 2)})
        self.assertEqual(r.context["unassigned"], 1)
        names = lambda params: [s.name for s in self.c.get("/supplier/", params).context["groups"]]
        self.assertEqual(names({"health": "healthy"}), ["Acme"])
        self.assertEqual(names({"contact": "no_email"}), ["Bolt"])
        self.assertEqual(names({"contact": "complete"}), ["Acme"])
        self.assertEqual(names({"q": "a@x"}), ["Acme"])
        self.assertEqual(names({"sort": "reorder", "order": "desc"}), ["Bolt", "Acme"])

    def test_group_detail_pages_filter_by_status(self):
        self._stock_fixture()
        r = self.c.get(f"/category/info/{self.cat_a.id}", {"status": "reorder"})
        self.assertEqual([p.barcode for p in r.context["products"]], ["low"])
        self.assertEqual((r.context["totals"]["products"], r.context["filtered_value"]), (2, 30))
        r = self.c.get(f"/supplier/{self.sup_b.id}/products", {"status": "out"})
        self.assertEqual([p.barcode for p in r.context["products"]], ["zero"])
        self.assertContains(r, "Εξαντλημένο")

    def test_dashboard_groups_tail_into_other(self):
        for i in range(10):
            sup = Supplier.objects.create(name=f"S{i}")
            Product.objects.create(barcode=str(i), price=1, stock=10 + i, supplier=sup)
        data = self.c.get("/dashboard").context["supplier_data"]
        self.assertEqual(len(data["labels"]), 8)
        self.assertEqual(data["labels"][0], "S9")
        self.assertEqual(data["labels"][-1], "Λοιποί προμηθευτές (σύνολο)")
        self.assertEqual(sum(data["values"]), sum(10 + i for i in range(10)))
        self.assertEqual(sum(data["counts"]), 10)

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
        self.assertEqual(r.context["groups"][0].product_count, 1)
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
