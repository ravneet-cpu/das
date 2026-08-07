#!/usr/bin/env python3
"""
TOTP (Time-based One-Time Password) service for 2FA with QR codes
Compatible with Google Authenticator, Microsoft Authenticator, etc.
"""

import pyotp
import qrcode
import io
import base64
from urllib.parse import quote


class TOTPService:
    def __init__(self, issuer_name="Photo Validator"):
        self.issuer_name = issuer_name
    
    def generate_secret(self):
        """Generate a new TOTP secret for a user"""
        return pyotp.random_base32()
    
    def generate_qr_code(self, secret, username, account_name=None):
        """
        Generate QR code for TOTP setup
        
        Args:
            secret: The TOTP secret
            username: User's username
            account_name: Optional account name (defaults to username)
        
        Returns:
            Base64 encoded PNG image of QR code
        """
        if not account_name:
            account_name = username
            
        # Create TOTP URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=account_name,
            issuer_name=self.issuer_name
        )
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_data = buffer.getvalue()
        buffer.close()
        
        return base64.b64encode(img_data).decode()
    
    def verify_token(self, secret, token):
        """
        Verify a TOTP token
        
        Args:
            secret: The user's TOTP secret
            token: The 6-digit code from authenticator app
            
        Returns:
            bool: True if token is valid
        """
        if not secret or not token:
            return False
            
        try:
            totp = pyotp.TOTP(secret)
            # Allow for clock drift (±1 window = ±30 seconds)
            return totp.verify(token, valid_window=1)
        except Exception:
            return False
    
    def get_backup_codes(self, count=10):
        """
        Generate backup codes for emergency access
        
        Args:
            count: Number of backup codes to generate
            
        Returns:
            List of backup codes
        """
        import secrets
        import string
        
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) 
                          for _ in range(8))
            # Format as XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        
        return codes
    
    def get_current_token(self, secret):
        """
        Get current TOTP token (for testing)
        
        Args:
            secret: The TOTP secret
            
        Returns:
            Current 6-digit token
        """
        totp = pyotp.TOTP(secret)
        return totp.now()


# Singleton instance
totp_service = TOTPService()