#!/usr/bin/env python3
"""
Test script for the photo validator backend
"""

import requests
import json
import sys

def test_endpoints():
    """Test all the API endpoints"""
    base_url = "http://localhost:5000"
    
    print("Testing Photo Validator API endpoints...")
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"✓ Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
    
    # Test 2: Auth status
    try:
        response = requests.get(f"{base_url}/api/auth/status")
        print(f"✓ Auth status: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"✗ Auth status failed: {e}")
    
    # Test 3: Login
    try:
        login_data = {
            "username": "admin",
            "password": "adminpass"
        }
        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        result = response.json()
        print(f"✓ Login: {response.status_code} - Success: {result.get('success', False)}")
        
        # Get token for authenticated requests
        token = result.get('token')
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        
        # Test 4: Get users (requires auth)
        if token:
            try:
                response = requests.get(f"{base_url}/api/auth/users", headers=headers)
                users = response.json()
                print(f"✓ Get users: {response.status_code} - Found {len(users.get('users', []))} users")
            except Exception as e:
                print(f"✗ Get users failed: {e}")
            
            # Test 5: Get tasks (requires auth)
            try:
                response = requests.get(f"{base_url}/api/tasks", headers=headers)
                tasks = response.json()
                print(f"✓ Get tasks: {response.status_code} - Found {len(tasks.get('tasks', []))} tasks")
            except Exception as e:
                print(f"✗ Get tasks failed: {e}")
            
            # Test 6: Photo endpoints
            try:
                response = requests.get(f"{base_url}/api/photos/next", headers=headers)
                print(f"✓ Get next photo: {response.status_code} - {response.json()}")
            except Exception as e:
                print(f"✗ Get next photo failed: {e}")
            
            try:
                response = requests.get(f"{base_url}/api/photos/stats", headers=headers)
                print(f"✓ Get photo stats: {response.status_code} - {response.json()}")
            except Exception as e:
                print(f"✗ Get photo stats failed: {e}")
            
            # Test 7: Photo details (with a sample filename)
            try:
                sample_photo = "Leger_Fernand_LEGEFE_50346_Visage_à_la_main,_1950,_VERSO.jpg"
                response = requests.get(f"{base_url}/api/photos/details/{sample_photo}", headers=headers)
                if response.status_code == 200:
                    details = response.json()
                    print(f"✓ Get photo details: {response.status_code} - {details}")
                else:
                    print(f"✓ Get photo details: {response.status_code} - Photo not found (expected)")
            except Exception as e:
                print(f"✗ Get photo details failed: {e}")
        
    except Exception as e:
        print(f"✗ Login failed: {e}")
    
    print("\nAPI testing completed!")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If a URL is provided as argument, use it
        base_url = sys.argv[1]
    
    test_endpoints()