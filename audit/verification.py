def verify_vote(blockchain, vote_hash):
    """Find a vote_hash in the blockchain. Returns block info dict."""
    for block in blockchain.chain:
        for tx in block.transactions:
            if tx.vote_hash == vote_hash:
                return {
                    "found": True,
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "candidate": tx.candidate,
                    "election_id": tx.election_id,
                    "timestamp": tx.timestamp
                }
    return {"found": False}


def verify_chain_integrity(blockchain):
    """
    Perform a detailed integrity check of the entire chain.
    Returns a dict with 'valid' bool and 'errors' list.
    """
    errors = []

    if not blockchain.chain:
        return {"valid": False, "errors": ["Chain is empty."]}

    # Check genesis block
    genesis = blockchain.chain[0]
    if genesis.index != 0:
        errors.append("Genesis block has wrong index.")
    if genesis.previous_hash != "0" * 64:
        errors.append("Genesis block has incorrect previous_hash.")

    for i in range(1, len(blockchain.chain)):
        current = blockchain.chain[i]
        previous = blockchain.chain[i - 1]

        recomputed = current.compute_hash()
        if current.hash != recomputed:
            errors.append(f"Block {i}: hash mismatch (stored != computed).")

        if current.previous_hash != previous.hash:
            errors.append(f"Block {i}: previous_hash does not match block {i-1} hash.")

        if not current.hash.startswith("0" * current.difficulty):
            errors.append(f"Block {i}: hash does not satisfy proof-of-work difficulty.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "chain_length": len(blockchain.chain)
    }
