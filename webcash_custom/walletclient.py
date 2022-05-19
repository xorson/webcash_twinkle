import json
import decimal
import secrets
import hashlib
import datetime
import struct
import os
import sys

import requests
import click

#from miner import mine
from webcash import (
    SecretWebcash,
    PublicWebcash,
    LEGALESE,
    amount_to_str,
    check_legal_agreements,
    deserialize_amount,
    WEBCASH_ENDPOINT_HEALTH_CHECK,
    WEBCASH_ENDPOINT_REPLACE,
)
# unused?


from utils import lock_wallet

FEE_AMOUNT = 0

WALLET_NAME = "default_wallet.webcash"

CHAIN_CODES = {
    "RECEIVE": 0,
    "PAY": 1,
    "CHANGE": 2,
    "MINING": 3,
}

def convert_secret_hex_to_bytes(secret):
    """
    Convert a string secret to bytes.
    """
    return int(secret, 16).to_bytes(32, byteorder="big")

def generate_new_secret(webcash_wallet=None, chain_code="RECEIVE", walletdepth=None):
    """
    Derive a new secret using the deterministic wallet's master secret.
    """
    if webcash_wallet:
        walletdepth_param = walletdepth
        if walletdepth == None:
            walletdepth = webcash_wallet["walletdepths"][chain_code]
        else:
            walletdepth = walletdepth

        master_secret = webcash_wallet["master_secret"]
        master_secret_bytes = convert_secret_hex_to_bytes(master_secret)

        tag = hashlib.sha256(b"webcashwalletv1").digest()
        new_secret = hashlib.sha256(tag + tag)
        new_secret.update(master_secret_bytes)
        new_secret.update(struct.pack(">Q", CHAIN_CODES[chain_code.upper()])) # big-endian
        new_secret.update(struct.pack(">Q", walletdepth))
        new_secret = new_secret.hexdigest()

        # Record the change in walletdepth, but don't record the new secret
        # because (1) it can be re-constructed even if it is lost, and (2) the
        # assumption is that other code elsewhere will do something with the
        # new secret.
        if walletdepth_param == None:
            # Only update the walletdepth if the walletdepth was not provided.
            # This allows for the recovery function to work correctly.
            webcash_wallet["walletdepths"][chain_code] = (walletdepth + 1)

        save_webcash_wallet(webcash_wallet)
    else:
        raise NotImplementedError
    return new_secret

def generate_new_master_secret():
    """
    Generate a new random master secret for the deterministic wallet.
    """
    return secrets.token_hex(32)

def generate_initial_walletdepths():
    """
    Setup the walletdepths object all zeroed out for each of the chaincodes.
    """
    return {key.upper(): 0 for key in CHAIN_CODES.keys()}

# TODO: decryption
def load_webcash_wallet(filename=WALLET_NAME):
    webcash_wallet = json.loads(open(filename, "r").read())

    if "unconfirmed" not in webcash_wallet:
        webcash_wallet["unconfirmed"] = []

    if "walletdepths" not in webcash_wallet:
        webcash_wallet["walletdepths"] = generate_initial_walletdepths()
        save_webcash_wallet(webcash_wallet)

    if "master_secret" not in webcash_wallet:
        print("Generating a new master secret for the wallet (none previously detected)")

        webcash_wallet["master_secret"] = generate_new_master_secret()
        save_webcash_wallet(webcash_wallet)

        print("Be sure to backup your wallet for safekeeping of its master secret.")

    return webcash_wallet

# TODO: encryption
def save_webcash_wallet(webcash_wallet, filename=WALLET_NAME):
    temporary_filename = f"{filename}.{os.getpid()}"
    with open(temporary_filename, "w") as fd:
        fd.write(json.dumps(webcash_wallet))
    os.replace(temporary_filename, filename)
    return True

def create_webcash_wallet():
    print("Generating a new wallet with a new master secret...")
    master_secret = generate_new_master_secret()

    return {
        "version": "1.0",
        "legalese": {disclosure_name: None for disclosure_name in LEGALESE.keys()},
        "log": [],
        "webcash": [],
        "unconfirmed": [],

        # The deterministic wallet uses the master secret to generate new
        # secrets in a recoverable way. As long as the master secret is backed
        # up, it's possible to recover webcash in the event of a loss of the
        # wallet file.
        "master_secret": master_secret,

        # walletdepths has multiple counters to track how many secrets have
        # been generated so that the wallet can generate unique secrets. Each
        # chaincode is used for a different purpose, like RECEIVE, CHANGE, and
        # PAY.
        "walletdepths": generate_initial_walletdepths(),
    }

