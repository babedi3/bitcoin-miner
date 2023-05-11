import time
import hashlib
import struct
from bitcoinrpc.authproxy import AuthServiceProxy

# Replace with your Bitcoin Core RPC credentials
RPC_USER = "your_rpc_username"
RPC_PASSWORD = "your_rpc_password"
RPC_HOST = "127.0.0.1"
RPC_PORT = 8332

def connect_to_bitcoin():
    return AuthServiceProxy(f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}")

def get_mempool_transactions(bitcoin):
    mempool = bitcoin.getrawmempool()
    transactions = []

    for txid in mempool:
        raw_tx = bitcoin.getrawtransaction(txid)
        tx = bitcoin.decoderawtransaction(raw_tx)
        fee = sum(input["value"] for input in tx["vin"]) - sum(output["value"] for output in tx["vout"])
        transactions.append({"txid": txid, "fee": fee, "raw_tx": raw_tx})

    return sorted(transactions, key=lambda x: x["fee"], reverse=True)

def create_block_template(bitcoin, coinbase_addr, max_transactions=500):
    # Get the best block and its height
    best_block_hash = bitcoin.getbestblockhash()
    best_block = bitcoin.getblock(best_block_hash)
    height = best_block["height"] + 1

    # Create the coinbase transaction
    coinbase = {
        "version": 1,
        "locktime": 0,
        "vin": [{"coinbase": "00", "sequence": 0xffffffff}],
        "vout": [{"value": 50, "scriptPubKey": {"addresses": [coinbase_addr]}}],
    }

    # Get mempool transactions and add them to the block
    transactions = get_mempool_transactions(bitcoin)[:max_transactions]
    block_transactions = [{"txid": tx["txid"], "data": tx["raw_tx"]} for tx in transactions]
    block_transactions.insert(0, coinbase)

    # Create the block template
    template = {
        "version": best_block["version"],
        "previousblockhash": best_block_hash,
        "timestamp": int(time.time()),
        "bits": best_block["bits"],
        "height": height,
        "transactions": block_transactions,
    }

    return template

def mine_block(template, target):
    version = struct.pack("<I", template["version"])
    prev_block = bytes.fromhex(template["previousblockhash"])[::-1]
 # Merkle tree calculation
    tx_hashes = [bytes.fromhex(tx["data"])[:32] for tx in template["transactions"]]
    merkle_root = calculate_merkle_root(tx_hashes)

    timestamp = struct.pack("<I", template["timestamp"])
    bits = struct.pack("<I", int(template["bits"], 16))
    nonce = 0

    while True:
        header = version + prev_block + merkle_root + timestamp + bits + struct.pack("<I", nonce)
        hash = hashlib.sha256(hashlib.sha256(header).digest()).digest()[::-1]

        if int.from_bytes(hash, byteorder="big") < target:
            print(f"Block found! Hash: {hash.hex()}, Nonce: {nonce}")
            return nonce
        else:
            nonce += 1
            if nonce % 100000 == 0:
                print(f"Hashes tried: {nonce}, Current hash: {hash.hex()}")

def submit_block(bitcoin, block_template, nonce):
    block_data = ""
    for tx in block_template["transactions"]:
        block_data += tx["data"]

    block = (
        struct.pack("<I", block_template["version"]) +
        bytes.fromhex(block_template["previousblockhash"])[::-1] +
        bytes.fromhex(block_template["merkleroot"])[::-1] +
        struct.pack("<I", block_template["timestamp"]) +
        struct.pack("<I", int(block_template["bits"], 16)) +
        struct.pack("<I", nonce) +
        block_data
    )

    return bitcoin.submitblock(block.hex())

def double_sha256(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def calculate_merkle_root(tx_hashes):
    if len(tx_hashes) == 1:
        return tx_hashes[0]

    new_hashes = []
    for i in range(0, len(tx_hashes) - 1, 2):
        new_hash = double_sha256(tx_hashes[i] + tx_hashes[i + 1])
        new_hashes.append(new_hash)

    if len(tx_hashes) % 2 == 1:
        new_hashes.append(double_sha256(tx_hashes[-1] * 2))

    return calculate_merkle_root(new_hashes)

def main():
    bitcoin = connect_to_bitcoin()
    coinbase_address = "your_bitcoin_address"

    while True:
        print("Creating block template...")
        block_template = create_block_template(bitcoin, coinbase_address)

        target = (1 << (256 - int(block_template["bits"], 16))) - 1
        print(f"Target: {target}")

        print("Mining block...")
        start_time = time.time()
        nonce = mine_block(block_template, target)
        elapsed_time = time.time() - start_time
        print(f"Elapsed time: {elapsed_time:.2f} seconds")

        if nonce is not None:
            print("Submitting block...")
            result = submit_block(bitcoin, block_template, nonce)
            if result is None:
                print("Block successfully submitted!")
            else:
                print(f"Error submitting block: {result}")

if __name__ == "__main__":
    main()

