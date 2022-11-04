import os
from web3.auto import w3
from eth_account.messages import encode_structured_data
import requests
import time

print(os.environ.get("CHAIN_ID"))

NETWORK = int(os.environ.get("CHAIN_ID"))
AUCTION_URL = os.environ.get("AUCTION_URL")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
CURRENT_ACCOUNT = w3.eth.account.privateKeyToAccount(PRIVATE_KEY)

print("Using address: ", CURRENT_ACCOUNT.address)

DELETE_BID_MSG = "I authorize to delete the bid"

verifying_contract = "0xdd1e9c25115e0d6e531d9f9e6ab7dbbed15158ce"

if NETWORK == 3:
    verifying_contract = "0xdd1e9c25115e0d6e531d9f9e6ab7dbbed15158ce"
elif NETWORK == 5:
    verifying_contract = "0x49a423Bc9F1dEe5A052b1E72a1dbE9de488d4411"


DOMAIN = {
    "chainId": NETWORK,
    "name": 'CrabOTC',
    "verifyingContract": verifying_contract,
    "version": '2',
}

DOMAIN_TYPE = [
    {"name": 'name', "type": 'string'},
    {"name": 'version', "type": 'string'},
    {"name": 'chainId', "type": 'uint256'},
    {"name": 'verifyingContract', "type": 'address'},
]

ORDER_TYPE = [
    {"type": 'uint256', "name": 'bidId'},
    {"type": 'address', "name": 'trader'},
    {"type": 'uint256', "name": 'quantity'},
    {"type": 'uint256', "name": 'price'},
    {"type": 'bool', "name": 'isBuying'},
    {"type": 'uint256', "name": 'expiry'},
    {"type": 'uint256', "name": 'nonce'},
]

MANDATE_TYPE = [
    {"type": 'string', "name": 'message'},
    {"type": 'uint256', "name": 'time'},
]


def get_signature(msg):
    encoded_msg = encode_structured_data(msg)
    signed_message = w3.eth.account.sign_message(
        encoded_msg, private_key=PRIVATE_KEY)
    return signed_message.signature.hex()


def get_latest_auction():
    req = requests.get(AUCTION_URL + 'api/auction/getLatestAuction')

    return req.json()


def get_user_bids(user_addr: str):
    req = requests.get(AUCTION_URL + 'api/auction/getLatestAuction')

    return req.json()


def create_or_edit_bid(bidId: int, trader: str, quantity: str, price: str, isBuying: bool, expiry: int, nonce: int):
    order = {
        "bidId": bidId,
        "trader": trader,
        "quantity": quantity,
        "price": price,
        "isBuying": isBuying,
        "expiry": expiry,
        "nonce": nonce
    }
    msg = {
        "domain": DOMAIN,
        "message": order,
        "primaryType": 'Order',
        "types": {
            "EIP712Domain": DOMAIN_TYPE,
            "Order": ORDER_TYPE,
        },
    }
    signature = get_signature(msg)
    order["quantity"] = str(order["quantity"])
    order["price"] = str(order["price"])
    req = requests.post(AUCTION_URL + 'api/auction/createOrEditBid',
                        json={"order": order, "signature": signature})
    if req.status_code != 200:
        raise Exception(req.json()['message'])

    return f'{order["trader"]}-{order["nonce"]}'


def delete_bid(user_bid: str):
    mandate = {
        "message": DELETE_BID_MSG,
        "time": int(round(time.time() * 1000))
    }
    msg = {
        "domain": DOMAIN,
        "message": mandate,
        "primaryType": 'Mandate',
        "types": {
            "EIP712Domain": DOMAIN_TYPE,
            "Mandate": MANDATE_TYPE,
        },
    }
    signature = get_signature(msg)
    req = requests.delete(AUCTION_URL + 'api/auction/deleteBid',
                          json={"bidId": user_bid, "signature": signature, "mandate": mandate})
    if req.status_code != 200:
        raise Exception(req.json()['message'])


auctionObj = get_latest_auction()


auction = auctionObj['auction']
bidId = auction['currentAuctionId']
quantity = 1000000000000000000  # 1 oSQTH
price = 500000000000000000  # .2 WETH
isBuying = auction['isSelling']  # If auction is selling you are buying

# Auction will be settled in 10m, Just to be safer side we are using 20m
expiry = auction['auctionEnd'] + 20 * 60 * 1000

# some random number that's not used before
nonce = int(round(time.time() * 1000))

print(
    f'Crab v2 is {"selling" if auction["isSelling"] else "buying"} {auction["oSqthAmount"]} oSQTH for {"min" if auction["isSelling"] else "max"} price {auction["price"]} WETH')


user_bid_id = create_or_edit_bid(bidId, CURRENT_ACCOUNT.address,
                                 quantity, price, isBuying, expiry, nonce)

print("Created new bid: ", user_bid_id)

#delete_bid(user_bid_id)