"""
Encryption module for secure communication
"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import os


class Encryptor:
    """Handles encryption and decryption of data"""
    
    def __init__(self, password=None):
        """
        Initialize encryptor
        
        Args:
            password: Password for encryption (if None, generates random key)
        """
        if password:
            self.key = self._derive_key(password)
        else:
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password):
        """
        Derive encryption key from password
        
        Args:
            password: Password string
            
        Returns:
            bytes: Derived key
        """
        # Use a fixed salt for simplicity (in production, use random salt and share it)
        salt = b'screenhacker_salt_v1'
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data):
        """
        Encrypt data
        
        Args:
            data: Bytes to encrypt
            
        Returns:
            bytes: Encrypted data
        """
        return self.cipher.encrypt(data)
    
    def decrypt(self, encrypted_data):
        """
        Decrypt data
        
        Args:
            encrypted_data: Encrypted bytes
            
        Returns:
            bytes: Decrypted data
        """
        return self.cipher.decrypt(encrypted_data)
    
    def get_key(self):
        """Get the encryption key"""
        return self.key
    
    def set_key(self, key):
        """
        Set a new encryption key
        
        Args:
            key: Encryption key bytes
        """
        self.key = key
        self.cipher = Fernet(key)


if __name__ == "__main__":
    # Test encryption
    encryptor = Encryptor(password="test_password")
    
    # Test data
    original = b"Hello, this is a secret message!"
    print(f"Original: {original}")
    
    # Encrypt
    encrypted = encryptor.encrypt(original)
    print(f"Encrypted: {encrypted}")
    
    # Decrypt
    decrypted = encryptor.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")
    
    assert original == decrypted
    print("Encryption test passed!")
