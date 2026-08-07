#!/usr/bin/env python3
"""
Email service for photo validation notifications
Supports multiple templates based on rejection reasons
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

# SMTP Configuration for Sendlayer
SMTP_CONFIG = {
    'server': 'smtp.sendlayer.net',
    'port': 587,
    'username': 'FFC4F03122CCDA0CB8F8685AA873BDAC',
    'password': '9E6FA9082F30587C9C2D259CE57B42CF',
    'from_email': 'noreply@operagallery.com',
    'from_name': 'Operagallery.com Validation Team'
}

class EmailTemplates:
    """Email templates for different rejection reasons"""
    
    @staticmethod
    def get_subject(reason, photo_id):
        """Get email subject based on rejection reason"""
        subjects = {
            'Poor photo quality': f'Photo Quality Issue - {photo_id}',
            'Bad lighting': f'Lighting Issue - {photo_id}',
            'Blurry photo': f'Photo Clarity Issue - {photo_id}',
            'Poor framing': f'Photo Framing Issue - {photo_id}',
            'Reflections on artwork': f'Reflection Issue - {photo_id}',
            'Partially visible artwork': f'Visibility Issue - {photo_id}',
            'Color issues': f'Color Accuracy Issue - {photo_id}',
            'Inappropriate format': f'Format Issue - {photo_id}',
            'Incorrect filename': f'Filename Issue - {photo_id}',
            'Artwork not found in database': f'Artwork Not Found - {photo_id}',
            'Duplicate artwork detected': f'Duplicate Detected - {photo_id}',
            'Potential duplicate found in Odoo': f'Potential Duplicate - {photo_id}',
        }
        return subjects.get(reason, f'Photo Rejected - {photo_id}')
    
    @staticmethod
    def get_template(reason, username, photo_id, validator_username):
        """Get email template based on rejection reason"""
        
        common_footer = f"""
Best regards,
Operagallery.com Validation Team

---
Validation Details:
• Validator: {validator_username}
• Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Photo: {photo_id}

For questions, please contact: info@operacrm.com
"""
        
        templates = {
            'Poor photo quality': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected due to insufficient image quality.

📷 ISSUE: Poor Photo Quality
The image does not meet our quality standards for archival purposes.

🔧 WHAT TO DO:
• Use a higher resolution camera or scan settings (minimum 300 DPI for A5 print quality)
• Ensure the image is sharp and well-focused
• Check that the file is not overly compressed
• Consider professional photography equipment if available

💡 TIP: For artwork photography, use good lighting and a tripod to ensure crisp, high-quality images.

{common_footer}""",

            'Bad lighting': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected due to inadequate lighting conditions.

💡 ISSUE: Bad Lighting
The lighting in the photo does not adequately illuminate the artwork or creates unwanted shadows.

🔧 WHAT TO DO:
• Use even, diffused lighting from multiple angles
• Avoid harsh direct lighting that creates shadows
• Consider using professional photography lighting or natural daylight
• Ensure colors are accurately represented

💡 TIP: The best results come from using two light sources at 45-degree angles to the artwork.

{common_footer}""",

            'Blurry photo': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected due to image blur.

🔍 ISSUE: Blurry Photo
The image lacks sharpness and clarity required for archival documentation.

🔧 WHAT TO DO:
• Use a tripod to eliminate camera shake
• Ensure proper focus on the artwork
• Use adequate lighting to allow faster shutter speeds
• Check camera settings for optimal focus

💡 TIP: Take multiple shots and select the sharpest one before submitting.

{common_footer}""",

            'Poor framing': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected due to inadequate framing.

🖼️ ISSUE: Poor Framing
The artwork is not properly centered or the composition needs improvement.

🔧 WHAT TO DO:
• Center the artwork in the frame
• Include the entire artwork with minimal background
• Ensure the artwork is straight and not tilted
• Maintain consistent margins around the artwork

💡 TIP: The artwork should fill most of the frame while showing its complete boundaries.

{common_footer}""",

            'Reflections on artwork': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected due to reflections on the artwork surface.

✨ ISSUE: Reflections on Artwork
Visible reflections or glare interfere with the artwork's appearance.

🔧 WHAT TO DO:
• Adjust lighting angles to minimize reflections
• Use polarizing filters if available
• Position lights at 45-degree angles to the artwork
• For glass-covered artworks, remove glass if possible

💡 TIP: Matte surfaces reflect less than glossy ones. Consider the artwork's surface when positioning lights.

{common_footer}""",

            'Partially visible artwork': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected because the artwork is not completely visible.

👁️ ISSUE: Partially Visible Artwork
Parts of the artwork are cropped out or obscured in the photograph.

🔧 WHAT TO DO:
• Ensure the entire artwork is visible in the frame
• Step back or adjust the camera position to capture the full piece
• Include a small border around the artwork edges
• Check that no parts are cut off in the viewfinder

💡 TIP: It's better to include slightly more background than to cut off any part of the artwork.

{common_footer}""",

            'Color issues': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected due to color accuracy problems.

🎨 ISSUE: Color Issues
The colors in the photograph do not accurately represent the original artwork.

🔧 WHAT TO DO:
• Use proper white balance settings on your camera
• Ensure adequate, even lighting
• Avoid colored lighting (fluorescent, tungsten without correction)
• Consider using a color reference card
• Check your camera's color profile settings

💡 TIP: Natural daylight or color-balanced photography lights produce the most accurate colors.

{common_footer}""",

            'Inappropriate format': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected due to an inappropriate file format.

📁 ISSUE: Inappropriate Format
The file format does not meet our archival standards.

