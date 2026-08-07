#!/usr/bin/env python3
"""
Service for managing and downloading PDF certificates
"""

import os
import requests
import tempfile
from flask import Blueprint, request, jsonify, send_file, Response
from auth import verify_token
from filemaker_service import filemaker_service
from urllib.parse import urlparse
import mimetypes
import time

certificate_bp = Blueprint('certificate', __name__)

def get_certificate_url(artwork_id):
    """Retrieve certificate URL from FileMaker"""
    try:
        artwork = filemaker_service.find_artwork_by_id(artwork_id)
        if artwork and 'CertificateFMUrl' in artwork:
            cert_url = artwork['CertificateFMUrl'].strip()
            return cert_url if cert_url else None
        return None
    except Exception as e:
        print(f"[CERT] Error retrieving certificate URL {artwork_id}: {e}")
        return None

def download_certificate_file(cert_url):
    """Download certificate file from URL"""
    try:
        # Headers to simulate a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        }
        
        response = requests.get(
            cert_url,
            headers=headers,
            timeout=30,
            verify=False,  # For self-signed certificates
            stream=True
        )
        
        if response.status_code == 200:
            # Check content-type
            content_type = response.headers.get('content-type', '').lower()

            if 'pdf' in content_type or 'application/pdf' in content_type:
                return response.content, 'application/pdf'
            elif 'octet-stream' in content_type:
                # Often used for PDFs
                return response.content, 'application/pdf'
            else:
                print(f"[CERT] Unexpected content-type: {content_type}")
                return response.content, 'application/pdf'  # Try anyway
        else:
            print(f"[CERT] HTTP error {response.status_code} for {cert_url}")
            return None, None
            
    except Exception as e:
        print(f"[CERT] Download error {cert_url}: {e}")
        return None, None

@certificate_bp.route('/api/certificate/download/<artwork_id>')
def download_certificate(artwork_id):
    """Download artwork certificate"""
    try:
        # Verify authentication
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401

        print(f"[CERT] Downloading certificate for {artwork_id}")

        # Get certificate URL
        cert_url = get_certificate_url(artwork_id)
        if not cert_url:
            return jsonify({'error': 'No certificate for this artwork'}), 404

        print(f"[CERT] Certificate URL: {cert_url}")

        # Download file
        file_content, content_type = download_certificate_file(cert_url)
        if not file_content:
            return jsonify({'error': 'Unable to download certificate'}), 500

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        # Clean filename
        safe_artwork_id = artwork_id.replace('/', '_').replace('\\', '_')
        filename = f"Certificate_{safe_artwork_id}.pdf"

        print(f"[CERT] Sending file: {filename} ({len(file_content)} bytes)")
        
        try:
            return send_file(
                tmp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        finally:
            # Clean up temporary file after delay
            def cleanup():
                time.sleep(2)
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            
            import threading
            threading.Thread(target=cleanup, daemon=True).start()
            
    except Exception as e:
        print(f"[CERT] Error downloading certificate {artwork_id}: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@certificate_bp.route('/api/certificate/info/<artwork_id>')
def get_certificate_info(artwork_id):
    """Get certificate info for an artwork"""
    try:
        # Verify authentication
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401

        # Get FileMaker data
        artwork = find_artwork_by_id(artwork_id)
        if not artwork:
            return jsonify({'error': 'Artwork not found'}), 404
        
        cert_url = artwork.get('CertificateFMUrl', '').strip()
        cert_wording = artwork.get('CertificateWording', '').strip()
        
        return jsonify({
            'artwork_id': artwork_id,
            'has_certificate': bool(cert_url),
            'certificate_url': cert_url,
            'certificate_wording': cert_wording,
            'download_available': bool(cert_url)
        })
        
    except Exception as e:
        print(f"[CERT] Error getting certificate info {artwork_id}: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@certificate_bp.route('/api/certificate/batch-download', methods=['POST'])
def batch_download_certificates():
    """Download multiple certificates in ZIP"""
    try:
        # Verify admin authentication
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload or payload.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        data = request.get_json()
        artwork_ids = data.get('artwork_ids', [])

        if not artwork_ids:
            return jsonify({'error': 'Artwork list required'}), 400

        print(f"[CERT] Batch download: {len(artwork_ids)} artworks")
        
        import zipfile
        import io
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            successful_downloads = 0

            for artwork_id in artwork_ids:
                try:
                    cert_url = get_certificate_url(artwork_id)
                    if not cert_url:
                        print(f"[CERT] No certificate for {artwork_id}")
                        continue

                    file_content, _ = download_certificate_file(cert_url)
                    if file_content:
                        safe_id = artwork_id.replace('/', '_').replace('\\', '_')
                        filename = f"Certificate_{safe_id}.pdf"
                        zip_file.writestr(filename, file_content)
                        successful_downloads += 1
                        print(f"[CERT] Added to ZIP: {filename}")

                except Exception as e:
                    print(f"[CERT] Error for {artwork_id}: {e}")
                    continue

        if successful_downloads == 0:
            return jsonify({'error': 'No downloadable certificates'}), 404

        zip_buffer.seek(0)

        print(f"[CERT] ZIP created: {successful_downloads} certificates")
        
        return Response(
            zip_buffer.getvalue(),
            mimetype='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="Certificates_{len(artwork_ids)}_artworks.zip"',
                'Content-Length': str(len(zip_buffer.getvalue()))
            }
        )

    except Exception as e:
        print(f"[CERT] Batch download error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@certificate_bp.route('/api/certificate/update-url/<artwork_id>', methods=['POST'])
def update_certificate_url(artwork_id):
    """Update certificate URL (admin only)"""
    try:
        # Verify admin authentication
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401

        token = token.split(' ')[1]
        payload = verify_token(token)
        if not payload or payload.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        data = request.get_json()
        new_url = data.get('certificate_url', '').strip()
        certificate_wording = data.get('certificate_wording', '').strip()

        # TODO: Implement update in FileMaker
        # For now, return explicit error
        return jsonify({
            'error': 'Certificate update not yet implemented',
            'todo': 'Implement FileMaker update API'
        }), 501

    except Exception as e:
        print(f"[CERT] Certificate update error {artwork_id}: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
