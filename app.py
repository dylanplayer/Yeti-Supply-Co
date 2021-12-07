from flask import Flask, render_template, request, redirect, send_from_directory, session, flash
from pymongo import MongoClient, collection
from datetime import datetime
from bson import ObjectId, json_util
import os
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET')
host = os.environ.get('MONGODB_URI')
salt = os.environ.get('SECRET')
client = MongoClient(host=host)
db = client.get_database('YETI-SUPPLY-CO')
products = db.products
collections = db.collections


@app.route('/')
def index():
    return render_template('index.html', collections=collections.find(), product=products.find_one(), cart=json_util.loads(session['cart']) if session.get('cart') else None, subtotal=cart_subtotal() if session['cart'] else 0)

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
        return render_template('new_product.html', collections=collections.find(), cart=json_util.loads(session['cart']) if session.get('cart') else None, subtotal=cart_subtotal() if session['cart'] else 0)

@app.route('/product/<_id>/', methods=['GET'], defaults={'show': False})
@app.route('/product/<_id>/show', methods=['GET'], defaults={'show': True})
def get_product(_id, show):
    if request.method == 'GET':
        product = products.find_one({'_id': ObjectId(_id)})
        return render_template('product.html', collections=collections.find(), product=product, cart=json_util.loads(session['cart']) if session.get('cart') else None, show_cart=show, subtotal=cart_subtotal() if session['cart'] else 0)

@app.route('/shop')
def get_all_products():
    return render_template('shop.html', collections=collections.find(), products=products.find(), cart=json_util.loads(session['cart']) if session.get('cart') else None, subtotal=cart_subtotal() if session['cart'] else 0), 200

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
        return render_template('new_collection.html', collections=collections.find(), cart=json_util.loads(session['cart']) if session.get('cart') else None, subtotal=cart_subtotal() if session['cart'] else 0)

@app.route('/collection/<_id>', methods=['GET'])
def get_collection(_id):
    if request.method == 'GET':
        collection = collections.find_one({'_id': ObjectId(_id)})
        products_list = []
        for _id in collection['products']:
            products_list.append(products.find_one({'_id': ObjectId(_id)}))
        return render_template('collection.html', collections=collections.find(), collection=collection, products=products_list, cart=json_util.loads(session['cart']) if session.get('cart') else None, subtotal=cart_subtotal() if session['cart'] else 0)

# Order
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

# Error Handler
@app.errorhandler(Exception)
def handle_exception(error):
    if isinstance(error, HTTPException):
        flash(f'{error} You have been redirected to the home page.', 'warning')
        return redirect('/')

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


# USER: FIRST, LAST, ADDRESS_LINE_1, ADDRESS_LINE_2, CITY, ZIPCODE, STATE, COUNTRY

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000 ,debug=False)