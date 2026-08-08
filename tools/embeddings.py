import hashlib, math, re

DIMENSION = 64

def embed(text):
    """Small deterministic local embedding; no cloud model or download required."""
    vector = [0.0] * DIMENSION
    for token in re.findall(r"[a-z0-9_:-]+", str(text).lower()):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:2], "big") % DIMENSION
        vector[index] += -1.0 if digest[2] & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
