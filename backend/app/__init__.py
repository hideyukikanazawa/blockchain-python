from flask import Flask, jsonify, request 
import os
import requests
import random
from backend.config import ROOT_PORT
from backend.blockchain.blockchain import Blockchain
from backend.pubsub import PubSub
from backend.wallet.wallet import Wallet
from backend.wallet.transaction import Transaction
from backend.wallet.transaction_pool import TransactionPool

app = Flask(__name__)
blockchain = Blockchain()
wallet = Wallet(blockchain)
transaction_pool = TransactionPool()
pubsub = PubSub(blockchain, transaction_pool)


@app.route('/')
def default():
    return 'Welcome to the blockchain!'

@app.route('/blockchain')
def route_blockchain(): 
    return jsonify(blockchain.to_json())

@app.route('/blockchain/mine')
def route_blockchain_mine():
    transaction_data = transaction_pool.transaction_data()
    transaction_data.append(Transaction.reward_transaction(wallet).to_json())
    blockchain.add_block(transaction_data)
    block = blockchain.chain[-1]
    
    pubsub.broadcast_block(block)
    transaction_pool.clear_blockchain_transactions(blockchain)
    
    return jsonify(block.to_json())

@app.route('/wallet/transact', methods=['POST'])
def route_wallet_transact():
    transaction_data = request.get_json()
    transaction = transaction_pool.existing_transaction(wallet.address)
    
    if transaction:
        transaction.update(
            wallet, 
            transaction_data['recipient'],
            transaction_data['amount']
        )
    else:
        transaction = Transaction(
            wallet, 
            transaction_data['recipient'],
            transaction_data['amount']
        )

    pubsub.broadcast_transaction(transaction)

    return jsonify(transaction.to_json())


@app.route('/wallet/info', methods=['GET'])
def route_wallet_info():
    return jsonify({'address': wallet.address, 'balance': wallet.balance})



PORT = ROOT_PORT

if os.environ.get('PEER') == 'True':
    PORT = random.randint(5001, 6000)

    result = requests.get(f'http://localhost:{ROOT_PORT}/blockchain')
    result_blockchain = Blockchain.from_json(result.json())
    
    try:
        blockchain.replace_chain(result_blockchain.chain)
        print('\n -- Successfully synchronized the local chain!')
    except Exception as e:
        print(f'\n -- Error synchronizing {e}')


app.config["JSON_SORT_KEYS"] = False
app.run(port=PORT, host="0.0.0.0")


