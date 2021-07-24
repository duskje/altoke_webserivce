from flask import Flask
from flask import jsonify
from flask import request

import firebase_admin
from firebase_admin import firestore
from firebase_admin import auth

default_app = firebase_admin.initialize_app()
database = firestore.client()

app = Flask(__name__)


def get_all_products_from_store(store_name: str):
    product_documents_from_store = database.collection(u'stores').document(store_name).collection(u'products')

    for document in product_documents_from_store.stream():
        document = document.to_dict()
        product_id = document['productRef'].id
        yield product_id


@app.route('/validate_transaction', methods=["POST"])
def validate_transaction():
    id_token = request.json['id_token']
    decoded_token = auth.verify_id_token(id_token)

    user_uid = decoded_token['uid']

    order_stores = request.json['stores']

    orders = []

    for _, order_data in order_stores.items():
        store_name = order_data['storeRef']
        order_products = order_data['products']

        if not order_products:
            return 'Null or empty product field', 400

        order_products = dict(order_products)

        store_products = get_all_products_from_store(store_name)

        for order_product in order_products.keys():
            if order_product not in store_products:
                return f"Product {order_product} is not a product from the store {store_name}", 400

        order_payload = {
            'products': order_products,
            'userRef': user_uid,
            'storeRef': store_name,
        }

        orders.append(order_payload)

    for order_payload in orders:
        result = database.collection('orders').add(order_payload)

        transaction_time = result[0]
        transaction_document = result[1].id

        app.logger.info(
            'A new order %s has been made at %s.',
            transaction_document,
            transaction_time
        )

    return 'All orders have been performed succesfully.', 200


@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run()
