from flask import Blueprint, render_template, request, jsonify
from app.models import db, Product, CompetitorPrice

products_bp = Blueprint('products', __name__)

@products_bp.route('/')
def index():
    category = request.args.get('category', '').strip()
    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 12

    query = Product.query

    if category:
        query = query.filter(Product.category == category)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

    pagination = query.order_by(Product.popularity_score.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Categories for filter chips
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]

    # Flash sale featured items (top 4 high discount products)
    flash_products = Product.query.filter(
        Product.current_price < Product.base_price
    ).order_by((Product.base_price - Product.current_price).desc()).limit(4).all()

    return render_template(
        'storefront/index.html',
        products=pagination.items,
        pagination=pagination,
        categories=categories,
        selected_category=category,
        search_query=search,
        flash_products=flash_products
    )

@products_bp.route('/products/<product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    competitors = CompetitorPrice.query.filter_by(product_id=product.id).all()
    related_products = Product.query.filter(
        Product.category == product.category,
        Product.id != product.id
    ).limit(4).all()

    return render_template(
        'storefront/product_detail.html',
        product=product,
        competitors=competitors,
        related_products=related_products
    )

@products_bp.route('/api/products')
def api_products():
    category = request.args.get('category')
    search = request.args.get('q')
    flash_only = request.args.get('flash_only', type=bool)

    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if flash_only:
        query = query.filter(Product.current_price < Product.base_price)

    products = query.limit(50).all()
    return jsonify([p.to_dict() for p in products])
