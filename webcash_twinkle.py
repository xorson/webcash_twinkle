#webcash twinkle -- enables sats-for-webcash exchange between 2 parties in a way to minimise trust by breaking down the trade to installements
#uses modified libraries from https://github.com/kanzure/webcash for webcash wallet operations. 
#workflow designed so that Webcash seller settles first, buyer settles second

from walletclient import pay, insert, create_webcash_wallet, save_webcash_wallet, ask_user_for_legal_agreements, get_balance
import binascii
import codecs, grpc, os
from tracemalloc import stop
from timeit import repeat
import time, secrets
from hashlib import sha256
from colorama import Fore


import lightning_pb2 as lnrpc, lightning_pb2_grpc as lightningstub
import router_pb2 as routerrpc, router_pb2_grpc as routerstub

#ASCII art of webcash twinkle
logo="20 20 20 20 20 20 20 20 20 20 20 20 20 20 5f 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 5f 20 20 20 20 20 20 20 5f 20 20 20 20 20 20 20 20 20 20 20 20 5f 20 20 20 20 20 20 20 5f 20 20 20 20 5f 20 20 20 20 20 20 0a 5f 5f 20 20 20 20 20 20 5f 5f 5f 5f 5f 7c 20 7c 5f 5f 20 20 20 5f 5f 5f 20 5f 5f 20 5f 20 5f 5f 5f 7c 20 7c 5f 5f 20 20 20 7c 20 7c 5f 5f 5f 20 20 20 20 20 20 5f 28 5f 29 5f 20 5f 5f 20 7c 20 7c 20 5f 7c 20 7c 20 5f 5f 5f 20 0a 5c 20 5c 20 2f 5c 20 2f 20 2f 20 5f 20 5c 20 27 5f 20 5c 20 2f 20 5f 5f 2f 20 5f 60 20 2f 20 5f 5f 7c 20 27 5f 20 5c 20 20 7c 20 5f 5f 5c 20 5c 20 2f 5c 20 2f 20 2f 20 7c 20 27 5f 20 5c 7c 20 7c 2f 20 2f 20 7c 2f 20 5f 20 5c 0a 20 5c 20 56 20 20 56 20 2f 20 20 5f 5f 2f 20 7c 5f 29 20 7c 20 28 5f 7c 20 28 5f 7c 20 5c 5f 5f 20 5c 20 7c 20 7c 20 7c 20 7c 20 7c 5f 20 5c 20 56 20 20 56 20 2f 7c 20 7c 20 7c 20 7c 20 7c 20 20 20 3c 7c 20 7c 20 20 5f 5f 2f 0a 20 20 5c 5f 2f 5c 5f 2f 20 5c 5f 5f 5f 7c 5f 2e 5f 5f 2f 20 5c 5f 5f 5f 5c 5f 5f 2c 5f 7c 5f 5f 5f 2f 5f 7c 20 7c 5f 7c 20 20 5c 5f 5f 7c 20 5c 5f 2f 5c 5f 2f 20 7c 5f 7c 5f 7c 20 7c 5f 7c 5f 7c 5c 5f 5c 5f 7c 5c 5f 5f 5f 7c 0a 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20 20"


def metadata_callback(context, callback):
    # for more info see grpc docs
    callback([('macaroon', macaroon)], None)


#setup creds for ln grpc
macaroon = codecs.encode(open(os.path.expanduser("~/.lnd/data/chain/bitcoin/mainnet/admin.macaroon"), 'rb').read(), 'hex')
os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
cert = open(os.path.expanduser("~")+'/.lnd/tls.cert', 'rb').read()
ssl_creds = grpc.ssl_channel_credentials(cert)
auth_creds = grpc.metadata_call_credentials(metadata_callback)
combined_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)

channel = grpc.secure_channel('localhost:10009',combined_creds)
lnstub = lightningstub.LightningStub(channel)
rostub = routerstub.RouterStub(channel)

msg_type=41414 #arbitrary value to distinguish other msgs 
WALLET_NAME = "default_wallet.webcash" 


def send_msg(msg): #
    request = lnrpc.SendCustomMessageRequest(
        peer=send_pubkey,
        type=msg_type,
        data=msg.encode(),
    )
    lnstub.SendCustomMessage(request)


def rcv_msg(): #ln msg sender
    request = lnrpc.SubscribeCustomMessagesRequest()
    for response in lnstub.SubscribeCustomMessages(request):
        if (response.type == int("41414")):
            return response.data.decode('UTF-8')
            break

def confirm_trade(trade_msg): #checks both parties have same understanding of trade parameters
    rcv_side,rcv_webcash,rcv_sats,rcv_txs = trade_msg.split(';',4)

    if (webcash_amount == (int)(rcv_webcash) and sats_amount ==(int) (rcv_sats) and num_txs == (int)(rcv_txs) and (side != rcv_side)):
        print("The other party has confirmed the same transaction parameters")
        return True
    else:
        print("Your trade parameters don't match with the other party\nExiting...")
        return False


