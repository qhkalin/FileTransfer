import os
import base64
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

def generate_key():
    """Generate a secure 64-byte key"""
    return secrets.token_bytes(64)

def pad_data(data):
    """Pad data to be a multiple of block size"""
    padder = padding.PKCS7(128).padder()
    return padder.update(data) + padder.finalize()

def unpad_data(padded_data):
    """Remove padding from data"""
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded_data) + unpadder.finalize()

def encrypt_file(file_data, key):
    """
    Encrypt file data using AES-256 with the provided key
    :param file_data: bytes to be encrypted
    :param key: 64-byte key (we'll use first 32 bytes for AES-256)
    :return: bytes containing IV + encrypted data
    """
    # Use first 32 bytes for AES-256
    aes_key = key[:32]
    # Generate a random IV
    iv = os.urandom(16)
    
    # Create an encryptor
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Pad the data to be a multiple of block size
    padded_data = pad_data(file_data)
    
    # Encrypt the data
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    # Return IV + encrypted data
    return iv + encrypted_data

def decrypt_file(encrypted_data, key):
    """
    Decrypt file data using AES-256 with the provided key
    :param encrypted_data: bytes containing IV + encrypted data
    :param key: 64-byte key (first 32 bytes for AES-256)
    :return: decrypted bytes
    """
    # Use first 32 bytes for AES-256
    aes_key = key[:32]
    
    # Extract IV from the beginning of encrypted data
    iv = encrypted_data[:16]
    encrypted_data = encrypted_data[16:]
    
    # Create a decryptor
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    
    # Decrypt the data
    padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    
    # Unpad the data
    return unpad_data(padded_data)

def get_file_icon(file_type):
    """Return appropriate Font Awesome icon class based on file type"""
    file_type = file_type.lower() if file_type else ''
    
    if file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp']:
        return 'fa-file-image'
    elif file_type in ['mp4', 'mov', 'avi', 'wmv', 'flv', 'webm']:
        return 'fa-file-video'
    elif file_type in ['mp3', 'wav', 'ogg', 'm4a', 'flac']:
        return 'fa-file-audio'
    elif file_type in ['doc', 'docx']:
        return 'fa-file-word'
    elif file_type in ['xls', 'xlsx']:
        return 'fa-file-excel'
    elif file_type in ['ppt', 'pptx']:
        return 'fa-file-powerpoint'
    elif file_type == 'pdf':
        return 'fa-file-pdf'
    elif file_type in ['zip', 'rar', '7z', 'tar', 'gz']:
        return 'fa-file-archive'
    elif file_type in ['html', 'htm', 'xml', 'css', 'js', 'py', 'php', 'java', 'c', 'cpp', 'h']:
        return 'fa-file-code'
    elif file_type in ['txt', 'md', 'rtf']:
        return 'fa-file-alt'
    else:
        return 'fa-file'

def format_file_size(size_bytes):
    """Format file size from bytes to human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < (1024 * 1024):
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < (1024 * 1024 * 1024):
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
