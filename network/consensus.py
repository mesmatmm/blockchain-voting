import requests


def resolve_conflicts(blockchain, peers):
    """
    Longest-chain consensus. Fetches chains from all peers,
    validates them, and replaces the local chain if a longer valid
    chain is found.
    Returns True if the local chain was replaced, False otherwise.
    """
    best_chain = None
    best_length = len(blockchain.chain)

    for peer in peers:
        try:
            r = requests.get(f"{peer}/chain", timeout=3)
            if r.status_code == 200:
                data = r.json()
                length = data.get("length", 0)
                chain_data = data.get("chain", [])
                if length > best_length:
                    from blockchain.blockchain import Blockchain
                    test_bc = Blockchain.from_dict(data)
                    if test_bc.is_valid_chain():
                        best_length = length
                        best_chain = test_bc
        except Exception:
            pass

    if best_chain:
        blockchain.chain = best_chain.chain
        return True
    return False


def broadcast_new_block(block_dict, peers):
    """
    Notify all peers about a newly mined block by triggering a sync.
    Each peer will fetch and compare chains via /sync.
    """
    for peer in peers:
        try:
            requests.post(f"{peer}/sync", json=block_dict, timeout=3)
        except Exception:
            pass


def ping_peer(peer_url):
    """Check if a peer is online. Returns True/False."""
    try:
        r = requests.get(f"{peer_url}/status", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