def get_balance():
    webcash_wallet = load_webcash_wallet()

    count = 0
    amount = 0
    for webcash in webcash_wallet["webcash"]:
        webcash = SecretWebcash.deserialize(webcash)
        amount += webcash.amount
        count += 1

    return amount


def get_info():
    webcash_wallet = load_webcash_wallet()

    count = 0
    amount = 0
    for webcash in webcash_wallet["webcash"]:
        webcash = SecretWebcash.deserialize(webcash)
        amount += webcash.amount
        count += 1

    amount_str = amount_to_str(amount) if amount != 0 else "0"
    print(f"Total amount stored in this wallet (if secure): e{amount_str}")

    walletdepths = webcash_wallet["walletdepths"]
    print(f"walletdepth: {walletdepths}")

    print(f"outputs: {count}")

@click.group()
def cli():
    pass

@cli.command("info")
def info():
    return get_info()

@cli.command("status")
def status():
    return get_info()

    
def yes_or_no(question):
    while "the user failed to choose y or n":
        reply = str(input(question+' (y/n): ')).lower().strip()
        if reply[:1] == 'y':
            return True
        if reply[:1] == 'n':
            return False

def ask_user_for_legal_agreements(webcash_wallet):
    """
    Allow the user to agree to the agreements, disclosures, and
    acknowledgements.
    """
    acks = check_legal_agreements(webcash_wallet)
    if acks:
        print("User has already agreed and acknowledged the disclosures.")
    elif not acks:
        for (disclosure_name, disclosure) in LEGALESE.items():
            print(f"Disclosure \"{disclosure_name}\": {disclosure}")
            print("\n\n")
            answer = yes_or_no(f"Do you agree?")

            if answer == False:
                print(f"Unfortunately, you must acknowledge and agree to all agreements to use webcash.")
                sys.exit(0)
            elif answer == True:
                webcash_wallet["legalese"][disclosure_name] = True
                continue

        print("\n\n\nAll done! You've acknowledged all the disclosures. You may now use webcash.")

        save_webcash_wallet(webcash_wallet)

def webcash_server_request_raw(url, json_data=None):
    method = "post" if json_data is not None else "get"
    response = requests.request(method=method, url=url, json=json_data)
    return response

def webcash_server_request(url, json_data):
    response = webcash_server_request_raw(url, json_data)
    if response.status_code != 200:
        raise Exception(f"Something went wrong on the server: {response.content}")
    json_response = response.json()
    if json_response.get("status", "") != "success":
        raise Exception(f"Something went wrong on the server: {response}")
    return json_response



def insert(webcash, memo=""):
    if type(memo) == list or type(memo) == tuple:
        memo = " ".join(memo)

    webcash_wallet = load_webcash_wallet()

    acks = check_legal_agreements(webcash_wallet)
    if not acks:
        print("User must acknowledge and agree to agreements first.")
        return

    # make sure it's valid webcash
    webcash = SecretWebcash.deserialize(webcash)

    # store it in a new webcash
    new_webcash = SecretWebcash(amount=webcash.amount, secret_value=generate_new_secret(webcash_wallet, chain_code="RECEIVE"))

    replace_request = {
        "webcashes": [str(webcash)],
        "new_webcashes": [str(new_webcash)],
        "legalese": webcash_wallet["legalese"],
    }
    # Save the webcash to the wallet in case there is a network error while
    # attempting to replace it.
    unconfirmed_webcash = [str(webcash), str(new_webcash)]
    webcash_wallet["unconfirmed"].extend(unconfirmed_webcash)
    save_webcash_wallet(webcash_wallet)
    #print("Sending to the server this replacement request: ", replace_request)

    a = webcash_server_request(WEBCASH_ENDPOINT_REPLACE, replace_request)

    # save this one in the wallet
    webcash_wallet["webcash"].append(str(new_webcash))

    # remove "unconfirmed" webcash
    for wc in unconfirmed_webcash:
        webcash_wallet["unconfirmed"].remove(wc)

    # preserve the memo
    webcash_wallet["log"].append({
        "type": "insert",
        "memo": str(memo),
        "amount": amount_to_str(new_webcash.amount),
        "input_webcash": str(webcash),
        "output_webcash": str(new_webcash),
        "timestamp": str(datetime.datetime.now()),
    })

    save_webcash_wallet(webcash_wallet)
    print("Success... Received webcash->",new_webcash.amount)