def get_trade(): #prompt for trade parameters
    global side, webcash_amount, sats_amount, num_txs
    confirmed = False
    while (not (confirmed)):
        side = input("Are you (s)elling your webcash or (b)uying? (S/B)? --> ").upper()
        if (side == "S"):
            webcash_amount = (int) (input("How much webcash are you selling ? --> "))
            sats_amount =  (int) (input("How many sats are you expecting in return? --> "))
 
        elif (side == "B"):
            webcash_amount = (int) (input("How much webcash are you buying ? --> "))
            sats_amount =  (int) (input("How many sats are you paying in return? -->" ))
        else:
            print("Invalid entry")
            continue

        num_txs = (int) (input("Divide the transaction into how many trades ? --> "))
        if ((webcash_amount % num_txs != 0) and (sats_amount %num_txs !=0)):
            print("Please choose more divisible numbers")
            continue
        
        confirmed=input("Is above correct (Y/N) --> ").upper() == "Y"
    msg=side+";"+str(webcash_amount)+";"+str(sats_amount)+";"+str(num_txs)    
    return msg


def buy_side(): 
    print("\nYou're a buyer")
    global webcash_amount
    global sats_amount
    global num_txs
    sell_chunk = (int) (webcash_amount / num_txs)
    buy_chunk = (int) (sats_amount / num_txs)    
    
    keySendPreimageType = 5482373484 #std for keysend push
    messageType = 34349334
    
    for i in range(num_txs):
        preimage = secrets.token_bytes(32)
        m = sha256()
        m.update(preimage)
        preimage_hash = m.digest()
        dest_custom_records = {
        keySendPreimageType: preimage,
		messageType: "swap sucessful".encode()
        }

        wc_rcv = rcv_msg() #receive webcash
        insert(wc_rcv,"trade") #check webcash validity
        if ((int) (wc_rcv[1:str.find(wc_rcv,":")]) != sell_chunk): #ensure as per agreed amount
            print(Fore.RED, "The other party might be cheating... terminating")
            exit() 
        else: #reciprocate with sats
            request = routerrpc.SendPaymentRequest(dest=send_pubkey,amt=buy_chunk,fee_limit_sat=0, timeout_seconds=5,payment_hash=preimage_hash,dest_custom_records=dest_custom_records)
            print("Sending sats: ",buy_chunk)
            time.sleep(2)
            for response in rostub.SendPaymentV2(request):
                print(".", end='', flush=True)
                if (response.status == 3):
                    print(Fore.RED, "Payment Failed, exiting...")
                    exit()
    return



def sell_side():
    print("\nYou're a seller")
    global webcash_amount
    global sats_amount
    global num_txs
    sell_chunk = (int) (webcash_amount / num_txs)
    buy_chunk = (int) (sats_amount / num_txs)
    
    for i in range(num_txs):
        tmp_cash = pay(sell_chunk,"trade") #generate webcash installement
        send_msg(tmp_cash) #send it over to peer
        time.sleep(2)

        request = lnrpc.InvoiceSubscription()
        print("Receiving sats ") 
        for response in lnstub.SubscribeInvoices(request): #wait for sats payment... this part needs to terminate in case invoice never seen
            print(".",end='', flush=True)
            if (response.value != buy_chunk): #ensure as per agreed installment
                print(Fore.RED, "The other party might be cheating... terminating")
                exit()
            if (response.settled): #pay out next installement if sats received
                print("Received sats: ",response.value)
                break
    return


if __name__ == "__main__":
    # Create a new webcash wallet if one does not already exist.
    if not os.path.exists(WALLET_NAME):
        print(f"Didn't find an existing webcash wallet, making a new one called {WALLET_NAME}")
        webcash_wallet = create_webcash_wallet()
        ask_user_for_legal_agreements(webcash_wallet)
        save_webcash_wallet(webcash_wallet)

print(Fore.LIGHTBLUE_EX, bytearray.fromhex(logo).decode())
print(Fore.LIGHTWHITE_EX, "\nWelcome to webcash twinkle ... Let's begin\n")
print("If you are the webcash seller, please standby until the buyer tells you to proceed\n")

while (True):
    send_pubkey=input("Enter destination PUBKEY --> ")
    try: 
        send_pubkey=bytes.fromhex(send_pubkey)
        break
    except:
        print("Incorrect PUBKEY format")


msg = get_trade()

##This portion needs to be re-written, as currently buyer must start and wait for the seller

if (side == "B"):
    print('\nWaiting on seller, you can tell them to proceed now.\n')
    trade_msg = rcv_msg()
    send_msg(msg)
else:
    send_msg(msg)
    trade_msg = rcv_msg()

if (not (confirm_trade(trade_msg))):
    exit()    


print("\nExecuting the trade. Do not interrupt")
start_wallet_balance = get_balance()
request = lnrpc.ListChannelsRequest(peer=send_pubkey)
response = lnstub.ListChannels(request)
start_chan_balance =  response.channels[0].local_balance

print("Your webcash wallet balance is: ",start_wallet_balance)
print("Your local sats balance is: ",start_chan_balance)

if (side == "S"):
    if (start_wallet_balance < webcash_amount):
        print(Fore.RED, "\nERROR: Not enough webcash to cary out transaction")
        exit()
    sell_side() 
else:
    if (start_chan_balance < sats_amount):
        print(Fore.RED, "\nERROR: Your channel does not have enough local capacity")
        exit()
    else:
        buy_side()

time.sleep(2)
end_wallet_balance = get_balance()
request = lnrpc.ListChannelsRequest(peer=send_pubkey)
response = lnstub.ListChannels(request)
end_chan_balance =  response.channels[0].local_balance

##print out trade results
print(Fore.LIGHTBLUE_EX,'\n\nTransaction successfully completed!')
print("Your initially had webcash ",start_wallet_balance, "and now have ",end_wallet_balance)
print("Your initially had sats ",start_chan_balance, "and now have ",end_chan_balance)
