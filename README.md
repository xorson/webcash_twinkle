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

<b>The webcash seller settles first.</b>

The python script uses gRPC for communication with the Lightning Network Daemon.

## Disclaimer
Review the code and use at your sole risk. Webcash <a href="https:///webcash.org/terms">terms of service</a> apply. 


## Installation

1. Ensure you have lnd installed with key-send capability (set in ~/.lnd/lnd.conf) by adding `accept-keysend=true`.

2. In case you don't have a full bitcoin node backend, you can still run lnd in neutrino mode, which requires minimal diskspace. Set the `--bitcoin.node` flag to `neutrino`, point the `--neutrino.addpeer` flag to `faucet.lightning.community` and grab the fees from https://nodes.lightning.computer/fees/v1/btc-fee-estimates.json using the `--fee-url` flag. 

    For example: <pre>lnd --bitcoin.active --bitcoin.mainnet --bitcoin.node=neutrino --neutrino.addpeer=faucet.lightning.community --feeurl https://nodes.lightning.computer/fees/v1/btc-fee-estimates.json</pre> 

3. Compile and install the gRPC dependencies (googleapis): lnd lightning.proto and RPC modules for subservers. These are 4 files called _lightning_pb2_grpc.py,  lightning_pb2.py, router_pb2_grpc.py,  router_pb2.py._

    These dependencies allow us to use lnd via python, keep them in the same working directory. Visit the <a href="https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md"> official repository</a> for detailed instructions on how to generate them. 

4. Download the customised webcash library and keep it in your webcash twinkle folder. 

<b>Please note: The official webcash library will not work as its intended to be run from the cli.</b>
The modified webcash library makes small changes to pass status and token secrets back to the twinkle script.


## Usage 

1. The buyer opens a lightning channel with the seller using lncli with the necessary capacity (remember to enable keysend)

2. The webcash seller loads a local webcash wallet

3. Both parties enter the corresponding side's pubkey and their desired trade parameters

4. webcash twinkle will cross-check to ensure both parties are 100% in agreement, and then start to piecemeal the transaction. Errors or cheating attempts will cause the script to terminate

It's recommended prior to starting the script to see if you can push 1 sat accross the channel using lncli --keysend. This will help ensure your setup is good and aid any troubleshooting.

## Bugs

Please report any.

## License

This repository and its source code is distributed under the BSD license.
