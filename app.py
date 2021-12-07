from flask import Flask, render_template, request, redirect, send_from_directory, session, flash
from pymongo import MongoClient, collection
from datetime import datetime
from bson import ObjectId, json_util
import os
import bcrypt
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET')
host = os.environ.get('MONGODB_URI')
salt = os.environ.get('SECRET')
client = MongoClient(host=host)
db = client.get_database('YETI-SUPPLY-CO')
products = db.products
collections = db.collections
users = db.users
orders = db.orders

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', collections=collections.find(), product=products.find_one(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),'favicon.ico')

# Product
@app.route('/product/new', methods=['POST', 'GET'])
def create_product():
    if request.method == 'POST':
        product = {
            'name': request.form.get('name'),
            'price': request.form.get('price'),
            'description': request.form.get('description'),
            'image_url': request.form.get('image_url'),
            'brand': request.form.get('brand'),
            'created_at': datetime.now(),
        }
        product_id = str(products.insert(product))
        collections.update_one(
            {'_id': ObjectId(request.form.get('collection'))},
            {'$push': {'products': product_id}}
        )
        return redirect(f'/product/{ product_id }')
    else:
        return render_template('new_product.html', collections=collections.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0)

@app.route('/product/<_id>/', methods=['GET'], defaults={'show': False})
@app.route('/product/<_id>/show', methods=['GET'], defaults={'show': True})
def get_product(_id, show):
    if request.method == 'GET':
        product = products.find_one({'_id': ObjectId(_id)})
        return render_template('product.html', collections=collections.find(), product=product, cart=json_util.loads(session['cart']) if session.get('cart') else None, show_cart=show, subtotal=cart_subtotal() if session.get('cart') else 0)

@app.route('/shop')
def get_all_products():
    return render_template('shop.html', collections=collections.find(), products=products.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0)

# Collection
@app.route('/collection/new', methods=['POST', 'GET'])
def create_collection():
    if request.method == 'POST':
        collection = {
            'name': request.form.get('name'),
            'products': [],
            'created_at': datetime.now(),
        }
        collection_id = str(collections.insert(collection))
        return redirect(f'/collection/{ collection_id }')
    else:
        return render_template('new_collection.html', collections=collections.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0)

@app.route('/collection/<_id>', methods=['GET'])
def get_collection(_id):
    if request.method == 'GET':
        collection = collections.find_one({'_id': ObjectId(_id)})
        products_list = []
        for _id in collection['products']:
            products_list.append(products.find_one({'_id': ObjectId(_id)}))
        return render_template('collection.html', collections=collections.find(), collection=collection, products=products_list, cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0)

# Order
@app.route('/order/<id>', methods=['GET'])
def get_order(id):
    order = orders.find_one({'_id': ObjectId(id)})
    if order:
        order['total'] = 0
        for item in order['products']:
            order['total'] += float(item['price']) * int(item['qty'])
        return render_template('order.html', order=order, collections=collections.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0)
    else:
        flash('Unable to find order', 'danger')
        return redirect('/account/')

@app.route('/cart', methods=['POST'])
def update_cart():
    if request.method == 'POST':
        product_id = ObjectId(request.form.get('product_id'))
        product = products.find_one({'_id': product_id})
        if 'cart' not in session:
            session['cart'] = json_util.dumps([])
        cart = json_util.loads(session['cart'])
        product_index = is_in_cart(cart, product)
        if product_index != None:
            product = cart[product_index]
            product['qty'] += 1
            cart[product_index] = product
        else:
            product['qty'] = 1
            cart.append(product)
        session['cart'] = json_util.dumps(cart)
        return redirect(f'/product/{product_id}/show')

@app.route('/cart/remove', methods=['POST'])
def remove_cart_item():
    if request.method == 'POST':
        product_id = ObjectId(request.form.get('item_id'))
        product = products.find_one({'_id': product_id})
        cart = json_util.loads(session['cart'])
        product_index = is_in_cart(cart, product)
        cart.pop(product_index)
        session['cart'] = json_util.dumps(cart)
        return redirect(f'/product/{product_id}/show')

def is_in_cart(cart, new_product):
    index = 0
    for product in cart:
        if product['_id'] == new_product['_id']:
            return index
        index += 1
    return None

