from flask import Blueprint, request, jsonify, current_app, send_file
from auth import verify_password, generate_token, verify_token, require_2fa, send_2fa_code, verify_2fa_code
from email_service import email_service
from totp_service import totp_service
from filemaker_service import filemaker_service, extract_artwork_id_from_filename
import sqlite3
import os
import csv
from datetime import datetime, timedelta
import shutil
from werkzeug.utils import secure_filename
from PIL import Image
from image_processor import process_uploaded_image
auth_bp = Blueprint('auth', __name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
FM_PUSH_CSV = os.path.join(DATA_DIR, 'fm_push_log.csv')

# Configuration paths
#PHOTOS_BASE_DIR = '/app/photos' if os.path.exists('/app/photos') else os.path.join(os.path.dirname(os.path.dirname(__file__)), 'photos')
PHOTOS_BASE_DIR = os.environ.get('PHOTOS_ROOT', os.path.join(PROJECT_ROOT, 'photos'))
PENDING_DIR = os.path.join(PHOTOS_BASE_DIR, 'a-valider')
VALIDATED_DIR = os.path.join(PHOTOS_BASE_DIR, 'output')
REJECTED_DIR = os.path.join(PHOTOS_BASE_DIR, 'refuse')
#FM_DIR = '/app/photos'  # FileMaker images directory - Pointe vers /home/projet/pictures/img/FM sur l'hôte
FM_DIR = os.path.join(PHOTOS_BASE_DIR, 'FM')
VIDEO_DIR = os.path.join(PHOTOS_BASE_DIR, 'video')
SCHEDULED_DIR = os.path.join(PHOTOS_BASE_DIR, 'scheduled')  # Photos programmées
ORIGINALS_DIR = os.path.join(PHOTOS_BASE_DIR, "originals")
os.makedirs(ORIGINALS_DIR, exist_ok=True)

# Database path (persistent storage)
DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(DATA_DIR, 'photo_validator.db'))
#DATABASE_PATH = '/home/projet/photo-validator/data/photo_validator.db'
print("PHOTOS_BASE_DIR =", PHOTOS_BASE_DIR)


# File type detection utility
def get_file_type_info(filename):
    """Detect file type and MIME type based on extension"""
    file_ext = os.path.splitext(filename)[1].lower()
    
    # Image formats
    image_extensions = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg', 
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff'
    }
    
    # PDF formats
    pdf_extensions = {
        '.pdf': 'application/pdf'
    }
    
    # Video formats
    video_extensions = {
        '.mp4': 'video/mp4',
        '.avi': 'video/avi', 
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska'
    }
    
    if file_ext in image_extensions:
        return 'image', image_extensions[file_ext], file_ext
    elif file_ext in pdf_extensions:
        return 'pdf', pdf_extensions[file_ext], file_ext
    elif file_ext in video_extensions:
        return 'video', video_extensions[file_ext], file_ext
    else:
        return None, None, file_ext

def get_file_size_limit(file_type):
    """Get maximum file size based on type"""
    limits = {
        'image': 1000 * 1024 * 1024,  # 1GB pour images
        'pdf': 1000 * 1024 * 1024,    # 1GB pour PDFs
        'video': 1000 * 1024 * 1024   # 1GB pour vidéos
    }
    return limits.get(file_type, 1000 * 1024 * 1024)  # 1GB par défaut

def _serve_with_range(file_path, mime_type):
    """Serve a file with HTTP Range request support (required for video playback in browsers)."""
    from flask import Response, request as _req
    file_size = os.path.getsize(file_path)
    range_header = _req.headers.get('Range', None)

    if not range_header:
        # No range requested — stream whole file with Accept-Ranges header
        def generate_full():
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    yield chunk
        resp = Response(generate_full(), 200, mimetype=mime_type, direct_passthrough=True)
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Content-Length'] = str(file_size)
        return resp

    # Parse "bytes=start-end"
    try:
        byte_range = range_header.replace('bytes=', '')
        parts = byte_range.split('-')
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
    except Exception:
        return Response(status=416)  # Range Not Satisfiable

    if start >= file_size or end >= file_size or start > end:
        resp = Response(status=416)
        resp.headers['Content-Range'] = f'bytes */{file_size}'
        return resp

    length = end - start + 1

    def generate_range():
        with open(file_path, 'rb') as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk_size = min(1024 * 1024, remaining)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    resp = Response(generate_range(), 206, mimetype=mime_type, direct_passthrough=True)
    resp.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    resp.headers['Accept-Ranges'] = 'bytes'
    resp.headers['Content-Length'] = str(length)
    return resp

def is_file_supported(filename):
    """Check if file is supported (filters out .eps, .ai, .ps)"""
    file_ext = os.path.splitext(filename)[1].lower()
    blocked_extensions = {'.eps', '.ai', '.ps'}
    return file_ext not in blocked_extensions

# Database initialization
def init_db():
    """Initialize the database with necessary tables"""
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
    
    
    # Create file validations table (extends photos to handle PDFs, videos, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photo_validations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id TEXT NOT NULL,
            photo_filename TEXT,
            file_type TEXT DEFAULT 'image',
            mime_type TEXT,
            file_size INTEGER,
            submitted_by INTEGER,
            validated_by INTEGER,
            status TEXT DEFAULT 'pending',
            classification TEXT,
            reject_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            validated_at TIMESTAMP,
            FOREIGN KEY (submitted_by) REFERENCES users (id),
            FOREIGN KEY (validated_by) REFERENCES users (id)
        )
    ''')
    
    # Migration: add streaming_url column for video HLS streaming
    try:
        cursor.execute("ALTER TABLE photo_validations ADD COLUMN streaming_url TEXT")
    except Exception:
        pass  # Column already exists

    # Create photo_marks table for user-specific photo marking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photo_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            photo_id TEXT NOT NULL,
            photo_filename TEXT,
            note TEXT,
            marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, photo_id)
        )
    ''')
    
    # Create scheduled_uploads table for timed photo releases to FileMaker
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artwork_id TEXT NOT NULL,
            photo_filename TEXT NOT NULL,
            classification TEXT NOT NULL,
            original_path TEXT NOT NULL,
            target_path TEXT NOT NULL,
            scheduled_date DATETIME NOT NULL,
            status TEXT DEFAULT 'scheduled',
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP NULL,
            error_message TEXT NULL,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Create default admin user if not exists
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (username, password, email, role) 
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'adminpass', 'admin@example.com', 'admin'))
    
    conn.commit()
    conn.close()

# Initialize database on import
init_db()

def schedule_photo_upload(conn,artwork_id, photo_filename, classification, original_path, target_path, scheduled_date, created_by):
    """Schedule a photo upload to FileMaker for a future date (Docker-safe)"""
    try:
        os.makedirs(SCHEDULED_DIR, exist_ok=True)

        # ✅ Normalize paths for host execution
        #normalized_original = os.path.abspath(original_path).replace("/app/photos", "/home/projet/pictures/img/FM")
        #normalized_target = os.path.abspath(target_path).replace("/app/photos", "/home/projet/pictures/img/FM")
        normalized_original = os.path.abspath(original_path)
        normalized_target = os.path.abspath(target_path)
        #conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO scheduled_uploads 
            (artwork_id, photo_filename, classification, original_path, target_path, scheduled_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (artwork_id, photo_filename, classification, normalized_original, normalized_target, scheduled_date, created_by))

        schedule_id = cursor.lastrowid
        #conn.commit()
        #conn.close()

        print(f"[SCHEDULER] ✅ Photo scheduled in DB → ID={schedule_id}, user={created_by}")
        print(f"[SCHEDULER] 📁 Stored Paths: original={normalized_original}, target={normalized_target}")
        return schedule_id

    except Exception as e:
        import traceback
        print(f"[SCHEDULER] ❌ Erreur programmation: {e}")
        traceback.print_exc()
        return None



