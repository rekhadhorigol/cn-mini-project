# crypto_config.py
# ================
# Shared AES key for all components (server, client, bridge).
# Fernet = AES-128-CBC + HMAC-SHA256 (authenticated encryption).
# A tampered or forged packet will be rejected by the receiver.

from cryptography.fernet import Fernet

# Pre-shared symmetric key.
# In production this would be exchanged via an RSA handshake.
AES_KEY = b'h2bKFiiFI46Efz1pyWQ8ApzcGvLjGxT7acm6x8RtR4g='

fernet = Fernet(AES_KEY)

def aes_encrypt(plaintext: str) -> bytes:
    """Encrypt a UTF-8 string and return bytes ready to send over UDP."""
    return fernet.encrypt(plaintext.encode("utf-8"))

def aes_decrypt(ciphertext: bytes) -> str:
    """Decrypt UDP bytes back to a UTF-8 string. Raises on tamper."""
    return fernet.decrypt(ciphertext).decode("utf-8")
