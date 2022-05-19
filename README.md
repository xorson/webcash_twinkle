# webcash twinkle

<pre><font color="#2A7BDE">__      _____| |__   ___ __ _ ___| |__   | |___      _(_)_ __ | | _| | ___ </font>
<font color="#2A7BDE">\ \ /\ / / _ \ &apos;_ \ / __/ _` / __| &apos;_ \  | __\ \ /\ / / | &apos;_ \| |/ / |/ _ \</font>
<font color="#2A7BDE"> \ V  V /  __/ |_) | (_| (_| \__ \ | | | | |_ \ V  V /| | | | |   &lt;| |  __/</font>
<font color="#2A7BDE">  \_/\_/ \___|_.__/ \___\__,_|___/_| |_|  \__| \_/\_/ |_|_| |_|_|\_\_|\___|</font>
</pre>

Automated sats for webcash micro swap.

Webcash twinkle allows 2 parties to trade sats for webcash by communicating and exchanging over a lightning channel.
The script will ask both parties for the amounts and # of trade lots, and start to automatically swap. 
Sellers need to ensure they have enough wallet balance and buyers need to ensure they have enough local channel capacity to send sats.

The python script uses gRPC for communication with the Lightning Network Daemon.

## Disclaimer
Review the code and use at your sole risk. Webcash <a href="https:///webcash.org/terms">terms of service</a> apply. 


## Installation

1. Ensure you have lnd installed with key-send capability (set in ~/.lnd/lnd.conf).
2. Compile and install the gRPC dependencies (googleapis), lnd lightning.proto,and RPC modules for subservers. Visit the <a href="https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md"> official repository</a> for detailed insllation instructions. 
3. Download the customised webcash library and keep it in your webcash twinkle folder. 

<b>Please note: The official webcash library will not work as its intended to be run from the cli.</b>
The modified webcash library makes small changes to pass status and token secrets back to the twinkle script.


## Usage 

1. The buyer opens a lightning channel with the seller using lncli with the necessary capacity (remember to enable keysend)
2. The webcash seller loads a local webcash wallet
3. Both parties enter the corresponding side's pubkey and their desired trade parameters
4. webcash twinkle will x-check to ensure both parties are 100% in agreement, and then start to piecemeal the transaction.Errors or cheating will cause the script to terminate

## Bugs

At the moment, the buyer needs to run the script first and wait for the prompt to inform the seller to run their script.


## License

This repository and its source code is distributed under the BSD license.
