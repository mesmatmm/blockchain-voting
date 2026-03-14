import hashlib
import re


def is_valid_voter_id(voter_id):
    """Basic validation: voter ID must be non-empty and at least 4 characters."""
    if not voter_id or not isinstance(voter_id, str):
        return False, "Voter ID must be a non-empty string."
    voter_id = voter_id.strip()
    if len(voter_id) < 4:
        return False, "Voter ID must be at least 4 characters long."
    return True, None


def hash_voter_id(voter_id):
    """Return the SHA-256 hash of a voter ID for privacy-preserving storage."""
    return hashlib.sha256(voter_id.strip().encode()).hexdigest()


def check_eligibility(voter_id, contract):
    """
    Check whether a voter is eligible to vote in a given contract's election.
    Returns (eligible: bool, reason: str or None).
    """
    valid, reason = is_valid_voter_id(voter_id)
    if not valid:
        return False, reason

    if not contract.is_active():
        return False, "Election is not currently active."

    hashed = hash_voter_id(voter_id)
    if hashed in contract.voted_hashes:
        return False, "Voter has already cast a vote in this election."

    return True, None
