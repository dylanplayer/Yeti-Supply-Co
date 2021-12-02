from flask import Flask, render_template, request, redirect
from pymongo import MongoClient, collection
from datetime import datetime
from bson import ObjectId
import os


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
    return render_template('index.html', collections=collections.find(), product=products.find_one())

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
        return render_template('new_product.html', collections=collections.find())

@app.route('/product/<_id>', methods=['GET'])
def get_product(_id):
    if request.method == 'GET':
        product = products.find_one({'_id': ObjectId(_id)})
        return render_template('product.html', collections=collections.find(), product=product)

@app.route('/shop/')
def get_all_products():
    return render_template('products.html', collections=collections.find(), products=products.find())

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
        return render_template('new_collection.html', collections=collections.find())

@app.route('/collection/<_id>', methods=['GET'])
def get_collection(_id):
    if request.method == 'GET':
        collection = collections.find_one({'_id': ObjectId(_id)})
        products_list = []
        for _id in collection['products']:
            products_list.append(products.find_one({'_id': ObjectId(_id)}))
        return render_template('collection.html', collections=collections.find(), collection=collection, products=products_list)

# USER: FIRST, LAST, ADDRESS_LINE_1, ADDRESS_LINE_2, CITY, ZIPCODE, STATE, COUNTRY

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000 ,debug=True)