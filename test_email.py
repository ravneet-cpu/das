#!/usr/bin/env python3
"""
Test script for email functionality
"""

from email_service import email_service

def test_rejection_emails():
    """Test different rejection email templates"""
    print("🧪 Testing rejection email templates...")
    
    test_cases = [
        {
            'email': 'test@example.com',
            'username': 'TestUser',
            'photo_id': 'AB-123-MAIN.jpg',
            'reason': 'Poor photo quality',
            'validator': 'AdminValidator'
        },
        {
            'email': 'test@example.com',
            'username': 'TestUser',
            'photo_id': 'CD-456-DETAIL.jpg',
            'reason': 'Bad lighting',
            'validator': 'AdminValidator'
        },
        {
            'email': 'test@example.com',
            'username': 'TestUser',
            'photo_id': 'EF-789-FRAME.jpg',
            'reason': 'Blurry photo',
            'validator': 'AdminValidator'
        },
        {
            'email': 'test@example.com',
            'username': 'TestUser',
            'photo_id': 'GH-101-MAIN.jpg',
            'reason': 'Reflections on artwork',
            'validator': 'AdminValidator'
        },
        {
            'email': 'test@example.com',
            'username': 'TestUser',
            'photo_id': 'IJ-202-DETAIL.jpg',
            'reason': 'Duplicate artwork detected',
            'validator': 'AdminValidator'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {case['reason']} ---")
        try:
            success = email_service.send_rejection_email(
                user_email=case['email'],
                username=case['username'],
                photo_id=case['photo_id'],
                reject_reason=case['reason'],
                validator_username=case['validator']
            )
            if success:
                print(f"✅ Test {i} passed")
            else:
                print(f"❌ Test {i} failed")
        except Exception as e:
            print(f"❌ Test {i} error: {e}")

def test_validation_email():
    """Test validation email"""
    print("\n🧪 Testing validation email...")
    
    try:
        success = email_service.send_validation_email(
            user_email='test@example.com',
            username='TestUser',
            photo_id='AB-123-MAIN.jpg',
            validator_username='AdminValidator',
            classification='MAIN'
        )
        if success:
            print("✅ Validation email test passed")
        else:
            print("❌ Validation email test failed")
    except Exception as e:
        print(f"❌ Validation email test error: {e}")

def test_smtp_connection():
    """Test SMTP connection without sending emails"""
    print("🔌 Testing SMTP connection...")
    
    import smtplib
    from email_service import SMTP_CONFIG
    
    try:
        with smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port']) as server:
            server.starttls()
            server.login(SMTP_CONFIG['username'], SMTP_CONFIG['password'])
            print("✅ SMTP connection successful")
            return True
    except Exception as e:
        print(f"❌ SMTP connection failed: {e}")
        return False

if __name__ == "__main__":
    print("📧 Email Service Test Suite")
    print("=" * 50)
    
    # Test SMTP connection first
    if test_smtp_connection():
        print("\n⚠️  SMTP connection is working!")
        print("⚠️  The following tests will send REAL emails to test@example.com")
        print("⚠️  Make sure this is okay before proceeding.")
        
        response = input("\nDo you want to send test emails? (y/N): ").strip().lower()
        
        if response == 'y':
            # Test rejection emails
            test_rejection_emails()
            
            # Test validation email
            test_validation_email()
            
            print("\n🎉 All email tests completed!")
        else:
            print("📧 Email sending tests skipped.")
    else:
        print("\n❌ SMTP connection failed. Check configuration.")
        print("Current SMTP settings:")
        print(f"  Server: {SMTP_CONFIG['server']}")
        print(f"  Port: {SMTP_CONFIG['port']}")
        print(f"  Username: {SMTP_CONFIG['username']}")
        print(f"  From: {SMTP_CONFIG['from_email']}")