🔧 WHAT TO DO:
• Use high-quality formats: TIFF, PNG, or high-quality JPEG
• Avoid heavily compressed files
• Ensure minimum resolution of 300 DPI for A5 print size
• Use uncompressed formats when possible

💡 TIP: TIFF format is preferred for archival purposes due to its lossless compression.

{common_footer}""",

            'Incorrect filename': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected due to an incorrect filename.

📝 ISSUE: Incorrect Filename
The filename does not follow our naming conventions.

🔧 WHAT TO DO:
• Follow the naming format: [ARTWORK-ID]-[VIEW-TYPE].[extension]
• Use artwork ID from the database
• Include view type: MAIN, DETAIL, FRAME, etc.
• Use only alphanumeric characters and hyphens

💡 TIP: Example correct filename: "AB-123-MAIN.jpg" or "CD-456-DETAIL.tiff"

{common_footer}""",

            'Artwork not found in database': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected because the artwork is not found in our database.

🔍 ISSUE: Artwork Not Found
The artwork referenced in the filename does not exist in our OperaCRM database.

🔧 WHAT TO DO:
• Verify the artwork ID is correct
• Check that the artwork has been properly catalogued in OperaCRM
• Contact the curator to add the artwork to the database first
• Resubmit with the correct artwork ID once verified

💡 TIP: All artworks must be registered in the system before photos can be submitted.

{common_footer}""",

            'Duplicate artwork detected': f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected because this artwork already has photos in our system.

🔄 ISSUE: Duplicate Artwork Detected
Our system detected that this artwork already has existing high-quality photographs.

🔧 WHAT TO DO:
• Check if your photo offers significantly better quality
• Consider if this is a different view (DETAIL, FRAME, etc.)
• Contact the collection manager if you believe this is a unique perspective
• Only resubmit if the new photo provides additional value

💡 TIP: We prefer to avoid duplicate images unless they offer substantially different views or improved quality.

{common_footer}""",

            'Potential duplicate found in Odoo': f"""Dear {username},

Your submitted photo "{photo_id}" has been flagged as a potential duplicate of existing imagery in our Odoo system.

⚠️ ISSUE: Potential Duplicate
Our automated system detected similarities with existing photographs.

🔧 WHAT TO DO:
• Review existing photos in the system
• Confirm this is indeed a unique photograph
• If it's a different angle or detail, specify the view type clearly
• Contact the validation team if you believe this is an error

💡 TIP: Our system errs on the side of caution to prevent true duplicates. Manual review may be needed.

{common_footer}""",
        }
        
        # Default template for custom or unrecognized reasons
        default_template = f"""Dear {username},

Your submitted photo "{photo_id}" has been rejected during the validation process.

❌ REJECTION REASON: {reason}

Please review the rejection reason and make the necessary corrections before resubmitting.

🔧 GENERAL GUIDELINES:
• Ensure high image quality (minimum 300 DPI for A5 print)
• Use proper lighting and avoid reflections
• Frame the artwork completely and centered
• Use appropriate file formats (TIFF, PNG, or high-quality JPEG)
• Follow correct naming conventions

If you need clarification on the rejection reason, please contact our validation team.

{common_footer}"""
        
        return templates.get(reason, default_template)

class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self):
        self.smtp_config = SMTP_CONFIG
    
    def send_rejection_email(self, user_email, username, photo_id, reject_reason, validator_username):
        """Send rejection notification email"""
        try:
            # Get appropriate template and subject
            subject = EmailTemplates.get_subject(reject_reason, photo_id)
            body = EmailTemplates.get_template(reject_reason, username, photo_id, validator_username)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.smtp_config['from_name']} <{self.smtp_config['from_email']}>"
            msg['To'] = user_email
            msg['Reply-To'] = self.smtp_config['from_email']
            
            # Add body
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
                server.starttls()
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)
            
            print(f"✅ Email sent successfully to {user_email}")
            print(f"📧 Subject: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {user_email}: {str(e)}")
            # Still log the email content for debugging
            print(f"""
=== EMAIL SENDING FAILED ===
To: {user_email}
Subject: {subject}
Reason: {str(e)}
============================
            """)
            return False
    
    def send_validation_email(self, user_email, username, photo_id, validator_username, classification):
        """Send validation confirmation email"""
        try:
            subject = f"Photo Approved - {photo_id}"
            
            body = f"""Dear {username},

Your submitted photo "{photo_id}" has been successfully validated and approved!

✅ STATUS: Approved
📋 Classification: {classification}
👤 Validated by: {validator_username}
📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Your photo has been added to the Operagallery.com collection and is now available in the system.

Thank you for your contribution to the collection!

Best regards,
Operagallery.com Validation Team

For questions, please contact: info@operacrm.com
"""
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.smtp_config['from_name']} <{self.smtp_config['from_email']}>"
            msg['To'] = user_email
            msg['Reply-To'] = self.smtp_config['from_email']
            
            # Add body
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
                server.starttls()
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)
            
            print(f"✅ Validation email sent successfully to {user_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send validation email to {user_email}: {str(e)}")
            return False
    
    def send_email(self, to, subject, html_content):
        """Send generic email with HTML content"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.smtp_config['from_name']} <{self.smtp_config['from_email']}>"
            msg['To'] = to
            msg['Reply-To'] = self.smtp_config['from_email']
            
            # Add HTML body
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
                server.starttls()
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)
            
            print(f"✅ Email sent successfully to {to}")
            print(f"📧 Subject: {subject}")
            return {'success': True}
            
        except Exception as e:
            print(f"❌ Failed to send email to {to}: {str(e)}")
            return {'success': False, 'error': str(e)}

# Global email service instance
email_service = EmailService()
