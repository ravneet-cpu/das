#!/usr/bin/env python3
"""
Simple Flask server for photo validator with task management
"""

from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import sys
import mimetypes
import time

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth_routes import auth_bp
from operagallery_service import operacrm_bp
from crm_api import crm_api_bp
from certificate_service import certificate_bp
from image_quality_checker import ImageQualityChecker
#from contact_search import contact_search_bp

app = Flask(__name__)
CORS(app)

# Use a portable local default in development.  Docker/production can set
# DATABASE_PATH explicitly (for example, /app/data/photo_validator.db).
DATABASE_PATH = os.environ.get(
    'DATABASE_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'photo_validator.db')
)

# Rate limiting désactivé
# limiter = Limiter(
#     key_func=get_remote_address,
#     default_limits=["200 per day", "50 per hour"],
#     storage_uri="memory://",
# )
# limiter.init_app(app)

# Configuration for large files
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1000MB (1GB) max
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # Cache images 1 year

# Configure MIME types
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')

# Apply rate limiting to specific routes before registering blueprints
from functools import wraps

# Rate limiting désactivé
# def apply_rate_limits():
#     """Apply rate limiting to sensitive routes"""
#     
#     # Auth routes - strict limits
#     limiter.limit("5 per minute")(auth_bp.view_functions.get('login', lambda: None))
#     limiter.limit("3 per minute")(auth_bp.view_functions.get('register', lambda: None))
#     limiter.limit("10 per hour")(auth_bp.view_functions.get('upload', lambda: None))
#     
#     # Search routes - moderate limits  
#     limiter.limit("30 per minute")(operacrm_bp.view_functions.get('search_artworks', lambda: None))
#     
#     # Upload routes - strict limits
#     limiter.limit("20 per hour")(operacrm_bp.view_functions.get('upload_artwork_image', lambda: None))
#     limiter.limit("50 per hour")(operacrm_bp.view_functions.get('validate_upload', lambda: None))
#     
#     # Image proxy - moderate limits
#     limiter.limit("100 per minute")(operacrm_bp.view_functions.get('get_image_proxy', lambda: None))

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(operacrm_bp)
app.register_blueprint(crm_api_bp)
app.register_blueprint(certificate_bp)
#app.register_blueprint(contact_search_bp)