def process_scheduled_uploads():
    """Process scheduled uploads that are ready"""
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        
        now = datetime.now()
        cursor.execute('''
            SELECT id, artwork_id, photo_filename, classification, original_path, target_path
            FROM scheduled_uploads 
            WHERE status = 'scheduled' AND scheduled_date <= ?
            ORDER BY scheduled_date ASC
        ''', (now,))
        
        ready_uploads = cursor.fetchall()
        
        # for upload_id, artwork_id, photo_filename, classification, original_path, target_path in ready_uploads:
        #     try:
        #         success = False
        #         error_message = None
        #         if os.path.exists(original_path):
        #             # Create FM directory if needed
        #             os.makedirs(FM_DIR, exist_ok=True)
                    
        #             # Move file to FileMaker directory
        #             shutil.move(original_path, target_path)
                    
        #             # Mark as completed
        #             cursor.execute('''
        #                 UPDATE scheduled_uploads 
        #                 SET status = 'completed', processed_at = ?
        #                 WHERE id = ?
        #             ''', (now, upload_id))
                    
        #             print(f"[SCHEDULER] Upload traité: {artwork_id} → {target_path}")
                    
        #         else:
        #             # File not found, mark as failed
        #             cursor.execute('''
        #                 UPDATE scheduled_uploads 
        #                 SET status = 'failed', processed_at = ?, error_message = ?
        #                 WHERE id = ?
        #             ''', (now, f"Fichier non trouvé: {original_path}", upload_id))
                    
        #     except Exception as e:
        #         cursor.execute('''
        #             UPDATE scheduled_uploads 
        #             SET status = 'failed', processed_at = ?, error_message = ?
        #             WHERE id = ?
        #         ''', (now, str(e), upload_id))
        #         print(f"[SCHEDULER] Erreur upload {upload_id}: {e}")
        CLASSIFICATION_TO_FIELD = {
            'MAIN': 'MAINFM', 'LEFT': 'LEFT300', 'RIGHT': 'FRONTRIGHT300',
            'FRONTRIGHT': 'FRONTRIGHT300', 'BACK': 'BACK300', 'PERS': 'PERS300',
            'INSITU': 'INSITU300', 'EDITIONNUMBER': 'EDITIONNUMBER300',
            'DET': 'DET300', 'DET2': 'DET2300', 'OTHER': 'OTHER300',
            'OTHER2': 'OTHER2300', 'FRAME': 'FRAME300', 'FRONT': 'FRONT300',
            'SIGN': 'Signature',
        }

        import re as _re

        def _add_classification_to_filename(filename, cls):
            name, ext = os.path.splitext(filename)
            m = _re.search(r'([A-Z]+-\d+)', filename)
            if m:
                return f"{m.group(1)}_{cls}{ext}"
            return f"{name}_{cls}{ext}"

        for upload_id, artwork_id, photo_filename, classification, original_path, target_path in ready_uploads:
            try:
                success = False
                error_message = None

                # Derive artwork_id from filename if not stored
                _m = _re.match(r'^([A-Z]+-\d+)', photo_filename)
                _aid = _m.group(1) if _m else artwork_id

                if os.path.exists(original_path):
                    os.makedirs(FM_DIR, exist_ok=True)

                    # Apply classification suffix to filename (same as direct validation)
                    final_filename = _add_classification_to_filename(photo_filename, classification) if classification else photo_filename
                    final_target_path = os.path.join(FM_DIR, final_filename)

                    shutil.move(original_path, final_target_path)
                    success = True
                    print(f"[SCHEDULER] Upload traité: {_aid} → {final_target_path}")
                else:
                    error_message = f"File not found: {original_path}"

                if success:
                    fm_url = f"https://images.operagallery.com/FM/{final_filename}"

                    cursor.execute("""
                        UPDATE scheduled_uploads
                        SET status = 'completed', processed_at = ?, target_path = ?
                        WHERE id = ?
                    """, (now, final_target_path, upload_id))

                    cursor.execute("""
                        UPDATE photo_validations
                        SET status = 'validated',
                            validated_at = ?,
                            artwork_id = ?,
                            photo_filename = ?
                        WHERE photo_filename = ?
                          AND status = 'scheduled'
                    """, (now, _aid, final_filename, photo_filename))

                    conn.commit()

                    # Call FM API to update the artwork field
                    target_field = CLASSIFICATION_TO_FIELD.get(classification) if classification else None
                    if target_field and _aid:
                        try:
                            filemaker_service.ensure_connected()
                            filemaker_service.update_specialized_field(_aid, target_field, fm_url)
                            print(f"[SCHEDULER] FM field '{target_field}' updated for {_aid}: {fm_url}")
                        except Exception as fm_err:
                            print(f"[SCHEDULER] FM update failed (non-fatal): {fm_err}")

                    # CSV log
                    try:
                        _write_header = not os.path.exists(FM_PUSH_CSV)
                        with open(FM_PUSH_CSV, 'a', newline='', encoding='utf-8-sig') as _f:
                            _w = csv.writer(_f, delimiter=';')
                            if _write_header:
                                _w.writerow(['ID_Artwork', 'FM_Field', 'URL_Pushed', 'Classification', 'Pushed_At'])
                            _w.writerow([_aid, target_field or '', fm_url, classification or '',
                                         datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')])
                    except Exception as _ce:
                        print(f"[SCHEDULER] CSV log failed: {_ce}")
                else:
                    cursor.execute("""
                        UPDATE scheduled_uploads
                        SET status = 'failed', processed_at = ?, error_message = ?
                        WHERE id = ?
                    """, (now, error_message, upload_id))
                    conn.commit()

            except Exception as e:
                cursor.execute("""
                    UPDATE scheduled_uploads
                    SET status = 'failed', processed_at = ?, error_message = ?
                    WHERE id = ?
                """, (now, str(e), upload_id))
                conn.commit()
                print(f"[SCHEDULER] Erreur upload {upload_id}: {e}")

        conn.close()
        
        return len(ready_uploads)
        
    except Exception as e:
        print(f"[SCHEDULER] Erreur traitement programmé: {e}")
        return 0


@auth_bp.route('/api/photos/list-scheduled')
def list_scheduled_photos():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Unauthorized'}), 401

        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 24))
        offset = (page - 1) * limit

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, artwork_id, photo_filename, classification,
                   scheduled_date, status, error_message
            FROM scheduled_uploads
            WHERE status IN ('scheduled', 'failed')
            ORDER BY scheduled_date ASC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        rows = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) FROM scheduled_uploads
            WHERE status IN ('scheduled', 'failed')
        """)
        total = cursor.fetchone()[0]

        conn.close()

        photos = []
        for r in rows:
            photos.append({
                "id": r[0],
                "artwork_id": r[1],
                "filename": r[2],
                "classification": r[3],
                "scheduled_date": r[4],
                "status": r[5],
                "error_message": r[6]
            })

        return jsonify({
            "photos": photos,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/api/photos/scheduled/<int:schedule_id>')
def get_scheduled_photo(schedule_id):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT original_path, target_path, status
            FROM scheduled_uploads
            WHERE id = ?
        """, (schedule_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "Not found"}), 404

        original_path, target_path, status = row

        # If completed → use target path
        if status == "completed" and os.path.exists(target_path):
            return send_file(target_path)

        # If scheduled or failed → show original
        if os.path.exists(original_path):
            return send_file(original_path)

        return jsonify({"error": "File not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def preserve_original(uploaded_path):
    """
    COPY original uploaded file to /originals.
    NEVER modified, NEVER deleted.
    """
    if not uploaded_path or not os.path.exists(uploaded_path):
        return None

    os.makedirs(ORIGINALS_DIR, exist_ok=True)

    filename = os.path.basename(uploaded_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    preserved_name = f"{ts}__{filename}"

    preserved_path = os.path.join(ORIGINALS_DIR, preserved_name)

    # IMPORTANT: COPY (not move)
    shutil.copy2(uploaded_path, preserved_path)

    return preserved_path


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Endpoint for user authentication with 2FA support."""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Missing credentials'}), 400

        username = data['username']
        password = data['password']
        two_fa_code = data.get('twofa_code', '')

        # Verify password first
        if not verify_password(username, password):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Get user data
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, role, email FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()

        if not user_data:
            return jsonify({'error': 'User not found'}), 401

        user_id, user_role, user_email = user_data

        # Check if 2FA is required
        print(f"[LOGIN DEBUG] Checking 2FA requirement for user {username}")

        # Special handling for cron_scheduler - bypass all 2FA checks
        if username == 'cron_scheduler':
            print(f"[LOGIN DEBUG] Bypassing all 2FA checks for cron_scheduler")
            token = generate_token(username)
            return jsonify({
                'success': True,
                'token': token,
                'message': f'Connexion réussie pour {username}'
            })

        if require_2fa(username):
            print(f"[LOGIN DEBUG] 2FA required for {username}")

            # Check if user has TOTP configured
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT totp_enabled, totp_secret FROM users WHERE username = ?', (username,))
            totp_data = cursor.fetchone()
            conn.close()

            totp_enabled = totp_data[0] if totp_data else False
            totp_secret = totp_data[1] if totp_data else None

            if not totp_enabled or not totp_secret:
                # User must configure TOTP first - generate temporary token
                temp_token = generate_token(username)  # Generate token for TOTP setup
                return jsonify({
                    'success': False,
                    'requires_totp_setup': True,
                    'temp_token': temp_token,
                    'message': 'TOTP authentication must be configured'
                })

            if not two_fa_code:
                # Request TOTP code
                return jsonify({
                    'success': False,
                    'requires_2fa': True,
                    'twofa_method': 'totp',
                    'message': 'Enter your authenticator code'
                })
            else:
                # Verify TOTP or backup code
                is_valid = False

                # Try TOTP verification first
                if totp_service.verify_token(totp_secret, two_fa_code):
                    print(f"[LOGIN DEBUG] TOTP code valid for {username}")
                    is_valid = True
                else:
                    # Try backup code verification
                    conn = sqlite3.connect(DATABASE_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id FROM user_backup_codes
                        WHERE user_id = ? AND code = ? AND used_at IS NULL
                    ''', (user_id, two_fa_code))
                    backup_code = cursor.fetchone()

                    if backup_code:
                        # Mark backup code as used
                        cursor.execute('''
                            UPDATE user_backup_codes
                            SET used_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (backup_code[0],))
                        conn.commit()
                        print(f"[LOGIN DEBUG] Backup code valid for {username}")
                        is_valid = True

                    conn.close()

                if not is_valid:
                    return jsonify({'error': 'Invalid authentication code'}), 401
        else:
            print(f"[LOGIN DEBUG] 2FA not required for {username}, skipping TOTP check")

        # Generate JWT token
        token = generate_token(username)
        if token:
            return jsonify({
                'success': True,
                'token': token,
                'username': username,
                'role': user_role
            })
        else:
            return jsonify({'error': 'Token generation error'}), 500

    except Exception as e:
        print(f"[LOGIN] Error: {str(e)}")
        return jsonify({'error': str(e)}), 500
 

@auth_bp.route('/api/auth/resend-2fa', methods=['POST'])
def resend_2fa():
    """Renvoyer un code 2FA"""
    try:
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'error': 'Username required'}), 400
            
        username = data['username']
        
        # Get user data
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, email FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if not user_data:
            return jsonify({'error': 'User not found'}), 401
            
        user_id, user_email = user_data
        
        # Check if 2FA is required for this user
        if not require_2fa(username):
            return jsonify({'error': '2FA not required for this account'}), 400
        
        # Send new 2FA code
        if send_2fa_code(user_id, user_email):
            return jsonify({
                'success': True,
                'message': f'Nouveau code envoyé à {user_email}'
            })
        else:
            return jsonify({'error': 'Failed to send verification code'}), 500
            
    except Exception as e:
        print(f"[RESEND-2FA] Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/status', methods=['GET'])
def status():
    """Endpoint to check authentication status."""
    return jsonify({
        'status': 'Authentication service is working correctly',
        'default_user': 'admin',
        'default_password': 'adminpass'
    })

@auth_bp.route('/api/auth/user-info', methods=['GET'])
def user_info():
    """Get current user information"""
    try:
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        
        # Verify token (you need to implement this based on your JWT verification)
        from auth import verify_token
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        username = payload.get('username')
        
        # Get user info from database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT username, role FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            return jsonify({
                'username': user_data[0],
                'role': user_data[1]
            })
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Helper functions
def get_user_id_by_username(username):
    """Get user ID by username"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def verify_admin_role(username):
    """Verify if user has admin role"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 'admin'

@auth_bp.route("/api/photos/replace", methods=["POST"])
def replace_pending_photo():
    """
    Replace file of a NOT validated (pending) photo
    """
    try:
        # --- AUTH ---
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Missing token"}), 401

        payload = verify_token(token.split(" ")[1])
        if not payload:
            return jsonify({"error": "Invalid token"}), 401

        # --- INPUT ---
        photo_id = request.form.get("photoId")
        new_file = request.files.get("file")

        if not photo_id or not new_file:
            return jsonify({"error": "Missing photoId or file"}), 400

        # --- DB CHECK ---
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT status FROM photo_validations WHERE photo_id = ?",
            (photo_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({"error": "Photo not found"}), 404

        if row[0] != "pending":
            conn.close()
            return jsonify({"error": "Only pending photos can be replaced"}), 403

        # --- FILE PATH ---
        old_path = os.path.join(PHOTOS_BASE_DIR, photo_id)

        if not os.path.exists(old_path):
            conn.close()
            return jsonify({"error": "Original file not found"}), 404

        # --- REPLACE FILE (overwrite) ---
        new_file.save(old_path)

        # --- UPDATE SIZE ---
        new_size = os.path.getsize(old_path)
        cursor.execute(
            "UPDATE photo_validations SET file_size = ? WHERE photo_id = ?",
            (new_size, photo_id)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Photo file replaced successfully"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_super_hd_url(original_path):
    if not original_path:
        return None
    filename = os.path.basename(original_path)
    return f"https://images.operagallery.com/originals/{filename}"


# User management endpoints (old)

# Photo management endpoints
@auth_bp.route('/api/photos/next', methods=['GET'])
def get_next_photo():
    """Get next photo to validate"""
    try:
        # Find real photos from the a-valider directory
        photos_dir = PHOTOS_BASE_DIR
        
        validation_dir = os.path.join(photos_dir, 'a-valider')
        
        if not os.path.exists(validation_dir):
            return jsonify({'error': 'No validation directory found'}), 404
        
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'}
        photo_files = []
        
        for filename in os.listdir(validation_dir):
            file_path = os.path.join(validation_dir, filename)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename.lower())
                if ext in image_extensions:
                    # Build relative path for API
                    relative_path = f"a-valider/{filename}"
                    photo_files.append({
                        'id': relative_path,
                        'filename': filename,
                        'path': file_path,
                        'status': 'pending'
                    })
        
        if not photo_files:
            return jsonify({'error': 'No photos found for validation'}), 404
        
        # For now, return the first photo (in real implementation, you'd track validated photos)
        import random
        selected_photo = random.choice(photo_files)
        
        # Enrich photo with Odoo metadata
        enriched_photo = enrich_photo_with_odoo_data(selected_photo)
        
        return jsonify({
            'photo': enriched_photo
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/<path:photo_id>/thumbnail', methods=['GET'])
def get_photo_thumbnail(photo_id):
    """Serve optimized thumbnail for mosaic view"""
    try:
        # Decode the photo_id if it was URL encoded
        import urllib.parse
        decoded_photo_id = urllib.parse.unquote(photo_id)
        
        # Security check - ensure we're not accessing files outside photos directory
        if '..' in decoded_photo_id or decoded_photo_id.startswith('/'):
            return jsonify({'error': 'Invalid photo path'}), 400
        
        # Try to serve from photos directory
        photos_dir = PHOTOS_BASE_DIR
        photo_path = os.path.join(photos_dir, decoded_photo_id)
        
        if os.path.exists(photo_path):
            # Create thumbnail cache directory
            cache_dir = os.path.join(photos_dir, '..', 'cache', 'thumbnails')
            os.makedirs(cache_dir, exist_ok=True)
            
            # Generate cache filename
            base_name = os.path.splitext(os.path.basename(photo_path))[0]
            cache_filename = f"{base_name}_thumb.jpg"
            cache_path = os.path.join(cache_dir, cache_filename)
            
            # Check if file is PDF
            is_pdf = photo_path.lower().endswith('.pdf')

            # Create thumbnail if it doesn't exist or is older than original
            if not os.path.exists(cache_path) or os.path.getmtime(photo_path) > os.path.getmtime(cache_path):
                try:
                    if is_pdf:
                        # For PDFs, create a simple placeholder thumbnail
                        from PIL import Image, ImageDraw, ImageFont
                        img = Image.new('RGB', (400, 400), color='#f0f0f0')
                        draw = ImageDraw.Draw(img)

                        # Draw PDF icon (simple rectangle with text)
                        draw.rectangle([100, 100, 300, 300], outline='#ff0000', width=3)
                        draw.text((200, 200), 'PDF', fill='#ff0000', anchor='mm')

                        img.save(cache_path, 'JPEG', quality=80, optimize=True)
                    else:
                        # For images, create normal thumbnail
                        from PIL import Image
                        with Image.open(photo_path) as img:
                            # Convert to RGB if necessary
                            if img.mode in ('RGBA', 'P'):
                                img = img.convert('RGB')

                            # Create thumbnail (400x400px max)
                            img.thumbnail((400, 400), Image.Resampling.LANCZOS)

                            # Save with good quality but compressed
                            img.save(cache_path, 'JPEG', quality=80, optimize=True)

                except Exception as e:
                    print(f"Error creating thumbnail: {e}")
                    # Fallback: return empty response for unsupported formats
                    return jsonify({'error': 'Thumbnail not available'}), 404
            
            # Serve the thumbnail
            return send_file(cache_path)
        else:
            return jsonify({'error': 'Photo not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/<path:photo_id>', methods=['GET'])
def get_photo(photo_id):
    """Serve photo file with optimization for large files"""
    try:
        # Decode the photo_id if it was URL encoded
        import urllib.parse
        decoded_photo_id = urllib.parse.unquote(photo_id)
        
        # Security check - ensure we're not accessing files outside photos directory
        if '..' in decoded_photo_id or decoded_photo_id.startswith('/'):
            return jsonify({'error': 'Invalid photo path'}), 400
        
        # Try to serve from photos directory
        photos_dir = PHOTOS_BASE_DIR
        
        photo_path = os.path.join(photos_dir, decoded_photo_id)
        
        if os.path.exists(photo_path):
            file_type_info = get_file_type_info(photo_path)
            file_type = file_type_info[0] if file_type_info[0] else 'image'
            mime_type = file_type_info[1] if file_type_info[1] else 'image/jpeg'

            # Videos: serve with HTTP Range support so browsers can seek/play
            if file_type == 'video':
                return _serve_with_range(photo_path, mime_type)

            # Check file size (only for images)
            file_size = os.path.getsize(photo_path)

            # For image files > 20MB, create and serve a compressed version
            if file_size > 20 * 1024 * 1024:  # 20MB
                cache_dir = os.path.join(photos_dir, '..', 'cache', 'optimized')
                os.makedirs(cache_dir, exist_ok=True)

                # Generate cache filename
                base_name = os.path.splitext(os.path.basename(photo_path))[0]
                cache_filename = f"{base_name}_optimized.jpg"
                cache_path = os.path.join(cache_dir, cache_filename)

                # Create optimized version if it doesn't exist
                if not os.path.exists(cache_path) or os.path.getmtime(photo_path) > os.path.getmtime(cache_path):
                    try:
                        from PIL import Image
                        with Image.open(photo_path) as img:
                            # Convert to RGB if necessary
                            if img.mode in ('RGBA', 'P'):
                                img = img.convert('RGB')

                            # Resize if too large (max 2048px on longest side)
                            max_size = 2048
                            if max(img.size) > max_size:
                                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                            # Save with high quality but compressed
                            img.save(cache_path, 'JPEG', quality=85, optimize=True)

                    except Exception as e:
                        print(f"Error creating optimized version: {e}")
                        # Fallback to original file
                        return send_file(photo_path)

                # Serve the optimized version
                if os.path.exists(cache_path):
                    return send_file(cache_path)

            # For smaller files, serve directly
            return send_file(photo_path)
        else:
            return jsonify({'error': 'Photo not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/admin/resync-crm', methods=['POST'])
def admin_resync_crm():
    """Super-admin only: push all validated DAS images to OperaCRM (Odoo).
    Matches artworks by ID NUMBER (accent/prefix-insensitive); only fills empty
    Odoo fields (never overwrites). Returns a summary for the UI."""
    import requests as _rq, unicodedata as _ud, re as _re
    token = request.headers.get('Authorization', '')
    if not token.startswith('Bearer '):
        return jsonify({'error': 'Missing token'}), 401
    payload = verify_token(token.split(' ')[1])
    if not payload:
        return jsonify({'error': 'Invalid token'}), 401
    if payload.get('role') != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    # Review2-aligned classifications (client spec) + legacy aliases.
    CLS2FIELD = {
        "MAIN": "NewMainHR", "MAIN_HR": "NewMainHR", "MAIN_LR": "NewMainLR",
        "FRAME": "frame_picture",
        "BACK": "back_pictures",
        "BACKFRAME": "back_frame_hr",
        "SIGN": "signatures_pictures",
        "DET": "detail_1_url", "DET1": "detail_1_url", "DET2": "detail_2_url",
        "PERS": "perspective_url", "SCALE": "perspective_url",
        "INSITU": "in_situ_hr",
        "OTHERS": "other_url", "OTHER": "other_url",
        "FRONT": "front_picture", "FRONTRIGHT": "right_picture", "LEFT": "left_picture",
        "VIEW34": "view_34_hr",
    }
    FIELDS = sorted(set(CLS2FIELD.values()))
    ODOO, DBN, LG, PW = "https://operacrm.com", "odoo_15", "surafelwubshet7@gmail.com", "Surafell"
    IMG = "https://images.operagallery.com/FM/"

    def _num(s):
        m = _re.search(r"(\d{3,})", s or ""); return m.group(1) if m else None
    def _pref(s):
        m = _re.match(r"\s*([A-Za-zÀ-ÿ ]+?)\s*-", s or "")
        if not m: return ""
        d = _ud.normalize("NFKD", m.group(1))
        return "".join(c for c in d if not _ud.combining(c)).upper().replace(" ", "")

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        rows = conn.execute(
            "SELECT artwork_id, classification, photo_filename FROM photo_validations "
            "WHERE status='validated' AND artwork_id IS NOT NULL AND TRIM(artwork_id)!='' "
            "AND classification IN (%s)" % ",".join("?" * len(CLS2FIELD)),
            list(CLS2FIELD.keys())).fetchall()
        conn.close()
        desired = {}
        for aid, cls, fname in rows:
            f = CLS2FIELD.get(cls)
            if f and fname:
                desired.setdefault(aid, {})[f] = IMG + fname

        s = _rq.Session()
        s.post(f"{ODOO}/web/session/authenticate", json={"jsonrpc": "2.0",
            "params": {"db": DBN, "login": LG, "password": PW}}, timeout=15)
        by_num, off = {}, 0
        while True:
            r = s.post(f"{ODOO}/web/dataset/call_kw", json={"jsonrpc": "2.0", "method": "call",
                "params": {"model": "product.template", "method": "search_read",
                           "args": [[["IdName", "!=", False]]],
                           "kwargs": {"fields": ["id", "IdName"] + FIELDS, "limit": 2000, "offset": off}}, "id": 1})
            b = r.json().get("result", [])
            if not b: break
            for rec in b:
                n = _num(rec["IdName"])
                if n: by_num.setdefault(n, []).append(rec)
            off += len(b)

        to_push, not_in_crm, already, ambiguous = [], 0, 0, 0
        for aid, fields in desired.items():
            n = _num(aid); cands = by_num.get(n, []) if n else []
            if len(cands) == 1:
                rec = cands[0]
            elif not cands:
                not_in_crm += 1; continue
            else:
                pm = [c for c in cands if _pref(c["IdName"]) == _pref(aid)]
                if len(pm) == 1: rec = pm[0]
                else: ambiguous += 1; continue
            for field, url in fields.items():
                if rec.get(field): already += 1
                else: to_push.append((rec["id"], field, url))

        pushed = errors = 0
        for _id, field, url in to_push:
            rr = s.post(f"{ODOO}/web/dataset/call_kw", json={"jsonrpc": "2.0", "method": "call",
                "params": {"model": "product.template", "method": "write",
                           "args": [[_id], {field: url}], "kwargs": {}}, "id": 1})
            if rr.json().get("result") is True: pushed += 1
            else: errors += 1
        return jsonify({'success': True, 'pushed': pushed, 'already_in_crm': already,
                        'not_in_crm': not_in_crm, 'ambiguous': ambiguous, 'errors': errors,
                        'candidates': len(to_push)})
    except Exception as e:
        print(f"[RESYNC] error: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/photos/artwork-slots/<path:artwork_id>', methods=['GET'])
def get_artwork_filled_slots(artwork_id):
    """Return the classifications already filled (validated) for an artwork,
    based on the photo_validator SQLite DB. Used by the classification dropdown
    to show a green dot (slot has an image) vs red dot (slot empty)."""
    try:
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        if not verify_token(token.split(' ')[1]):
            return jsonify({'error': 'Invalid token'}), 401

        import urllib.parse
        artwork_id = urllib.parse.unquote(artwork_id)

        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute(
            """SELECT DISTINCT classification FROM photo_validations
               WHERE artwork_id = ? AND status = 'validated'
                 AND classification IS NOT NULL AND TRIM(classification) != ''""",
            (artwork_id,)
        )
        filled = [row[0] for row in cur.fetchall()]
        conn.close()

        # Fetch the artwork's Category from Odoo (Painting / Sculpture / ...) so
        # the classification dropdown can show the right category set.
        category = None
        try:
            import requests as _requests
            _s = _requests.Session()
            _s.post('https://operacrm.com/web/session/authenticate',
                    json={'jsonrpc': '2.0', 'params': {
                        'db': 'odoo_15',
                        'login': 'surafelwubshet7@gmail.com',
                        'password': 'Surafell'}},
                    timeout=10)
            _r = _s.post('https://operacrm.com/web/dataset/call_kw',
                         json={'jsonrpc': '2.0', 'method': 'call', 'params': {
                             'model': 'product.template', 'method': 'search_read',
                             'args': [[['IdName', '=', artwork_id]]],
                             'kwargs': {'fields': ['Category', 'Type', 'Medium'], 'limit': 1}},
                             'id': 1},
                         timeout=10)
            _res = (_r.json() or {}).get('result') or []
            if _res:
                category = _res[0].get('Category') or None
        except Exception as _ce:
            print(f"artwork-slots: category fetch failed for {artwork_id}: {_ce}")

        return jsonify({'success': True, 'artwork_id': artwork_id,
                        'filled': filled, 'category': category})
    except Exception as e:
        print(f"Error getting artwork filled slots: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/photos/details/<path:photo_id>', methods=['GET'])
def get_photo_details(photo_id):
    """Get photo details and metadata"""
    try:
        # Decode the photo_id if it was URL encoded
        import urllib.parse
        decoded_photo_id = urllib.parse.unquote(photo_id)
        
        # Security check
        if '..' in decoded_photo_id or decoded_photo_id.startswith('/'):
            return jsonify({'error': 'Invalid photo path'}), 400
        
        # Try to get photo from photos directory
        photos_dir = PHOTOS_BASE_DIR
        
        photo_path = os.path.join(photos_dir, decoded_photo_id)
        base_name, ext = os.path.splitext(decoded_photo_id)
          
          
        #   base_name, ext = os.path.splitext(decoded_photo_id)
        if ext.lower() in [".tif", ".tiff"]:
            jpg_name = base_name + "_300dpi.jpg"
            jpg_path = os.path.join(photos_dir, jpg_name)

            if os.path.exists(jpg_path):
                photo_path = jpg_path
                decoded_photo_id = jpg_name

        if not os.path.exists(photo_path):
            return jsonify({'error': 'Photo not found'}), 404 
        
        # Get file stats
        import stat
        file_stats = os.stat(photo_path)
        file_size = file_stats.st_size
        
        # Format file size
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        
        # Get file extension
        _, ext = os.path.splitext(decoded_photo_id)
        
        # Try to get image dimensions if it's an image
        width, height = None, None
        try:
            from PIL import Image
            with Image.open(photo_path) as img:
                width, height = img.size
        except:
            # If PIL is not available or it's not an image, use placeholder values
            width, height = "Unknown", "Unknown"
        
        # Get modification time
        import time
        mod_time = time.ctime(file_stats.st_mtime)
        
        # Get file type information
        filename = os.path.basename(decoded_photo_id)
        file_type_info = get_file_type_info(filename)
        file_type = file_type_info[0] if file_type_info[0] else 'unknown'
        mime_type = file_type_info[1] if file_type_info[1] else 'application/octet-stream'
        
        # Determine paper format based on dimensions (if available)
        paper_format = "Not detected"
        if isinstance(width, int) and isinstance(height, int):
            # Simple format detection based on common ratios
            ratio = max(width, height) / min(width, height)
            if 1.4 < ratio < 1.5:  # A4 ratio is ~1.414
                paper_format = "A4"
            elif 1.2 < ratio < 1.3:
                paper_format = "A5"
            elif 0.9 < ratio < 1.1:
                paper_format = "Square"
            else:
                paper_format = "Custom Format"
        
        return jsonify({
            'width': width,
            'height': height,
            'size': size_str,
            'type': ext.upper().replace('.', '') if ext else 'Unknown',
            'file_type': file_type,
            'mime_type': mime_type,
            'modified': mod_time,
            'paperFormat': paper_format,
            'path': photo_path
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def fix_local_photo_path(url_or_path):
    """
    Converts public CDN URLs to local Docker paths.
    Keeps local paths unchanged.
    """

    if not url_or_path:
        return url_or_path

    # Already local path?
    if url_or_path.startswith("/app/photos/"):
        return url_or_path

    # Public URL → local Docker path
    url = url_or_path

    url = url.replace("https://images.operagallery.com/FM/", "/app/photos/FM/")
    url = url.replace("https://images.operagallery.com/A5/", "/app/photos/A5/")
    url = url.replace("https://images.operagallery.com/Thumb/", "/app/photos/Thumb/")
    url = url.replace("https://images.operagallery.com/Perspective/", "/app/photos/Perspective/")
    url = url.replace("https://images.operagallery.com/", "/app/photos/")

    return url

@auth_bp.route('/api/photos/validate', methods=['POST'])
def validate_photo():
    """Validate or reject a photo with classification, scheduling, and FileMaker/OperaCRM sync"""
    try:
        # ------------------------------
        # 🔐 Authorization Check
        # ------------------------------
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401

        validator_username = payload.get('username')
        validator_id = get_user_id_by_username(validator_username)

        # ------------------------------
        # 📦 Extract Data from Request
        # ------------------------------
        data = request.get_json()
        photo_id = data.get('photoId')
        decision = data.get('decision')  # 'valider' or 'refuser'
        classification = data.get('classification')
        artwork_id = data.get('artworkId')
        reject_reason = data.get('rejectReason')
        new_filename = data.get('newFilename')
        scheduled_date = data.get('scheduledDate')
        display_name = data.get("displayName")
        should_generate_perspective = data.get("generatePerspective", False)
                # 🔥 Normalize frontend decision values
        if decision == "validate":
            decision = "valider"
        elif decision == "reject":
            decision = "refuser"

        # 🔥 If scheduling → override decision
        if scheduled_date:
            decision = "scheduled"
        if not photo_id or not decision:
            return jsonify({'error': 'photoId et decision requis'}), 400

        # ------------------------------
        # 📸 Determine File Paths
        # ------------------------------
        if '/' in photo_id:
            filename = os.path.basename(photo_id)
            directory = os.path.dirname(photo_id)
        else:
            filename = photo_id
            directory = 'a-valider'

        current_filename = new_filename if new_filename and new_filename != filename else filename
        # Determine file type
        ext = os.path.splitext(current_filename)[1].lower()
        is_pdf = ext == ".pdf"
        is_video = ext in [".mp4", ".mov", ".avi", ".mkv"]
        if is_pdf or is_video:
            fm_existing = None
            odoo_existing = False
            
        # Display name required for PDF or VIDEO
        if (is_pdf or is_video) and not display_name:
            return jsonify({'error': 'Display name is required for PDF or Video'}), 400

        photo_path = os.path.join(PHOTOS_BASE_DIR, directory, current_filename)
        if not os.path.exists(photo_path):
            if new_filename and new_filename != filename:
                photo_path = os.path.join(PHOTOS_BASE_DIR, directory, filename)
                if not os.path.exists(photo_path):
                    return jsonify({'error': 'Photo not found'}), 404
                current_filename = filename
            else:
                return jsonify({'error': 'Photo not found'}), 404

        # Resolve the original/super-HD URL only once photo_path points at a file
        # that actually exists on disk — resolving it before the rename fallback
        # above made preserve_original() silently fail on renamed uploads and
        # return None, which then wiped main_super_picture_hd in Odoo (see fix below).
        original_preserved_path = preserve_original(photo_path)
        print("[ORIGINAL SAVED]", original_preserved_path)
        super_hd_url = get_super_hd_url(original_preserved_path)
        print("[SUPER HD URL]", super_hd_url)

        # ------------------------------
        # 🧠 Get Submitter Info
        # ------------------------------
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT submitted_by FROM photo_validations WHERE photo_id = ? OR photo_filename = ?',
            (filename, filename)
        )
        existing_record = cursor.fetchone()
        submitted_by = existing_record[0] if existing_record else None

        if not submitted_by:
            cursor.execute('SELECT id FROM users WHERE role = ?', ('uploader',))
            uploader_result = cursor.fetchone()
            submitted_by = uploader_result[0] if uploader_result else None

        # ===============================================================
        # 🕒 SCHEDULING BRANCH
        # ===============================================================
        #if scheduled_date:
        if decision == "scheduled":
            try:
                print(f"[SCHEDULE] Scheduling photo {photo_id} for {scheduled_date} with classification {classification}")

                # Parse date
                if isinstance(scheduled_date, str):
                    schedule_datetime = datetime.fromisoformat(scheduled_date.replace('Z', '+00:00'))
                else:
                    schedule_datetime = datetime.now() + timedelta(days=1)

                if not classification:
                    conn.close()
                    return jsonify({'error': 'Classification requise pour la programmation'}), 400

                os.makedirs(SCHEDULED_DIR, exist_ok=True)

                base_filename = new_filename if new_filename else filename
                scheduled_path = os.path.join(SCHEDULED_DIR, base_filename)
                destination_path = os.path.join(FM_DIR, base_filename)
                real_scheduled_path = os.path.abspath(scheduled_path)
                real_destination_path = os.path.abspath(destination_path)

                # If running inside Docker, adjust /app/photos → /home/projet/pictures/img/FM
                scheduled_path = os.path.join(SCHEDULED_DIR, base_filename)
                destination_path = os.path.join(FM_DIR, base_filename)

                if os.path.exists(photo_path):
                    # shutil.move(photo_path, scheduled_path)
                    shutil.copy2(photo_path, scheduled_path)
                    os.remove(photo_path)
                else:
                    conn.close()
                    return jsonify({'error': f'Photo introuvable: {photo_path}'}), 404

                print(f"[DEBUG] validator_username = {validator_username}, validator_id = {validator_id}")
                if not validator_id:
                    print("[DEBUG] validator_id is None — assigning default admin user (id=1)")
                    validator_id = 1  # fallback

                schedule_id = schedule_photo_upload(
                    conn,
                    artwork_id=artwork_id,
                    photo_filename=base_filename,
                    classification=classification,
                    original_path=scheduled_path,
                    target_path=destination_path,
                    scheduled_date=schedule_datetime,
                    created_by=validator_id
                )
                print(f"[DEBUG] schedule_photo_upload() returned: {schedule_id}")

                cursor.execute('''
                    INSERT INTO photo_validations 
                    (photo_id, photo_filename, submitted_by, validated_by, status, classification, artwork_id,display_name, scheduled_date, validated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (filename, base_filename, submitted_by, validator_id, 'scheduled', classification, artwork_id, display_name, schedule_datetime))

                conn.commit()
                conn.close()

                print(f"[SCHEDULE] ✅ Photo scheduled successfully (ID {schedule_id}) for {schedule_datetime}")
                return jsonify({
                    'success': True,
                    'status': 'scheduled',
                    'message': f'Photo programmée pour publication le {schedule_datetime.strftime("%d/%m/%Y %H:%M")}'
                }), 200

            except Exception as e:
                conn.close()
                print(f"[SCHEDULE] ❌ Scheduling error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Programming error: {str(e)}'}), 500

        # ===============================================================
        # ✅ VALIDATION BRANCH
        # ===============================================================
        if decision == 'valider':
            print(f"[DEBUG VALIDATION] Starting validation with classification: {classification}")
            streaming_url = None  # Will be set for videos sent to streaming server
            if not classification:
                conn.close()
                return jsonify({'error': 'Classification requise pour la validation'}), 400

            CLASSIFICATION_TO_FIELD = {
                    # Images
                    'MAIN':          'MAINFM',
                    'LEFT':          'LEFT300',
                    'RIGHT':         'FRONTRIGHT300',
                    'FRONTRIGHT':    'FRONTRIGHT300',
                    'BACK':          'BACK300',
                    'PERS':          'PERS300',
                    'INSITU':        'INSITU300',
                    'EDITIONNUMBER': 'EDITIONNUMBER300',
                    'DET':           'DET300',
                    'DET2':          'DET2300',
                    'OTHER':         'OTHER300',
                    'OTHER2':        'OTHER2300',
                    'FRAME':         'FRAME300',
                    'FRONT':         'FRONT300',
                    'BACKFRAME':     'BACK300',
                    'DET1':          'DET300',
                    'SCALE':         'PERS300',
                    'OTHERS':        'OTHER300',
                    "SIGN":          "Signature",

                    # New HR/LR + A6 + 3/4 View classifications (client 2026 spec).
                    # FM is being retired; these primarily drive the Odoo write
                    # below. FM values here are placeholders (best-effort push).
                    'MAIN_HR': 'MAINFM',      'MAIN_LR': 'MAINFM',
                    'FRAME_HR': 'FRAME300',   'FRAME_LR': 'FRAME300',
                    'BACK_HR': 'BACK300',     'BACK_LR': 'BACK300',
                    'BACKFRAME_HR': 'BACK300','BACKFRAME_LR': 'BACK300',
                    'SIGN_HR': 'Signature',   'SIGN_LR': 'Signature',
                    'DET1_HR': 'DET300',      'DET1_LR': 'DET300',
                    'DET2_HR': 'DET2300',     'DET2_LR': 'DET2300',
                    'SCALE_HR': 'PERS300',    'SCALE_LR': 'PERS300',
                    'INSITU_HR': 'INSITU300', 'INSITU_LR': 'INSITU300',
                    'OTHERS_HR': 'OTHER300',  'OTHERS_LR': 'OTHER300',
                    'A6': 'MAINFM',
                    'VIEW34_HR': 'OTHER300',  'VIEW34_LR': 'OTHER300',

                    # Additional image fields
                    'OPENSEA': 'UrlOpensea',
                    'UHD': 'UHDPictureUrl',
                    'BAK1': 'ImageBAK1',
                    'BAK2': 'ImageBAK2',
                    'BAK3': 'ImageBAK3',
                    'BAK4': 'ImageBAK4',
                    'BAK5': 'ImageBAK5',
                    
                    # PDF Classifications - 2 champs par catégorie
                    'CERT_AUTHENTICITY_1': 'CertAuthenticityUrl1',
                    'CERT_AUTHENTICITY_2': 'CertAuthenticityUrl2',
                    'CATALOG_RAISONNE_1': 'CatalogRaisonneUrl1',
                    'CATALOG_RAISONNE_2': 'CatalogRaisonneUrl2',
                    'EXHIBITION_CATALOG_1': 'ExhibitionCatalogUrl1',
                    'EXHIBITION_CATALOG_2': 'ExhibitionCatalogUrl2',
                    'CONDITION_REPORT_1': 'ConditionReportUrl1',
                    'CONDITION_REPORT_2': 'ConditionReportUrl2',
                    'OTHER_DOCUMENT_1': 'OtherDocumentUrl1',
                    'OTHER_DOCUMENT_2': 'OtherDocumentUrl2',
                    
                    # Video Classifications - 2 champs par category
                    'VIDEO_PRESENTATION_1': 'VideoPresentationUrl1',
                    'VIDEO_PRESENTATION_2': 'VideoPresentationUrl2',
                    'VIDEO_DETAIL_1': 'VideoDetailUrl1',
                    'VIDEO_DETAIL_2': 'VideoDetailUrl2',
                    'VIDEO_INSTALLATION_1': 'VideoInstallationUrl1',
                    'VIDEO_INSTALLATION_2': 'VideoInstallationUrl2',
                    'VIDEO_TIMELAPSE_1': 'VideoTimelapseUrl1',
                    'VIDEO_TIMELAPSE_2': 'VideoTimelapseUrl2',
                    'VIDEO_DOCUMENTARY_1': 'VideoDocumentaryUrl1',
                    'VIDEO_DOCUMENTARY_2': 'VideoDocumentaryUrl2',
                    'VIDEO_INTERVIEW_1': 'VideoInterviewUrl1',
                    'VIDEO_INTERVIEW_2': 'VideoInterviewUrl2'
                }

            valid_classifications = list(CLASSIFICATION_TO_FIELD.keys())
            if classification not in valid_classifications:
                conn.close()
                return jsonify({'error': f'Classification invalide: {classification}'}), 400

            target_field = CLASSIFICATION_TO_FIELD[classification]
            base_filename = current_filename
            extracted_id_from_original = extract_artwork_id_from_filename(base_filename)
            def add_classification_to_filename(filename, classification):
                import re
                name, ext = os.path.splitext(filename)
                match = re.search(r'([A-Z]+-\d+)', filename)
                if match:
                    artwork_id = match.group(1)
                    return f"{artwork_id}_{classification}{ext}"
                return f"{name}_{classification}{ext}"

            final_filename = add_classification_to_filename(base_filename, classification)
            # artwork_id = extract_artwork_id_from_filename(final_filename)
            artwork_id = extracted_id_from_original

            # ---------------------------------------------------------
            # FINAL & ONLY DUPLICATE CHECK (FileMaker + Odoo + local)
            # - This runs BEFORE moving the new file into FM_DIR.
            # - New file will remain in the same 'a-valider' folder (per your choice).
            # ---------------------------------------------------------
            from image_metrics import get_image_metrics
            from search_operacrm_corrected import OperaCRMClient

            fm_existing = None
            existing_path = None
            existing_metrics = {}
            odoo_existing = False
            odoo_url = None
            
            # NEW IMAGE METRICS
            real_new_path = fix_local_photo_path(photo_path)
            # new_metrics = get_image_metrics(real_new_path)
            new_metrics = {} if (is_pdf or is_video) else get_image_metrics(real_new_path)

            # ---- FileMaker check ----
            try:
                fm_existing = filemaker_service.get_field_value(artwork_id, target_field)
            except:
                fm_existing = None

            if not fm_existing:
                direct_match = final_filename  # Example: ABC-123_MAIN.jpg
                direct_path = os.path.join(FM_DIR, direct_match)

                if os.path.exists(direct_path):
                    fm_existing = f"https://images.operagallery.com/FM/{direct_match}"
                    existing_path = direct_path
                    existing_metrics = get_image_metrics(direct_path)

            # ---- Odoo check (skip for video/PDF - VIDEO_ not in odoo_field_map, saves an auth call) ----
            if not (is_pdf or is_video):
                try:
                    odoo = OperaCRMClient()
                    if odoo.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell"):
                        recs = odoo.search_by_idname(artwork_id) or []
                        if recs:
                            odoo_field_map = {
                                "MAIN":          "main_picture_hd",
                                "MAIN_HR":       "main_picture_hd",
                                "MAIN_LR":       "main_web_picture",
                                "LEFT":          "left_picture",
                                "RIGHT":         "right_picture",
                                "FRONTRIGHT":    "right_picture",
                                "FRONT":         "front_picture",
                                "BACK":          "back_pictures",
                                "BACKFRAME":     "back_frame_hr",
                                "PERS":          "perspective_url",
                                "SCALE":         "perspective_url",
                                "INSITU":        "in_situ_url",
                                "EDITIONNUMBER": "edition_number_url",
                                "DET":           "detail_1_url",
                                "DET1":          "detail_1_url",
                                "DET2":          "detail_2_url",
                                "OTHER":         "other_url",
                                "OTHERS":        "other_url",
                                "OTHER2":        "signatures_pictures",
                                "FRAME":         "frame_picture",
                                "SIGN":          "signatures_pictures",
                            }
                            f = odoo_field_map.get(classification)
                            if classification in ("MAIN", "MAIN_HR", "MAIN_LR"):
                                main_old = recs[0].get("main_picture_hd") or recs[0].get("main_web_picture")
                                if main_old:
                                    odoo_existing = True
                                    odoo_url = main_old
                            else:
                                if f and recs[0].get(f):
                                    odoo_existing = True
                                    odoo_url = recs[0].get(f)
                finally:
                    try:
                        if 'odoo' in locals() and getattr(odoo, "session", None):
                            odoo.session.close()
                    except:
                        pass

            # ---- If duplicate exists ----
            # if fm_existing or odoo_existing:
            if (fm_existing or odoo_existing) and not (is_pdf or is_video):
                existing_url = fm_existing or odoo_url
                existing_path = fix_local_photo_path(existing_url)
                existing_metrics = get_image_metrics(existing_path)
                cursor.execute("""
                    INSERT INTO photo_validations
                    (photo_id, photo_filename, submitted_by, validated_by, status, classification, artwork_id, display_name, validated_at)
                    VALUES (?, ?, ?, ?, 'duplicate_pending', ?, ?, ?, CURRENT_TIMESTAMP)
                """, (filename, final_filename, submitted_by, validator_id, classification, artwork_id, display_name))
                conn.commit()
                conn.close()

                # Return both previews (new stays in a-valider)
                # new_preview_url = f"/api/photos/preview?file={directory}/{os.path.basename(photo_path)}"
                return jsonify({
                    "duplicate": True,
                    "artworkId": artwork_id,
                    "classification": classification,
                    "existing": {
                        "url": existing_url,
                        "metrics": existing_metrics
                    },
                    "new": {
                        "local_path": photo_path,
                        "metrics": new_metrics
                    },
                    "newFilePath": photo_path,
                    "message": "Duplicate found — choose which photo to keep."
                }), 409

            # If not duplicate — proceed with existing flow (move, process, update)
            if artwork_id:
                try:
                    artwork = filemaker_service.find_artwork_by_id(artwork_id)
                    print("[FM ARTWORK KEYS]", artwork.keys())
                    print("[FM ARTWORK FULL]", artwork)
		    # -----------------------------------------------------
                    # NEW RULE: MUST EXIST IN FileMaker OR Odoo → OTHERWISE STOP
                    # -----------------------------------------------------
                    try:
                        fm_found = artwork is not None

                        # Check Odoo
                        from search_operacrm_corrected import OperaCRMClient
                        check_client = OperaCRMClient()
                        odoo_found = False

                        if check_client.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell"):
                            odoo_records = check_client.search_by_idname(artwork_id)
                            odoo_found = bool(odoo_records)
                            
                            try:
                                check_client.session.close()
                            except:
                                pass

                        if not fm_found and not odoo_found:
                            print(f"[STOP] Artwork {artwork_id} not found in FM or Odoo → sending email + abort")
                            email_service.send_email(
                                "frederic@karroad.fr",
                                f"[Missing Artwork] {artwork_id} not found in FileMaker or Odoo",
                                f"""
                                <h2>Artwork Not Found</h2>
                                <p><b>Artwork ID:</b> {artwork_id}</p>
                                <p><b>Filename:</b> {final_filename}</p>
                                <p><b>Submitted by user ID:</b> {submitted_by}</p>
                                <p style="color:red;font-weight:bold;">This artwork does not exist in FileMaker or Odoo. Please create it manually.</p>
                                """
                            )

                            conn.close()
                            return jsonify({
                                "error": f"Artwork {artwork_id} not found in FileMaker or Odoo. Admin notified."
                            }), 400
                      
                    except Exception as e:
                        print("[CHECK ERROR]", e)

                except Exception as e:
                    print(f"[VALIDATION] FileMaker search error: {e}")
                    artwork = None

                if is_video:
                    os.makedirs(VIDEO_DIR, exist_ok=True)
                    destination_path = os.path.join(VIDEO_DIR, final_filename)
                else:
                    os.makedirs(FM_DIR, exist_ok=True)
                    destination_path = os.path.join(FM_DIR, final_filename)
                # ⛔ STOP AUTO-RENAME: If file exists → return duplicate popup
                # if os.path.exists(destination_path):
                #     existing_url = f"https://images.operagallery.com/FM/{final_filename}"
                #     # fm_real = fix_local_path(destination_path)
                #     # existing_metrics = get_image_metrics(fm_real)

                #     # existing_metrics = get_image_metrics(destination_path)
                #     real_existing_path = fix_local_photo_path(destination_path)
                #     existing_metrics = get_image_metrics(real_existing_path)


                #     conn.close()

                #     return jsonify({
                #         "duplicate": True,
                #         "artworkId": artwork_id,
                #         "classification": classification,
                #         "existing": {
                #             "url": existing_url,
                #             "metrics": existing_metrics
                #         },
                #         "new": {
                #             "local_path": photo_path,
                #             "metrics": new_metrics
                #         },
                #         "newFilePath": photo_path,
                #         "message": "Duplicate found — choose which photo to keep."
                #     }), 409
                if not (is_pdf or is_video):  # Only IMAGES go to duplicate popup
                    if os.path.exists(destination_path):
                        existing_url = f"https://images.operagallery.com/FM/{final_filename}"
                        real_existing_path = fix_local_photo_path(destination_path)

                        existing_metrics = get_image_metrics(real_existing_path)  # normal for images
                        conn.close()

                        return jsonify({
                            "duplicate": True,
                            "artworkId": artwork_id,
                            "classification": classification,
                            "existing": {
                                "url": existing_url,
                                "metrics": existing_metrics
                            },
                            "new": {
                                "local_path": photo_path,
                                "metrics": new_metrics
                            },
                            "newFilePath": photo_path,
                            "message": "Duplicate found — choose which photo to keep."
                        }), 409
                shutil.move(photo_path, destination_path)

                # ------------------------------------------------------------
                # PDF / VIDEO → NO PROCESSING (skip PIL completely)
                # ------------------------------------------------------------
                if is_pdf or is_video:
                    if is_video:
                        # Import video into HLS streaming server
                        _source_url = f"https://video.operagallery.com/video/{final_filename}"
                        _mp4_url = _source_url  # direct download URL (always available)
                        try:
                            import requests as _req
                            _resp = _req.post(
                                "https://video.operagallery.com/api/import",
                                json={"url": _source_url, "title": final_filename},
                                timeout=30
                            )
                            if _resp.ok:
                                _vid_id = _resp.json().get("id")
                                fm_url = f"https://video.operagallery.com/hls/{_vid_id}/master.m3u8"
                                streaming_url = fm_url
                                print(f"[PROCESSOR] Video sent to streaming server, ID: {_vid_id}, HLS: {fm_url}, MP4: {_mp4_url}")
                            else:
                                fm_url = _source_url
                                _mp4_url = None
                                print(f"[PROCESSOR] Streaming server error {_resp.status_code}, fallback: {fm_url}")
                        except Exception as _e:
                            fm_url = _source_url
                            _mp4_url = None
                            print(f"[PROCESSOR] Streaming server unreachable: {_e}, fallback: {fm_url}")
                    else:
                        fm_url = f"https://images.operagallery.com/FM/{final_filename}"
                    a5_url = None
                    thumb_url = None
                    pers_url = None
                    web300_url = None
                    maintif_url = None
                    print("[PROCESSOR] PDF/Video detected — skipping processing, using FM URL only:", fm_url)

                else:
                    try:
                        from image_processor import process_uploaded_image
                        from urllib.parse import quote as _quote
                        
                        
                        artwork_width_cm = None
                        artwork_height_cm = None

                        if should_generate_perspective and artwork:
                            try:
                                #size_l = artwork.get("SizeL")  # width in cm
                                #size_h = artwork.get("SizeH")  # height in cm
                                field_data = artwork.get("fieldData", {})
                                size_l = field_data.get("SizeL")
                                size_h = field_data.get("SizeH")

                                if size_l and size_h:
                                    artwork_width_cm = float(size_l)
                                    artwork_height_cm = float(size_h)
                                    print(
                                        f"[PERSPECTIVE] Using real dimensions: "
                                        f"{artwork_width_cm} x {artwork_height_cm} cm"
                                    )
                            except Exception as e:
                                print("[PERSPECTIVE] Could not parse dimensions:", e)


                        # process_result = process_uploaded_image(
                        #     destination_path,
                        #     artwork_id,
                        #     classification,
                        #     should_generate_perspective=should_generate_perspective
                        # )
                        process_result = process_uploaded_image(
                            destination_path,
                            artwork_id,
                            classification,
                            should_generate_perspective=should_generate_perspective,
                            artwork_width_cm=artwork_width_cm,
                            artwork_height_cm=artwork_height_cm
                        )

                        def public_url_for_local(local_path, subfolder=None):
                            name = os.path.basename(local_path) if local_path else None
                            if not name:
                                return None
                            if subfolder:
                                return f"https://images.operagallery.com/{subfolder}/{_quote(name)}"
                            return f"https://images.operagallery.com/FM/{_quote(name)}"

                        fm_url = public_url_for_local(process_result.get("original"))
                        a5_url = public_url_for_local(process_result.get("a5"), subfolder="A5")
                        thumb_url = public_url_for_local(process_result.get("thumb"), subfolder="Thumb")
                        pers_url = public_url_for_local(process_result.get("perspective"), subfolder="Perspective")
                        web300_url = public_url_for_local(process_result.get("web300"), subfolder="300")
                        maintif_url = None
                        if destination_path.lower().endswith(('.tif', '.tiff')):
                            maintif_url = f"https://images.operagallery.com/FM/{_quote(os.path.basename(destination_path))}"

                    except Exception as e:
                        print("[PROCESSOR ERROR]", e)
                        fm_url = None
                        a5_url = None
                        thumb_url = None
                        pers_url = None
                        maintif_url = None


                # -------------------------
                # Update FileMaker fields (existing helper)
                # -------------------------
                try:

                    # --- MAIN ---
                    if classification == "MAIN":
                        if super_hd_url:
                            filemaker_service.update_specialized_field(
                                artwork_id,
                                "MAIN_HD",
                                super_hd_url
                            )
                        if fm_url:
                            filemaker_service.update_specialized_field(artwork_id, "MAINFM", fm_url)

                        if a5_url:
                            filemaker_service.update_specialized_field(artwork_id, "UrlMainA5", a5_url)

                        if thumb_url:
                            filemaker_service.update_specialized_field(artwork_id, "ThumbnailCrm", thumb_url)

                        if maintif_url:
                            filemaker_service.update_specialized_field(artwork_id, "MAINTIF", maintif_url)
                        if web300_url:
                            filemaker_service.update_specialized_field(artwork_id, "MAIN300", web300_url)

                    # --- OTHER CLASSIFICATIONS ---
                    else:
                        if super_hd_url:
                            filemaker_service.update_specialized_field(
                                artwork_id,
                                "MAIN_HD",
                                super_hd_url
                            )
                        if fm_url:
                            filemaker_service.update_specialized_field(artwork_id, target_field, fm_url)

                        # --- VIDEO: also save MP4 direct URL in companion Url2 field ---
                        if is_video and _mp4_url and target_field and target_field.endswith("Url1"):
                            _mp4_field = target_field[:-1] + "2"  # e.g. VideoPresentationUrl1 → VideoPresentationUrl2
                            filemaker_service.update_specialized_field(artwork_id, _mp4_field, _mp4_url)
                            print(f"[PROCESSOR] FM MP4 URL saved in {_mp4_field}: {_mp4_url}")

                        if thumb_url:
                            filemaker_service.update_specialized_field(artwork_id, "ThumbnailCrm", thumb_url)
                        if web300_url:
                            filemaker_service.update_specialized_field(artwork_id, target_field, web300_url)

                    # --- PERSPECTIVE ---
                        if pers_url:
                            filemaker_service.update_specialized_field(artwork_id, "PERS300", pers_url)

                    print("[VALIDATION] FileMaker updates done.")

                except Exception as e:
                    print(f"[VALIDATION] FileMaker update failed: {e}")
                    
              
                try:
                    from search_operacrm_corrected import OperaCRMClient
                    opera = OperaCRMClient()

                    # Authenticate
                    print(f"[ODOO] Authenticating for {artwork_id} / {classification}...")
                    if opera.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell"):
                        print(f"[ODOO] Auth OK")
                        # 1) SEARCH BY IDNAME
                        records = opera.search_by_idname(artwork_id)


                        # 3) UPDATE RECORD
                        if not records:
                            print(f"[ODOO] Artwork {artwork_id} not found in Odoo search")
                        if records:   # artwork=None means not in FM, but might still be in Odoo
                            r_id = records[0]["id"]
                            update_data = {}

                            # New HR/LR + A6 + 3/4 View scheme (client 2026 spec):
                            # one classification -> one Odoo field.
                            # Review2-aligned classifications (client spec).
                            _NEW_ODOO_FIELD = {
                                "MAIN_HR": "NewMainHR", "MAIN_LR": "NewMainLR",
                                "FRAME": "frame_picture",
                                "BACK": "back_pictures",
                                "BACKFRAME": "back_frame_hr",
                                "SIGN": "signatures_pictures",
                                "DET1": "detail_1_url", "DET2": "detail_2_url",
                                "SCALE": "perspective_url",   # Pers -> Scale
                                "INSITU": "in_situ_hr",
                                "OTHERS": "other_url",
                                "VIEW34": "view_34_hr",       # sculptures
                                # legacy aliases (historical validations)
                                "MAIN": "NewMainHR", "DET": "detail_1_url",
                                "PERS": "perspective_url",
                            }

                            if classification in _NEW_ODOO_FIELD:
                                update_data[_NEW_ODOO_FIELD[classification]] = fm_url
                                if display_name and classification.startswith("OTHERS"):
                                    update_data["other_note"] = display_name
                            elif classification == "MAIN":
                                update_data = {
                                    "main_super_picture_hd": super_hd_url,
                                    "main_picture_hd": fm_url,
                                    "main_web_picture": web300_url,
                                    "main_a6_picture": a5_url,
                                    "image_url": web300_url,
                                    "thumbnail_url": thumb_url,
                                }
                                if pers_url:
                                    update_data["perspective_url"] = pers_url

                            elif classification == "DET":
                                update_data["detail_1_url"] = fm_url

                            elif classification == "DET2":
                                update_data["detail_2_url"] = fm_url

                            elif classification == "DET3":
                                update_data["detail_3_url"] = fm_url

                            elif classification == "LEFT":
                                update_data["left_picture"] = fm_url
                            elif classification in ["RIGHT", "FRONTRIGHT"]:
                                update_data["right_picture"] = fm_url
                            elif classification == "BACK":
                                update_data["back_pictures"] = fm_url
                            elif classification == "PERS":
                                update_data["perspective_url"] = pers_url or fm_url
                            elif classification == "INSITU":
                                update_data["in_situ_url"] = fm_url
                            elif classification == "EDITIONNUMBER":
                                update_data["edition_number_url"] = fm_url
                            elif classification == "OTHER":
                                update_data["other_url"] = fm_url
                            elif classification == "OTHER2":
                                update_data["signatures_pictures"] = a5_url or fm_url
                            elif classification == "FRAME":
                                update_data["frame_picture"] = fm_url
                            elif classification == "SIGN":
                                update_data["signatures_pictures"] = a5_url or fm_url
                            elif classification == "FRONT":
                                update_data["other_url"] = fm_url
                            elif classification.startswith("VIDEO_"):
                            # -------------------------
                            # SAVE VIDEO INTO ODOO - direct field update + media.bunny
                            # -------------------------
                                _VIDEO_FIELD_MAP = {
                                    'VIDEO_PRESENTATION_1': 'VideoPresentationUrl1',
                                    'VIDEO_PRESENTATION_2': 'VideoPresentationUrl2',
                                    'VIDEO_DETAIL_1': 'VideoDetailUrl1',
                                    'VIDEO_DETAIL_2': 'VideoDetailUrl2',
                                    'VIDEO_INSTALLATION_1': 'VideoInstallationUrl1',
                                    'VIDEO_INSTALLATION_2': 'VideoInstallationUrl2',
                                    'VIDEO_TIMELAPSE_1': 'VideoTimelapseUrl1',
                                    'VIDEO_TIMELAPSE_2': 'VideoTimelapseUrl2',
                                    'VIDEO_DOCUMENTARY_1': 'VideoDocumentaryUrl1',
                                    'VIDEO_DOCUMENTARY_2': 'VideoDocumentaryUrl2',
                                    'VIDEO_INTERVIEW_1': 'VideoInterviewUrl1',
                                    'VIDEO_INTERVIEW_2': 'VideoInterviewUrl2',
                                }
                                _video_field = _VIDEO_FIELD_MAP.get(classification)
                                if _video_field:
                                    update_data[_video_field] = fm_url  # HLS URL in Url1
                                    # MP4 direct URL in companion Url2 field
                                    if _mp4_url and _video_field.endswith("Url1"):
                                        _mp4_odoo_field = _video_field[:-1] + "2"
                                        update_data[_mp4_odoo_field] = _mp4_url
                                try:
                                    # HLS streaming record
                                    opera.create("product.media.bunny", {
                                        "product_id": r_id,
                                        "media_type": "video",
                                        "media_url": fm_url,
                                        "media_name": display_name or final_filename,
                                        "is_uploaded": True
                                    })
                                    # MP4 direct download record
                                    if _mp4_url:
                                        opera.create("product.media.bunny", {
                                            "product_id": r_id,
                                            "media_type": "video",
                                            "media_url": _mp4_url,
                                            "media_name": (display_name or final_filename) + " (MP4)",
                                            "is_uploaded": True
                                        })
                                except Exception as e:
                                    print("[ODOO VIDEO ERROR]", e)

                            elif is_pdf:
                                try:
                                    print("[ODOO] Creating PDF media:", {
                                        "product_id": r_id,
                                        "media_type": "image",
                                        "media_url": fm_url,
                                        "media_name": final_filename,
                                        "media_display_name": display_name,
                                        "is_uploaded": True
                                    })

                                    opera.create("product.media.bunny", {
                                        "product_id": r_id,
                                        "media_type": "image",          # PDF accepted as 'image'
                                        "media_url": fm_url,            # direct FM URL
                                        "media_name": final_filename,   # actual filename
                                        "media_display_name": display_name,  # frontend display name
                                        "is_uploaded": True
                                    })

                                except Exception as e:
                                    print("[ODOO PDF ERROR]", e)

                            # 4) APPLY UPDATE
                            # Guard: never send an empty/None value for a field — Odoo's write()
                            # would clear whatever was already stored there. Only push fields we
                            # actually have a real value for, same as the FileMaker branch above.
                            update_data = {k: v for k, v in update_data.items() if v}
                            if update_data:
                                print("[ODOO] REAL-TIME UPDATE:", update_data)
                                opera.update_artwork_record(r_id, update_data)

                    else:
                        print(f"[ODOO] Auth FAILED for {artwork_id}")

                    # Always set message
                    message = f"Photo validée ({classification}) ajoutée dans FileMaker et OperaCRM"

                except Exception as e:
                    print("[ODOO] REAL-TIME UPDATE ERROR:", e)
                    message = f"Photo validée ({classification}) (Odoo error ignored)"

            else:
                os.makedirs(FM_DIR, exist_ok=True)
                destination_path = os.path.join(FM_DIR, final_filename)
                shutil.move(photo_path, destination_path)
                message = f"Photo validée sans ID d'œuvre"

            cursor.execute('''
                INSERT INTO photo_validations
                (photo_id, photo_filename, submitted_by, validated_by, status, classification, artwork_id, display_name, streaming_url, validated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (filename, final_filename, submitted_by, validator_id, 'validated', classification, artwork_id, display_name, streaming_url))

        # ===============================================================
        # ❌ REJECTION BRANCH
        # ===============================================================
        else:
            if not reject_reason:
                conn.close()
                return jsonify({'error': 'Reason for rejection required'}), 400

            os.makedirs(REJECTED_DIR, exist_ok=True)
            destination_path = os.path.join(REJECTED_DIR, filename)
            if os.path.exists(destination_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(os.path.join(REJECTED_DIR, f"{base}_rejected_{counter}{ext}")):
                    counter += 1
                final_filename = f"{base}_rejected_{counter}{ext}"
                destination_path = os.path.join(REJECTED_DIR, final_filename)
            else:
                final_filename = filename

            shutil.move(photo_path, destination_path)
            cursor.execute('''
                INSERT INTO photo_validations 
                (photo_id, photo_filename, submitted_by, validated_by, status, reject_reason, validated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (filename, final_filename, submitted_by, validator_id, 'rejected', reject_reason))
            message = f"Photo rejetée: {reject_reason}"

        # ===============================================================
        # ✅ FINAL COMMIT
        # ===============================================================

        # Append to FM push CSV log on successful validation
        if decision == 'valider' and artwork_id and fm_url:
            try:
                write_header = not os.path.exists(FM_PUSH_CSV)
                with open(FM_PUSH_CSV, 'a', newline='', encoding='utf-8-sig') as _f:
                    _w = csv.writer(_f, delimiter=';')
                    if write_header:
                        _w.writerow(['ID_Artwork', 'FM_Field', 'URL_Pushed', 'Classification', 'Pushed_At'])
                    _w.writerow([artwork_id, target_field, fm_url, classification, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')])
            except Exception as _e:
                print(f"[CSV LOG] Failed to write FM push log: {_e}")

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': message,
            'decision': decision,
            'validator': validator_username,
            'classification': classification if decision == 'valider' else None,
            'reject_reason': reject_reason if decision == 'refuser' else None
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500



@auth_bp.route("/api/photos/preview", methods=["POST"])
def preview_duplicate():
    # data = request.get_json()
    new_local_path = request.args.get("file")
    artwork_id = data.get("artworkId")
    classification = data.get("classification")
    new_local_path = data.get("newLocalPath")  # path of uploaded new file
    old_url = data.get("oldUrl")               # existing FM/Odoo URL

    if not artwork_id or not classification or not new_local_path:
        return jsonify({"error": "Missing parameters"}), 400

    from image_metrics import get_image_metrics
    import os

    # ------- NEW IMAGE METRICS -------
    new_metrics = get_image_metrics(new_local_path)

    # ------- OLD IMAGE METRICS -------
    old_metrics = {}
    old_path = None

    if old_url and old_url.startswith("https://images.operagallery.com/FM/"):
        filename = old_url.split("/")[-1]
        fm_candidate = os.path.join(FM_DIR, filename)
        if os.path.exists(fm_candidate):
            old_path = fm_candidate
            old_metrics = get_image_metrics(fm_candidate)

    return jsonify({
        "duplicate": True,
        "artworkId": artwork_id,
        "classification": classification,
        "existing": {
            "url": old_url,
            "metrics": old_metrics
        },
        "new": {
            "local_path": new_local_path,
            "metrics": new_metrics
        },
        "message": "Duplicate detected. Choose which photo to keep."
    }), 200

# ===================================================
def add_classification_to_filename(filename, classification):
    import os
    import re

    name, ext = os.path.splitext(filename)
    match = re.search(r'([A-Z]+-\d+)', filename)

    if match:
        return f"{match.group(1)}_{classification}{ext}"

    return f"{name}_{classification}{ext}"

@auth_bp.route("/api/photos/duplicate-resolve", methods=["POST"])
def resolve_duplicate():
    data = request.get_json()

    CLASSIFICATION_TO_FIELD = {
        'MAIN':          'MAINFM',
        'MAIN_HR':       'MAINFM',
        'MAIN_LR':       'MAINFM',
        'LEFT':          'LEFT300',
        'RIGHT':         'FRONTRIGHT300',
        'FRONTRIGHT':    'FRONTRIGHT300',
        'BACK':          'BACK300',
        'BACKFRAME':     'BACKFRAME300',
        'PERS':          'PERS300',
        'INSITU':        'INSITU300',
        'EDITIONNUMBER': 'EDITIONNUMBER300',
        'DET':           'DET300',
        'DET1':          'DET300',
        'DET2':          'DET2300',
        'OTHER':         'OTHER300',
        'OTHER2':        'OTHER2300',
        'OTHERS':        'OTHER300',
        'FRAME':         'FRAME300',
        'FRONT':         'FRONT300',
        'SCALE':         'SCALE300',
        "SIGN":          "Signature",

        'CERT_AUTHENTICITY_1': 'CertAuthenticityUrl1',
        'CERT_AUTHENTICITY_2': 'CertAuthenticityUrl2',
        'CATALOG_RAISONNE_1': 'CatalogRaisonneUrl1',
        'CATALOG_RAISONNE_2': 'CatalogRaisonneUrl2',
        'EXHIBITION_CATALOG_1': 'ExhibitionCatalogUrl1',
        'EXHIBITION_CATALOG_2': 'ExhibitionCatalogUrl2',
        'CONDITION_REPORT_1': 'ConditionReportUrl1',
        'CONDITION_REPORT_2': 'ConditionReportUrl2',
        'OTHER_DOCUMENT_1': 'OtherDocumentUrl1',
        'OTHER_DOCUMENT_2': 'OtherDocumentUrl2',

        'VIDEO_PRESENTATION_1': 'VideoPresentationUrl1',
        'VIDEO_PRESENTATION_2': 'VideoPresentationUrl2',
        'VIDEO_DETAIL_1': 'VideoDetailUrl1',
        'VIDEO_DETAIL_2': 'VideoDetailUrl2',
        'VIDEO_INSTALLATION_1': 'VideoInstallationUrl1',
        'VIDEO_INSTALLATION_2': 'VideoInstallationUrl2',
        'VIDEO_TIMELAPSE_1': 'VideoTimelapseUrl1',
        'VIDEO_TIMELAPSE_2': 'VideoTimelapseUrl2',
        'VIDEO_DOCUMENTARY_1': 'VideoDocumentaryUrl1',
        'VIDEO_DOCUMENTARY_2': 'VideoDocumentaryUrl2',
        'VIDEO_INTERVIEW_1': 'VideoInterviewUrl1',
        'VIDEO_INTERVIEW_2': 'VideoInterviewUrl2'
    }

    choice = data.get("choice")
    classification = data.get("classification")
    artwork_id = data.get("artworkId")
    new_file_path = data.get("newFilePath")
    old_url = data.get("oldUrl")
    should_generate_perspective = data.get("generatePerspective", False)

    if not choice or not classification or not artwork_id:
        return jsonify({"error": "Missing fields"}), 400

    import os
    import shutil
    from urllib.parse import quote as _quote
    from image_processor import process_uploaded_image

    # ---------------------------------------------------
    # KEEP OLD
    # ---------------------------------------------------
    if choice == "old":
        if new_file_path and os.path.exists(new_file_path):
            os.remove(new_file_path)
        return jsonify({"success": True, "message": "Old image kept. New discarded."}), 200

    # ---------------------------------------------------
    # KEEP NEW
    # ---------------------------------------------------
    if choice == "new":

        # 1️⃣ delete old FM file
        if old_url and old_url.startswith("https://images.operagallery.com/FM/"):
            old_name = old_url.split("/")[-1]
            old_path = os.path.join(FM_DIR, old_name)
            if os.path.exists(old_path):
                os.remove(old_path)

        # 2️⃣ move new file
        final_name = add_classification_to_filename(
            os.path.basename(new_file_path),
            classification
        )
        final_path = os.path.join(FM_DIR, final_name)
        shutil.move(new_file_path, final_path)

        ext = os.path.splitext(final_name)[1].lower()
        is_pdf = ext == ".pdf"
        is_video = ext in [".mp4", ".mov", ".avi", ".mkv"]

        # ---------------------------------------------------
        # PDF / VIDEO
        # ---------------------------------------------------
        if is_pdf or is_video:
            fm_url = f"https://images.operagallery.com/FM/{_quote(final_name)}"
            filemaker_service.update_specialized_field(
                artwork_id,
                CLASSIFICATION_TO_FIELD[classification],
                fm_url
            )
            return jsonify({"success": True, "message": "PDF / Video replaced successfully"}), 200

        # ---------------------------------------------------
        # 🔥 FETCH DIMENSIONS (FIX)
        # ---------------------------------------------------
        artwork_width_cm = None
        artwork_height_cm = None
        artwork = None

        try:
            artwork = filemaker_service.find_artwork_by_id(artwork_id)
            if artwork:
                field_data = artwork.get("fieldData", {})
                size_l = field_data.get("SizeL")
                size_h = field_data.get("SizeH")
                if size_l and size_h:
                    artwork_width_cm = float(size_l)
                    artwork_height_cm = float(size_h)
                    print(
                        f"[PERSPECTIVE DUPLICATE] "
                        f"{artwork_width_cm} x {artwork_height_cm} cm"
                    )
        except Exception as e:
            print("[PERSPECTIVE DUPLICATE] dimension error:", e)

        # ---------------------------------------------------
        # PROCESS IMAGE (WITH DIMENSIONS)
        # ---------------------------------------------------
        result = process_uploaded_image(
            final_path,
            artwork_id,
            classification,
            should_generate_perspective=should_generate_perspective,
            artwork_width_cm=artwork_width_cm,
            artwork_height_cm=artwork_height_cm
        )

        # ---------------------------------------------------
        # URLS
        # ---------------------------------------------------
        fm_url = f"https://images.operagallery.com/FM/{_quote(os.path.basename(result['original']))}"
        a5_url = f"https://images.operagallery.com/A5/{_quote(os.path.basename(result['a5']))}" if result.get("a5") else None
        thumb_url = f"https://images.operagallery.com/Thumb/{_quote(os.path.basename(result['thumb']))}" if result.get("thumb") else None
        pers_url = f"https://images.operagallery.com/Perspective/{_quote(os.path.basename(result['perspective']))}" if result.get("perspective") else None
        web300_url = None

        if result.get("web300"):
            web300_url = f"https://images.operagallery.com/300/{_quote(os.path.basename(result['web300']))}"

        # ---------------------------------------------------
        # UPDATE FILEMAKER
        # ---------------------------------------------------
        fm_updated = filemaker_service.update_specialized_field(
            artwork_id,
            CLASSIFICATION_TO_FIELD[classification],
            fm_url
        )
        if not fm_updated:
            print(f"[DUPLICATE RESOLVE] WARNING: FM update failed for {artwork_id} field {CLASSIFICATION_TO_FIELD[classification]}")

        if thumb_url:
            filemaker_service.update_specialized_field(artwork_id, "ThumbnailCrm", thumb_url)

        if pers_url:
            filemaker_service.update_specialized_field(artwork_id, "PERS300", pers_url)

        if classification == "MAIN":
            if a5_url:
                filemaker_service.update_specialized_field(artwork_id, "UrlMainA5", a5_url)
            if web300_url:
                filemaker_service.update_specialized_field(artwork_id, "MAIN300", web300_url)

        # ---------------------------------------------------
        # UPDATE ODOO (mirrors normal validation flow)
        # ---------------------------------------------------
        try:
            from search_operacrm_corrected import OperaCRMClient
            opera = OperaCRMClient()
            if opera.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell"):
                records = opera.search_by_idname(artwork_id)
                if records:   # artwork=None means not in FM, but might still be in Odoo
                    r_id = records[0]["id"]
                    update_data = {}

                    if classification == "MAIN":
                        update_data = {
                            "main_picture_hd": fm_url,
                            "main_web_picture": web300_url,
                            "main_a6_picture": a5_url,
                            "image_url": web300_url,
                            "thumbnail_url": thumb_url,
                        }
                        if pers_url:
                            update_data["perspective_url"] = pers_url
                    elif classification == "DET":
                        update_data["detail_1_url"] = fm_url
                    elif classification == "DET2":
                        update_data["detail_2_url"] = fm_url
                    elif classification == "LEFT":
                        update_data["left_picture"] = fm_url
                    elif classification in ["RIGHT", "FRONTRIGHT"]:
                        update_data["right_picture"] = fm_url
                    elif classification == "BACK":
                        update_data["back_pictures"] = fm_url
                    elif classification == "PERS":
                        update_data["perspective_url"] = pers_url or fm_url
                    elif classification == "INSITU":
                        update_data["in_situ_url"] = fm_url
                    elif classification == "EDITIONNUMBER":
                        update_data["edition_number_url"] = fm_url
                    elif classification == "OTHER":
                        update_data["other_url"] = fm_url
                    elif classification == "OTHER2":
                        update_data["signatures_pictures"] = a5_url or fm_url
                    elif classification == "FRAME":
                        update_data["frame_picture"] = fm_url
                    elif classification == "SIGN":
                        update_data["signatures_pictures"] = a5_url or fm_url
                    elif classification == "FRONT":
                        update_data["other_url"] = fm_url
                    elif classification.startswith("VIDEO_"):
                        _VIDEO_FIELD_MAP = {
                            'VIDEO_PRESENTATION_1': 'VideoPresentationUrl1',
                            'VIDEO_PRESENTATION_2': 'VideoPresentationUrl2',
                            'VIDEO_DETAIL_1': 'VideoDetailUrl1',
                            'VIDEO_DETAIL_2': 'VideoDetailUrl2',
                            'VIDEO_INSTALLATION_1': 'VideoInstallationUrl1',
                            'VIDEO_INSTALLATION_2': 'VideoInstallationUrl2',
                            'VIDEO_TIMELAPSE_1': 'VideoTimelapseUrl1',
                            'VIDEO_TIMELAPSE_2': 'VideoTimelapseUrl2',
                            'VIDEO_DOCUMENTARY_1': 'VideoDocumentaryUrl1',
                            'VIDEO_DOCUMENTARY_2': 'VideoDocumentaryUrl2',
                            'VIDEO_INTERVIEW_1': 'VideoInterviewUrl1',
                            'VIDEO_INTERVIEW_2': 'VideoInterviewUrl2',
                        }
                        _video_field = _VIDEO_FIELD_MAP.get(classification)
                        if _video_field:
                            update_data[_video_field] = fm_url

                    # Same guard as the main validation flow: never push an empty/None
                    # value, or Odoo's write() clears whatever was already stored.
                    update_data = {k: v for k, v in update_data.items() if v}
                    if update_data:
                        print("[DUPLICATE RESOLVE] Odoo update:", update_data)
                        opera.update_artwork_record(r_id, update_data)

                    if classification.startswith("VIDEO_"):
                        try:
                            opera.create("product.media.bunny", {
                                "product_id": r_id,
                                "media_type": "video",
                                "media_url": fm_url,
                                "media_name": final_filename,
                                "is_uploaded": True,
                            })
                        except Exception as e:
                            print("[DUPLICATE RESOLVE] bunny create error (ignored):", e)

                try:
                    opera.session.close()
                except Exception:
                    pass
        except Exception as e:
            print(f"[DUPLICATE RESOLVE] Odoo update error (ignored): {e}")

        # ---------------------------------------------------
        # UPDATE DB STATUS: duplicate_pending → validated
        # ---------------------------------------------------
        try:
            import sqlite3
            from auth import DATABASE_PATH
            conn_dup = sqlite3.connect(DATABASE_PATH)
            conn_dup.execute("""
                UPDATE photo_validations
                SET status = 'validated', validated_at = CURRENT_TIMESTAMP
                WHERE (photo_id = ? OR photo_filename LIKE ?)
                  AND status = 'duplicate_pending'
            """, (os.path.basename(new_file_path), f"%{artwork_id}%"))
            conn_dup.commit()
            conn_dup.close()
        except Exception as e:
            print(f"[DUPLICATE RESOLVE] DB status update error (ignored): {e}")

        return jsonify({
            "success": True,
            "message": "Duplicate resolved – new image replaced old",
            "fm_url": fm_url
        }), 200

    return jsonify({"error": "Invalid choice"}), 400


@auth_bp.route('/api/photos/delete-selected-pending', methods=['DELETE'])
def delete_selected_pending_photos():
    try:
        # 🔐 Auth check
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401

        data = request.get_json()
        photo_ids = data.get("photoIds", [])

        if not photo_ids or not isinstance(photo_ids, list):
            return jsonify({"error": "photoIds list required"}), 400

        deleted_count = 0

        for photo_id in photo_ids:
            filename = os.path.basename(photo_id)
            file_path = os.path.join(PENDING_DIR, filename)

            if os.path.exists(file_path) and os.path.isfile(file_path):
                os.remove(file_path)
                deleted_count += 1

        return jsonify({
            "success": True,
            "deleted": deleted_count,
            "message": f"{deleted_count} selected photos deleted successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500




@auth_bp.route('/api/photos/delete-all-pending', methods=['DELETE'])
def delete_all_pending_photos():
    try:
        # 🔐 Auth check
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401

        deleted_count = 0

        if os.path.exists(PENDING_DIR):
            for filename in os.listdir(PENDING_DIR):
                file_path = os.path.join(PENDING_DIR, filename)

                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1

        return jsonify({
            "success": True,
            "deleted": deleted_count,
            "message": f"{deleted_count} pending photos deleted successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route('/api/photos/list', methods=['GET'])
def list_photos():
    """List photos with pagination and filters - WORKING VERSION"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        status = request.args.get('status', 'validated')
        
        # Get ALL validation info
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT photo_filename, status, classification, validated_at,
                   u1.username as validator_username, u2.username as submitter_username,
                   exists_status, pv.streaming_url
            FROM photo_validations pv
            LEFT JOIN users u1 ON pv.validated_by = u1.id
            LEFT JOIN users u2 ON pv.submitted_by = u2.id
        ''')

        validation_lookup = {}
        for row in cursor.fetchall():
            fname = row[0]
            record = {
                'status': row[1], 'classification': row[2], 'validated_at': row[3],
                'validator_username': row[4], 'submitter_username': row[5], 'exists_status': row[6],
                'streaming_url': row[7]
            }
            existing = validation_lookup.get(fname)
            # A filename can have several photo_validations rows (re-uploads,
            # duplicates). Prefer the row whose status matches what we're listing
            # so the displayed metadata is the relevant one.
            if existing is None or (record['status'] == status and existing['status'] != status):
                validation_lookup[fname] = record
        conn.close()
        
        # Scan filesystem directly for ALL file types
        photo_list = []
        status_to_dirs = {
            'validated': ['output', 'FM', 'video'],
            'pending': ['a-valider', 'a-valider-pdf', 'a-valider-video'],
            'rejected': ['refuse'],
            'scheduled': ['scheduled']
        }
        
        dirs_to_check = status_to_dirs.get(status, ['output'])
        
        for target_dir in dirs_to_check:
            dir_path = os.path.join(PHOTOS_BASE_DIR, target_dir)
            
            if os.path.exists(dir_path):
                # Use os.walk to include subdirectories like stats API
                for root, dirs, files in os.walk(dir_path):
                    for filename in files:
                        # Check if file is supported (images, PDFs, videos) and not .eps
                        if is_file_supported(filename):
                            file_type, mime_type, _ = get_file_type_info(filename)
                            if file_type is not None:
                                file_path = os.path.join(root, filename)
                                file_stats = os.stat(file_path)
                                relative_path = os.path.relpath(file_path, PHOTOS_BASE_DIR)
                                validation_info = validation_lookup.get(filename, {})
                                # The directory a file lives in is authoritative for its
                                # status here: dirs_to_check is already scoped to the
                                # requested status and /api/photos/stats counts the same
                                # way. Trusting the DB status instead caused files with
                                # stale/duplicate photo_validations rows (e.g. an old
                                # 'validated' row for a file still sitting in a-valider) to
                                # be filtered out, so the pending tab showed nothing while
                                # the dashboard still counted them.
                                actual_status = status
                                exists_status = validation_info.get('exists_status')
                                
                                # Include all files if requesting validated status OR if file matches status
                                if status == 'validated' or actual_status == status:
                                    import re
                                    artwork_id_match = re.search(r'([A-Z]+-\d+)', filename.upper())
                                    artwork_id = artwork_id_match.group(1) if artwork_id_match else None
                                    
                                    # Use relative path from base directory
                                    #relative_path = os.path.relpath(file_path, PHOTOS_BASE_DIR)
                                    # ------------------------------
                                    # REAL-TIME FM + ODOO EXISTENCE CHECK (ONLY FOR PENDING)
                                    # ------------------------------

                                    
                                    

                                    photo_list.append({
                                        'id': relative_path,
                                        'filename': filename,
                                        'file_type': file_type,
                                        'mime_type': mime_type,
                                        'status': actual_status,
                                        'artwork_id': artwork_id,
                                        'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat() + 'Z',
                                        'modified_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat() + 'Z',
                                        'validated_by': validation_info.get('validator_username'),
                                        'submitted_by': validation_info.get('submitter_username'),
                                        'classification': validation_info.get('classification'),
                                        'validated_at': validation_info.get('validated_at'),
                                        'size': file_stats.st_size,
                                        'reject_reason': None,
                                        'exists_status': exists_status,
                                        'streaming_url': validation_info.get('streaming_url')
                                    })
        
        # Sort by validated_at descending, then by modified_at
        photo_list.sort(key=lambda x: (x.get('validated_at') or '1900-01-01', x['modified_at']), reverse=True)
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_photos = photo_list[start_idx:end_idx]
        
        return jsonify({
            'photos': paginated_photos,
            'total': len(photo_list),
            'page': page,
            'limit': limit,
            'total_pages': (len(photo_list) + limit - 1) // limit
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos-fixed/list', methods=['GET'])
def list_photos_fixed():
    """WORKING VERSION - List all photos from filesystem"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        status = request.args.get('status', 'validated')
        
        # Get ALL validation info
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT photo_filename, status, classification, validated_at,
                   u1.username as validator_username, u2.username as submitter_username
            FROM photo_validations pv
            LEFT JOIN users u1 ON pv.validated_by = u1.id
            LEFT JOIN users u2 ON pv.submitted_by = u2.id
        ''')
        
        validation_lookup = {}
        for row in cursor.fetchall():
            validation_lookup[row[0]] = {
                'status': row[1], 'classification': row[2], 'validated_at': row[3],
                'validator_username': row[4], 'submitter_username': row[5]
            }
        conn.close()
        
        # Scan filesystem directly
        photo_list = []
        status_to_dir = {'validated': 'output', 'pending': 'a-valider', 'rejected': 'refuse'}
        target_dir = status_to_dir.get(status, 'output')
        dir_path = os.path.join(PHOTOS_BASE_DIR, target_dir)
        
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif')):
                    file_path = os.path.join(dir_path, filename)
                    file_stats = os.stat(file_path)
                    
                    validation_info = validation_lookup.get(filename, {})
                    actual_status = validation_info.get('status', status)
                    
                    # Include all files if requesting validated status OR if file matches status
                    if status == 'validated' or actual_status == status:
                        import re
                        artwork_id_match = re.search(r'([A-Z]+-\d+)', filename.upper())
                        artwork_id = artwork_id_match.group(1) if artwork_id_match else None
                        
                        photo_list.append({
                            'id': f'{target_dir}/{filename}',
                            'filename': filename,
                            'status': actual_status,
                            'artwork_id': artwork_id,
                            'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat() + 'Z',
                            'modified_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat() + 'Z',
                            'validated_by': validation_info.get('validator_username'),
                            'submitted_by': validation_info.get('submitter_username'),
                            'classification': validation_info.get('classification'),
                            'validated_at': validation_info.get('validated_at'),
                            'size': file_stats.st_size,
                            'reject_reason': None
                        })
        
        # Sort by validated_at descending, then by modified_at
        photo_list.sort(key=lambda x: (x.get('validated_at') or '1900-01-01', x['modified_at']), reverse=True)
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_photos = photo_list[start_idx:end_idx]
        
        return jsonify({
            'photos': paginated_photos,
            'total': len(photo_list),
            'page': page,
            'limit': limit,
            'total_pages': (len(photo_list) + limit - 1) // limit
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/debug-count')
def debug_count():
    """Debug count - why only 8 photos"""
    import os
    photo_list_length = 0
    validation_data_length = 0
    try:
        # Simulate list_photos exactly
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pv.photo_id, pv.photo_filename, pv.status, pv.classification, pv.validated_at
            FROM photo_validations pv
            LEFT JOIN users u1 ON pv.validated_by = u1.id
            LEFT JOIN users u2 ON pv.submitted_by = u2.id
        ''')
        
        validation_data = {}
        for row in cursor.fetchall():
            validation_data[row[0]] = {'status': row[2], 'validated_at': row[4]}
            if row[1] and row[1] != row[0]:
                validation_data[row[1]] = validation_data[row[0]].copy()
        
        validation_data_length = len(validation_data)
        conn.close()
        
        # Count photos in output directory
        photo_list = []
        dir_path = os.path.join(PHOTOS_BASE_DIR, 'output')
        if os.path.exists(dir_path):
            for root, dirs, files in os.walk(dir_path):
                for filename in files:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif')):
                        validation_info = validation_data.get(filename, {})
                        if validation_info:
                            photo_list.append({'filename': filename})
        
        photo_list_length = len(photo_list)
        
    except Exception as e:
        return jsonify({'error': str(e)})
    
    return jsonify({
        'validation_data_length': validation_data_length,
        'photo_list_length': photo_list_length,
        'image_5_in_validation': len([k for k in validation_data.keys() if 'image_5' in k.lower()]),
        'image_5_in_photo_list': len([p for p in photo_list if 'image_5' in p['filename'].lower()])
    })

@auth_bp.route('/api/photos/by-status/<status>', methods=['GET'])
def get_photos_by_status(status):
    """Get photos by their validation status"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Validate status
        if status not in ['pending', 'validated', 'rejected']:
            return jsonify({'error': 'Invalid status'}), 400
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        # Map status to directory
        status_to_dir = {
            'pending': 'a-valider',
            'validated': 'output',
            'rejected': 'refuse'
        }
        
        photos_dir = PHOTOS_BASE_DIR
        target_dir = status_to_dir[status]
        dir_path = os.path.join(photos_dir, target_dir)
        
        if not os.path.exists(dir_path):
            return jsonify({
                'photos': [],
                'total': 0,
                'page': page,
                'limit': limit,
                'total_pages': 0
            })
        
        # Load validation data from database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get ALL validation records for better matching, filter by status later
        cursor.execute('''
            SELECT pv.photo_id, pv.classification, pv.reject_reason, 
                   pv.validated_at, pv.created_at, pv.status,
                   u1.username as validator_username,
                   u2.username as submitter_username
            FROM photo_validations pv
            LEFT JOIN users u1 ON pv.validated_by = u1.id
            LEFT JOIN users u2 ON pv.submitted_by = u2.id
        ''')
        
        validation_data = {}
        for row in cursor.fetchall():
            photo_id = row[0]
            record_status = row[5]  # Status from database
            
            # Only include records that match the requested status
            if record_status == status:
                validation_data[photo_id] = {
                    'classification': row[1],
                    'reject_reason': row[2],
                    'validated_at': row[3],
                    'created_at': row[4],
                    'status': record_status,
                    'validator_username': row[6],
                    'submitter_username': row[7]
                }
        
        conn.close()
        
        # Get photos from directory
        photo_list = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'}
        
        print(f"\n" + "="*50)
        print(f"[LIST-PHOTOS] Status: {status}")
        print(f"[LIST-PHOTOS] Directory: {dir_path}")
        print(f"[LIST-PHOTOS] Directory exists: {os.path.exists(dir_path)}")
        print(f"[LIST-PHOTOS] Validation records: {len(validation_data)}")
        if os.path.exists(dir_path):
            all_files = os.listdir(dir_path)
            image_files = [f for f in all_files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'))]
            print(f"[LIST-PHOTOS] Total files in dir: {len(all_files)}")
            print(f"[LIST-PHOTOS] Image files in dir: {len(image_files)}")
            if image_files:
                print(f"[LIST-PHOTOS] Image files: {image_files[:5]}")  # Show first 5
        print("="*50)
        
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename.lower())
                if ext in image_extensions:
                    file_stats = os.stat(file_path)
                    relative_path = f"{target_dir}/{filename}"
                    
                    # Get validation info if available - try multiple lookup strategies
                    validation_info = (
                        validation_data.get(filename, {}) or
                        validation_data.get(relative_path, {}) or
                        validation_data.get(os.path.basename(filename), {})
                    )
                    
                    # If no validation info found but we're looking at validated photos,
                    # this might be because the file was renamed after validation
                    # Try to find a record by searching for similar names
                    if not validation_info and status in ['validated', 'rejected']:
                        # Try to find a validation record by searching for patterns
                        base_name = os.path.splitext(filename)[0]
                        
                        # Enhanced pattern matching for better filename correlation
                        for db_key in validation_data.keys():
                            db_base = os.path.splitext(db_key)[0]
                            
                            # Multiple matching strategies
                            matches = [
                                # Exact match
                                base_name == db_base,
                                # One contains the other
                                base_name in db_base or db_base in base_name,
                                # Remove common suffixes and compare
                                base_name.split('_')[0] == db_base.split('_')[0],
                                # Remove all separators and compare
                                base_name.replace('_', '').replace('-', '').replace(' ', '').lower() in 
                                db_base.replace('_', '').replace('-', '').replace(' ', '').lower(),
                                # Check if original filename (without classification) matches
                                db_base.replace('_MAIN', '').replace('_FRAME', '').replace('_DET', '') == base_name
                            ]
                            
                            if any(matches):
                                validation_info = validation_data[db_key]
                                print(f"[MATCH] Found validation for '{filename}' using db_key '{db_key}'")
                                break
                        
                        # If still no validation info, create a default one
                        if not validation_info:
                            validation_info = {
                                'classification': 'UNKNOWN',
                                'validated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat() + 'Z'
                            }
                    
                    # For validated/rejected status, create default validation info if none found
                    # This ensures all files in the directory are shown
                    if status in ['validated', 'rejected'] and not validation_info:
                        validation_info = {
                            'classification': 'UNKNOWN',
                            'validated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat() + 'Z',
                            'status': status
                        }
                    
                    # Extract artwork ID from filename
                    artwork_id = extract_artwork_id_from_filename(filename)
                    
                    photo_list.append({
                        'id': relative_path,
                        'filename': filename,
                        'status': status,
                        'artwork_id': artwork_id,
                        'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat() + 'Z',
                        'modified_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat() + 'Z',
                        'validated_by': validation_info.get('validator_username'),
                        'submitted_by': validation_info.get('submitter_username'),
                        'classification': validation_info.get('classification'),
                        'rejection_reason': validation_info.get('reject_reason'),
                        'validated_at': validation_info.get('validated_at'),
                        'size': file_stats.st_size
                    })
        
        print(f"[LIST-PHOTOS] Found {len(photo_list)} photos in directory")
        
        # Check if image_5 is in the list before sorting
        image_5_before_sort = [p for p in photo_list if 'image_5' in p['filename'].lower()]
        print(f"[LIST-PHOTOS] Image_5 photos before sort: {len(image_5_before_sort)}")
        
        # Sort by modification time (newest first)
        try:
            photo_list.sort(key=lambda x: x['modified_at'], reverse=True)
            print(f"[LIST-PHOTOS] Sorting completed successfully")
        except Exception as sort_error:
            print(f"[LIST-PHOTOS] Sorting error: {sort_error}")
            # Fallback: sort by filename
            photo_list.sort(key=lambda x: x['filename'])
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_photos = photo_list[start_idx:end_idx]
        
        return jsonify({
            'photos': paginated_photos,
            'total': len(photo_list),
            'page': page,
            'limit': limit,
            'total_pages': (len(photo_list) + limit - 1) // limit
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/stats', methods=['GET'])
def get_photo_stats():
    """Get photo validation statistics"""
    try:
        # Count real photos from directories
        photos_dir = PHOTOS_BASE_DIR
        
        stats = {
            'total': 0,
            'pending': 0,
            'validated': 0,
            'rejected': 0,
            'scheduled': 0
        }
        
        # Count files in each directory, including PDFs and videos
        directories = {
            'a-valider': 'pending',
            'a-valider-pdf': 'pending',
            'FM': 'validated',
            'refuse': 'rejected',
            'scheduled': 'scheduled'
        }
        
        for dir_name, status_key in directories.items():
            dir_path = os.path.join(photos_dir, dir_name)
            if os.path.exists(dir_path):
                count = 0
                # Use os.walk to count files in subdirectories too
                for root, dirs, files in os.walk(dir_path):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        if os.path.isfile(file_path) and is_file_supported(filename):
                            # Use get_file_type_info to check if file is supported
                            file_type, _, _ = get_file_type_info(filename)
                            if file_type is not None:  # Any supported file type
                                count += 1
                
                stats[status_key] += count
                stats['total'] += count
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/batch-analyze-quality', methods=['POST'])
def batch_analyze_quality():
    """Analyze quality of all photos in a specified folder"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        folder = data.get('folder', 'a-valider')
        
        # Import quality checker
        from image_quality_checker import ImageQualityChecker
        quality_checker = ImageQualityChecker()
        
        photos_dir = PHOTOS_BASE_DIR
        folder_path = os.path.join(photos_dir, folder)
        
        if not os.path.exists(folder_path):
            return jsonify({'error': f'Folder {folder} not found'}), 404
        
        results = []
        stats = {
            'total': 0,
            'excellent': 0,
            'good': 0,
            'acceptable': 0,
            'poor': 0,
            'error': 0
        }
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'}
        
        # Analyze all images in the folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(filename.lower())
                if ext in image_extensions:
                    try:
                        # Analyze quality
                        quality_result = quality_checker.analyze_image_quality(file_path)
                        
                        result = {
                            'filename': filename,
                            'photo_id': f"{folder}/{filename}",
                            'quality_analysis': quality_result
                        }
                        
                        results.append(result)
                        stats['total'] += 1
                        
                        # Count quality levels
                        quality_level = quality_result.get('quality_level', 'error')
                        if quality_level in stats:
                            stats[quality_level] += 1
                        else:
                            stats['error'] += 1
                            
                    except Exception as e:
                        # Error analyzing this file
                        result = {
                            'filename': filename,
                            'photo_id': f"{folder}/{filename}",
                            'quality_analysis': {
                                'error': f'Analysis error: {str(e)}',
                                'quality_level': 'error'
                            }
                        }
                        results.append(result)
                        stats['total'] += 1
                        stats['error'] += 1
        
        return jsonify({
            'success': True,
            'results': results,
            'stats': stats,
            'folder': folder
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/analyze-single', methods=['POST'])
def analyze_single_photo():
    """Analyze quality of a single uploaded file (image, PDF, video)"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'No authorization token provided'}), 401
        
        from auth import decode_token
        try:
            payload = decode_token(token.split(' ')[1])
            username = payload['username']
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get file type information
        file_type_info = get_file_type_info(file.filename)
        file_type = file_type_info['type']
        
        # Check if file type is supported
        if file_type == 'unknown':
            return jsonify({'error': f'Unsupported file type: {os.path.splitext(file.filename)[1]}'}), 400
        
        # Save file temporarily for analysis
        import tempfile
        import uuid
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        temp_filename = f"temp_{uuid.uuid4().hex}{file_ext}"
        temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
        
        try:
            file.save(temp_path)
            
            # Analyze based on file type
            if file_type == 'image':
                # Analyze the image
                from image_quality_checker import ImageQualityChecker
                quality_checker = ImageQualityChecker()
                analysis = quality_checker.analyze_image_quality(temp_path)
                message = 'Photo analyzed successfully using server-side analysis'
                
            elif file_type == 'pdf':
                # Basic PDF analysis
                file_size = os.path.getsize(temp_path)
                analysis = {
                    'quality_score': 90,  # PDFs are generally high quality
                    'quality_issues': [],
                    'recommendations': [],
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'file_type': 'PDF Document',
                    'pdf_info': f'PDF file ({round(file_size / (1024 * 1024), 2)} MB)'
                }
                message = 'PDF analyzed successfully'
                
            elif file_type == 'video':
                # Basic video analysis
                file_size = os.path.getsize(temp_path)
                analysis = {
                    'quality_score': 85,  # Videos are generally good quality
                    'quality_issues': [],
                    'recommendations': [],
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'file_type': 'Video File',
                    'video_info': f'Video file ({round(file_size / (1024 * 1024), 2)} MB)'
                }
                message = 'Video analyzed successfully'
            
            else:
                analysis = {
                    'quality_score': 75,
                    'quality_issues': [],
                    'recommendations': [],
                    'file_size_mb': round(os.path.getsize(temp_path) / (1024 * 1024), 2),
                    'file_type': 'File'
                }
                message = 'File analyzed successfully'
            
            # Clean up temporary file
            os.remove(temp_path)
            
            return jsonify({
                'success': True,
                'quality_analysis': analysis,
                'message': message,
                'file_type': file_type
            })
            
        except Exception as analysis_error:
            # Clean up temporary file if it exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return jsonify({
                'success': False,
                'error': f'Server analysis failed: {str(analysis_error)}',
                'message': 'The image file may be corrupted or in an unsupported format'
            }), 400
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# COMMENTED OUT - Now using OperaGallery service instead
# @auth_bp.route('/api/artworks/marked-for-processing', methods=['GET'])
def get_marked_artworks_old():
    """Get list of artworks marked for processing - REPLACED BY OPERAGALLERY"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # For now, return empty list
        # In a real implementation, you would query the database
        return jsonify({
            'success': True,
            'marked_artwork_ids': []
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/artworks/<artwork_id>/mark-for-processing', methods=['POST'])
def mark_artwork_for_processing(artwork_id):
    """Mark an artwork for processing"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # For now, just return success
        # In a real implementation, you would update the database
        return jsonify({
            'success': True,
            'message': f'Artwork {artwork_id} marked for processing'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/artworks/<artwork_id>/unmark-for-processing', methods=['POST'])
def unmark_artwork_for_processing(artwork_id):
    """Unmark an artwork for processing"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # For now, just return success
        # In a real implementation, you would update the database
        return jsonify({
            'success': True,
            'message': f'Artwork {artwork_id} unmarked for processing'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# COMMENTED OUT - Now using OperaGallery service instead
# @auth_bp.route('/api/artworks/galleries', methods=['GET'])
def get_galleries_old():
    """Get all available galleries/locations - REPLACED BY OPERAGALLERY"""
    # Real locations extracted from OperaCRM (76 unique locations)
    static_galleries = [
        "ASP",
        "BEI",
        "CUSTOMER - GVA",
        "Consign out",
        "Consign out - ARTIST-MIA",
        "Consign out - ARTIST-SUPPL",
        "Consign out - ASP-SUPPL",
        "Consign out - GVA-SUPPL",
        "Consign out - LON-3RDP",
        "Consign out - LON-SUPPL",
        "Consign out - MAD-CUST",
        "Consign out - MON-CUST",
        "Consign out - PAR-CUST",
        "Consign out - PAR-SUPPL",
        "Consign out SEO",
        "Customer - ASP",
        "Customer - DXB",
        "Customer - ETYGVA",
        "Customer - ETYMIA",
        "Customer - GVA",
        "Customer - HKG",
        "Customer - LON",
        "Customer - MAD",
        "Customer - MIA",
        "Customer - MON",
        "Customer - NYC",
        "Customer - OGBH",
        "Customer - PAR",
        "Customer - SEO",
        "Customer - SIN",
        "DXB",
        "ETYGVA",
        "ETYMIA",
        "GVA",
        "HKG",
        "LON",
        "Local Consign out - ETYMIA-SUPPL",
        "Local Consign out - MIA-SUPPL",
        "Local Consign out - PAR-SUPPL",
        "MAD",
        "MIA",
        "MON",
        "NYC",
        "OGBH",
        "OPA",
        "Owner - DXA",
        "Owner - DXB",
        "Owner - ETYMIA",
        "Owner - ETYPAR",
        "Owner - GVA",
        "Owner - HKG",
        "Owner - LON",
        "Owner - MAD",
        "Owner - MIA",
        "Owner - MON",
        "Owner - NYC",
        "Owner - PAR",
        "Owner - SEO",
        "Owner - SIN",
        "Owner - SUPPL",
        "PAR",
        "PickUp ASP",
        "PickUp DXB",
        "PickUp ETYMIA",
        "PickUp GVA",
        "PickUp HKG",
        "PickUp LON",
        "PickUp MAD",
        "PickUp MIA",
        "PickUp MON",
        "PickUp NYC",
        "PickUp PAR",
        "PickUp SEO",
        "PickUp SIN",
        "SEO",
        "SIN"
    ]
    
    return jsonify({
        'success': True,
        'galleries': static_galleries
    })

# Collaboration endpoints
@auth_bp.route('/api/collaboration/status', methods=['GET'])
def get_collaboration_status():
    """Get collaboration status"""
    try:
        # For now, return empty status
        # In a real implementation, you would query active locks from database
        
        return jsonify({
            'locked_photos': [],
            'active_users': []
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/collaboration/lock', methods=['POST'])
def lock_photo():
    """Lock a photo for editing"""
    try:
        data = request.get_json()
        photo_id = data.get('photoId')
        duration = data.get('duration', 300)
        
        # For now, just return success
        # In a real implementation, you would:
        # 1. Store lock information in database
        # 2. Set expiration time
        # 3. Return lock details
        
        return jsonify({
            'success': True,
            'message': f'Photo {photo_id} locked for {duration} seconds'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/debug/list-photos/<status>', methods=['GET'])
def debug_list_photos(status):
    """Debug endpoint to see what's happening with photo listing"""
    try:
        # Map status to directory
        status_to_dir = {
            'pending': 'a-valider',
            'validated': 'output',
            'rejected': 'refuse'
        }
        
        photos_dir = PHOTOS_BASE_DIR
        target_dir = status_to_dir[status]
        dir_path = os.path.join(photos_dir, target_dir)
        
        result = {
            'status': status,
            'dir_path': dir_path,
            'dir_exists': os.path.exists(dir_path),
            'files_in_dir': [],
            'image_files': [],
            'validation_records': []
        }
        
        if os.path.exists(dir_path):
            result['files_in_dir'] = os.listdir(dir_path)
            
            image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'}
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(filename.lower())
                    if ext in image_extensions:
                        result['image_files'].append(filename)
        
        # Get validation records
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT photo_id, photo_filename, status, classification, validated_at
            FROM photo_validations 
            WHERE status = ?
            ORDER BY validated_at DESC
            LIMIT 10
        ''', (status,))
        
        for row in cursor.fetchall():
            result['validation_records'].append({
                'photo_id': row[0],
                'photo_filename': row[1],
                'status': row[2],
                'classification': row[3],
                'validated_at': row[4]
            })
        
        conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/collaboration/unlock', methods=['POST'])
def unlock_photo():
    """Unlock a photo"""
    try:
        data = request.get_json()
        photo_id = data.get('photoId')
        
        # For now, just return success
        # In a real implementation, you would:
        # 1. Remove lock from database
        # 2. Notify other users
        
        return jsonify({
            'success': True,
            'message': f'Photo {photo_id} unlocked'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/batch', methods=['POST'])
def process_batch():
    """Process multiple photos in batch"""
    try:
        data = request.get_json()
        photo_ids = data.get('photoIds', [])
        decision = data.get('decision')
        reject_reason = data.get('rejectReason')
        
        # For now, just return success
        # In a real implementation, you would:
        # 1. Process each photo according to decision
        # 2. Update database
        # 3. Move/copy files as needed
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(photo_ids)} photos with decision: {decision}',
            'processed_count': len(photo_ids)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/upload', methods=['POST'])
def upload_single_photo():
    """Upload a single photo"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user has upload permission
        user_role = payload.get('role')
        if user_role not in ['uploader', 'admin']:
            return jsonify({'error': 'Permission insuffisante pour uploader'}), 403
        
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        # Validate file type using new multi-format detection
        file_type, mime_type, file_ext = get_file_type_info(file.filename)
        if file_type is None:
            return jsonify({'error': f'File type not supported: {file_ext}. Supported: images, PDFs, videos'}), 400
        
        # Check file size limits
        file_size = len(file.read())
        file.seek(0)  # Reset file pointer
        size_limit = get_file_size_limit(file_type)
        if file_size > size_limit:
            size_mb = file_size / (1024 * 1024)
            limit_mb = size_limit / (1024 * 1024)
            return jsonify({'error': f'File too large: {size_mb:.1f}MB. Max allowed for {file_type}: {limit_mb:.0f}MB'}), 400
        
        # Create specialized directories based on file type
        if file_type == 'image':
            target_dir = PENDING_DIR  # Images go to a-valider as usual
        elif file_type == 'pdf':
            target_dir = os.path.join(PHOTOS_BASE_DIR, 'a-valider-pdf')
        elif file_type == 'video':
            target_dir = os.path.join(PHOTOS_BASE_DIR, 'a-valider-video')
        
        os.makedirs(target_dir, exist_ok=True)
        
        # Generate secure filename - use custom filename if provided
        custom_filename = request.form.get('custom_filename')
        if custom_filename:
            filename = secure_filename(custom_filename)
        else:
            filename = secure_filename(file.filename)
        filepath = os.path.join(target_dir, filename)
        
        # Handle filename conflicts
        counter = 1
        base_name, ext = os.path.splitext(filename)
        while os.path.exists(filepath):
            filename = f"{base_name}_{counter}{ext}"
            filepath = os.path.join(PENDING_DIR, filename)
            counter += 1
        
        # Save file
        file.save(filepath)
        artwork_id = extract_artwork_id_from_filename(filename)
        print("[UPLOAD] artwork_id:", artwork_id)
        
        # File-specific validation
        if file_type == 'image':
            # Validate it's actually an image
            try:
                with Image.open(filepath) as img:
                    img.verify()
            except Exception:
                os.remove(filepath)
                return jsonify({'error': 'Fichier image invalide'}), 400
        elif file_type == 'pdf':
            # Basic PDF validation (just check file starts with PDF header)
            try:
                with open(filepath, 'rb') as f:
                    header = f.read(4)
                    if header != b'%PDF':
                        raise Exception("Not a valid PDF")
            except Exception:
                os.remove(filepath)
                return jsonify({'error': 'Fichier PDF invalide'}), 400
        elif file_type == 'video':
            # For videos, we just trust the extension for now
            # Could add ffmpeg validation later if needed
            print(f"Video file uploaded: {filename} ({file_size} bytes)")
        
        
        exists_status = None
        if artwork_id:
            fm_exists = False
            odoo_exists = False

            # ---- FileMaker check ----
            try:
                fm_record = filemaker_service.find_artwork_by_id(artwork_id)
                if fm_record:
                    fm_exists = True
            except Exception as e:
                print("[UPLOAD] FileMaker error:", e)

            # ---- Odoo check ----
            try:
                operacrm_data = search_artwork_in_odoo_by_id(artwork_id)
                if operacrm_data:
                    odoo_exists = True
            except Exception as e:
                print("[UPLOAD] Odoo error:", e)

            exists_status = "green" if (fm_exists or odoo_exists) else "red"

        print("[UPLOAD] exists_status:", exists_status)
        # Record the upload in database to track who uploaded it
        uploader_username = payload.get('username')
        uploader_id = get_user_id_by_username(uploader_username)
        
        if uploader_id:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Insert record to track the upload with new multi-format fields
            relative_path = os.path.relpath(filepath, PHOTOS_BASE_DIR)
            cursor.execute('''
                INSERT INTO photo_validations 
                (photo_id, photo_filename, file_type, mime_type, file_size, submitted_by, status,exists_status)
                VALUES (?, ?, ?, ?, ?, ?, ?,?)
            ''', (relative_path, filename, file_type, mime_type, file_size, uploader_id, 'pending',exists_status))
            
            conn.commit()
            conn.close()
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'filename': filename,
            'original_filename': file.filename,
            'size': os.path.getsize(filepath),
            'uploaded_by': uploader_username
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/validate-upload-metadata', methods=['POST'])
def validate_upload_with_artwork_search():
    """Validate upload and search for artwork metadata (FileMaker + OperaCRM)"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user has upload permission
        user_role = payload.get('role')
        if user_role not in ['uploader', 'admin']:
            return jsonify({'error': 'Permission insuffisante pour uploader'}), 403
        
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        # Extract artwork ID from filename
        artwork_id = extract_artwork_id_from_filename(file.filename)
        print(f"[VALIDATE-UPLOAD] Extracted artwork_id: {artwork_id} from filename: {file.filename}")
        
        # Basic file validation
        file_type, mime_type, file_ext = get_file_type_info(file.filename)
        if file_type is None:
            return jsonify({'error': f'File type not supported: {file_ext}'}), 400
        
        # Search for artwork metadata
        artwork_found = False
        artwork_metadata = None
        enrichment_status = 'not_found'
        
        if artwork_id:
            print(f"Extracted artwork ID: {artwork_id} from filename: {file.filename}")
            
            # 1. Try FileMaker first in CRMRecordArtworks layout, IdName field
            try:
                from filemaker_service import FileMakerService
                fm_service = FileMakerService()
                
                print(f"[VALIDATE-UPLOAD] Searching FileMaker for IdName = '{artwork_id}'")
                fm_result = fm_service.find_artwork_by_id(artwork_id)
                
                if fm_result:
                    print(f"[VALIDATE-UPLOAD] SUCCESS! Found {artwork_id} in FileMaker!")
                    print(f"[VALIDATE-UPLOAD] FileMaker result: {fm_result}")
                    fm_data = fm_result['fieldData']
                    artwork_found = True
                    enrichment_status = 'filemaker_data'
                    artwork_metadata = {
                        'IdName': fm_data.get('IdName', artwork_id),
                        'title': fm_data.get('Name', 'Titre inconnu'),
                        'artist': fm_data.get('Artists::TotalNameArtist', 'Artiste inconnu'),
                        'year': fm_data.get('Artworkyear'),
                        'category': fm_data.get('Category'),
                        'medium': fm_data.get('Medium'),
                        'source': 'FileMaker'
                    }
                else:
                    print(f"[VALIDATE-UPLOAD] NOT FOUND: {artwork_id} not found in FileMaker CRMRecordArtworks.IdName")
                    
            except Exception as e:
                print(f"[VALIDATE-UPLOAD] FileMaker search ERROR: {e}")
            
            # 2. If not found in FileMaker, try OperaCRM
            if not artwork_found:
                try:
                    operacrm_data = search_artwork_in_odoo_by_id(artwork_id)
                    if operacrm_data:
                        print(f"Artwork {artwork_id} found in OperaCRM!")
                        artwork_found = True
                        enrichment_status = 'operacrm_data'
                        artwork_metadata = {
                            'IdName': operacrm_data.get('name', artwork_id),
                            'title': operacrm_data.get('title', 'Titre inconnu'),
                            'artist': operacrm_data.get('artist_name', 'Artiste inconnu'),
                            'year': operacrm_data.get('year'),
                            'category': operacrm_data.get('category'),
                            'source': 'OperaCRM'
                        }
                except Exception as e:
                    print(f"OperaCRM search failed: {e}")
        
        # Return validation result
        return jsonify({
            'success': True,
            'artwork_id': artwork_id,
            'artwork_found': artwork_found,
            'artwork_metadata': artwork_metadata,
            'enrichment_status': enrichment_status,
            'file_type': file_type,
            'filename': file.filename,
            'upload_recommendation': {
                'should_accept': True,
                'reason': f'File validation passed ({file_type})'
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/batch-upload', methods=['POST'])
def upload_multiple_photos():
    """Upload multiple photos"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user has upload permission
        user_role = payload.get('role')
        if user_role not in ['uploader', 'admin']:
            return jsonify({'error': 'Permission insuffisante pour uploader'}), 403
        
        # Check if files are in request
        if 'files[]' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        files = request.files.getlist('files[]')
        if not files:
            return jsonify({'error': 'No file provided'}), 400
        
        results = {
            'success': [],
            'failed': [],
            'summary': {
                'total': len(files),
                'uploaded': 0,
                'failed': 0
            }
        }
        
        for file in files:
            try:
                if file.filename == '':
                    results['failed'].append({
                        'original_filename': 'Fichier sans nom',
                        'error': 'Nom de fichier vide'
                    })
                    continue
                
                # Validate file type using new multi-format detection
                file_type, mime_type, file_ext = get_file_type_info(file.filename)
                if file_type is None:
                    results['failed'].append({
                        'original_filename': file.filename,
                        'error': f'Type de fichier non autorisé: {file_ext}'
                    })
                    continue
                
                # Check file size limits
                file_size = len(file.read())
                file.seek(0)  # Reset file pointer
                size_limit = get_file_size_limit(file_type)
                if file_size > size_limit:
                    size_mb = file_size / (1024 * 1024)
                    limit_mb = size_limit / (1024 * 1024)
                    results['failed'].append({
                        'original_filename': file.filename,
                        'error': f'Fichier trop volumineux: {size_mb:.1f}MB. Max pour {file_type}: {limit_mb:.0f}MB'
                    })
                    continue
                
                # Create specialized directories based on file type
                if file_type == 'image':
                    target_dir = PENDING_DIR  # Images go to a-valider as usual
                elif file_type == 'pdf':
                    target_dir = os.path.join(PHOTOS_BASE_DIR, 'a-valider-pdf')
                elif file_type == 'video':
                    target_dir = os.path.join(PHOTOS_BASE_DIR, 'a-valider-video')
                
                os.makedirs(target_dir, exist_ok=True)
                
                # Generate secure filename
                filename = secure_filename(file.filename)
                filepath = os.path.join(target_dir, filename)
                
                # Handle filename conflicts
                counter = 1
                base_name, ext = os.path.splitext(filename)
                while os.path.exists(filepath):
                    filename = f"{base_name}_{counter}{ext}"
                    filepath = os.path.join(target_dir, filename)
                    counter += 1
                
                # Save file
                file.save(filepath)
                artwork_id = extract_artwork_id_from_filename(filename)
                
                # File-specific validation (same logic as single upload)
                if file_type == 'image':
                    try:
                        with Image.open(filepath) as img:
                            img.verify()
                    except Exception:
                        os.remove(filepath)
                        results['failed'].append({
                            'original_filename': file.filename,
                            'error': 'Fichier image invalide'
                        })
                        continue
                elif file_type == 'pdf':
                    try:
                        with open(filepath, 'rb') as f:
                            header = f.read(4)
                            if header != b'%PDF':
                                raise Exception("Not a valid PDF")
                    except Exception:
                        os.remove(filepath)
                        results['failed'].append({
                            'original_filename': file.filename,
                            'error': 'Fichier PDF invalide'
                        })
                        continue
                elif file_type == 'video':
                    # For videos, we just trust the extension for now
                    print(f"Video file uploaded: {filename} ({file_size} bytes)")
                
                exists_status = None
                if artwork_id:
                    fm_exists = False
                    odoo_exists = False

                    # ---- FileMaker check ----
                    try:
                        fm_record = filemaker_service.find_artwork_by_id(artwork_id)
                        if fm_record:
                            fm_exists = True
                    except Exception as e:
                        print("[BATCH UPLOAD] FileMaker error:", e)

                    # ---- Odoo / OperaCRM check ----
                    try:
                        operacrm_data = search_artwork_in_odoo_by_id(artwork_id)
                        if operacrm_data:
                            odoo_exists = True
                    except Exception as e:
                        print("[BATCH UPLOAD] Odoo error:", e)

                    exists_status = "green" if (fm_exists or odoo_exists) else "red"
                # Record in database with multi-format fields
                uploader_username = payload.get('username')
                uploader_id = get_user_id_by_username(uploader_username)
                
                if uploader_id:
                    conn = sqlite3.connect(DATABASE_PATH)
                    cursor = conn.cursor()
                    
                    # Insert record with new multi-format fields
                    relative_path = os.path.relpath(filepath, PHOTOS_BASE_DIR)
                    cursor.execute('''
                        INSERT INTO photo_validations 
                        (photo_id, photo_filename, file_type, mime_type, file_size, submitted_by, status,artwork_id,exists_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (relative_path, filename, file_type, mime_type, file_size, uploader_id, 'pending',artwork_id, exists_status))
                    
                    conn.commit()
                    conn.close()
                
                results['success'].append({
                    'original_filename': file.filename,
                    'filename': filename,
                    'file_type': file_type,
                    'mime_type': mime_type,
                    'size': file_size
                })
                results['summary']['uploaded'] += 1
                
            except Exception as e:
                results['failed'].append({
                    'original_filename': file.filename,
                    'error': str(e)
                })
        
        results['summary']['failed'] = len(results['failed'])
        
        return jsonify({
            'success': True,
            'message': f'Upload completed: {results["summary"]["uploaded"]} success, {results["summary"]["failed"]} failures',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/rename', methods=['POST'])
@auth_bp.route('/api/photos/rename', methods=['POST'])
def rename_photo():
    """Rename a photo file"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user has validation permission
        user_role = payload.get('role')
        if user_role not in ['validator', 'admin']:
            return jsonify({'error': 'Permission insuffisante'}), 403
        
        data = request.get_json()
        if not data or 'photoId' not in data or 'newFilename' not in data:
            return jsonify({'error': 'photoId et newFilename requis'}), 400
        
        photo_id = data['photoId']
        new_filename_input = data['newFilename'].strip()

        # -------------------------------------------------
        # 📂 Extract filename from photo_id (EXISTING LOGIC)
        # -------------------------------------------------
        if '/' in photo_id:
            filename = os.path.basename(photo_id)
            directory = os.path.dirname(photo_id)
        else:
            filename = photo_id
            directory = 'a-valider'

        # -------------------------------------------------
        # ✅ Preserve original extension (EXISTING ADD)
        # -------------------------------------------------
        old_name, old_ext = os.path.splitext(filename)
        if not old_ext:
            return jsonify({'error': 'Original file has no extension'}), 400

        new_name_only = os.path.splitext(new_filename_input)[0]
        if not new_name_only or '..' in new_name_only or '/' in new_name_only:
            return jsonify({'error': 'Nom de fichier invalide'}), 400

        new_filename = f"{new_name_only}{old_ext}"

        # Check if photo exists
        old_path = os.path.join(PHOTOS_BASE_DIR, directory, filename)
        if not os.path.exists(old_path):
            return jsonify({'error': 'Photo not found'}), 404
        
        # Check if new filename already exists
        new_path = os.path.join(PHOTOS_BASE_DIR, directory, new_filename)
        if os.path.exists(new_path) and new_path != old_path:
            return jsonify({'error': 'Un fichier avec ce nom existe déjà'}), 409
        
        # Rename the file
        os.rename(old_path, new_path)

        # -------------------------------------------------
        # ✅ ADDED: Update DB so validated image reappears
        # -------------------------------------------------
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE photo_validations
                SET photo_filename = ?
                WHERE photo_filename = ?
                AND status = 'validated'
            """, (new_filename, filename))

            conn.commit()
            conn.close()

            print(f"[RENAME] DB updated: {filename} → {new_filename}")

        except Exception as db_err:
            print("[RENAME] DB update failed:", db_err)
            # ❗ Do NOT rollback rename

        # --------------------------------------------
        # 🔁 OPTIONAL: Sync rename with FileMaker / Odoo
        # --------------------------------------------
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT classification, artwork_id
                FROM photo_validations
                WHERE photo_filename = ?
                AND status = 'validated'
                ORDER BY validated_at DESC
                LIMIT 1
            """, (new_filename,))

            validated_row = cursor.fetchone()
            conn.close()

            if validated_row:
                classification, artwork_id = validated_row

                old_fm_url = f"https://images.operagallery.com/FM/{filename}"
                new_fm_url = f"https://images.operagallery.com/FM/{new_filename}"

                try:
                    from filemaker_service import filemaker_service

                    CLASSIFICATION_TO_FIELD = {
                        'MAIN':          'MAINFM',
                        'LEFT':          'LEFT300',
                        'RIGHT':         'FRONTRIGHT300',
                        'FRONTRIGHT':    'FRONTRIGHT300',
                        'BACK':          'BACK300',
                        'PERS':          'PERS300',
                        'INSITU':        'INSITU300',
                        'EDITIONNUMBER': 'EDITIONNUMBER300',
                        'DET':           'DET300',
                        'DET2':          'DET2300',
                        'OTHER':         'OTHER300',
                        'OTHER2':        'OTHER2300',
                        'FRAME':         'FRAME300',
                        'FRONT':         'FRONT300',
                    }

                    target_field = CLASSIFICATION_TO_FIELD.get(classification)
                    if target_field and artwork_id:
                        filemaker_service.update_specialized_field(
                            artwork_id,
                            target_field,
                            new_fm_url
                        )
                        print("[RENAME SYNC] FileMaker updated")

                except Exception as fm_err:
                    print("[RENAME SYNC] FileMaker update failed:", fm_err)

                try:
                    from search_operacrm_corrected import OperaCRMClient

                    opera = OperaCRMClient()
                    if opera.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell"):
                        records = opera.search_by_idname(artwork_id)
                        if records:
                            r_id = records[0]["id"]

                            _RENAME_ODOO_MAP = {
                                "MAIN":          "main_picture_hd",
                                "LEFT":          "left_picture",
                                "RIGHT":         "right_picture",
                                "FRONTRIGHT":    "right_picture",
                                "BACK":          "back_pictures",
                                "PERS":          "perspective_url",
                                "INSITU":        "in_situ_url",
                                "EDITIONNUMBER": "edition_number_url",
                                "DET":           "detail_1_url",
                                "DET2":          "detail_2_url",
                                "OTHER":         "other_url",
                                "OTHER2":        "signatures_pictures",
                                "FRAME":         "frame_picture",
                                "FRONT":         "other_url",
                                "SIGN":          "signatures_pictures",
                            }
                            _odoo_field = _RENAME_ODOO_MAP.get(classification)
                            update_data = {_odoo_field: new_fm_url} if _odoo_field else {}

                            if update_data:
                                opera.update_artwork_record(r_id, update_data)
                                print("[RENAME SYNC] Odoo updated")

                except Exception as odoo_err:
                    print("[RENAME SYNC] Odoo update failed:", odoo_err)

        except Exception as sync_err:
            print("[RENAME SYNC] Global sync error:", sync_err)

        return jsonify({
            'success': True,
            'message': f'Fichier renommé de {filename} à {new_filename}',
            'old_filename': filename,
            'new_filename': new_filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ancien endpoint supprimé - utiliser /api/artworks/search à la place


def extract_artwork_id_from_filename(filename):
    """
    Extract artwork ID from filename
    Examples: 
    - PICAPA-12345_some_description.jpg -> PICAPA-12345
    - Leger_Fernand_LEGEFE_50346_Visage_à_la_main,_1950,_VERSO.jpg -> LEGEFE_50346
    """
    import re
    
    # Pattern 1: Standard format ARTIST-NUMBER
    pattern1 = r'([A-Z]+[-_]\d+)'
    match1 = re.search(pattern1, filename.upper())
    if match1:
        return match1.group(1).replace('_', '-')
    
    # Pattern 2: Complex format with artist name first
    # Example: Leger_Fernand_LEGEFE_50346_Visage_à_la_main
    pattern2 = r'([A-Z]+_\d+)'
    match2 = re.search(pattern2, filename.upper())
    if match2:
        return match2.group(1).replace('_', '-')
    
    # Pattern 3: Just artist code and number
    pattern3 = r'([A-Z]{5,8})[_-]?(\d+)'
    match3 = re.search(pattern3, filename.upper())
    if match3:
        return f"{match3.group(1)}-{match3.group(2)}"
    
    return None

def search_artwork_in_odoo_by_id(artwork_id):
    """
    Search for a specific artwork in OperaCRM by its ID using JSON-RPC
    """
    try:
        print(f"🔍 Recherche OperaCRM pour artwork_id: {artwork_id}")
        
        # Import OperaCRM client
        from operacrm_service import client
        
        # Ensure client is authenticated
        if not client.session_id:
            if not client.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell"):
                print("❌ Échec de l'authentification OperaCRM")
                return None
        
        # Search by IdName
        results = client.search_by_idname(artwork_id)
        
        if results and len(results) > 0:
            artwork = results[0]
            print(f"✅ Œuvre trouvée dans OperaCRM: {artwork.get('name')}")
            
            # Convert OperaCRM data to expected format
            return {
                'name': artwork.get('IdName', artwork_id),
                'title': artwork.get('name', 'Titre inconnu'),
                'artist_name': artwork.get('ArtistName', 'Artiste inconnu'),
                'year': artwork.get('artwork_year', 'Année inconnue'),
                'medium': artwork.get('Medium', 'Medium inconnu'),
                'dimensions': f"{artwork.get('SizeH', '')} × {artwork.get('SizeL', '')} cm" if artwork.get('SizeH') and artwork.get('SizeL') else 'Dimensions inconnues',
                'description': artwork.get('description', ''),
                'main_picture_hd': f"/api/operacrm/image/{artwork.get('id')}/image_1920" if artwork.get('id') else None,
                'main_picture': f"/api/operacrm/image/{artwork.get('id')}/image_1024" if artwork.get('id') else None,
                'picture_front': f"/api/operacrm/image/{artwork.get('id')}/image_512" if artwork.get('id') else None,
                'picture_back': None,
                'picture_detail': None,
                'picture_signature': None,
                'picture_in_situ': None,
                'price_estimate': f"{artwork.get('artwork_price_combined', artwork.get('PriceRef', 'Non estimé'))} {artwork.get('CurrencyRef', 'EUR')}" if artwork.get('artwork_price_combined') or artwork.get('PriceRef') else 'Non estimé',
                'provenance': artwork.get('artwork_provenance'),
                'exhibition_history': artwork.get('artwork_exhibited')
            }
        else:
            print(f"❌ Aucune œuvre trouvée pour {artwork_id}")
            return None
        
    except Exception as e:
        print(f"Erreur lors de la recherche OperaCRM pour {artwork_id}: {e}")
        return None

def get_mock_artwork_data(artwork_id):
    """
    Generate realistic mock data for artwork when Odoo is not available
    """
    # Specific artworks we know exist
    specific_artworks = {
        'KAWS-46538': {
            'artist_name': 'KAWS',
            'title': 'Companion (Flayed)',
            'medium': 'Vinyl',
            'year': 2016,
            'dimensions': '37 × 28 × 16 cm',
            'description': 'Limited edition vinyl figure from KAWS Companion series',
            'price_estimate': '$8,000 - $12,000'
        },
        'KAWS46538': {
            'artist_name': 'KAWS',
            'title': 'Companion (Flayed)',
            'medium': 'Vinyl',
            'year': 2016,
            'dimensions': '37 × 28 × 16 cm',
            'description': 'Limited edition vinyl figure from KAWS Companion series',
            'price_estimate': '$8,000 - $12,000'
        }
    }
    
    # Check if we have specific data for this artwork
    if artwork_id in specific_artworks:
        specific_data = specific_artworks[artwork_id]
        base_url = 'https://images.unsplash.com/photo-1578321272176-b7bbc0679853?w=800&h=600&fit=crop'
        
        return {
            'name': artwork_id,
            'title': specific_data['title'],
            'artist_name': specific_data['artist_name'],
            'year': specific_data['year'],
            'medium': specific_data['medium'],
            'dimensions': specific_data['dimensions'],
            'description': specific_data['description'],
            'main_picture_hd': base_url,
            'main_picture': base_url.replace('w=800&h=600', 'w=400&h=300'),
            'picture_front': base_url,
            'picture_back': f'{base_url}&seed=back',
            'picture_detail': f'{base_url}&seed=detail',
            'picture_signature': f'{base_url}&seed=signature',
            'picture_in_situ': f'{base_url}&seed=insitu',
            'price_estimate': specific_data['price_estimate']
        }
    
    # Map of known artwork patterns to realistic data
    artwork_patterns = {
        'PICAPA': {
            'artist_name': 'Pablo Picasso',
            'medium': 'Oil on Canvas',
            'year_range': (1900, 1970)
        },
        'LEGEFE': {
            'artist_name': 'Fernand Léger',
            'medium': 'Oil on Canvas',
            'year_range': (1920, 1950)
        },
        'CHAGMA': {
            'artist_name': 'Marc Chagall',
            'medium': 'Oil on Canvas',
            'year_range': (1930, 1980)
        },
        'MIROJO': {
            'artist_name': 'Joan Miró',
            'medium': 'Acrylic on Canvas',
            'year_range': (1940, 1980)
        },
        'KUSAYA': {
            'artist_name': 'Yayoi Kusama',
            'medium': 'Mixed Media',
            'year_range': (1980, 2020)
        },
        'WARHAN': {
            'artist_name': 'Andy Warhol',
            'medium': 'Screenprint',
            'year_range': (1960, 1985)
        },
        'BASQJE': {
            'artist_name': 'Jean-Michel Basquiat',
            'medium': 'Acrylic and Oil on Canvas',
            'year_range': (1980, 1988)
        },
        'HARIKE': {
            'artist_name': 'Keith Haring',
            'medium': 'Acrylic on Canvas',
            'year_range': (1980, 1990)
        },
        'KAWS': {
            'artist_name': 'KAWS',
            'medium': 'Acrylic and Vinyl',
            'year_range': (2000, 2024)
        }
    }
    
    # Extract prefix from artwork ID
    prefix = artwork_id.split('-')[0] if '-' in artwork_id else artwork_id[:6]
    
    # Get pattern data or use default
    pattern_data = artwork_patterns.get(prefix, {
        'artist_name': 'Unknown Artist',
        'medium': 'Mixed Media',
        'year_range': (1950, 2020)
    })
    
    # Generate realistic data
    import random
    year_start, year_end = pattern_data['year_range']
    year = random.randint(year_start, year_end)
    
    # Generate image URLs
    base_url = f'https://images.unsplash.com/photo-{1541961017774 + hash(artwork_id) % 1000000}?w=800&h=600&fit=crop'
    
    return {
        'name': artwork_id,
        'title': f'Artwork {artwork_id}',
        'artist_name': pattern_data['artist_name'],
        'year': year,
        'medium': pattern_data['medium'],
        'dimensions': f'{random.randint(60, 200)} x {random.randint(50, 150)} cm',
        'description': f'Contemporary artwork {artwork_id} from the gallery collection.',
        'main_picture_hd': base_url,
        'main_picture': base_url.replace('w=800&h=600', 'w=400&h=300'),
        'picture_front': base_url,
        'picture_back': f'{base_url}&seed=back',
        'picture_detail': f'{base_url}&seed=detail',
        'picture_signature': f'{base_url}&seed=signature',
        'picture_in_situ': f'{base_url}&seed=insitu',
        'price_estimate': f'${random.randint(10, 500):,},000 - ${random.randint(15, 750):,},000'
    }

def enrich_photo_with_odoo_data(photo):
    """
    Enrich photo data with artwork metadata from Odoo
    """
    try:
        # Extract artwork ID from filename
        artwork_id = extract_artwork_id_from_filename(photo['filename'])
        
        if not artwork_id:
            # No recognizable artwork ID in filename
            return {
                **photo,
                'artwork_id': None,
                'artwork_found': False,
                'enrichment_status': 'no_id_detected',
                'artwork_metadata': None
            }
        
        print(f"Extracted artwork ID: {artwork_id} from filename: {photo['filename']}")
        
        # Search in FileMaker first (layer CRMRecordArtworks, field IdName), then OperaCRM as fallback
        artwork_data = None
        artwork_found = False
        enrichment_status = 'not_found'
        
        # 1. Try FileMaker first in CRMRecordArtworks layout, IdName field
        try:
            from filemaker_service import FileMakerService
            fm_service = FileMakerService()
            # Search in CRMRecordArtworks layout using IdName field
            fm_result = fm_service.search_records(
                layout='CRMRecordArtworks',
                query={'IdName': artwork_id}
            )
            if fm_result and len(fm_result) > 0:
                print(f"Artwork {artwork_id} found in FileMaker CRMRecordArtworks!")
                artwork_data = fm_result[0]  # Take first result
                artwork_found = True
                enrichment_status = 'filemaker_data'
        except Exception as e:
            print(f"FileMaker search failed: {e}")
        
        # 2. If not found in FileMaker, try OperaCRM
        if not artwork_data:
            artwork_data = search_artwork_in_odoo_by_id(artwork_id)
            if artwork_data:
                print(f"Artwork {artwork_id} found in OperaCRM!")
                artwork_found = True
                enrichment_status = 'operacrm_data'
            else:
                print(f"Artwork {artwork_id} not found in OperaCRM either, using mock data")
                artwork_data = get_mock_artwork_data(artwork_id)
                artwork_found = False
                enrichment_status = 'mock_data'
        
        # Build all_image_urls array from Odoo data
        all_image_urls = []
        image_fields = [
            artwork_data.get('main_picture_hd'),
            artwork_data.get('main_picture'),
            artwork_data.get('picture_front'),
            artwork_data.get('picture_back'),
            artwork_data.get('picture_detail'),
            artwork_data.get('picture_signature'),
            artwork_data.get('picture_in_situ')
        ]
        
        for img_url in image_fields:
            if img_url and img_url.strip():
                all_image_urls.append(img_url.strip())
        
        # Enrich photo data
        enriched_photo = {
            **photo,
            'artwork_id': artwork_id,
            'artwork_found': artwork_found,
            'enrichment_status': enrichment_status,
            'artwork_metadata': {
                'IdName': artwork_data.get('name', artwork_id),
                'title': artwork_data.get('title', 'Titre inconnu'),
                'artist': artwork_data.get('artist_name', 'Artiste inconnu'),
                'year': str(artwork_data.get('year', 'Année inconnue')),
                'medium': artwork_data.get('medium', 'Medium inconnu'),
                'dimensions': artwork_data.get('dimensions', 'Dimensions inconnues'),
                'description': artwork_data.get('description', ''),
                'main_picture_hd': artwork_data.get('main_picture_hd'),
                'all_image_urls': all_image_urls,
                'image_count': len(all_image_urls),
                'price_estimate': artwork_data.get('price_estimate', 'Non estimé'),
                'provenance': artwork_data.get('provenance'),
                'exhibition_history': artwork_data.get('exhibition_history')
            }
        }
        
        # Check for potential duplicates
        if artwork_found and all_image_urls:
            enriched_photo['duplicate_warning'] = {
                'has_existing_images': True,
                'existing_image_count': len(all_image_urls),
                'message': f"Attention: Cette œuvre existe déjà dans Odoo avec {len(all_image_urls)} image(s)",
                'recommendation': 'check_duplicate'
            }
        
        return enriched_photo
        
    except Exception as e:
        print(f"Erreur lors de l'enrichissement avec Odoo: {e}")
        # Return original photo data if enrichment fails
        return {
            **photo,
            'artwork_id': None,
            'artwork_found': False,
            'enrichment_status': 'error',
            'enrichment_error': str(e),
            'artwork_metadata': None
        }

def send_rejection_email(user_id, photo_id, reject_reason, validator_username):
    """Send email notification when photo is rejected"""
    try:
        # Get user email
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT username, email FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if not user_data:
            print(f"User {user_id} not found for email notification")
            return
        
        username, email = user_data
        
        # Send actual email using email service
        from email_service import email_service
        
        if email and email.strip():
            success = email_service.send_rejection_email(
                user_email=email,
                username=username,
                photo_id=photo_id,
                reject_reason=reject_reason,
                validator_username=validator_username
            )
            
            if success:
                print(f"✅ Rejection email sent to {username} ({email})")
            else:
                print(f"❌ Failed to send rejection email to {username} ({email})")
        else:
            print(f"⚠️ No email address for user {username}")
        
    except Exception as e:
        print(f"Error sending rejection email: {e}")

def send_validation_email(user_id, photo_id, validator_username, classification):
    """Send email notification when photo is validated"""
    try:
        # Get user email
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT username, email FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if not user_data:
            print(f"User {user_id} not found for email notification")
            return
        
        username, email = user_data
        
        # Send actual email using email service
        from email_service import email_service
        
        if email and email.strip():
            success = email_service.send_validation_email(
                user_email=email,
                username=username,
                photo_id=photo_id,
                validator_username=validator_username,
                classification=classification
            )
            
            if success:
                print(f"✅ Validation email sent to {username} ({email})")
            else:
                print(f"❌ Failed to send validation email to {username} ({email})")
        else:
            print(f"⚠️ No email address for user {username}")
        
    except Exception as e:
        print(f"Error sending validation email: {e}")

def search_artworks_in_odoo(query='', search_type='all', filters=None, page=1, limit=20):
    """
    Search artworks in OperaCRM database with advanced filtering using JSON-RPC
    """
    try:
        print(f"🔍 Recherche OperaCRM - Query: {query}, Type: {search_type}")
        
        # Import OperaCRM client
        from operacrm_service import client
        
        # Ensure client is authenticated
        if not client.session_id:
            if not client.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell"):
                print("❌ Échec de l'authentification OperaCRM")
                return get_mock_artworks_data(query, search_type, filters, page, limit)
        
        # Search based on type
        results = []
        if search_type == 'artist':
            results = client.search_by_artist(query, limit)
        elif search_type == 'artwork_id':
            if query:
                results = client.search_by_idname(query)
                if not results:
                    results = []
        elif search_type == 'title':
            results = client.search_by_artwork_name(query, limit)
        elif search_type == 'category':
            results = client.search_by_category(query, limit)
        else:  # search_type == 'all'
            results = client.search_by_artist(query, limit)
        
        if not results:
            print(f"Aucun résultat OperaCRM trouvé pour '{query}'")
            return []
        
        print(f"✅ {len(results)} résultats trouvés dans OperaCRM")
        
        # Convert OperaCRM data to expected format
        formatted_results = []
        for artwork in results:
            formatted = {
                'id': artwork.get('id'),
                'IdName': artwork.get('IdName', ''),
                'title': artwork.get('name', ''),
                'artist': artwork.get('ArtistName', ''),
                'year': artwork.get('artwork_year', ''),
                'category': artwork.get('Category', ''),
                'medium': artwork.get('Medium', ''),
                'description': artwork.get('description', ''),
                'price_estimate': f"{artwork.get('artwork_price_combined', artwork.get('PriceRef', 'Non estimé'))} {artwork.get('CurrencyRef', 'EUR')}" if artwork.get('artwork_price_combined') or artwork.get('PriceRef') else 'Non estimé',
                'location': artwork.get('Location', ''),
                'status': artwork.get('Status', ''),
                'signed': artwork.get('artwork_signed', ''),
                'provenance': artwork.get('artwork_provenance', ''),
                'exhibited': artwork.get('artwork_exhibited', ''),
                'image_count': 1 if artwork.get('image_1920') else 0,
                'created_date': artwork.get('create_date', ''),
                'updated_date': artwork.get('write_date', ''),
            }
            formatted_results.append(formatted)
        
        return formatted_results
        
    except Exception as e:
        print(f"Erreur lors de la recherche OperaCRM: {e}")
        # Fallback: return mock data if OperaCRM is not available
        return get_mock_artworks_data(query, search_type, filters, page, limit)

def get_mock_artworks_data(query='', search_type='all', filters=None, page=1, limit=20):
    """
    Fallback function that returns mock data when Odoo is not available
    """
    # Générer des données mockées basées sur des patterns réalistes
    mock_artworks = []
    
    # Add specific known artworks first
    specific_artworks = [
        {
            'id': 'KAWS-46538',
            'IdName': 'KAWS-46538',
            'title': 'Companion (Flayed)',
            'artist': 'KAWS',
            'year': '2016',
            'medium': 'Vinyl',
            'dimensions': '37 × 28 × 16 cm',
            'description': 'Limited edition vinyl figure from KAWS Companion series',
            'main_picture_hd': 'https://images.unsplash.com/photo-1578321272176-b7bbc0679853?w=800&h=600&fit=crop',
            'main_picture': 'https://images.unsplash.com/photo-1578321272176-b7bbc0679853?w=400&h=300&fit=crop',
            'picture_front': 'https://images.unsplash.com/photo-1578321272176-b7bbc0679853?w=800&h=600&fit=crop',
            'all_image_urls': [
                'https://images.unsplash.com/photo-1578321272176-b7bbc0679853?w=800&h=600&fit=crop',
                'https://images.unsplash.com/photo-1578321272176-b7bbc0679853?w=800&h=600&fit=crop&seed=back',
                'https://images.unsplash.com/photo-1578321272176-b7bbc0679853?w=800&h=600&fit=crop&seed=detail'
            ],
            'image_count': 3,
            'price_estimate': '$8,000 - $12,000'
        }
    ]
    
    # Check if specific artworks match the search
    for artwork in specific_artworks:
        include = True
        if query:
            query_lower = query.lower()
            if search_type == 'artist':
                include = query_lower in artwork['artist'].lower()
            elif search_type == 'artwork_id':
                include = query_lower in artwork['IdName'].lower()
            elif search_type == 'title':
                include = query_lower in artwork['title'].lower()
            elif search_type == 'all':
                include = (query_lower in artwork['artist'].lower() or 
                         query_lower in artwork['IdName'].lower() or 
                         query_lower in artwork['title'].lower())
        
        if include:
            mock_artworks.append(artwork)
    
    # Simuler 80,000 œuvres avec des patterns réalistes
    artists = [
        'Pablo Picasso', 'Joan Miró', 'Marc Chagall', 'Andy Warhol', 'Yayoi Kusama',
        'Fernand Léger', 'Jean-Michel Basquiat', 'Keith Haring', 'KAWS', 'Banksy',
        'Gerhard Richter', 'Damien Hirst', 'Jeff Koons', 'Takashi Murakami', 'Ed Ruscha',
        'Sam Francis', 'Helen Frankenthaler', 'Cy Twombly', 'Robert Rauschenberg', 'Jasper Johns'
    ]
    
    prefixes = ['PICAPA', 'MIROJO', 'CHAGMA', 'WARHAN', 'KUSAYA', 'LEGEFE', 'BASQJE', 'HARIKE', 'KAWS', 'BANK']
    
    # Générer des œuvres qui matchent la recherche
    import random
    total_generated = 0
    
    print(f"🔍 Recherche - Query: '{query}', Type: '{search_type}', Filtres: {filters}")
    
    # Filtrer les artistes selon la recherche
    matching_artists = artists
    if query and search_type == 'artist':
        query_lower = query.lower()
        matching_artists = [artist for artist in artists if query_lower in artist.lower()]
        print(f"📝 Artistes correspondants: {matching_artists}")
    
    # Si aucun artiste ne correspond, retourner uniquement les œuvres spécifiques
    if query and search_type == 'artist' and not matching_artists:
        print("❌ Aucun artiste ne correspond à la recherche")
        return {
            'success': True,
            'artworks': mock_artworks,  # Seulement les œuvres spécifiques
            'total': len(mock_artworks),
            'page': page,
            'limit': limit,
            'total_pages': (len(mock_artworks) + limit - 1) // limit,
            'note': 'Données simulées - Odoo non disponible'
        }
    
    # Générer les œuvres pour les artistes correspondants  
    for i, artist in enumerate(matching_artists):
        # Secure access to prefixes
        if i < len(prefixes) and artist in artists:
            try:
                prefix = prefixes[artists.index(artist)]
            except (ValueError, IndexError):
                prefix = f"GEN{hash(artist) % 1000:03d}"
        else:
            prefix = f"GEN{hash(artist) % 1000:03d}"
        
        # Générer 10-50 œuvres par artiste correspondant
        num_artworks = random.randint(10, 50)
        for i in range(1, num_artworks + 1):
            artwork_id = f'{prefix}-{i:05d}'
            title = f'Artwork {i} by {artist.split()[1] if len(artist.split()) > 1 else artist}'
            
            # Appliquer les filtres de recherche pour les autres types
            include = True
            
            if query and search_type != 'artist':  # Artist déjà filtré
                query_lower = query.lower()
                if search_type == 'artwork_id':
                    include = query_lower in artwork_id.lower()
                elif search_type == 'title':
                    include = query_lower in title.lower()
                elif search_type == 'all':
                    include = (query_lower in artist.lower() or 
                             query_lower in artwork_id.lower() or 
                             query_lower in title.lower())
            
            if not include:
                continue
                
            # Appliquer les filtres
            year = 1950 + (i % 70)
            if filters and filters.get('year'):
                year_filter = filters['year']
                if '-' in year_filter:
                    try:
                        start_year, end_year = map(int, year_filter.split('-'))
                        if not (start_year <= year <= end_year):
                            continue
                    except ValueError:
                        pass
                elif year_filter not in str(year):
                    continue
            
            medium = ['Oil on Canvas', 'Acrylic', 'Mixed Media', 'Sculpture', 'Digital Print'][i % 5]
            if filters and filters.get('medium'):
                if filters['medium'].lower() not in medium.lower():
                    continue
            
            # Générer des URLs d'images
            base_url = f'https://images.unsplash.com/photo-{1541961017774 + i}?w=800&h=600&fit=crop'
            all_image_urls = [
                base_url,
                f'{base_url}&seed=back',
                f'{base_url}&seed=detail'
            ]
            
            if filters and filters.get('hasImages') and not all_image_urls:
                continue
            
            artwork = {
                'id': artwork_id,
                'IdName': artwork_id,
                'title': title,
                'artist': artist,
                'year': str(year),
                'medium': medium,
                'dimensions': f'{100 + (i % 50)} x {80 + (i % 40)} cm',
                'description': f'Contemporary artwork {artwork_id} from the gallery collection.',
                'main_picture_hd': base_url,
                'main_picture': base_url.replace('w=800&h=600', 'w=400&h=300'),
                'picture_front': base_url,
                'picture_back': f'{base_url}&seed=back',
                'picture_detail': f'{base_url}&seed=detail',
                'picture_signature': f'{base_url}&seed=signature',
                'picture_in_situ': f'{base_url}&seed=insitu',
                'all_image_urls': all_image_urls,
                'image_count': len(all_image_urls),
                'price_estimate': f'${(i * 1000):,} - ${(i * 1500):,}'
            }
            
            mock_artworks.append(artwork)
            total_generated += 1
            
            # Limiter le nombre total pour éviter la surcharge
            if total_generated >= 1000:
                break
        
        if total_generated >= 1000:
            break
    
    # Appliquer la pagination
    total_results = len(mock_artworks)
    start_index = (page - 1) * limit
    end_index = start_index + limit
    paginated_artworks = mock_artworks[start_index:end_index]
    
    return {
        'success': True,
        'artworks': paginated_artworks,
        'total': total_results,
        'page': page,
        'limit': limit,
        'total_pages': (total_results + limit - 1) // limit,
        'note': 'Données simulées - Odoo non disponible'
    }

# Conflicting route commented out - using OperaCRM service for searches
# @auth_bp.route('/api/artworks/search', methods=['GET', 'POST'])
# def search_artworks():
#     """Advanced artwork search engine with multiple criteria"""
#     try:
#         # Check authorization
#         token = request.headers.get('Authorization')
#         if not token or not token.startswith('Bearer '):
#             return jsonify({'error': 'Missing token'}), 401
#         
#         token = token.split(' ')[1]
#         payload = verify_token(token)
#         if not payload:
#             return jsonify({'error': 'Invalid token'}), 401
#         
#         # Handle both GET and POST requests
#         if request.method == 'POST':
#             data = request.get_json()
#             if not data:
#                 return jsonify({'error': 'Données manquantes'}), 400
#             query = data.get('query', '').strip()
#             search_type = data.get('searchType', 'all')
#             page = data.get('page', 1)
#             limit = data.get('limit', 20)
#             filters = data.get('filters', {})
#         else:  # GET request
#             query = request.args.get('query', '').strip()
#             search_type = request.args.get('searchType', 'all')
#             page = int(request.args.get('page', 1))
#             limit = int(request.args.get('limit', 20))
#             filters = {}
#         
#         print(f"🔍 Recherche artworks - Query: '{query}', Type: '{search_type}'")
#         
#         # Use OperaCRM API to search artworks
#         artworks_from_odoo = search_artworks_in_odoo(
#             query=query,
#             search_type=search_type,
#             filters=filters,
#             page=page,
#             limit=limit
#         )
#         
#         # Format response for frontend compatibility
#         if isinstance(artworks_from_odoo, list):
#             return jsonify({
#                 'success': True,
#                 'artworks': artworks_from_odoo,
#                 'total': len(artworks_from_odoo)
#             })
#         else:
#             return jsonify(artworks_from_odoo)
#         
#     except Exception as e:
#         print(f"Erreur recherche artworks: {e}")
#         import traceback
#         traceback.print_exc()
#         return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/legacy/artworks/search', methods=['GET', 'POST'])
def search_artworks_legacy():
    """Advanced artwork search engine with multiple criteria"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Handle both GET and POST requests
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Données manquantes'}), 400
            query = data.get('query', '').strip()
            search_type = data.get('searchType', 'all')
            page = data.get('page', 1)
            limit = data.get('limit', 20)
            filters = data.get('filters', {})
        else:  # GET request
            query = request.args.get('query', '').strip()
            search_type = request.args.get('searchType', 'all')
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 20))
            filters = {}
        
        # Use Odoo API to search artworks
        artworks_from_odoo = search_artworks_in_odoo(
            query=query,
            search_type=search_type,
            filters=filters,
            page=page,
            limit=limit
        )
        
        return jsonify(artworks_from_odoo)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
def send_rejection_email_end():
    pass

@auth_bp.route('/api/photos/<path:photo_id>/history', methods=['GET'])
def get_photo_history(photo_id):
    """Get validation history for a specific photo"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Extract filename from photo_id if it contains path
        if '/' in photo_id:
            filename = os.path.basename(photo_id)
        else:
            filename = photo_id
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get validation history with user details
        cursor.execute('''
            SELECT pv.status, pv.classification, pv.reject_reason, pv.validated_at,
                   u1.username as validator_username,
                   u2.username as submitter_username
            FROM photo_validations pv
            LEFT JOIN users u1 ON pv.validated_by = u1.id
            LEFT JOIN users u2 ON pv.submitted_by = u2.id
            WHERE pv.photo_id = ?
            ORDER BY pv.validated_at DESC
        ''', (filename,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'status': row[0],
                'classification': row[1],
                'reject_reason': row[2],
                'validated_at': row[3],
                'validator_username': row[4],
                'submitter_username': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'photo_id': photo_id,
            'history': history
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/validations/recent', methods=['GET'])
def get_recent_validations():
    """Get recent validation activities"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get recent validations with user details
        cursor.execute('''
            SELECT pv.photo_id, pv.photo_filename, pv.status, pv.classification, 
                   pv.reject_reason, pv.validated_at,
                   u1.username as validator_username,
                   u2.username as submitter_username
            FROM photo_validations pv
            LEFT JOIN users u1 ON pv.validated_by = u1.id
            LEFT JOIN users u2 ON pv.submitted_by = u2.id
            ORDER BY pv.validated_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        validations = []
        for row in cursor.fetchall():
            validations.append({
                'photo_id': row[0],
                'photo_filename': row[1],
                'status': row[2],
                'classification': row[3],
                'reject_reason': row[4],
                'validated_at': row[5],
                'validator_username': row[6],
                'submitter_username': row[7]
            })
        
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM photo_validations')
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'validations': validations,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/users', methods=['GET'])
def get_users():
    """Get all users with details"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user is admin
        user_role = payload.get('role')
        if user_role != 'admin':
            return jsonify({'error': 'Permission insuffisante'}), 403
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all users with statistics
        cursor.execute('''
            SELECT u.id, u.username, u.email, u.role, u.created_at,
                   COUNT(pv.id) as validation_count,
                   COUNT(CASE WHEN pv.status = 'validated' THEN 1 END) as validated_count,
                   COUNT(CASE WHEN pv.status = 'rejected' THEN 1 END) as rejected_count
            FROM users u
            LEFT JOIN photo_validations pv ON u.id = pv.validated_by
            GROUP BY u.id, u.username, u.email, u.role, u.created_at
            ORDER BY u.username
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'role': row[3],
                'created_at': row[4],
                'validation_count': row[5],
                'validated_count': row[6],
                'rejected_count': row[7]
            })
        
        conn.close()
        
        return jsonify({'users': users})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user details"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user is admin
        user_role = payload.get('role')
        if user_role != 'admin':
            return jsonify({'error': 'Permission insuffisante'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données requises'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Update user fields
        updates = []
        params = []
        
        if 'username' in data:
            # Check if username already exists for other users
            cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (data['username'], user_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'Ce nom d\'utilisateur existe déjà'}), 409
            updates.append('username = ?')
            params.append(data['username'])
        
        if 'role' in data:
            if data['role'] not in ['admin', 'validator', 'uploader']:
                conn.close()
                return jsonify({'error': 'Invalid role'}), 400
            updates.append('role = ?')
            params.append(data['role'])
        
        if 'password' in data and data['password']:
            from auth import hash_password
            hashed_password = hash_password(data['password'])
            updates.append('password = ?')
            params.append(hashed_password)
        
        if 'email' in data:
            updates.append('email = ?')
            params.append(data['email'])
        
        if not updates:
            conn.close()
            return jsonify({'error': 'Aucune donnée à mettre à jour'}), 400
        
        # Perform update
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user is admin
        user_role = payload.get('role')
        if user_role != 'admin':
            return jsonify({'error': 'Permission insuffisante'}), 403
        
        data = request.get_json()
        if not data or not all(k in data for k in ['username', 'password', 'role']):
            return jsonify({'error': 'Username, password et role requis'}), 400
        
        username = data['username']
        password = data['password']
        email = data.get('email', None)  # Email is optional
        role = data['role']
        
        if role not in ['admin', 'validator', 'uploader']:
            return jsonify({'error': 'Rôle invalide'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must contain at least 6 characters'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Ce nom d\'utilisateur existe déjà'}), 409
        
        # Create user
        from auth import hash_password
        hashed_password = hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (username, password, email, role)
            VALUES (?, ?, ?, ?)
        ''', (username, hashed_password, email, role))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user_id': user_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user is admin
        user_role = payload.get('role')
        if user_role != 'admin':
            return jsonify({'error': 'Permission insuffisante'}), 403
        
        # Prevent admin from deleting themselves
        current_user_id = payload.get('user_id')
        if current_user_id == user_id:
            return jsonify({'error': 'Vous ne pouvez pas supprimer votre propre compte'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Delete user
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'User {user[0]} deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/users/<int:user_id>/send-password', methods=['POST'])
def send_user_password(user_id):
    """Send password to user via email"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user is admin
        user_role = payload.get('role')
        if user_role != 'admin':
            return jsonify({'error': 'Permission insuffisante'}), 403
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get user details
        cursor.execute('SELECT username, email FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        username, email = user_data
        
        # Check if user has email
        if not email:
            conn.close()
            return jsonify({'error': 'Utilisateur sans email configuré'}), 400
        
        # Generate new password
        import secrets
        import string
        
        # Generate secure password: 12 characters with letters, digits and some symbols
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        # Hash and update password in database
        from auth import hash_password
        hashed_password = hash_password(new_password)
        
        cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
        conn.commit()
        conn.close()
        
        # Send password via email
        try:
            subject = "Your OperaGallery Login Credentials"
            html_content = f"""
            <html>
            <body>
                <h2>Your OperaGallery Login Credentials</h2>
                <p>Hello,</p>
                <p>Here are your credentials to access the OperaGallery Photo Validator system:</p>
                
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Username:</strong> <code style="background: white; padding: 4px 8px; border-radius: 4px;">{username}</code></p>
                    <p><strong>Password:</strong> <code style="background: white; padding: 4px 8px; border-radius: 4px; color: #dc2626; font-weight: bold;">{new_password}</code></p>
                </div>
                
                <div style="background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>🔒 Two-Factor Authentication Required</strong></p>
                    <p>For enhanced security, this system now requires two-factor authentication (2FA) using an authenticator app.</p>
                    
                    <p><strong>Before your first login, please:</strong></p>
                    <ol>
                        <li>Install an authenticator app on your smartphone:
                            <ul>
                                <li><strong>Google Authenticator</strong> (recommended)</li>
                                <li><strong>Microsoft Authenticator</strong></li>
                                <li>Or any other TOTP-compatible app</li>
                            </ul>
                        </li>
                        <li>Log in with your username and password</li>
                        <li>Follow the on-screen setup process to configure 2FA</li>
                        <li>Scan the QR code displayed with your authenticator app</li>
                        <li>Complete the setup by entering a verification code</li>
                    </ol>
                    
                    <p><em>Note: The 2FA setup is mandatory and will be completed during your first login process.</em></p>
                </div>
                
                <p><strong>Important:</strong></p>
                <ul>
                    <li>This password has been automatically generated</li>
                    <li>We recommend changing it after your first login</li>
                    <li>Keep these credentials confidential</li>
                    <li>Prepare your authenticator app before attempting to log in</li>
                </ul>
                
                <p>Login at: <a href="https://das.operagallery.com">https://das.operagallery.com</a></p>
                
                <hr>
                <p style="color: #6b7280; font-size: 12px;">
                    OperaGallery Photo Validator - User Management<br>
                    This email was sent automatically, please do not reply.
                </p>
            </body>
            </html>
            """
            
            result = email_service.send_email(
                to=email,
                subject=subject,
                html_content=html_content
            )
            
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': f'Nouveau mot de passe envoyé à {email}'
                })
            else:
                return jsonify({'error': 'Échec de l\'envoi de l\'email'}), 500
                
        except Exception as e:
            print(f"[SEND PASSWORD] Error sending email: {str(e)}")
            return jsonify({'error': 'Erreur lors de l\'envoi de l\'email'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Photo Marking Endpoints
@auth_bp.route('/api/photos/mark', methods=['POST'])
def mark_photo():
    """Mark/unmark a photo for the current user"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        data = request.get_json()
        
        if not data or 'photo_id' not in data:
            return jsonify({'error': 'Photo ID required'}), 400
        
        photo_id = data['photo_id']
        photo_filename = data.get('photo_filename', '')
        note = data.get('note', '')
        action = data.get('action', 'toggle')  # 'mark', 'unmark', 'toggle'
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if photo is already marked
        cursor.execute('''
            SELECT id FROM photo_marks 
            WHERE user_id = ? AND photo_id = ?
        ''', (user_id, photo_id))
        
        existing_mark = cursor.fetchone()
        
        if action == 'toggle':
            if existing_mark:
                # Unmark the photo
                cursor.execute('''
                    DELETE FROM photo_marks 
                    WHERE user_id = ? AND photo_id = ?
                ''', (user_id, photo_id))
                is_marked = False
                message = 'Photo unmarked'
            else:
                # Mark the photo
                cursor.execute('''
                    INSERT INTO photo_marks (user_id, photo_id, photo_filename, note)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, photo_id, photo_filename, note))
                is_marked = True
                message = 'Photo marked'
        
        elif action == 'mark':
            if existing_mark:
                # Update existing mark
                cursor.execute('''
                    UPDATE photo_marks 
                    SET note = ?, marked_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND photo_id = ?
                ''', (note, user_id, photo_id))
                message = 'Photo mark updated'
            else:
                # Create new mark
                cursor.execute('''
                    INSERT INTO photo_marks (user_id, photo_id, photo_filename, note)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, photo_id, photo_filename, note))
                message = 'Photo marked'
            is_marked = True
            
        elif action == 'unmark':
            cursor.execute('''
                DELETE FROM photo_marks 
                WHERE user_id = ? AND photo_id = ?
            ''', (user_id, photo_id))
            is_marked = False
            message = 'Photo unmarked'
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': message,
            'is_marked': is_marked,
            'photo_id': photo_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/marked', methods=['GET'])
def get_marked_photos():
    """Get all marked photos for the current user"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        
        # Pagination
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute('''
            SELECT COUNT(*) FROM photo_marks 
            WHERE user_id = ?
        ''', (user_id,))
        total = cursor.fetchone()[0]
        
        # Get marked photos with pagination
        cursor.execute('''
            SELECT pm.photo_id, pm.photo_filename, pm.note, pm.marked_at,
                   pv.classification, pv.status, pv.reject_reason
            FROM photo_marks pm
            LEFT JOIN photo_validations pv ON pm.photo_id = pv.photo_id
            WHERE pm.user_id = ?
            ORDER BY pm.marked_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))
        
        marked_photos = []
        for row in cursor.fetchall():
            photo_data = {
                'photo_id': row[0],
                'photo_filename': row[1],
                'note': row[2],
                'marked_at': row[3],
                'classification': row[4],
                'status': row[5],
                'reject_reason': row[6]
            }
            marked_photos.append(photo_data)
        
        conn.close()
        
        total_pages = (total + limit - 1) // limit
        
        return jsonify({
            'success': True,
            'marked_photos': marked_photos,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': total_pages
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/<path:photo_id>/mark-status', methods=['GET'])
def get_mark_status(photo_id):
    """Check if a photo is marked by the current user"""
    try:
        # Decode the photo_id in case it was URL encoded
        from urllib.parse import unquote
        photo_id = unquote(photo_id)
        
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT note, marked_at FROM photo_marks 
            WHERE user_id = ? AND photo_id = ?
        ''', (user_id, photo_id))
        
        mark = cursor.fetchone()
        conn.close()
        
        if mark:
            return jsonify({
                'success': True,
                'is_marked': True,
                'note': mark[0],
                'marked_at': mark[1]
            })
        else:
            return jsonify({
                'success': True,
                'is_marked': False
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/photos/cache/warmup', methods=['POST'])
def warmup_cache():
    """Pre-generate thumbnails for pending photos to improve loading speed"""
    try:
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get pending photos
        photos_dir = PHOTOS_BASE_DIR
        pending_dir = os.path.join(photos_dir, 'a-valider')
        
        if not os.path.exists(pending_dir):
            return jsonify({'error': 'Pending directory not found'}), 404
        
        # Create thumbnail cache directory
        cache_dir = os.path.join(photos_dir, '..', 'cache', 'thumbnails')
        os.makedirs(cache_dir, exist_ok=True)
        
        thumbnails_created = 0
        thumbnails_skipped = 0
        errors = []
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'}
        
        for root, dirs, files in os.walk(pending_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(filename.lower())
                    if ext in image_extensions:
                        try:
                            # Generate cache filename
                            base_name = os.path.splitext(filename)[0]
                            cache_filename = f"{base_name}_thumb.jpg"
                            cache_path = os.path.join(cache_dir, cache_filename)
                            
                            # Create thumbnail if it doesn't exist or is older than original
                            if not os.path.exists(cache_path) or os.path.getmtime(file_path) > os.path.getmtime(cache_path):
                                from PIL import Image
                                with Image.open(file_path) as img:
                                    # Convert to RGB if necessary
                                    if img.mode in ('RGBA', 'P'):
                                        img = img.convert('RGB')
                                    
                                    # Create thumbnail (400x400px max)
                                    img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                                    
                                    # Save with good quality but compressed
                                    img.save(cache_path, 'JPEG', quality=80, optimize=True)
                                    thumbnails_created += 1
                            else:
                                thumbnails_skipped += 1
                                
                        except Exception as e:
                            errors.append(f"Error processing {filename}: {str(e)}")
                            continue
        
        return jsonify({
            'success': True,
            'thumbnails_created': thumbnails_created,
            'thumbnails_skipped': thumbnails_skipped,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# User Profile Management Endpoints
# =============================================================================
@auth_bp.route('/api/user/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        username = payload.get('username')
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing data'}), 400
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Validate new password strength
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters long'}), 400
        
        # Verify current password
        from auth import verify_password, hash_password
        if not verify_password(username, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password in database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        hashed_new_password = hash_password(new_password)
        cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_new_password, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/user/update', methods=['PUT'])
def update_user_profile():
    """Update user profile (username, email)"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing data'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if 'username' in data and data['username']:
            # Check if username already exists
            cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (data['username'], user_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': 'Username already exists'}), 409
            updates.append('username = ?')
            params.append(data['username'])
        
        if 'email' in data:
            updates.append('email = ?')
            params.append(data['email'])
        
        if updates:
            params.append(user_id)
            cursor.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = ?', params)
            conn.commit()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/user/stats', methods=['GET'])
def get_user_stats():
    """Get user statistics"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get user stats
        cursor.execute('SELECT COUNT(*) FROM photo_validations WHERE submitted_by = ?', (user_id,))
        uploaded = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM photo_validations WHERE validated_by = ?', (user_id,))
        validated = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM photo_validations WHERE validated_by = ? AND status = "rejected"', (user_id,))
        rejected = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM photo_validations WHERE submitted_by = ? AND status = "pending"', (user_id,))
        pending = cursor.fetchone()[0]
        
        # Get recent activity
        cursor.execute('''
            SELECT status, validated_at, photo_filename
            FROM photo_validations 
            WHERE submitted_by = ? OR validated_by = ?
            ORDER BY validated_at DESC 
            LIMIT 10
        ''', (user_id, user_id))
        
        recent_activity = []
        for row in cursor.fetchall():
            status, date, filename = row
            if status == 'validated':
                activity_type = 'validate'
                description = f'Validated {filename}'
            elif status == 'rejected':
                activity_type = 'reject'
                description = f'Rejected {filename}'
            else:
                activity_type = 'upload'
                description = f'Uploaded {filename}'
            
            recent_activity.append({
                'type': activity_type,
                'description': description,
                'date': date
            })
        
        conn.close()
        
        return jsonify({
            'uploaded': uploaded,
            'validated': validated,
            'rejected': rejected,
            'pending': pending,
            'recent_activity': recent_activity
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# TOTP (Authenticator App) Endpoints
# =============================================================================

@auth_bp.route('/api/auth/totp/setup', methods=['POST'])
def setup_totp():
    """Generate TOTP secret and QR code for user"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        username = payload.get('username')
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT two_factor_enabled FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()

        # ❌ If 2FA is disabled, block setup
        if row is not None and row[0] == 0:
            return jsonify({
                'success': False,
                'error': 'Two-factor authentication is disabled'
            }), 403
        
        # Generate new TOTP secret
        secret = totp_service.generate_secret()
        
        # Generate QR code
        qr_code_data = totp_service.generate_qr_code(secret, username)
        
        # Generate backup codes
        backup_codes = totp_service.get_backup_codes()
        
        # Store secret in database (but don't enable TOTP yet)
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET totp_secret = ?, totp_enabled = 0 
            WHERE id = ?
        ''', (secret, user_id))
        
        # Clear old backup codes and add new ones
        cursor.execute('DELETE FROM user_backup_codes WHERE user_id = ?', (user_id,))
        for code in backup_codes:
            cursor.execute('''
                INSERT INTO user_backup_codes (user_id, code) 
                VALUES (?, ?)
            ''', (user_id, code))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'secret': secret,  # For manual entry
            'qr_code': qr_code_data,
            'backup_codes': backup_codes,
            'message': 'Scan the QR code with your authenticator app, then verify with a code to enable 2FA'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@auth_bp.route('/api/auth/totp/verify', methods=['POST'])
def verify_totp():
    """Verify TOTP code and enable 2FA"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({'error': 'TOTP code required'}), 400
        
        totp_code = data['code'].strip().replace(' ', '')
        
        # Get user's TOTP secret
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT totp_secret FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            conn.close()
            return jsonify({'error': 'TOTP not set up. Please set up TOTP first.'}), 400
        
        secret = result[0]
        
        # Verify the TOTP code
        if totp_service.verify_token(secret, totp_code):
            # Enable TOTP and overall 2FA
            cursor.execute('''
                UPDATE users 
                SET totp_enabled = 1, two_factor_enabled = 1 
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'TOTP authentication enabled successfully!'
            })
        else:
            conn.close()
            return jsonify({'error': 'Invalid TOTP code'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/auth/totp/status', methods=['GET'])
def totp_status():
    """Get TOTP status for current user"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = payload.get('user_id')
        
        # Get user's TOTP status
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT totp_enabled, two_factor_enabled, totp_secret 
            FROM users WHERE id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'User not found'}), 404
        
        totp_enabled, two_factor_enabled, has_secret = result[0], result[1], bool(result[2])
        
        return jsonify({
            'totp_enabled': bool(totp_enabled),
            'two_factor_enabled': bool(two_factor_enabled),
            'totp_configured': has_secret
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/filemaker/artwork/<artwork_id>/images', methods=['GET'])
def get_artwork_images(artwork_id):
    """Get all image fields for an artwork from FileMaker"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # FileMaker is down — serve image fields from the local catalogue
        # (same data photo-validator already uses).
        from operagallery_service import local_artwork_by_id
        art = local_artwork_by_id(artwork_id)
        image_fields = (art or {}).get('image_fields') if art else None

        if not image_fields:
            return jsonify({'error': f'Artwork {artwork_id} not found in local catalogue'}), 404

        return jsonify({
            'success': True,
            'artwork_id': artwork_id,
            'image_fields': image_fields
        })
        
    except Exception as e:
        print(f"Error getting artwork images: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/filemaker/artwork/check/<photo_filename>', methods=['GET'])
def check_artwork_exists(photo_filename):
    """Check if artwork exists in FileMaker based on photo filename"""
    try:
        # Check authorization
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Extract artwork ID from filename
        artwork_id = extract_artwork_id_from_filename(photo_filename)
        
        if not artwork_id:
            return jsonify({
                'success': True,
                'exists': False,
                'artwork_id': None,
                'message': 'No artwork ID found in filename'
            })
        
        # FileMaker is down — check existence against the local catalogue.
        from operagallery_service import local_artwork_by_id
        artwork = local_artwork_by_id(artwork_id)

        if artwork:
            return jsonify({
                'success': True,
                'exists': True,
                'artwork_id': artwork_id,
                'artwork_info': {
                    'title': artwork.get('title', ''),
                    'artist': artwork.get('artist', ''),
                    'year': artwork.get('year', ''),
                    'medium': artwork.get('medium', '')
                }
            })
        else:
            return jsonify({
                'success': True,
                'exists': False,
                'artwork_id': artwork_id,
                'message': f'Artwork {artwork_id} not found in local catalogue'
            })
        
    except Exception as e:
        print(f"Error checking artwork: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/admin/filemaker/update-image-fields', methods=['POST'])
def update_filemaker_image_fields():
    """Update multiple image fields for an artwork (admin only, with detailed Odoo + FileMaker sync and UI update)"""
    try:
        # --- AUTH CHECK ---
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            print("🚫 Missing or invalid token header")
            return jsonify({'error': 'Missing token'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            print("🚫 Invalid JWT token")
            return jsonify({'error': 'Invalid token'}), 401

        if payload.get('role') != 'admin':
            print("🚫 Access denied — user not admin")
            return jsonify({'error': 'Admin access required'}), 403

        # --- INPUT VALIDATION ---
        data = request.get_json()
        artwork_id = data.get('artworkId')
        fields = data.get('fields', {})

        print(f"\n📩 Received API request for artwork: {artwork_id}")
        print(f"🖼️ Fields to update: {fields}\n")

        if not artwork_id:
            return jsonify({'error': 'artworkId is required'}), 400

        if not fields:
            return jsonify({'error': 'fields data is required'}), 400

        # --- UPDATE FILEMAKER ---
        print("🔄 Updating FileMaker fields...")
        success = filemaker_service.update_multiple_fields(artwork_id, fields)
        print(f"✅ FileMaker update status: {success}")

        # --- IF FILEMAKER SUCCESS, UPDATE ODOO ---
        if success:
            try:
                import xmlrpc.client

                # ⚙️ Static Odoo configuration
                odoo_url = "https://operacrm.com"
                db = "odoo_15"
                username = "frederic@faucouneau.fr"
                password = "ONc8VxiDFnSgCuwSkArqur3Sj1WFZhov"

                print("\n🌐 Connecting to Odoo server...")
                common = xmlrpc.client.ServerProxy(f"{odoo_url}/xmlrpc/2/common")
                uid = common.login(db, username, password)
                print(f"✅ Odoo connection OK (UID={uid})")

                models = xmlrpc.client.ServerProxy(f"{odoo_url}/xmlrpc/2/object")

                # --- SEARCH PRODUCT BY IDNAME ---
                print(f"🔍 Searching Odoo product with IdName='{artwork_id}' ...")
                product_ids = models.execute_kw(
                    db, uid, password,
                    'product.template', 'search',
                    [[('IdName', '=', artwork_id)]]
                )
                print(f"📦 Found product IDs: {product_ids}")

                if not product_ids:
                    print(f"⚠️ No product found in Odoo for {artwork_id}")
                else:
                    product_id = product_ids[0]
                    print(f"✅ Using product ID: {product_id}")

                    # --- LOOP THROUGH IMAGE FIELDS ---
                    for field_name, image_url in fields.items():
                        if not image_url:
                            print(f"⚠️ Skipping empty URL for field '{field_name}'")
                            continue

                        print(f"🖼️ Checking image '{image_url}' for field '{field_name}'")

                        # Search if image already exists for this product
                        existing_img_ids = models.execute_kw(
                            db, uid, password,
                            'product.template.images', 'search',
                            [[('product_template_id', '=', product_id),
                              ('image_url', '=', image_url)]]
                        )

                        if existing_img_ids:
                            print(f"🔁 Existing image found (IDs: {existing_img_ids}) — updating...")
                            models.execute_kw(
                                db, uid, password,
                                'product.template.images', 'write',
                                [existing_img_ids, {'image_url': image_url}]
                            )
                            print(f"✅ Updated existing image for {artwork_id}")
                        else:
                            print(f"➕ Creating new image record for {artwork_id}")
                            created_id = models.execute_kw(
                                db, uid, password,
                                'product.template.images', 'create',
                                [{
                                    'product_template_id': product_id,
                                    'image_url': image_url
                                }]
                            )
                            print(f"🆕 Created new image record ID={created_id} for {artwork_id}")

                        # --- 🧩 NEW: Update main product field (for frontend display)
                        # Update 'main_picture_hd' field directly in product.template
                        try:
                            models.execute_kw(
                                db, uid, password,
                                'product.template', 'write',
                                [[product_id], {'main_picture_hd': image_url}]
                            )
                            print(f"🖼️ Updated main_picture_hd in product.template for {artwork_id}")
                        except Exception as field_err:
                            print(f"⚠️ Failed to update main_picture_hd for {artwork_id}: {field_err}")

                    print(f"🎉 Finished syncing all images for artwork {artwork_id}\n")

            except Exception as e:
                print(f"⚠️ Odoo sync failed: {e}")

        # --- RESPONSE ---
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully updated FileMaker + Odoo for artwork {artwork_id}',
                'updated_fields': list(fields.keys())
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update FileMaker fields'
            }), 500

    except Exception as e:
        print(f"❌ Exception in update_filemaker_image_fields(): {e}")
        return jsonify({'error': str(e)}), 500



@auth_bp.route('/api/admin/scheduled-uploads', methods=['GET'])
def get_scheduled_uploads():
    """Get list of scheduled uploads (admin only)"""
    try:
        # Verify authentication and admin role
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token manquant'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token invalide'}), 401
        
        # Check admin role
        username = payload.get('username')
        if not username:
            return jsonify({'error': 'Utilisateur invalide'}), 401
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        
        if not result or result[0] != 'admin':
            conn.close()
            return jsonify({'error': 'Accès admin requis'}), 403
        
        # Get scheduled uploads
        cursor.execute('''
            SELECT su.id, su.artwork_id, su.photo_filename, su.classification,
                   su.scheduled_date, su.status, su.created_at, su.processed_at,
                   su.error_message, u.username as created_by_username
            FROM scheduled_uploads su
            JOIN users u ON su.created_by = u.id
            ORDER BY su.scheduled_date ASC
        ''')
        
        uploads = []
        for row in cursor.fetchall():
            uploads.append({
                'id': row[0],
                'artwork_id': row[1],
                'photo_filename': row[2],
                'classification': row[3],
                'scheduled_date': row[4],
                'status': row[5],
                'created_at': row[6],
                'processed_at': row[7],
                'error_message': row[8],
                'created_by': row[9]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'uploads': uploads,
            'total': len(uploads)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/api/admin/scheduled-uploads/<int:upload_id>', methods=['DELETE'])
def cancel_scheduled_upload(upload_id):
    """Cancel a scheduled upload (admin only)"""
    try:
        # Verify authentication and admin role
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token manquant'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token invalide'}), 401
        
        # Check admin role
        username = payload.get('username')
        if not username:
            return jsonify({'error': 'Utilisateur invalide'}), 401
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        
        if not result or result[0] != 'admin':
            conn.close()
            return jsonify({'error': 'Accès admin requis'}), 403
        
        # Get upload details
        cursor.execute('SELECT original_path, status FROM scheduled_uploads WHERE id = ?', (upload_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({'error': 'Upload non trouvé'}), 404
        
        original_path, status = row
        
        if status != 'scheduled':
            conn.close()
            return jsonify({'error': f'Impossible d\'annuler un upload avec le statut: {status}'}), 400
        
        # Delete the scheduled file
        try:
            if os.path.exists(original_path):
                os.unlink(original_path)
        except Exception as e:
            print(f"[SCHEDULER] Erreur suppression fichier {original_path}: {e}")
        
        # Mark as cancelled
        cursor.execute('''
            UPDATE scheduled_uploads 
            SET status = 'cancelled', processed_at = ?
            WHERE id = ?
        ''', (datetime.now(), upload_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Upload annulé avec succès'
        })

    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/api/admin/scheduled-uploads/<int:upload_id>/release', methods=['POST'])
def release_scheduled_upload(upload_id):
    """Release a scheduled upload immediately (admin only).

    Mirrors per-row logic of process_scheduled_uploads(): moves the file
    from the scheduled folder to FM_DIR and marks the row 'completed'.
    Bypasses the scheduled_date check so it can be triggered manually.
    """
    try:
        # Verify authentication and admin role
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token manquant'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token invalide'}), 401

        username = payload.get('username')
        if not username:
            return jsonify({'error': 'Utilisateur invalide'}), 401

        conn = sqlite3.connect(DATABASE_PATH, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()

        if not result or result[0] != 'admin':
            conn.close()
            return jsonify({'error': 'Accès admin requis'}), 403

        # Load upload row
        cursor.execute(
            'SELECT artwork_id, photo_filename, classification, original_path, target_path, status FROM scheduled_uploads WHERE id = ?',
            (upload_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({'error': 'Upload non trouvé'}), 404

        artwork_id, photo_filename, classification, original_path, target_path, status = row

        if status != 'scheduled':
            conn.close()
            return jsonify({'error': f'Impossible de relâcher un upload avec le statut: {status}'}), 400

        now = datetime.now()
        success = False
        error_message = None
        final_filename = photo_filename
        final_target_path = target_path

        try:
            if os.path.exists(original_path):
                os.makedirs(FM_DIR, exist_ok=True)

                # Apply classification suffix (same as direct validation)
                import re as _re
                def _add_cls(fname, cls):
                    name, ext = os.path.splitext(fname)
                    m = _re.search(r'([A-Z]+-\d+)', fname)
                    if m:
                        return f"{m.group(1)}_{cls}{ext}"
                    return f"{name}_{cls}{ext}"

                final_filename = _add_cls(photo_filename, classification) if classification else photo_filename
                final_target_path = os.path.join(FM_DIR, final_filename)

                shutil.move(original_path, final_target_path)
                success = True

                # Derive artwork_id from filename if not stored
                _m = _re.match(r'^([A-Z]+-\d+)', photo_filename)
                _aid = _m.group(1) if _m else artwork_id

                print(f"[RELEASE] Upload released: id={upload_id} {_aid} → {final_target_path}")
            else:
                error_message = f"File not found: {original_path}"
        except Exception as move_err:
            error_message = str(move_err)
            print(f"[RELEASE] Erreur release {upload_id}: {move_err}")

        if success:
            fm_url = f"https://images.operagallery.com/FM/{final_filename}"

            cursor.execute(
                "UPDATE scheduled_uploads SET status = 'completed', processed_at = ?, target_path = ? WHERE id = ?",
                (now, final_target_path, upload_id)
            )
            cursor.execute("""
                UPDATE photo_validations
                SET status = 'validated', validated_at = ?, artwork_id = ?, photo_filename = ?
                WHERE photo_filename = ? AND status = 'scheduled'
            """, (now, _aid, final_filename, photo_filename))
            conn.commit()
            conn.close()

            # Call FM API to update artwork field
            CLASSIFICATION_TO_FIELD = {
                'MAIN': 'MAINFM', 'LEFT': 'LEFT300', 'RIGHT': 'FRONTRIGHT300',
                'FRONTRIGHT': 'FRONTRIGHT300', 'BACK': 'BACK300', 'PERS': 'PERS300',
                'INSITU': 'INSITU300', 'EDITIONNUMBER': 'EDITIONNUMBER300',
                'DET': 'DET300', 'DET2': 'DET2300', 'OTHER': 'OTHER300',
                'OTHER2': 'OTHER2300', 'FRAME': 'FRAME300', 'FRONT': 'FRONT300',
                'SIGN': 'Signature',
            }
            target_field = CLASSIFICATION_TO_FIELD.get(classification) if classification else None
            if target_field and _aid:
                try:
                    filemaker_service.ensure_connected()
                    fm_ok = filemaker_service.update_specialized_field(_aid, target_field, fm_url)
                    if fm_ok:
                        print(f"[RELEASE] FM field '{target_field}' updated for {_aid}")
                    else:
                        print(f"[RELEASE] FM field '{target_field}' update FAILED for {_aid} (FM offline or error)")
                except Exception as fm_err:
                    print(f"[RELEASE] FM update failed (non-fatal): {fm_err}")

            return jsonify({
                'success': True,
                'message': 'Photo released and published successfully',
                'upload_id': upload_id,
                'artwork_id': _aid,
                'filename': final_filename
            })
        else:
            cursor.execute(
                "UPDATE scheduled_uploads SET status = 'failed', processed_at = ?, error_message = ? WHERE id = ?",
                (now, error_message, upload_id)
            )
            conn.commit()
            conn.close()
            return jsonify({
                'success': False,
                'error': error_message or 'Release failed'
            }), 500

    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/api/admin/scheduled-uploads/release-bulk', methods=['POST'])
def release_scheduled_uploads_bulk():
    """Release multiple scheduled uploads immediately (admin only).

    Body: { "ids": [1, 2, 3] }
    Returns per-id results so the UI can report partial failures.
    """
    try:
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token manquant'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token invalide'}), 401

        username = payload.get('username')
        if not username:
            return jsonify({'error': 'Utilisateur invalide'}), 401

        conn = sqlite3.connect(DATABASE_PATH, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        if not result or result[0] != 'admin':
            conn.close()
            return jsonify({'error': 'Accès admin requis'}), 403

        data = request.get_json(silent=True) or {}
        ids = data.get('ids', [])
        if not ids or not isinstance(ids, list):
            conn.close()
            return jsonify({'error': 'ids list required'}), 400

        CLASSIFICATION_TO_FIELD = {
            'MAIN': 'MAINFM', 'LEFT': 'LEFT300', 'RIGHT': 'FRONTRIGHT300',
            'FRONTRIGHT': 'FRONTRIGHT300', 'BACK': 'BACK300', 'PERS': 'PERS300',
            'INSITU': 'INSITU300', 'EDITIONNUMBER': 'EDITIONNUMBER300',
            'DET': 'DET300', 'DET2': 'DET2300', 'OTHER': 'OTHER300',
            'OTHER2': 'OTHER2300', 'FRAME': 'FRAME300', 'FRONT': 'FRONT300',
            'SIGN': 'Signature',
        }

        import re as _re
        def _add_cls(fname, cls):
            name, ext = os.path.splitext(fname)
            m = _re.search(r'([A-Z]+-\d+)', fname)
            if m:
                return f"{m.group(1)}_{cls}{ext}"
            return f"{name}_{cls}{ext}"

        results = []
        now = datetime.now()

        for upload_id in ids:
            try:
                cursor.execute(
                    'SELECT artwork_id, photo_filename, classification, original_path, target_path, status FROM scheduled_uploads WHERE id = ?',
                    (upload_id,)
                )
                row = cursor.fetchone()

                if not row:
                    results.append({'id': upload_id, 'success': False, 'error': 'Not found'})
                    continue

                artwork_id, photo_filename, classification, original_path, target_path, status = row

                if status != 'scheduled':
                    results.append({'id': upload_id, 'success': False, 'error': f'Status is {status}, not scheduled'})
                    continue

                if not os.path.exists(original_path):
                    cursor.execute(
                        "UPDATE scheduled_uploads SET status = 'failed', processed_at = ?, error_message = ? WHERE id = ?",
                        (now, f"File not found: {original_path}", upload_id)
                    )
                    conn.commit()
                    results.append({'id': upload_id, 'success': False, 'error': f'File not found: {original_path}'})
                    continue

                os.makedirs(FM_DIR, exist_ok=True)
                final_filename = _add_cls(photo_filename, classification) if classification else photo_filename
                final_target_path = os.path.join(FM_DIR, final_filename)

                shutil.move(original_path, final_target_path)

                _m = _re.match(r'^([A-Z]+-\d+)', photo_filename)
                _aid = _m.group(1) if _m else artwork_id
                fm_url = f"https://images.operagallery.com/FM/{final_filename}"

                cursor.execute(
                    "UPDATE scheduled_uploads SET status = 'completed', processed_at = ?, target_path = ? WHERE id = ?",
                    (now, final_target_path, upload_id)
                )
                cursor.execute("""
                    UPDATE photo_validations
                    SET status = 'validated', validated_at = ?, artwork_id = ?, photo_filename = ?
                    WHERE photo_filename = ? AND status = 'scheduled'
                """, (now, _aid, final_filename, photo_filename))
                conn.commit()

                target_field = CLASSIFICATION_TO_FIELD.get(classification) if classification else None
                fm_updated = False
                if target_field and _aid:
                    try:
                        filemaker_service.ensure_connected()
                        fm_updated = filemaker_service.update_specialized_field(_aid, target_field, fm_url) or False
                        if not fm_updated:
                            print(f"[RELEASE-BULK] FM field '{target_field}' update FAILED for {_aid} (FM offline or error)")
                    except Exception as fm_err:
                        print(f"[RELEASE-BULK] FM update failed for {upload_id}: {fm_err}")

                print(f"[RELEASE-BULK] Released id={upload_id} {_aid} → {final_target_path} (FM updated: {fm_updated})")
                results.append({'id': upload_id, 'success': True, 'filename': final_filename, 'artwork_id': _aid})

            except Exception as item_err:
                print(f"[RELEASE-BULK] Error on id={upload_id}: {item_err}")
                results.append({'id': upload_id, 'success': False, 'error': str(item_err)})

        conn.close()

        succeeded = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]

        return jsonify({
            'success': True,
            'released': len(succeeded),
            'failed': len(failed),
            'results': results,
            'message': f"{len(succeeded)} photo(s) released successfully" + (f", {len(failed)} failed" if failed else "")
        })

    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@auth_bp.route('/api/admin/scheduled-uploads/release-all', methods=['POST'])
def release_all_scheduled():
    """Release ALL scheduled uploads immediately (admin only)."""
    try:
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token manquant'}), 401
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token invalide'}), 401
        username = payload.get('username')
        conn = sqlite3.connect(DATABASE_PATH, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        if not result or result[0] != 'admin':
            conn.close()
            return jsonify({'error': 'Accès admin requis'}), 403

        cursor.execute("SELECT id FROM scheduled_uploads WHERE status = 'scheduled'")
        ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not ids:
            return jsonify({'success': True, 'released': 0, 'failed': 0, 'message': 'No scheduled uploads to release'})

        # Reuse bulk logic by calling the internal helper
        from flask import current_app
        with current_app.test_request_context(
            '/api/admin/scheduled-uploads/release-bulk',
            method='POST',
            json={'ids': ids},
            headers={'Authorization': f'Bearer {request.headers.get("Authorization", "").split(" ")[-1]}'}
        ):
            pass

        # Process directly (same logic as release-bulk)
        CLASSIFICATION_TO_FIELD = {
            'MAIN': 'MAINFM', 'LEFT': 'LEFT300', 'RIGHT': 'FRONTRIGHT300',
            'FRONTRIGHT': 'FRONTRIGHT300', 'BACK': 'BACK300', 'PERS': 'PERS300',
            'INSITU': 'INSITU300', 'EDITIONNUMBER': 'EDITIONNUMBER300',
            'DET': 'DET300', 'DET2': 'DET2300', 'OTHER': 'OTHER300',
            'OTHER2': 'OTHER2300', 'FRAME': 'FRAME300', 'FRONT': 'FRONT300',
            'SIGN': 'Signature',
        }
        import re as _re
        def _add_cls(fname, cls):
            name, ext = os.path.splitext(fname)
            m = _re.search(r'([A-Z]+-\d+)', fname)
            if m:
                return f"{m.group(1)}_{cls}{ext}"
            return f"{name}_{cls}{ext}"

        conn = sqlite3.connect(DATABASE_PATH, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        now = datetime.now()
        released, failed = 0, 0

        for upload_id in ids:
            try:
                cursor.execute(
                    'SELECT artwork_id, photo_filename, classification, original_path, target_path, status FROM scheduled_uploads WHERE id = ?',
                    (upload_id,)
                )
                row = cursor.fetchone()
                if not row:
                    failed += 1
                    continue
                artwork_id, photo_filename, classification, original_path, target_path, status = row
                if status != 'scheduled':
                    failed += 1
                    continue
                if not os.path.exists(original_path):
                    cursor.execute(
                        "UPDATE scheduled_uploads SET status='failed', processed_at=?, error_message=? WHERE id=?",
                        (now, f"File not found: {original_path}", upload_id)
                    )
                    conn.commit()
                    failed += 1
                    continue

                os.makedirs(FM_DIR, exist_ok=True)
                final_filename = _add_cls(photo_filename, classification) if classification else photo_filename
                final_target_path = os.path.join(FM_DIR, final_filename)
                shutil.move(original_path, final_target_path)

                _m = _re.match(r'^([A-Z]+-\d+)', photo_filename)
                _aid = _m.group(1) if _m else artwork_id
                fm_url = f"https://images.operagallery.com/FM/{final_filename}"

                cursor.execute(
                    "UPDATE scheduled_uploads SET status='completed', processed_at=?, target_path=? WHERE id=?",
                    (now, final_target_path, upload_id)
                )
                cursor.execute("""
                    UPDATE photo_validations
                    SET status='validated', validated_at=?, artwork_id=?, photo_filename=?
                    WHERE photo_filename=? AND status='scheduled'
                """, (now, _aid, final_filename, photo_filename))
                conn.commit()

                target_field = CLASSIFICATION_TO_FIELD.get(classification) if classification else None
                if target_field and _aid:
                    try:
                        filemaker_service.ensure_connected()
                        fm_ok = filemaker_service.update_specialized_field(_aid, target_field, fm_url) or False
                        if not fm_ok:
                            print(f"[RELEASE-ALL] FM update FAILED for {_aid} (offline)")
                    except Exception as fm_err:
                        print(f"[RELEASE-ALL] FM error for {upload_id}: {fm_err}")

                print(f"[RELEASE-ALL] Released id={upload_id} {_aid} → {final_target_path}")
                released += 1
            except Exception as e:
                print(f"[RELEASE-ALL] Error on id={upload_id}: {e}")
                failed += 1

        conn.close()
        return jsonify({
            'success': True,
            'released': released,
            'failed': failed,
            'message': f"{released} photo(s) released" + (f", {failed} failed" if failed else "")
        })

    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@auth_bp.route('/api/admin/scheduled-uploads/delete-all', methods=['DELETE'])
def delete_all_scheduled():
    """Delete (cancel) ALL scheduled uploads and remove their files (admin only)."""
    try:
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token manquant'}), 401
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token invalide'}), 401
        username = payload.get('username')
        conn = sqlite3.connect(DATABASE_PATH, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        if not result or result[0] != 'admin':
            conn.close()
            return jsonify({'error': 'Accès admin requis'}), 403

        cursor.execute("SELECT id, original_path FROM scheduled_uploads WHERE status = 'scheduled'")
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return jsonify({'success': True, 'deleted': 0, 'message': 'No scheduled uploads to delete'})

        now = datetime.now()
        deleted = 0
        for upload_id, original_path in rows:
            try:
                if original_path and os.path.exists(original_path):
                    os.unlink(original_path)
            except Exception as e:
                print(f"[DELETE-ALL] File removal error {original_path}: {e}")
            cursor.execute(
                "UPDATE scheduled_uploads SET status='cancelled', processed_at=? WHERE id=?",
                (now, upload_id)
            )
            deleted += 1

        conn.commit()
        conn.close()
        print(f"[DELETE-ALL] Cancelled {deleted} scheduled uploads")
        return jsonify({
            'success': True,
            'deleted': deleted,
            'message': f"{deleted} scheduled upload(s) cancelled and removed"
        })

    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@auth_bp.route('/api/admin/process-scheduled-uploads', methods=['POST'])
def manual_process_scheduled():
    """Manually process scheduled uploads (admin only)"""
    try:
        # Verify authentication and admin role
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token manquant'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token invalide'}), 401
        
        # Check admin role
        username = payload.get('username')
        if not username:
            return jsonify({'error': 'Utilisateur invalide'}), 401
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        
        if not result or result[0] != 'admin':
            conn.close()
            return jsonify({'error': 'Accès admin requis'}), 403
        
        conn.close()
        
        # Process scheduled uploads
        processed_count = process_scheduled_uploads()
        
        return jsonify({
            'success': True,
            'message': f'{processed_count} uploads traités',
            'processed_count': processed_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/api/files/<path:file_id>', methods=['GET'])
def serve_file_universal(file_id):
    """Serve any type of file (images, PDFs, videos) with proper content-type detection"""
    try:
        # Decode the file_id if it was URL encoded
        import urllib.parse
        decoded_file_id = urllib.parse.unquote(file_id)
        
        # Security check
        if '..' in decoded_file_id or decoded_file_id.startswith('/'):
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Build full path
        file_path = os.path.join(PHOTOS_BASE_DIR, decoded_file_id)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Block .eps files completely
        file_ext = os.path.splitext(decoded_file_id)[1].lower()
        if file_ext in ['.eps', '.ai', '.ps']:
            return jsonify({'error': 'EPS files are not supported'}), 403
        
        # Detect file type from extension
        file_type, mime_type, _ = get_file_type_info(file_path)
        
        if file_type is None:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        # Serve file with appropriate content-type
        try:
            # Videos need Range request support for browser playback
            if file_type == 'video':
                return _serve_with_range(file_path, mime_type)
            return send_file(
                file_path,
                mimetype=mime_type,
                as_attachment=False,  # Never force download, let browser display
                download_name=None
            )
        except Exception as e:
            return jsonify({'error': f'Error serving file: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@auth_bp.route('/api/photos/delete', methods=['DELETE'])
def delete_photo():
    """Delete a photo - only for admins and validators"""
    try:
        # Verify authentication
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Token manquant'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token invalide'}), 401
        
        # Check if user has permission to delete photos
        if payload.get('role') not in ['admin', 'validator']:
            return jsonify({'error': 'Access denied. Only admins and validators can delete photos.'}), 403
        
        # Get photo_id from query parameters
        photo_id = request.args.get('id')
        if not photo_id:
            return jsonify({'error': 'Photo ID is required'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get photo information first from photo_validations table
        # Debug: see what we're looking for and what's in database
        filename_only = os.path.basename(photo_id)
        print(f"[DELETE DEBUG] Looking for photo_id: {photo_id}")
        print(f"[DELETE DEBUG] Filename only: {filename_only}")
        
        # Check what photos are actually in the database
        cursor.execute('SELECT photo_filename FROM photo_validations LIMIT 5')
        sample_photos = cursor.fetchall()
        print(f"[DELETE DEBUG] Sample photos in DB: {sample_photos}")
        
        # Try to find by full path first, then by filename only
        cursor.execute('SELECT * FROM photo_validations WHERE photo_filename = ? OR photo_filename = ?', 
                      (photo_id, filename_only))
        photo = cursor.fetchone()
        print(f"[DELETE DEBUG] Photo found: {photo is not None}")
        
        if not photo:
            conn.close()
            return jsonify({
                'error': 'Photo not found',
                'debug': {
                    'searched_id': photo_id,
                    'searched_filename': filename_only,
                    'sample_db_entries': [row[0] for row in sample_photos]
                }
            }), 404
        
        # Get photo path - it should be the photo_id itself as it's the path
        #photo_path = photo_id  
        absolute_path = os.path.join(PHOTOS_BASE_DIR, photo_id)
        absolute_path = os.path.abspath(absolute_path)

        # If the computed absolute path does not exist, try common directories
        if not os.path.exists(absolute_path):
            filename_only = os.path.basename(photo_id)
            possible_dirs = ['a-valider', 'refuse', 'FM', 'output', 'a-valider-pdf']
            for d in possible_dirs:
                attempt = os.path.abspath(os.path.join(PHOTOS_BASE_DIR, d, filename_only))
                if os.path.exists(attempt):
                    absolute_path = attempt
                    break

        photo_path = absolute_path
        print("[DELETE] Final resolved path:", photo_path)
        # Delete photo record from database - use the same pattern as the search
        cursor.execute('DELETE FROM photo_validations WHERE photo_filename = ? OR photo_filename = ?', 
                      (photo_id, os.path.basename(photo_id)))
        
        # Delete physical file if it exists
        try:
            if photo_path and os.path.exists(photo_path):
                os.unlink(photo_path)
                print(f"[DELETE] Physical file deleted: {photo_path}")
        except Exception as e:
            print(f"[DELETE] Error deleting physical file {photo_path}: {e}")
            # Continue anyway - database deletion is more important
        
        conn.commit()
        conn.close()
        
        print(f"[DELETE] Photo {photo_id} deleted by {payload.get('username')} ({payload.get('role')})")
        
        return jsonify({
            'success': True,
            'message': f'Photo {photo_id} supprimée avec succès'
        })
        
    except Exception as e:
        print(f"[DELETE] Error deleting photo {photo_id}: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@auth_bp.route('/api/fm-push-log/download', methods=['GET'])
def download_fm_push_log():
    """Download the FM push log CSV (ID_Artwork + URL for each validated photo)"""
    token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token or not verify_token(token):
        return jsonify({'error': 'Unauthorized'}), 401

    if not os.path.exists(FM_PUSH_CSV):
        empty = 'ID_Artwork;FM_Field;URL_Pushed;Classification;Pushed_At\r\n'
        return Response(empty, mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename="fm_push_log.csv"'})

    return send_file(
        FM_PUSH_CSV,
        mimetype='text/csv',
        as_attachment=True,
        download_name='fm_push_log.csv'
    )


@auth_bp.route('/api/fm-push-log/reset', methods=['POST'])
def reset_fm_push_log():
    """Reset (archive + clear) the FM push log CSV — call after sending it to FM"""
    token = request.headers.get('Authorization', '')
    if not token.startswith('Bearer ') or not verify_token(token.split(' ')[1]):
        return jsonify({'error': 'Unauthorized'}), 401

    if not os.path.exists(FM_PUSH_CSV):
        return jsonify({'message': 'Nothing to reset'}), 200

    archive_path = FM_PUSH_CSV.replace('.csv', f'_archive_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv')
    shutil.copy2(FM_PUSH_CSV, archive_path)
    os.remove(FM_PUSH_CSV)
    return jsonify({'success': True, 'archived_to': os.path.basename(archive_path)})
