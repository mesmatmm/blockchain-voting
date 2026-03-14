import hashlib


def hash_pair(a, b):
    return hashlib.sha256((a + b).encode()).hexdigest()


def compute_merkle_root(hashes):
    if not hashes:
        return hashlib.sha256(b"empty").hexdigest()
    hashes = list(hashes)
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [hash_pair(hashes[i], hashes[i + 1]) for i in range(0, len(hashes), 2)]
    return hashes[0]
