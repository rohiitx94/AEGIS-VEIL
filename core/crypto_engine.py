"""
Crypto Engine — AES-256-GCM Encryption & Decryption
====================================================
Zero-knowledge architecture: the encryption key (derived from the user's password)
never leaves the client. Even if the server is compromised, data remains unreadable.

Encryption scheme:
    - Key derivation:  PBKDF2-HMAC-SHA256 with 100,000 iterations
    - Cipher:          AES-256-GCM (authenticated encryption)
    - Output format:   [16-byte salt][16-byte nonce][ciphertext][16-byte GCM tag]

Design decisions:
    - GCM over CBC: provides both confidentiality AND integrity (tamper detection)
    - Random salt + nonce per encryption: identical plaintext + password → different ciphertext
    - PBKDF2 with high iteration count: resistant to brute-force/dictionary attacks
"""

import os
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256


# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────
SALT_SIZE = 16          # 128-bit salt
NONCE_SIZE = 16         # 128-bit nonce (GCM supports up to 128-bit)
TAG_SIZE = 16           # 128-bit authentication tag
KEY_SIZE = 32           # 256-bit key (AES-256)
KDF_ITERATIONS = 100_000  # PBKDF2 iteration count


# ──────────────────────────────────────────────
#  Key Derivation
# ──────────────────────────────────────────────
def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit encryption key from a user password using PBKDF2-HMAC-SHA256.

    Args:
        password: The user's plaintext password.
        salt:     A 16-byte random salt (unique per encryption).

    Returns:
        A 32-byte (256-bit) derived key.

    The high iteration count (100k) makes brute-force attacks computationally
    expensive — each password guess requires ~0.1s of CPU time.
    """
    # Encode password to UTF-8 bytes to support any Unicode characters.
    # PyCryptodome's PBKDF2 uses latin-1 internally, which fails on
    # non-Latin chars (Cyrillic, CJK, emoji). Pre-encoding avoids this.
    password_bytes = password.encode("utf-8")
    return PBKDF2(
        password_bytes,
        salt,
        dkLen=KEY_SIZE,
        count=KDF_ITERATIONS,
        hmac_hash_module=SHA256
    )


# ──────────────────────────────────────────────
#  Encryption
# ──────────────────────────────────────────────
def encrypt(data: bytes, password: str) -> bytes:
    """
    Encrypt arbitrary binary data using AES-256-GCM.

    Args:
        data:     The raw bytes to encrypt (e.g., contents of a secret file).
        password: The user's plaintext password.

    Returns:
        Encrypted blob in the format:
            [16-byte salt][16-byte nonce][ciphertext][16-byte tag]

    The salt and nonce are generated randomly for each call, so encrypting
    the same data with the same password produces different output every time.
    """
    if not data:
        raise ValueError("Cannot encrypt empty data.")
    if not password:
        raise ValueError("Password cannot be empty.")

    # Generate random salt and derive key
    salt = os.urandom(SALT_SIZE)
    key = derive_key(password, salt)

    # Create AES-GCM cipher with random nonce
    cipher = AES.new(key, AES.MODE_GCM, nonce=os.urandom(NONCE_SIZE))

    # Encrypt and generate authentication tag
    ciphertext, tag = cipher.encrypt_and_digest(data)

    # Pack: salt + nonce + ciphertext + tag
    return salt + cipher.nonce + ciphertext + tag


# ──────────────────────────────────────────────
#  Decryption
# ──────────────────────────────────────────────
def decrypt(encrypted_data: bytes, password: str) -> bytes:
    """
    Decrypt data that was encrypted with `encrypt()`.

    Args:
        encrypted_data: The full encrypted blob (salt + nonce + ciphertext + tag).
        password:       The user's plaintext password (must match the one used for encryption).

    Returns:
        The original plaintext bytes.

    Raises:
        ValueError: If the encrypted data is too short or malformed.
        Exception:  If the password is wrong or the data has been tampered with
                    (GCM authentication failure).
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    # Minimum size: salt + nonce + at least 1 byte of ciphertext + tag
    min_size = SALT_SIZE + NONCE_SIZE + 1 + TAG_SIZE
    if len(encrypted_data) < min_size:
        raise ValueError(
            f"Encrypted data is too short ({len(encrypted_data)} bytes). "
            f"Minimum expected: {min_size} bytes."
        )

    # Unpack components
    salt = encrypted_data[:SALT_SIZE]
    nonce = encrypted_data[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    tag = encrypted_data[-TAG_SIZE:]
    ciphertext = encrypted_data[SALT_SIZE + NONCE_SIZE:-TAG_SIZE]

    # Derive the same key from password + salt
    key = derive_key(password, salt)

    # Decrypt and verify integrity
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError:
        raise ValueError(
            "Decryption failed. Either the password is incorrect or "
            "the data has been tampered with."
        )

    return plaintext
