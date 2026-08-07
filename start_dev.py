#!/usr/bin/env python3
"""
Development server script for photo validator
"""

import os
import sys
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth_routes import auth_bp

app = Flask(__name__)
CORS(app)

# Enable debug mode for development
app.config['DEBUG'] = True

# Register the auth blueprint
app.register_blueprint(auth_bp)

# Serve static files from src directory for development
@app.route('/')
def serve_dev_index():
    # For development, we'll serve a simple test page
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Photo Validator - Development Server</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-left: 4px solid #007cba; }
            .method { color: #007cba; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>Photo Validator - Development Server</h1>
        <p>Backend server is running successfully!</p>
        
        <h2>Available API Endpoints:</h2>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/health - Health check
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/auth/status - Authentication status
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> /api/auth/login - User login
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/auth/users - List users (admin only)
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> /api/auth/create-user - Create new user (admin only)
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/tasks - List tasks
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> /api/tasks - Create new task
        </div>
        
        <div class="endpoint">
            <span class="method">PUT</span> /api/tasks/{id} - Update task
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/tasks/{id}/history - Get task history
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/photos/next - Get next photo to validate
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/photos/{id} - Get photo file
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/photos/details/{id} - Get photo details
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> /api/photos/validate - Validate/reject photo
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/photos/list - List photos
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/photos/stats - Get photo statistics
        </div>
        
        <h2>Default Login:</h2>
        <p><strong>Username:</strong> admin</p>
        <p><strong>Password:</strong> adminpass</p>
        
        <h2>Test the API:</h2>
        <p>You can test the endpoints using curl or any HTTP client:</p>
        <pre>
# Login example:
curl -X POST http://localhost:5000/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "admin", "password": "adminpass"}'

# Get photo details example:
curl http://localhost:5000/api/photos/details/sample_photo.jpg
        </pre>
    </body>
    </html>
    """

@app.route('/test')
def test_page():
    """Test page to verify API functionality"""
    return jsonify({
        'message': 'Photo Validator API is working!',
        'endpoints': [
            'GET /api/health',
            'GET /api/auth/status',
            'POST /api/auth/login',
            'GET /api/auth/users',
            'POST /api/auth/create-user',
            'GET /api/tasks',
            'POST /api/tasks',
            'PUT /api/tasks/{id}',
            'GET /api/tasks/{id}/history',
            'GET /api/photos/next',
            'GET /api/photos/{id}',
            'GET /api/photos/details/{id}',
            'POST /api/photos/validate',
            'GET /api/photos/list',
            'GET /api/photos/stats'
        ]
    })

if __name__ == '__main__':
    print("Starting Photo Validator Development Server...")
    print("Backend API will be available at: http://localhost:5001")
    print("Test page: http://localhost:5001")
    print("API test endpoint: http://localhost:5001/test")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)