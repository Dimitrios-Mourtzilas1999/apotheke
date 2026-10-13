import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.utils.text import get_valid_filename


def paginate(queryset, page, per_page=20):
    """Same return shape as the Flask helper: items, page, pages, total."""
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    return page_obj.object_list, page_obj.number, paginator.num_pages, paginator.count


def uploads_storage():
    return FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "uploads"),
                             base_url=settings.MEDIA_URL + "uploads/")


def save_product_image(uploaded, barcode):
    """Store an upload as '<barcode>_<name>' (never overwrites; Django de-dupes the name)."""
    name = get_valid_filename(f"{barcode}_{os.path.basename(uploaded.name)}")
    return uploads_storage().save(name, uploaded)


def delete_product_image(filename):
    if filename and filename != "default.jpg":
        uploads_storage().delete(filename)


def make_qr_code(barcode):
    """Write media/qrcodes/<barcode>.png and return the file name."""
    import qrcode

    folder = os.path.join(settings.MEDIA_ROOT, "qrcodes")
    os.makedirs(folder, exist_ok=True)
    filename = get_valid_filename(f"{barcode}.png")
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(barcode)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(os.path.join(folder, filename))
    return filename
