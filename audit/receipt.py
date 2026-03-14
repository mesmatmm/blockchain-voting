import hashlib
import time
import json


def generate_receipt(voter_id, candidate, election_id, vote_hash):
    """Generate a receipt that a voter can use to verify their vote later."""
    ts = time.time()
    receipt_code = hashlib.sha256(
        f"{voter_id}{vote_hash}{ts}".encode()
    ).hexdigest()[:16].upper()

    receipt_data = {
        "vote_hash": vote_hash,
        "election_id": election_id,
        "candidate": candidate,
        "timestamp": ts,
        "receipt_code": receipt_code
    }
    return receipt_data


def format_receipt(receipt_data):
    """Return a human-readable string version of a receipt."""
    lines = [
        "=" * 50,
        "       VOTE RECEIPT",
        "=" * 50,
        f"Election:     {receipt_data.get('election_id', 'N/A')}",
        f"Candidate:    {receipt_data.get('candidate', 'N/A')}",
        f"Receipt Code: {receipt_data.get('receipt_code', 'N/A')}",
        f"Vote Hash:    {receipt_data.get('vote_hash', 'N/A')}",
        f"Timestamp:    {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(receipt_data.get('timestamp', 0)))}",
        "=" * 50,
        "Keep this receipt to verify your vote later."
    ]
    return "\n".join(lines)
