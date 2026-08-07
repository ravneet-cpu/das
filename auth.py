"""
Simple authentication module for photo validator
"""

import jwt
import sqlite3
from datetime import datetime, timedelta
import os
import hashlib
import secrets
import random

# Secret key for JWT tokens (in production, use environment variable)
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Database path (persistent storage).  Default to this project's data folder so
# the application runs both locally and in a container; deployments can override
# it with DATABASE_PATH.
DATABASE_PATH = os.environ.get(
    'DATABASE_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'photo_validator.db')
)

#DATABASE_PATH = '/home/projet/photo-validator/data/photo_validator.db'

def init_auth_db():
    """Initialize authentication database"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create users table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'validator',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Create 2FA codes table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS two_fa_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create test user without TOTP configured (for setup testing)
    # DISABLED: Test accounts are no longer needed in production
    # cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('test',))
    # if cursor.fetchone()[0] == 0:
    #     cursor.execute('''
    #         INSERT INTO users (username, password, email, role)
    #         VALUES (?, ?, ?, ?)
    #     ''', ('test', hash_password('test123'), 'frederic@faucouneau.fr', 'admin'))

    # Create default admin user if not exists
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (username, password, email, role) 
            VALUES (?, ?, ?, ?)
        ''', ('admin', hash_password('adminpass'), 'frederic@faucouneau.fr', 'admin'))
    else:
        # Update existing admin email if needed
        cursor.execute('''
            UPDATE users SET email = ? WHERE username = ?
        ''', ('frederic@faucouneau.fr', 'admin'))
    
    # Create default uploader user if not exists
    # DISABLED: Default test accounts are no longer needed in production
    # cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('uploader',))
    # if cursor.fetchone()[0] == 0:
    #     cursor.execute('''
    #         INSERT INTO users (username, password, email, role)
    #         VALUES (?, ?, ?, ?)
    #     ''', ('uploader', hash_password('uploader123'), 'frederic@faucouneau.fr', 'uploader'))
    # else:
    #     # Update existing uploader email if needed
    #     cursor.execute('''
    #         UPDATE users SET email = ? WHERE username = ?
    #     ''', ('frederic@faucouneau.fr', 'uploader'))

    # Create default validator user if not exists
    # DISABLED: Default test accounts are no longer needed in production
    # cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('validator',))
    # if cursor.fetchone()[0] == 0:
    #     cursor.execute('''
    #         INSERT INTO users (username, password, email, role)
    #         VALUES (?, ?, ?, ?)
    #     ''', ('validator', hash_password('validator123'), 'frederic@faucouneau.fr', 'validator'))
    # else:
    #     # Update existing validator email if needed
    #     cursor.execute('''
    #         UPDATE users SET email = ? WHERE username = ?
    #     ''', ('frederic@faucouneau.fr', 'validator'))
    
    conn.commit()
    conn.close()

def generate_2fa_code():
    """Générer un code 2FA à 6 chiffres"""
    return f"{random.randint(100000, 999999):06d}"

def send_2fa_code(user_id, email):
    """Envoyer un code 2FA par email et le stocker en base"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    code = generate_2fa_code()
    expires_at = datetime.now() + timedelta(minutes=10)  # Code valide 10 minutes
    
    print(f"[2FA DEBUG] Generated code for user {user_id}: {code}")
    print(f"[2FA DEBUG] Code expires at: {expires_at}")
    
    # Invalider les anciens codes non utilisés
    cursor.execute('''
        UPDATE two_fa_codes 
        SET used_at = CURRENT_TIMESTAMP 
        WHERE user_id = ? AND used_at IS NULL
    ''', (user_id,))
    
    # Insérer le nouveau code
    cursor.execute('''
        INSERT INTO two_fa_codes (user_id, code, expires_at)
        VALUES (?, ?, ?)
    ''', (user_id, code, expires_at))
    
    conn.commit()
    conn.close()
    
    # Envoyer l'email
    try:
        from email_service import email_service
        
        subject = "OperaGallery Verification Code"
        html_content = f"""
        <html>
        <body>
            <h2>OperaGallery Verification Code</h2>
            <p>Your verification code is:</p>
            <h1 style="color: #2563eb; font-size: 32px; text-align: center; 
                       background: #f3f4f6; padding: 20px; border-radius: 8px;">
                {code}
            </h1>
            <p><strong>This code expires in 10 minutes.</strong></p>
            <p>If you did not request this code, please ignore this email.</p>
            <hr>
            <p style="color: #6b7280; font-size: 12px;">
                OperaGallery Photo Validator - Security System
            </p>
        </body>
        </html>
        """
        
        result = email_service.send_email(
            to=email,
            subject=subject,
            html_content=html_content
        )
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"[2FA] Error sending email: {str(e)}")
        return False

def verify_2fa_code(user_id, submitted_code):
    """Vérifier un code 2FA"""
    print(f"[2FA DEBUG] Verifying code for user {user_id}: '{submitted_code}'")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, code, expires_at FROM two_fa_codes
        WHERE user_id = ? AND used_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
    ''', (user_id,))
    
    result = cursor.fetchone()
    
    if not result:
        print(f"[2FA DEBUG] No unused codes found for user {user_id}")
        conn.close()
        return False
    
    code_id, stored_code, expires_at = result
    print(f"[2FA DEBUG] Found stored code: '{stored_code}', expires at: {expires_at}")
    
    expires_at = datetime.fromisoformat(expires_at)
    
    # Vérifier expiration
    if datetime.now() > expires_at:
        print(f"[2FA DEBUG] Code expired: {datetime.now()} > {expires_at}")
        conn.close()
        return False
    
    # Vérifier le code
    if submitted_code != stored_code:
        print(f"[2FA DEBUG] Code mismatch: '{submitted_code}' != '{stored_code}'")
        conn.close()
        return False
    
    print(f"[2FA DEBUG] Code valid! Marking as used.")
    
    # Marquer le code comme utilisé
    cursor.execute('''
        UPDATE two_fa_codes 
        SET used_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (code_id,))
    
    conn.commit()
    conn.close()
    
    return True

def require_2fa(username):
    """
    2FA rule:
    - admin & cron_scheduler → never 2FA
    - baaki sab → DB ke two_factor_enabled par depend
    """

    if username in ['admin', 'cron_scheduler']:
        return False

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT two_factor_enabled FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()

        # Default behaviour: 2FA ON
        if row is None:
            return True

        return bool(row[0] == 1)

    except Exception as e:
        print(f"[require_2fa ERROR] {e}")
        # Safe default → 2FA ON
        return True


def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(username, password):
    """Verify user credentials"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT password, role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        
        if result and result[0] == hash_password(password):  # Check hashed password
            # Update last login
            cursor.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?', 
                (username,)
            )
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def generate_token(username):
    """Generate JWT token for user"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            user_id, role = result
            
            # Create payload
            payload = {
                'user_id': user_id,
                'username': username,
                'role': role,
                'exp': datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
            }
            
            # Generate token
            token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
            return token
        
        return None
    except Exception as e:
        print(f"Error generating token: {e}")
        return None

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_user_by_token(token):
    """Get user information from token"""
    payload = verify_token(token)
    if payload:
        return {
            'user_id': payload.get('user_id'),
            'username': payload.get('username'),
            'role': payload.get('role')
        }
    return None

# Initialize database when module is imported
init_auth_db()