def pay(amount, memo=""):
    try:
        amount = deserialize_amount(str(amount))
    except decimal.InvalidOperation:
        raise click.ClickException("Invalid decimal format.")
    int(amount) # just to make sure
    amount += FEE_AMOUNT # fee...
    webcash_wallet = load_webcash_wallet()

    acks = check_legal_agreements(webcash_wallet)
    if not acks:
        print("User must acknowledge and agree to all agreements first.")
        return

    # scan for an amount
    use_this_webcash = []
    for webcash in webcash_wallet["webcash"]:
        webcash = SecretWebcash.deserialize(webcash)

        if webcash.amount >= amount:
            use_this_webcash.append(webcash)
            break
    else:
        running_amount = decimal.Decimal(0)
        running_webcash = []
        for webcash in webcash_wallet["webcash"]:
            webcash = SecretWebcash.deserialize(webcash)
            running_webcash.append(webcash)
            running_amount += webcash.amount

            if running_amount >= amount:
                use_this_webcash = running_webcash
                break
        else:
            print("Couldn't find enough webcash in the wallet.")
            sys.exit(0)

    found_amount = sum([ec.amount for ec in use_this_webcash])
    print(f"Sending webcash: {amount_to_str(amount)}")
    if found_amount > (amount + FEE_AMOUNT): # +1 for the fee
        change = found_amount - amount - FEE_AMOUNT

        mychange = SecretWebcash(amount=change, secret_value=generate_new_secret(webcash_wallet, chain_code="CHANGE"))
        payable = SecretWebcash(amount=amount, secret_value=generate_new_secret(webcash_wallet, chain_code="PAY"))

        replace_request = {
            "webcashes": [str(ec) for ec in use_this_webcash],
            "new_webcashes": [str(mychange), str(payable)],
            "legalese": webcash_wallet["legalese"],
        }

        # Save the webcash to the wallet in case there is a network error while
        # attempting to replace it.
        unconfirmed_webcash = [str(mychange), str(payable)]
        webcash_wallet["unconfirmed"].extend(unconfirmed_webcash)
        save_webcash_wallet(webcash_wallet)

        # Attempt replacement
        #print("Sending to the server this replacement request: ", replace_request)
        webcash_server_request(WEBCASH_ENDPOINT_REPLACE, replace_request)

        # remove old webcashes
        for ec in use_this_webcash:
            #new_wallet = [x for x in webcash_wallet["webcash"] if x != str(ec)]
            #webcash_wallet["webcash"] = new_wallet
            webcash_wallet["webcash"].remove(str(ec))

        # remove unconfirmed webcashes
        for wc in unconfirmed_webcash:
            webcash_wallet["unconfirmed"].remove(wc)

        # store change
        webcash_wallet["webcash"].append(str(mychange))

        log_entry = {
            "type": "change",
            "amount": amount_to_str(mychange.amount),
            "webcash": str(mychange),
            "timestamp": str(datetime.datetime.now()),
        }
        webcash_wallet["log"].append(log_entry)

        use_this_webcash = [payable]
    elif found_amount == amount + FEE_AMOUNT:
        payable = SecretWebcash(amount=amount, secret_value=generate_new_secret(webcash_wallet, chain_code="PAY"))

        replace_request = {
            "webcashes": [str(ec) for ec in use_this_webcash],
            "new_webcashes": [str(payable)],
            "legalese": webcash_wallet["legalese"],
        }
        # Save the webcash to the wallet in case there is a network error while
        # attempting to replace it.
        unconfirmed_webcash = [str(payable)]
        webcash_wallet["unconfirmed"].extend(unconfirmed_webcash)
        save_webcash_wallet(webcash_wallet)

        #print("replace_request: ", replace_request)

        #print("Sending to the server this replacement request: ", replace_request)
        webcash_server_request(WEBCASH_ENDPOINT_REPLACE, replace_request)

        # remove unconfirmed webcashes
        for wc in unconfirmed_webcash:
            webcash_wallet["unconfirmed"].remove(wc)

        # remove old webcashes
        for ec in use_this_webcash:
            #new_wallet = [x for x in webcash_wallet["webcash"] if x != str(ec)]
            #webcash_wallet["webcash"] = new_wallet
            webcash_wallet["webcash"].remove(str(ec))

        use_this_webcash = [payable]
    else:
        raise NotImplementedError

    # store a record of this transaction
    webcash_wallet["log"].append({
        "type": "payment",
        "memo": " ".join(memo),
        "amount": amount_to_str(amount),
        "input_webcashes": [str(ec) for ec in use_this_webcash],
        "output_webcash": str(payable),
        "timestamp": str(datetime.datetime.now()),
    })

    save_webcash_wallet(webcash_wallet)
    return(str(use_this_webcash[0]))
    
if __name__ == "__main__":

    # Create a new webcash wallet if one does not already exist.
    if not os.path.exists(WALLET_NAME):
        print(f"Didn't find an existing webcash wallet, making a new one called {WALLET_NAME}")
        webcash_wallet = create_webcash_wallet()
        ask_user_for_legal_agreements(webcash_wallet)
        save_webcash_wallet(webcash_wallet)

    cli()