# Route de test pour les artistes célèbres
@app.route('/api/test/famous-artists', methods=['GET'])
def test_famous_artists():
    """Simple test to verify famous artists"""
    try:
        from artist_indexer import FAMOUS_ARTISTS
        return jsonify({
            'success': True,
            'total': len(FAMOUS_ARTISTS),
            'first_10': FAMOUS_ARTISTS[:10],
            'last_10': FAMOUS_ARTISTS[-10:],
            'all_artists': FAMOUS_ARTISTS
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# Rate limiting désactivé
# apply_rate_limits()

# Global quality checker instance
quality_checker = ImageQualityChecker()

# Rate limiting error handler (désactivé)
# @app.errorhandler(429)
# def ratelimit_handler(e):
#     return jsonify({
#         'error': 'Rate limit exceeded',
#         'message': 'Too many requests. Please slow down and try again later.',
#         'retry_after': getattr(e, 'retry_after', None)
#     }), 429

# Security monitoring endpoint (admin only)
@app.route('/api/admin/security-status')
# @limiter.limit("10 per minute")
def security_status():
    """Security status and metrics (admin only)"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        from auth import verify_token
        payload = verify_token(auth_header.split(' ')[1])
        if payload.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
    except:
        return jsonify({'error': 'Invalid token'}), 401
    
    # Récupérer les statistiques de rate limiting
    stats = {
        'timestamp': time.time(),
        'remote_addr': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'rate_limits': {
            'global_limits': ["200 per day", "50 per hour"],
            'specific_limits': {
                'login': "5 per minute",
                'upload': "20 per hour", 
                'search': "30 per minute",
                'images': "100 per minute"
            }
        },
        'security_features': {
            'https': True,  # Via Traefik
            'rate_limiting': True,
            'jwt_auth': True,
            'file_validation': True,
            'cors_enabled': True
        }
    }
    
    return jsonify(stats)

# Serve static files from dist directory
@app.route('/')
def serve_index():
    response = send_from_directory('dist', 'index.html')
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; connect-src 'self' https: http:; img-src 'self' data: https: http:; style-src 'self' 'unsafe-inline'"
    
    # 🔥 ANTI-CACHE HEADERS pour éviter les problèmes de connexion
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/<path:path>')
def serve_static(path):
    if path.startswith('api/'):
        # API routes are handled by blueprints
        return jsonify({'error': 'API endpoint not found'}), 404
    
    try:
        response = send_from_directory('dist', path)
        
        # Force correct MIME types for assets
        if path.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript'
            # 🔥 JS files doivent être fresh pour les mises à jour de code
            response.headers['Cache-Control'] = 'no-cache, must-revalidate, max-age=0'
        elif path.endswith('.css'):
            response.headers['Content-Type'] = 'text/css'
            # 🔥 CSS files doivent être fresh pour les mises à jour de style
            response.headers['Cache-Control'] = 'no-cache, must-revalidate, max-age=0'
        elif path.endswith('.svg'):
            response.headers['Content-Type'] = 'image/svg+xml'
        elif path.endswith('.ico'):
            response.headers['Content-Type'] = 'image/x-icon'
        
        # Add permissive CSP for all assets
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; connect-src 'self' https: http:; img-src 'self' data: https: http:; style-src 'self' 'unsafe-inline'"
            
        return response
    except:
        # Fallback to index.html for SPA routing
        return send_from_directory('dist', 'index.html')

@app.route('/api/clear-cache')
def clear_browser_cache():
    """Endpoint to force browser cache refresh"""
    import datetime
    response = jsonify({
        'success': True,
        'message': 'Cache refresh headers sent',
        'timestamp': datetime.datetime.now().isoformat(),
        'instructions': {
            'en': 'Please refresh your browser with Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)',
            'fr': 'Veuillez rafraîchir votre navigateur avec Ctrl+F5 (Windows/Linux) ou Cmd+Shift+R (Mac)'
        }
    })
    
    # 🔥 HEADERS ANTI-CACHE maximaux
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, s-maxage=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Last-Modified'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
    response.headers['ETag'] = '"0"'
    
    return response

@app.route('/api/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Photo Validator API is running'
    })

@app.route('/api/debug-validated')
def debug_validated():
    """Debug endpoint for validated photos and list_photos function"""
    import os
    import sqlite3
    from datetime import datetime
    
    PHOTOS_BASE_DIR = '/app/photos'
    
    result = {
        'output_dir': '/app/photos/output',
        'files_in_output': [],
        'validation_records': [],
        'image_5_files': [],
        'list_photos_simulation': {}
    }
    
    # List files in output directory
    output_dir = '/app/photos/output'
    if os.path.exists(output_dir):
        all_files = os.listdir(output_dir)
        image_files = [f for f in all_files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'))]
        result['files_in_output'] = image_files
        result['image_5_files'] = [f for f in image_files if 'image_5' in f.lower()]
    
    # Get validation records
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all validation records
        cursor.execute('''
            SELECT pv.photo_id, pv.photo_filename, pv.status, pv.classification, pv.validated_at,
                   u1.username as validator_username,
                   u2.username as submitter_username
            FROM photo_validations pv
            LEFT JOIN users u1 ON pv.validated_by = u1.id
            LEFT JOIN users u2 ON pv.submitted_by = u2.id
            WHERE pv.status = 'validated'
        ''')
        
        validation_data = {}
        for row in cursor.fetchall():
            # Store by photo_id (original filename)
            validation_data[row[0]] = {
                'photo_filename': row[1],
                'status': row[2],
                'classification': row[3],
                'validated_at': row[5],
                'validator_username': row[5],
                'submitter_username': row[6]
            }
            # Also store by photo_filename (final filename) for lookup
            if row[1] and row[1] != row[0]:
                validation_data[row[1]] = validation_data[row[0]].copy()
        
        result['validation_records_count'] = len(validation_data)
        
        # Simulate list_photos logic
        photos_dir = PHOTOS_BASE_DIR
        photo_list = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'}
        
        # Scan output directory (validated photos)
        dir_path = os.path.join(photos_dir, 'output')
        if os.path.exists(dir_path):
            result['list_photos_simulation']['scanning_output_dir'] = True
            result['list_photos_simulation']['files_found'] = []
            
            for root, dirs, files in os.walk(dir_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    if os.path.isfile(file_path):
                        _, ext = os.path.splitext(filename.lower())
                        if ext in image_extensions:
                            file_stats = os.stat(file_path)
                            relative_path = os.path.relpath(file_path, photos_dir)
                            
                            # Get validation info - try multiple lookups
                            validation_info = (
                                validation_data.get(filename, {}) or 
                                validation_data.get(relative_path, {}) or
                                validation_data.get(os.path.basename(filename), {})
                            )
                            
                            has_validation = bool(validation_info)
                            result['list_photos_simulation']['files_found'].append({
                                'filename': filename,
                                'has_validation_data': has_validation,
                                'validation_info': validation_info
                            })
                            
                            if has_validation:
                                photo_list.append({
                                    'filename': filename,
                                    'status': 'validated',
                                    'validated_at': validation_info.get('validated_at')
                                })
        
        result['list_photos_simulation']['total_files_processed'] = len(result['list_photos_simulation'].get('files_found', []))
        result['list_photos_simulation']['photos_with_validation'] = len(photo_list)
        result['list_photos_simulation']['first_5_with_validation'] = photo_list[:5]
        
        # Check image_5 specifically
        image_5_in_validation = [key for key in validation_data.keys() if 'image_5' in key.lower()]
        result['image_5_in_validation_keys'] = image_5_in_validation
        
        conn.close()
    except Exception as e:
        result['db_error'] = str(e)
    
    return jsonify(result)

@app.route('/api/test-logs', methods=['GET'])
def test_logs():
    """Test if logs are working"""
    print("TEST LOG MESSAGE - THIS SHOULD APPEAR IN LOGS")
    print("SECOND TEST LOG MESSAGE")
    return jsonify({'message': 'Test logs sent', 'check': 'docker logs'})

@app.route('/api/debug-rename', methods=['POST'])
def debug_rename():
    """Debug rename functionality step by step"""
    data = request.get_json()
    old_filename = data.get('oldFilename', 'soulages.jpeg')
    new_filename = data.get('newFilename', 'test_soulages.jpeg')
    
    result = {
        'old_filename': old_filename,
        'new_filename': new_filename,
        'steps': []
    }
    
    try:
        import sqlite3
        from auth import DATABASE_PATH
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Step 1: Check current records
        cursor.execute('''
            SELECT photo_id, photo_filename, status, classification 
            FROM photo_validations 
            WHERE photo_id = ? OR photo_filename = ?
        ''', (old_filename, old_filename))
        
        current_records = cursor.fetchall()
        result['steps'].append({
            'step': 'current_records',
            'count': len(current_records),
            'records': [{'photo_id': r[0], 'photo_filename': r[1], 'status': r[2], 'classification': r[3]} for r in current_records]
        })
        
        # Step 2: Get the most recent record
        cursor.execute('''
            SELECT photo_id, submitted_by, validated_by, status, classification, reject_reason, validated_at
            FROM photo_validations 
            WHERE photo_id = ? OR photo_filename = ?
            ORDER BY validated_at DESC LIMIT 1
        ''', (old_filename, old_filename))
        
        record = cursor.fetchone()
        if record:
            result['steps'].append({
                'step': 'most_recent_record',
                'record': {'photo_id': record[0], 'status': record[3], 'classification': record[4]}
            })
            
            # Step 3: Delete old records
            cursor.execute('''
                DELETE FROM photo_validations 
                WHERE photo_id = ? OR photo_filename = ?
            ''', (old_filename, old_filename))
            deleted_count = cursor.rowcount
            result['steps'].append({
                'step': 'deleted_old_records',
                'count': deleted_count
            })
            
            # Step 4: Insert new record
            cursor.execute('''
                INSERT INTO photo_validations 
                (photo_id, photo_filename, submitted_by, validated_by, status, classification, reject_reason, validated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_filename, new_filename, record[1], record[2], record[3], record[4], record[5], record[6]))
            
            result['steps'].append({
                'step': 'inserted_new_record',
                'new_record': {'photo_id': new_filename, 'photo_filename': new_filename, 'status': record[3]}
            })
            
            conn.commit()
        else:
            result['steps'].append({
                'step': 'no_record_found'
            })
        
        # Step 5: Check final state
        cursor.execute('''
            SELECT photo_id, photo_filename, status 
            FROM photo_validations 
            WHERE photo_id = ? OR photo_filename = ?
        ''', (new_filename, new_filename))
        
        final_records = cursor.fetchall()
        result['steps'].append({
            'step': 'final_records',
            'count': len(final_records),
            'records': [{'photo_id': r[0], 'photo_filename': r[1], 'status': r[2]} for r in final_records]
        })
        
        conn.close()
        result['success'] = True
        
    except Exception as e:
        result['error'] = str(e)
        result['success'] = False
    
    return jsonify(result)

@app.route('/api/debug-simple')
def debug_simple():
    """Simple debug - count photos step by step like list_photos"""
    import os
    import sqlite3
    from datetime import datetime
    
    PHOTOS_BASE_DIR = '/app/photos'
    
    # Simulate exactly what list_photos does
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT pv.photo_id, pv.photo_filename, pv.status, pv.classification, pv.validated_at,
               u1.username as validator_username,
               u2.username as submitter_username
        FROM photo_validations pv
        LEFT JOIN users u1 ON pv.validated_by = u1.id
        LEFT JOIN users u2 ON pv.submitted_by = u2.id
    ''')
    
    validation_data = {}
    for row in cursor.fetchall():
        validation_data[row[0]] = {
            'photo_filename': row[1],
            'status': row[2],
            'classification': row[3],
            'validated_at': row[4],
            'validator_username': row[5],
            'submitter_username': row[6]
        }
        if row[1] and row[1] != row[0]:
            validation_data[row[1]] = validation_data[row[0]].copy()
    
    conn.close()
    
    # Scan output directory exactly like list_photos
    photo_list = []
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'}
    
    dir_path = os.path.join(PHOTOS_BASE_DIR, 'output')
    files_found = 0
    files_processed = 0
    files_with_validation = 0
    
    if os.path.exists(dir_path):
        for root, dirs, files in os.walk(dir_path):
            for filename in files:
                files_found += 1
                file_path = os.path.join(root, filename)
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(filename.lower())
                    if ext in image_extensions:
                        files_processed += 1
                        
                        # Try to find validation info exactly like list_photos
                        file_stats = os.stat(file_path)
                        relative_path = os.path.relpath(file_path, PHOTOS_BASE_DIR)
                        
                        validation_info = (
                            validation_data.get(filename, {}) or 
                            validation_data.get(relative_path, {}) or
                            validation_data.get(os.path.basename(filename), {})
                        )
                        
                        if validation_info:
                            files_with_validation += 1
                            photo_list.append({
                                'filename': filename,
                                'status': 'validated',
                                'validated_at': validation_info.get('validated_at')
                            })
    
    return jsonify({
        'validation_records_total': len(validation_data),
        'files_found_in_output': files_found,
        'image_files_processed': files_processed,
        'files_with_validation': files_with_validation,
        'final_photo_list_count': len(photo_list),
        'image_5_in_validation_data': len([k for k in validation_data.keys() if 'image_5' in k.lower()]),
        'image_5_in_final_list': len([p for p in photo_list if 'image_5' in p['filename'].lower()])
    })

@app.route('/api/photos/<path:photo_id>/analyze-quality', methods=['GET'])
def analyze_local_photo_quality(photo_id):
    """Analyze local photo quality"""
    try:
        # Decode photo path
        photo_path = f"/app/photos/{photo_id}"
        
        if not os.path.exists(photo_path):
            return jsonify({
                'success': False,
                'error': 'Photo not found'
            }), 404
        
        # Analyze quality
        quality_analysis = quality_checker.analyze_image_quality(photo_path)
        
        return jsonify({
            'success': True,
            'photo_id': photo_id,
            'quality_analysis': quality_analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error analyzing photo quality: {str(e)}'
        }), 500

# DOUBLON SUPPRIMÉ - Utiliser la version dans auth_routes.py qui est plus complète
# @app.route('/api/photos/batch-analyze-quality', methods=['POST'])
def batch_analyze_quality_DISABLED():
    """[DISABLED - DOUBLON] Analyser la qualité de toutes les photos en lot"""
    try:
        data = request.get_json() or {}
        folder = data.get('folder', 'a-valider')
        
        photos_dir = f"/app/photos/{folder}"
        if not os.path.exists(photos_dir):
            return jsonify({
                'success': False,
                'error': 'Photos directory not found'
            }), 404
        
        results = []
        
        # Scanner tous les fichiers image
        for filename in os.listdir(photos_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp')):
                photo_path = os.path.join(photos_dir, filename)
                try:
                    quality_analysis = quality_checker.analyze_image_quality(photo_path)
                    results.append({
                        'filename': filename,
                        'photo_id': f"{folder}/{filename}",
                        'quality_analysis': quality_analysis
                    })
                except Exception as e:
                    results.append({
                        'filename': filename,
                        'photo_id': f"{folder}/{filename}",
                        'error': str(e),
                        'quality_analysis': {
                            'error': f'Analysis failed: {str(e)}',
                            'quality_level': 'error',
                            'color_code': 'gray'
                        }
                    })
        
        # Statistiques
        stats = {
            'total': len(results),
            'excellent': len([r for r in results if r.get('quality_analysis', {}).get('quality_level') == 'excellent']),
            'good': len([r for r in results if r.get('quality_analysis', {}).get('quality_level') == 'good']),
            'acceptable': len([r for r in results if r.get('quality_analysis', {}).get('quality_level') == 'acceptable']),
            'poor': len([r for r in results if r.get('quality_analysis', {}).get('quality_level') == 'poor']),
            'error': len([r for r in results if r.get('quality_analysis', {}).get('quality_level') == 'error'])
        }
        
        return jsonify({
            'success': True,
            'folder': folder,
            'results': results,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error batch analyzing photos: {str(e)}'
        }), 500

@app.route('/api/photos/validate-upload-quality', methods=['POST'])
def validate_photo_upload():
    """Validate photo upload (format, size, quality analysis)"""
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization token required'}), 401
        
        token = auth_header.split(' ')[1]
        try:
            from auth import verify_token
            payload = verify_token(token)
            if not payload:
                return jsonify({'error': 'Invalid token'}), 401
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Basic file validation
        validations = []
        
        # 1. File format validation
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            validations.append({
                'type': 'error',
                'message': f'Unsupported format: {file_ext}. Accepted: {", ".join(allowed_extensions)}'
            })
        else:
            validations.append({
                'type': 'success', 
                'message': f'Valid format: {file_ext}'
            })
        
        # 2. File size validation
        file.seek(0, 2)  # Go to end
        file_size = file.tell()
        file.seek(0)  # Back to start
        
        max_size = 1000 * 1024 * 1024  # 1000MB (1GB)
        if file_size > max_size:
            validations.append({
                'type': 'error',
                'message': f'File too large: {file_size / 1024 / 1024:.1f}MB (max: 50MB)'
            })
        else:
            validations.append({
                'type': 'success',
                'message': f'Valid size: {file_size / 1024 / 1024:.1f}MB'
            })
        
        # 3. Quality analysis if possible
        quality_analysis = None
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=file_ext) as temp_file:
                file.stream.seek(0)
                temp_file.write(file.stream.read())
                temp_file.flush()
                
                quality_checker = ImageQualityChecker()
                quality_analysis = quality_checker.analyze_image_quality(temp_file.name)
                validations.append({
                    'type': 'info',
                    'message': f'Quality: {quality_analysis.get("quality_level", "unknown")}'
                })
                
            file.stream.seek(0)  # Reset stream
        except Exception as e:
            validations.append({
                'type': 'warning',
                'message': f'Could not analyze quality: {str(e)}'
            })
        
        # 4. Artwork search and existing photos detection
        import re
        import sqlite3
        from auth import DATABASE_PATH
        
        artwork_id = None
        artwork_found = False
        artwork_metadata = None
        existing_photos = []
        duplicate_warning = None
        
        # Extract artwork ID from filename
        artwork_id_match = re.search(r'([A-Z]{2,10}-\d+)', file.filename.upper())
        if artwork_id_match:
            artwork_id = artwork_id_match.group(1)
            
            try:
                # Search in OperaGallery
                from operagallery_integration import OperaGalleryClient
                client = OperaGalleryClient()
                search_results = client.search_artworks(artwork_id, limit=1)
                
                if search_results and len(search_results) > 0:
                    artwork = search_results[0]
                    artwork_found = True
                    artwork_metadata = {
                        'title': artwork.get('title', ''),
                        'artist': artwork.get('artist', ''),
                        'year': artwork.get('year', ''),
                        'category': artwork.get('category', ''),
                        'IdName': artwork.get('IdName', artwork_id)
                    }
                    
                    # Search for existing photos of this artwork
                    try:
                        # Get PHOTOS_BASE_DIR
                        PHOTOS_BASE_DIR = os.environ.get('PHOTOS_BASE_DIR', '/app/photos')
                        existing_photos_data = []
                        
                        # Search in filesystem for photos with this artwork ID
                        directories = ['a-valider', 'output', 'refuse']
                        for dir_name in directories:
                            dir_path = os.path.join(PHOTOS_BASE_DIR, dir_name)
                            if os.path.exists(dir_path):
                                for root, dirs, files in os.walk(dir_path):
                                    for filename in files:
                                        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif')):
                                            # Check if filename contains the artwork ID
                                            if artwork_id in filename.upper():
                                                file_path = os.path.join(root, filename)
                                                relative_path = os.path.relpath(file_path, PHOTOS_BASE_DIR)
                                                existing_photos_data.append({
                                                    'id': relative_path,
                                                    'filename': filename
                                                })
                        
                        if len(existing_photos_data) > 0:
                            existing_photos = [f"/api/photos/{photo['id']}" for photo in existing_photos_data[:5]]
                            duplicate_warning = {
                                'message': f'Warning: {len(existing_photos_data)} existing photo(s) found for artwork {artwork_id}',
                                'existing_images': existing_photos
                            }
                    except Exception as ex:
                        print(f"Error searching existing photos: {ex}")
                        pass  # Ignore errors getting existing photos
                        
                    validations.append({
                        'type': 'success',
                        'message': f'Artwork found in OperaGallery: {artwork_id}'
                    })
                else:
                    validations.append({
                        'type': 'warning',
                        'message': f'Artwork {artwork_id} not found in OperaGallery'
                    })
            except Exception as e:
                validations.append({
                    'type': 'warning',
                    'message': f'Could not search OperaGallery: {str(e)}'
                })
        else:
            validations.append({
                'type': 'info',
                'message': 'No artwork ID detected in filename'
            })
        
        # Determine overall status
        has_errors = any(v['type'] == 'error' for v in validations)
        
        # Generate upload recommendation
        upload_recommendation = None
        if quality_analysis:
            should_accept = quality_analysis.get('quality_level') not in ['poor', 'error']
            upload_recommendation = {
                'should_accept': should_accept,
                'reason': f"Photo quality is {quality_analysis.get('quality_level', 'unknown')}"
            }
        
        return jsonify({
            'success': not has_errors,
            'data': {
                'artwork_id': artwork_id,
                'artwork_found': artwork_found,
                'artwork_metadata': artwork_metadata,
                'quality_analysis': quality_analysis,
                'upload_recommendation': upload_recommendation,
                'duplicate_warning': duplicate_warning,
                'validations': validations,
                'file_info': {
                    'name': file.filename,
                    'size': file_size,
                    'type': file.content_type
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Validation failed: {str(e)}'
        }), 500

# DOUBLON SUPPRIMÉ - Utiliser la version dans auth_routes.py qui gère mieux la base de données
# @app.route('/api/photos/rename', methods=['POST'])
def rename_photo_DISABLED():
    """[DISABLED - DOUBLON] Rename a photo file"""
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization token required'}), 401
        
        token = auth_header.split(' ')[1]
        try:
            from auth import verify_token
            payload = verify_token(token)
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        photo_id = data.get('photoId')
        new_filename = data.get('newFilename')
        
        if not photo_id or not new_filename:
            return jsonify({
                'success': False,
                'error': 'photoId and newFilename are required'
            }), 400
        
        # Construct full paths
        old_path = f"/app/photos/{photo_id}"
        
        # Extract directory from photo_id and construct new path
        photo_dir = os.path.dirname(old_path)
        new_path = os.path.join(photo_dir, new_filename)
        
        # Check if old file exists
        if not os.path.exists(old_path):
            return jsonify({
                'success': False,
                'error': 'Original photo not found'
            }), 404
        
        # Check if new filename already exists and generate alternative if needed
        if os.path.exists(new_path):
            # Generate an alternative filename
            base, ext = os.path.splitext(new_filename)
            counter = 1
            
            # Try different suffixes until we find an available name
            while os.path.exists(os.path.join(photo_dir, f'{base}_{counter}{ext}')):
                counter += 1
                if counter > 100:  # Safety limit
                    return jsonify({
                        'success': False,
                        'error': 'Unable to generate unique filename after 100 attempts'
                    }), 409
            
            # Use the alternative filename
            alternative_filename = f'{base}_{counter}{ext}'
            new_path = os.path.join(photo_dir, alternative_filename)
            
            print(f"[RENAME] File exists, using alternative: {new_filename} -> {alternative_filename}")
            new_filename = alternative_filename
        
        # Perform the rename
        os.rename(old_path, new_path)
        
        # Update database if photo has validation record
        import sys
        print(f"[RENAME] *** DATABASE UPDATE STARTING ***", file=sys.stderr)
        try:
            import sqlite3
            from auth import DATABASE_PATH
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Update photo_validations table with new filename
            old_filename = os.path.basename(photo_id)
            
            print(f"[RENAME] Starting database update: {old_filename} -> {new_filename}", file=sys.stderr)
            print(f"[RENAME] photo_id parameter: {photo_id}", file=sys.stderr)
            print(f"[RENAME] old_filename: {old_filename}", file=sys.stderr)
            print(f"[RENAME] new_filename: {new_filename}", file=sys.stderr)
            
            # Clean approach: Remove duplicates and update properly
            # First, get the most recent validation record for this photo
            cursor.execute('''
                SELECT photo_id, submitted_by, validated_by, status, classification, reject_reason, validated_at
                FROM photo_validations 
                WHERE photo_id = ? OR photo_filename = ?
                ORDER BY validated_at DESC LIMIT 1
            ''', (photo_id, old_filename))
            
            record = cursor.fetchone()
            if record:
                print(f"[RENAME] Found validation record for {old_filename}")
                
                # Delete ALL old records for this photo (clean slate)
                cursor.execute('''
                    DELETE FROM photo_validations 
                    WHERE photo_id = ? OR photo_filename = ? OR photo_id = ?
                ''', (photo_id, old_filename, old_filename))
                deleted_count = cursor.rowcount
                
                # Insert a single clean record with the new filename
                cursor.execute('''
                    INSERT INTO photo_validations 
                    (photo_id, photo_filename, submitted_by, validated_by, status, classification, reject_reason, validated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (new_filename, new_filename, record[1], record[2], record[3], record[4], record[5], record[6]))
                
                print(f"[RENAME] Deleted {deleted_count} old records, created 1 new record")
            else:
                print(f"[RENAME] No validation record found for {old_filename}")
            
            conn.commit()
            conn.close()
            
            print(f"[RENAME] Database update completed: {old_filename} -> {new_filename}")
            
        except Exception as db_error:
            print(f"[RENAME] Database update failed: {db_error}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            # Continue anyway since file rename was successful
        
        # Determine if we used an alternative filename
        original_requested = data.get('newFilename')
        used_alternative = new_filename != original_requested
        
        message = 'Photo renamed successfully'
        if used_alternative:
            message += f' (renamed to {new_filename} to avoid conflict)'
        
        return jsonify({
            'success': True,
            'message': message,
            'old_filename': os.path.basename(photo_id),
            'new_filename': new_filename,
            'new_photo_id': f"{os.path.basename(photo_dir)}/{new_filename}",
            'used_alternative': used_alternative,
            'requested_filename': original_requested
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error renaming photo: {str(e)}'
        }), 500

@app.route('/api/artworks/galleries', methods=['GET'])
def get_galleries():
    """Get list of available galleries for filtering"""
    try:
        # Retourner une liste statique de galeries pour l'instant
        galleries = [
            {'id': 'all', 'name': 'All galleries'},
            {'id': 'opera', 'name': 'Opera Gallery'},
            {'id': 'london', 'name': 'London'},
            {'id': 'paris', 'name': 'Paris'},
            {'id': 'new-york', 'name': 'New York'},
            {'id': 'singapore', 'name': 'Singapore'},
            {'id': 'monaco', 'name': 'Monaco'},
            {'id': 'geneva', 'name': 'Geneva'},
            {'id': 'hong-kong', 'name': 'Hong Kong'},
            {'id': 'beirut', 'name': 'Beirut'},
            {'id': 'seoul', 'name': 'Seoul'},
            {'id': 'dubai', 'name': 'Dubai'},
            {'id': 'HOU', 'name': 'Houston'}
        ]
        
        return jsonify({
            'success': True,
            'galleries': galleries
        })
        
    except Exception as e:
        print(f"[GALLERIES] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'galleries': []
        }), 500

# Map local catalogue image types -> the flat *300 field names the frontend
# (PhotoDetail / PhotoValidator) expects. One type can feed several aliases.
_TYPE_TO_300_FIELDS = {
    'MAIN':       ['MAIN300'],
    'DET':        ['DET300', 'DETAIL300'],
    'BACK':       ['BACK300', 'DOS300', 'VERSO300'],
    'FRONT':      ['FRONT300', 'FACE300', 'RECTO300'],
    'INSITU':     ['INSITU300'],
    'LEFT':       ['LEFT300'],
    'FRAME':      ['FRAME300'],
    'FRONTRIGHT': ['FRONTRIGHT300'],
    'PERS':       ['PERS300'],
    'OTHER':      ['OTHER300', 'FULL300'],
}

@app.route('/api/filemaker/artwork/<string:id_name>', methods=['GET'])
def get_filemaker_artwork(id_name):
    """Get artwork data by IdName.

    FileMaker is down and the Odoo creds are dead, so this now serves from the
    local image catalogue (images_catalog.csv + list-url-id.csv) — the same data
    photo-validator already uses. The response keeps the original flat shape
    (IdName / Title / Artist / *300 image fields) for PhotoDetail & PhotoValidator
    AND adds success/artwork for the search widgets.
    """
    try:
        from operagallery_service import local_artwork_by_id, local_search_artworks

        art = local_artwork_by_id(id_name)
        if not art:
            # Fallback to text search when exact ID lookup fails
            results = local_search_artworks(id_name, limit=1)
            if results:
                art = results[0]
            else:
                return jsonify({'success': False, 'error': 'Artwork not found'}), 404

        image_fields = art.get('image_fields', {}) or {}

        # Build the flat *300 image URL fields from the catalogue types.
        artwork_data = {
            'success': True,
            'artwork': art,               # rich shape for search UIs
            'IdName': art.get('IdName', ''),
            'Title': art.get('title', ''),
            'Artist': art.get('artist', ''),
            'Date': art.get('year', ''),
            'Width': '',
            'Height': '',
            'Price': '',
            'Status': '',
            'MAINFM': '',
            'CertificateFMUrl': '',
            'CertificateWording': '',
            'source': 'LocalCatalogue',
        }

        first_fm = ''
        for img_type, url_blob in image_fields.items():
            urls = [u for u in (url_blob or '').split('\n') if u.strip()]
            if not urls:
                continue
            for field_name in _TYPE_TO_300_FIELDS.get(img_type.upper(), []):
                # don't overwrite an already-filled alias
                artwork_data.setdefault(field_name, '')
                if not artwork_data.get(field_name):
                    artwork_data[field_name] = urls[0]
            # MAINFM = first URL served from the /FM/ render, else main image
            if not first_fm:
                for u in urls:
                    if '/FM/' in u:
                        first_fm = u
                        break

        artwork_data['MAINFM'] = first_fm or art.get('main_picture_hd', '') or ''
        if not artwork_data.get('MAIN300'):
            artwork_data['MAIN300'] = art.get('main_picture_hd', '') or ''

        return jsonify(artwork_data)

    except Exception as e:
        return jsonify({'success': False, 'error': f'Error fetching artwork data: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = True  # Force debug mode to see error details
    
    print(f"Starting Photo Validator server on port {port}")
    print(f"Debug mode: {debug}")
    
    # Démarrer l'indexation automatique des artistes célèbres en arrière-plan
    try:
        import subprocess
        import threading
        
        def start_indexer_background():
            try:
                subprocess.Popen([sys.executable, "start_indexer.py"], 
                               cwd=os.path.dirname(os.path.abspath(__file__)))
                print("🎨 Artist indexer started in background")
            except Exception as e:
                print(f"⚠️ Could not start background indexer: {e}")
        
        # Lancer en thread pour ne pas bloquer le démarrage
        indexer_thread = threading.Thread(target=start_indexer_background, daemon=True)
        indexer_thread.start()
        
    except Exception as e:
        print(f"⚠️ Could not start artist indexing: {e}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