def cart_subtotal():
    cart = json_util.loads(session['cart'])
    subtotal = 0
    for item in cart:
        subtotal += float(item['price']) * int(item['qty'])
    return subtotal

@app.route('/checkout/', methods=['POST'])
def checkout():
    if request.method == 'POST':
        if session.get('email') and session.get('password'):
            email = session['email']
            password = session['password']
            user = users.find_one({"$and": [{'email': email}, {'password': password}]})
            if user:
                if 'cart' in session:
                    cart = json_util.loads(session['cart'])
                    if len(cart) > 0:
                        order = {
                            'number': orders.count() + 1,
                            'user_id': user['_id'],
                            'products': [],
                            'created_at': datetime.now(),
                        }
                        for item in cart:
                            order['products'].append(item)
                        order_id = orders.insert_one(order)
                        users.update_one(
                            {
                                '_id': ObjectId(user['_id'])
                            },
                            {
                                '$push': {
                                    'orders': order_id.inserted_id
                                }
                            }
                        )
                        session['cart'] = json_util.dumps([])
                        return redirect(f'/order/{order_id.inserted_id}')
                    else:
                        flash('Cart is empty', 'danger')
                        return redirect('/')
                else:
                    flash('Cart does not exist', 'danger')
                    return redirect('/')
            else:
                flash('You must login first', 'danger')
                return redirect('/login/')
        else:
            flash('You must login first', 'danger')
            return redirect('/login/')

# User
@app.route('/login/', methods=['GET','POST'])
def login():
    if (request.method == 'POST'):
        email = request.form.get('email')
        password = bcrypt.hashpw(request.form.get('password').encode('UTF-8'), salt.encode('UTF-8'))
        user = users.find_one({"$and": [{'email': email}, {'password': password}]})
        if user:
            session['email'] = user['email']
            session['password'] = user['password']
            return redirect('/account')
        else:
            flash('Incorrect username or password', 'danger')
            return render_template('login.html', collections=collections.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0)
    else:
        if session.get('email') and session.get('password'):
            email = session['email']
            password = session['password']
            user = users.find_one({"$and": [{'email': email}, {'password': password}]})
            if user:
                return redirect('/account')
            else:
                return render_template('login.html', collections=collections.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0 )
        else:
            return render_template('login.html', collections=collections.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0 )

@app.route('/register/', methods=['GET','POST'])
def register():
    if (request.method == 'POST'):
        user = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'email': request.form.get('email'),
            'password': bcrypt.hashpw(request.form.get('password').encode('UTF-8'), salt.encode('UTF-8')),
            'orders': [],
            'created_at': datetime.now(),
        }
        users.insert_one(user)
        session['email'] = user['email']
        session['password'] = user['password']
        return redirect('/account/')
    else:
        if session.get('email') and session.get('password'):
            email = session['email']
            password = session['password']
            user = users.find_one({"$and": [{'email': email}, {'password': password}]})
            if user:
                return redirect('/account')
            else:
                return render_template('register.html', collections=collections.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0 )
        else:
            return render_template('register.html', collections=collections.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0 )

@app.route('/account/')
def dashboard():
    if session.get('email') and session.get('password'):
        email = session['email']
        password = session['password']
        user = users.find_one({"$and": [{'email': email}, {'password': password}]})
        if user:
            orders_list = []
            for order in user['orders']:
                orders_list.append(orders.find_one({'_id': ObjectId(order)}))
            for order in orders_list:
                order['total'] = 0
                for item in order['products']:
                    order['total'] += float(item['price']) * int(item['qty'])
            return render_template('account.html', collections=collections.find(), cart = json_util.loads(session['cart']) if session.get('cart') else None, subtotal = cart_subtotal() if session.get('cart') else 0, orders=orders_list)
        else:
            flash('You must login first')
            return redirect('/login')
    else:
        flash('You must login first')
        return redirect('/login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Error Handler
@app.errorhandler(Exception)
def handle_exception(error):
    if isinstance(error, HTTPException):
        flash(f'{error} You have been redirected to the home page.', 'warning')
        return redirect('/')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000 ,debug=True)