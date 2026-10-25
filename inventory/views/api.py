from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Sum
from ..models import Product, Category, Supplier
from ..serializers import (
    ProductSerializer, ProductDetailSerializer,
    CategorySerializer, CategoryProductSerializer,
    SupplierSerializer, SupplierProductSerializer,
    LowStockProductSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'per_page'
    max_page_size = 100


@api_view(['GET'])
def api_products(request):
    """API endpoint to retrieve products with filtering and search"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    supplier_id = request.GET.get('supplier')
    low_stock = request.GET.get('low_stock', '').lower() == 'true'

    # Build queryset
    products = Product.objects.select_related('category', 'supplier').all()

    # Search by barcode or description
    if query:
        products = products.filter(
            Q(barcode__icontains=query) | Q(desc__icontains=query)
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
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(products, request)

    serializer = ProductSerializer(page, many=True)

    return paginator.get_paginated_response({
        'products': serializer.data
    })


@api_view(['GET'])
def api_product_detail(request, product_id):
    """API endpoint to retrieve a single product by ID or barcode"""
    try:
        # Try to find by ID first, then by barcode
        try:
            product = Product.objects.select_related('category', 'supplier').get(id=product_id)
        except Product.DoesNotExist:
            product = Product.objects.select_related('category', 'supplier').get(barcode=product_id)

        serializer = ProductDetailSerializer(product)
        return Response(serializer.data)

    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def api_categories(request):
    """API endpoint to retrieve categories with product counts"""
    search = request.GET.get('search', '')

    categories = Category.objects.annotate(
        product_count=Count('products'),
        total_stock=Sum('products__stock')
    ).all()

    # Search by category type
    if search:
        categories = categories.filter(cat_type__icontains=search)

    # Paginate
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(categories, request)

    serializer = CategorySerializer(page, many=True)

    return paginator.get_paginated_response({
        'categories': serializer.data
    })


@api_view(['GET'])
def api_category_detail(request, category_id):
    """API endpoint to retrieve a single category with its products"""
    try:
        search = request.GET.get('search', '')

        category = Category.objects.get(id=category_id)
        products = category.products.select_related('supplier').all()

        # Search products
        if search:
            products = products.filter(
                Q(barcode__icontains=search) | Q(desc__icontains=search)
            )

        # Paginate
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(products, request)

        serializer = CategoryProductSerializer(page, many=True)

        data = {
            'id': category.id,
            'cat_type': category.cat_type,
            'product_count': products.count(),
            'products': serializer.data
        }

        return paginator.get_paginated_response(data)

    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def api_suppliers(request):
    """API endpoint to retrieve suppliers with product counts"""
    search = request.GET.get('search', '')

    suppliers = Supplier.objects.annotate(
        product_count=Count('products')
    ).all()

    # Search by name
    if search:
        suppliers = suppliers.filter(name__icontains=search)

    # Paginate
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(suppliers, request)

    serializer = SupplierSerializer(page, many=True)

    return paginator.get_paginated_response({
        'suppliers': serializer.data
    })


@api_view(['GET'])
def api_supplier_detail(request, supplier_id):
    """API endpoint to retrieve a single supplier with its products"""
    try:
        search = request.GET.get('search', '')

        supplier = Supplier.objects.get(id=supplier_id)
        products = supplier.products.select_related('category').all()

        # Search products
        if search:
            products = products.filter(
                Q(barcode__icontains=search) | Q(desc__icontains=search)
            )

        # Paginate
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(products, request)

        serializer = SupplierProductSerializer(page, many=True)

        data = {
            'id': supplier.id,
            'name': supplier.name,
            'phone': supplier.phone,
            'email': supplier.email,
            'product_count': products.count(),
            'products': serializer.data
        }

        return paginator.get_paginated_response(data)

    except Supplier.DoesNotExist:
        return Response({'error': 'Supplier not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def api_stock_summary(request):
    """API endpoint to retrieve stock summary information"""
    products = Product.objects.all()

    total_products = products.count()
    low_stock = products.filter(stock__lt=10).count()
    out_of_stock = products.filter(stock=0).count()
    total_stock = products.aggregate(Sum('stock'))['stock__sum'] or 0

    # Get low stock products with pagination
    low_stock_products = products.filter(stock__lt=10).select_related('category', 'supplier')

    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(low_stock_products, request)

    serializer = LowStockProductSerializer(page, many=True)

    data = {
        'summary': {
            'total_products': total_products,
            'low_stock': low_stock,
            'out_of_stock': out_of_stock,
            'total_stock': total_stock,
        },
        'low_stock_products': serializer.data
    }

    return paginator.get_paginated_response(data)
