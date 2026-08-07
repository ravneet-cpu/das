#!/usr/bin/env python3
"""
Simple email test
"""

from email_service import email_service

# Test une seule fois avec un email de rejet
print("🧪 Testing single rejection email...")

try:
    success = email_service.send_rejection_email(
        user_email='surafell@operacrm.com',  # Email de test 
        username='TestUser',
        photo_id='TEST-123-MAIN.jpg',
        reject_reason='Poor photo quality',
        validator_username='SystemTest'
    )
    
    if success:
        print("✅ Test email sent successfully!")
        print("📧 Check surafell@operacrm.com for the email")
    else:
        print("❌ Failed to send test email")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\nDone!")