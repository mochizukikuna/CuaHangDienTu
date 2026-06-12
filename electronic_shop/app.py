import os
# BỔ SUNG: Thêm "session" vào dòng import dưới đây
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
# BỔ SUNG: Import thêm Order và OrderItem
from models import db, User, Product, Order, OrderItem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dien_tu_bi_mat_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# --- CÁC ROUTE CŨ GIỮ NGUYÊN (Index, Register, Login, Logout, Product CRUD...) ---
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    if search_query:
        products_query = Product.query.filter(Product.name.like(f"%{search_query}%"))
    else:
        products_query = Product.query
    paginated_products = products_query.paginate(page=page, per_page=12)
    return render_template('index.html', products=paginated_products, search_query=search_query)

# --- CẬP NHẬT ROUTE ĐĂNG KÝ USER THƯỜNG ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # CỐ ĐỊNH: Luôn là 'user', không lấy từ form chọn như trước nữa
        role = 'user' 
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Tên tài khoản đã tồn tại!', 'danger')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Đăng ký tài khoản thành công! Hãy đăng nhập.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


# --- THÊM MỚI ROUTE ĐĂNG KÝ ADMIN (Có mã xác thực) ---
@app.route('/register/admin', methods=['GET', 'POST'])
def register_admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        secret_code = request.form.get('secret_code') # Lấy mã bí mật từ form
        
        # Đặt mã bảo mật nội bộ của hệ thống (Bạn có thể đổi thành mã tùy ý)
        ADMIN_SECRET_KEY = 'TechMartAdmin@2026'
        
        # Kiểm tra mã bí mật trước khi xử lý tạo tài khoản
        if secret_code != ADMIN_SECRET_KEY:
            flash('Mã xác thực quyền Admin không chính xác! Vui lòng liên hệ cấp trên.', 'danger')
            return render_template('register_admin.html')
            
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Tên tài khoản Admin này đã tồn tại!', 'danger')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            # CỐ ĐỊNH: Thiết lập quyền là 'admin'
            new_admin = User(username=username, password=hashed_password, role='admin')
            db.session.add(new_admin)
            db.session.commit()
            flash('Đăng ký tài khoản Admin thành công! Hãy đăng nhập vào hệ thống.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register_admin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Sai tài khoản hoặc mật khẩu!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện thao tác này!', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        file = request.files.get('image')
        filename = 'default.jpg'
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_product = Product(name=name, price=price, description=description, image=filename)
        db.session.add(new_product)
        db.session.commit()
        flash('Thêm sản phẩm thành công!', 'success')
        return redirect(url_for('index'))
    return render_template('add_product.html')

@app.route('/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền!', 'danger')
        return redirect(url_for('index'))
    product = Product.query.get(id)
    if not product:
        flash('Sản phẩm không tồn tại!', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.price = float(request.form.get('price'))
        product.description = request.form.get('description')
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.image = filename
        db.session.commit()
        flash('Cập nhật sản phẩm thành công!', 'success')
        return redirect(url_for('index'))
    return render_template('edit_product.html', product=product)

@app.route('/product/delete/<int:id>')
@login_required
def delete_product(id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền!', 'danger')
        return redirect(url_for('index'))
    product = Product.query.get(id)
    if product:
        db.session.delete(product)
        db.session.commit()
        flash('Đã xóa sản phẩm!', 'success')
    return redirect(url_for('index'))


# =======================================================
# --- THÊM CÁC ROUTE MỚI: GIỎ HÀNG & THANH TOÁN ---
# =======================================================

@app.route('/cart/add/<int:product_id>')
@login_required
def add_to_cart(product_id):
    if current_user.role == 'admin':
        flash('Tài khoản Admin không thực hiện chức năng mua hàng!', 'danger')
        return redirect(url_for('index'))
        
    cart = session.get('cart', {})
    p_id_str = str(product_id)
    
    # Nếu sản phẩm đã có trong giỏ, tăng số lượng thêm 1
    if p_id_str in cart:
        cart[p_id_str] += 1
    else:
        cart[p_id_str] = 1
        
    session['cart'] = cart
    flash('Đã thêm sản phẩm vào giỏ hàng!', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
@login_required
def view_cart():
    cart = session.get('cart', {})
    cart_items = []
    total_price = 0
    
    for p_id_str, quantity in cart.items():
        product = Product.query.get(int(p_id_str))
        if product:
            item_total = product.price * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total
            })
            
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/cart/remove/<int:product_id>')
@login_required
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    p_id_str = str(product_id)
    
    if p_id_str in cart:
        del cart[p_id_str]
        session['cart'] = cart
        flash('Đã xóa sản phẩm khỏi giỏ hàng.', 'info')
        
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Giỏ hàng của bạn đang trống!', 'warning')
        return redirect(url_for('index'))
        
    cart_items = []
    total_price = 0
    for p_id_str, quantity in cart.items():
        product = Product.query.get(int(p_id_str))
        if product:
            item_total = product.price * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': item_total
            })
            
    if request.method == 'POST':
        # 1. Tạo bản ghi đơn hàng mới
        new_order = Order(user_id=current_user.id, total_amount=total_price)
        db.session.add(new_order)
        db.session.flush() # Đồng bộ tạm thời để lấy ID của đơn hàng vừa tạo
        
        # 2. Tạo các bản ghi chi tiết đơn hàng
        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price=item['product'].price
            )
            db.session.add(order_item)
            
        db.session.commit()
        
        # 3. Làm sạch giỏ hàng trong session sau khi mua thành công
        session.pop('cart', None)
        flash('Đặt hàng thành công! Đơn hàng của bạn đang được xử lý.', 'success')
        return redirect(url_for('index'))
        
    return render_template('checkout.html', cart_items=cart_items, total_price=total_price)

# Khởi tạo DB tự động tại lần chạy đầu tiên
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)