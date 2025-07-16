import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Tuple
import secrets

from app.core.config import settings


class SecurityManager:
    def __init__(self):
        self.encryption_key = settings.encryption_key.encode()
    
    def generate_salt(self) -> str:
        """Generate a random salt for password encryption"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    
    def derive_key(self, salt: str) -> bytes:
        """Derive encryption key from master key and salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.encryption_key))
    
    def encrypt_password(self, password: str) -> Tuple[str, str]:
        """Encrypt password and return encrypted password with salt"""
        salt = self.generate_salt()
        key = self.derive_key(salt)
        
        fernet = Fernet(key)
        encrypted_password = fernet.encrypt(password.encode())
        
        return base64.urlsafe_b64encode(encrypted_password).decode(), salt
    
    def decrypt_password(self, encrypted_password: str, salt: str) -> str:
        """Decrypt password using salt"""
        key = self.derive_key(salt)
        fernet = Fernet(key)
        
        encrypted_data = base64.urlsafe_b64decode(encrypted_password.encode())
        decrypted_password = fernet.decrypt(encrypted_data)
        
        return decrypted_password.decode()
    
    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        return secrets.token_urlsafe(32)
    
    def verify_api_key(self, provided_key: str) -> bool:
        """Verify API key"""
        return provided_key == settings.api_key


security_manager = SecurityManager()
