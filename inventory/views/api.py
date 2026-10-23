from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.conf import settings
from ..models import Product, Category, Supplier


@require_GET
def api_products(request):
    """API endpoint to retrieve products with filtering and search"""
    try:
        query = request.GET.get('q', '')
        category_id = request.GET.get('category')
        supplier_id = request.GET.get('supplier')
        low_stock = request.GET.get('low_stock', '').lower() == 'true'
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))

        # Build queryset
        products = Product.objects.select_related('category', 'supplier').all()

        # Search by barcode or description
        if query:
            products = products.filter(
                Q(barcode__icontains=query) | Q(description__icontains=query)
            )

        # Filter by category
        if category_id:
            products = products.filter(category_id=category_id)

        # Filter by supplier
        if supplier_id:
            products = products.filter(supplier_id=supplier_id)

        # Filter low stock (less than 10)
        if low_stock:
            products = products.filter(stock__lt=10)

        # Paginate
        paginator = Paginator(products, per_page)
        products_page = paginator.get_page(page)

        # Serialize
        data = {
            'products': [
                {
                    'id': p.id,
                    'barcode': p.barcode,
                    'description': p.description,
                    'category': p.category.cat_type if p.category else None,
                    'supplier': p.supplier.name if p.supplier else None,
                    'stock': p.stock,
                    'price': p.price,
                    'image': p.image.url if p.image else None,
                    'qr_code': p.qr_code.url if p.qr_code else None,
                }
                for p in products_page
            ],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginator.count,
                'total_pages': paginator.num_pages,
            }
        }

        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def api_product_detail(request, product_id):
    """API endpoint to retrieve a single product by ID or barcode"""
    try:
        # Try to find by ID first, then by barcode
        try:
            product = Product.objects.select_related('category', 'supplier').get(id=product_id)
        except Product.DoesNotExist:
            product = Product.objects.select_related('category', 'supplier').get(barcode=product_id)

        data = {
            'id': product.id,
            'barcode': product.barcode,
            'description': product.description,
            'category': product.category.cat_type if product.category else None,
            'supplier': product.supplier.name if product.supplier else None,
            'stock': product.stock,
            'price': product.price,
            'image': product.image.url if product.image else None,
            'qr_code': product.qr_code.url if product.qr_code else None,
            'date_added': product.date_added.isoformat() if product.date_added else None,
            'date_updated': product.date_updated.isoformat() if product.date_updated else None,
        }

        return JsonResponse(data)

    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def api_categories(request):
    """API endpoint to retrieve categories with product counts"""
    try:
        categories = Category.objects.annotate(
            product_count=Count('products'),
            total_stock=Sum('products__stock')
        ).all()

        data = {
            'categories': [
                {
                    'id': c.id,
                    'cat_type': c.cat_type,
                    'product_count': c.product_count or 0,
                    'total_stock': c.total_stock or 0,
                }
                for c in categories
            ]
        }

        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def api_category_detail(request, category_id):
    """API endpoint to retrieve a single category with its products"""
    try:
        category = Category.objects.get(id=category_id)
        products = category.products.select_related('supplier').all()

        data = {
            'id': category.id,
            'cat_type': category.cat_type,
            'product_count': products.count(),
            'products': [
                {
                    'id': p.id,
                    'barcode': p.barcode,
                    'description': p.description,
                    'supplier': p.supplier.name if p.supplier else None,
                    'stock': p.stock,
                    'price': p.price,
                }
                for p in products
            ]
        }

        return JsonResponse(data)

    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def api_suppliers(request):
    """API endpoint to retrieve suppliers with product counts"""
    try:
        suppliers = Supplier.objects.annotate(
            product_count=Count('products')
        ).all()

        data = {
            'suppliers': [
                {
                    'id': s.id,
                    'name': s.name,
                    'address': s.address,
                    'phone': s.phone,
                    'email': s.email,
                    'product_count': s.product_count or 0,
                }
                for s in suppliers
            ]
        }

        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def api_supplier_detail(request, supplier_id):
    """API endpoint to retrieve a single supplier with its products"""
    try:
        supplier = Supplier.objects.get(id=supplier_id)
        products = supplier.products.select_related('category').all()

        data = {
            'id': supplier.id,
            'name': supplier.name,
            'address': supplier.address,
            'phone': supplier.phone,
            'email': supplier.email,
            'product_count': products.count(),
            'products': [
                {
                    'id': p.id,
                    'barcode': p.barcode,
                    'description': p.description,
                    'category': p.category.cat_type if p.category else None,
                    'stock': p.stock,
                    'price': p.price,
                }
                for p in products
            ]
        }

        return JsonResponse(data)

    except Supplier.DoesNotExist:
        return JsonResponse({'error': 'Supplier not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def api_stock_summary(request):
    """API endpoint to retrieve stock summary information"""
    try:
        products = Product.objects.all()

        total_products = products.count()
        low_stock = products.filter(stock__lt=10).count()
        out_of_stock = products.filter(stock=0).count()
        total_stock = products.aggregate(Sum('stock'))['stock__sum'] or 0

        # Get low stock products
        low_stock_products = products.filter(stock__lt=10).select_related('category', 'supplier')[:10]

        data = {
            'summary': {
                'total_products': total_products,
                'low_stock': low_stock,
                'out_of_stock': out_of_stock,
                'total_stock': total_stock,
            },
            'low_stock_products': [
                {
                    'id': p.id,
                    'barcode': p.barcode,
                    'description': p.description,
                    'category': p.category.cat_type if p.category else None,
                    'stock': p.stock,
                }
                for p in low_stock_products
            ]
        }

        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
