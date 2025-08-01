import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get encryption key from environment or generate one
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())

# Create Fernet cipher
cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_credentials(data: str) -> str:
    """
    Encrypt sensitive data
    
    Args:
        data (str): Data to encrypt
        
    Returns:
        str: Encrypted data
    """
    if not data:
        return ""
    
    encrypted_data = cipher.encrypt(data.encode())
    return encrypted_data.decode()

def decrypt_credentials(encrypted_data: str) -> str:
    """
    Decrypt sensitive data
    
    Args:
        encrypted_data (str): Encrypted data
        
    Returns:
        str: Decrypted data
    """
    if not encrypted_data:
        return ""
    
    decrypted_data = cipher.decrypt(encrypted_data.encode())
    return decrypted_data.decode()