from flask import Flask, render_template
from pymongo import MongoClient
import datetime
import os
from werkzeug.utils import redirect

from werkzeug.wrappers import request


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
    return render_template('index.html')

# PRODUCT: NAME, PRICE, DESCRIPTION, IMAGE, CREATED_AT

app.route('/product/new', methods=['POST'])
def create_product():
    if request.method == 'POST':
        product = {
            'name': request.form.get('name'),
            'price': request.form.get('price'),
            'description': request.form.get('description'),
            'image_url': request.form.get('image_url'),
            'created_at': datetime.now(),
        }
        products.insert_one(product)
        product = products.find_one({'created_at', product['created_at']})
        return redirect(f'/product/{product._id}')
    else:
        return render_template('new_product.html', collections=collections.find())

app.route('/product/<_id>', methods=['GET'])
def get_product(_id):
    if request.method == 'GET':
        product = products.find_one({'_id', _id})
        return render_template('product.html', product)

app.route('/shop/')
def get_all_products():
    return render_template('products.html', products=products.find())

# USER: FIRST, LAST, ADDRESS_LINE_1, ADDRESS_LINE_2, CITY, ZIPCODE, STATE, COUNTRY

