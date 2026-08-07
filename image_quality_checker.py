#!/usr/bin/env python3
"""
Image quality verification module for A5 printing
"""

import os
import json
from PIL import Image
import math

class ImageQualityChecker:
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'quality_config.json')
        self.config_file = config_file
        self.load_config()
    
    def load_config(self):
        """Load quality configuration from JSON file"""
        default_config = {
            # A5 dimensions in pixels at different resolutions
            "a5_dimensions": {
                "300dpi": {"width": 1748, "height": 2480},  # A5 at 300 DPI (print quality)
                "200dpi": {"width": 1166, "height": 1654},  # A5 at 200 DPI (acceptable)
                "150dpi": {"width": 874, "height": 1240}    # A5 at 150 DPI (minimum)
            },
            # Quality thresholds
            "quality_thresholds": {
                "excellent": {"min_dpi": 300, "min_pixels": 4331840},  # 1748x2480
                "good": {"min_dpi": 200, "min_pixels": 1929164},       # 1166x1654  
                "acceptable": {"min_dpi": 150, "min_pixels": 1083760}, # 874x1240
                "poor": {"min_dpi": 100, "min_pixels": 500000}
            },
            # Validation rules
            "validation_rules": {
                "allow_poor_if_no_existing": True,  # Accept poor quality if no existing image
                "reject_poor_if_existing": True,    # Reject poor quality if image already exists
                "min_file_size_kb": 50,             # Minimum file size in KB
                "max_file_size_mb": 1000,           # Maximum file size in MB (1GB)
                "supported_formats": ["JPEG", "JPG", "PNG", "TIFF", "BMP"]
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            print(f"Config loading error: {e}")
            self.config = default_config
    
    def save_config(self):
        """Save configuration"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Config save error: {e}")
    
    def calculate_dpi_for_a5(self, width, height):
        """Calculate equivalent DPI for A5 printing"""
        # A5 dimensions in inches: 5.83 x 8.27 inches
        a5_width_inches = 5.83
        a5_height_inches = 8.27
        
        # Calculate DPI based on dimensions
        dpi_width = width / a5_width_inches
        dpi_height = height / a5_height_inches
        
        # Take the lowest DPI (limiting factor)
        return min(dpi_width, dpi_height)
    
    def analyze_image_quality(self, image_path):
        """Analyze image quality"""
        try:
            # Open image
            with Image.open(image_path) as img:
                width, height = img.size
                format_name = img.format
                
                # File information
                file_size = os.path.getsize(image_path)
                file_size_kb = file_size / 1024
                file_size_mb = file_size / (1024 * 1024)
                
                # Calculate equivalent DPI for A5
                equivalent_dpi = self.calculate_dpi_for_a5(width, height)
                total_pixels = width * height
                
                # Determine quality
                quality_level = self.determine_quality_level(equivalent_dpi, total_pixels)
                
                # Generate report
                analysis = {
                    'dimensions': {'width': width, 'height': height},
                    'total_pixels': total_pixels,
                    'equivalent_dpi_a5': round(equivalent_dpi, 1),
                    'file_size_kb': round(file_size_kb, 1),
                    'file_size_mb': round(file_size_mb, 2),
                    'format': format_name,
                    'quality_level': quality_level,
                    'color_code': self.get_quality_color(quality_level),
                    'print_quality_a5': self.get_print_quality_description(quality_level),
                    'recommendations': self.get_recommendations(quality_level, equivalent_dpi),
                    'validation_issues': self.check_validation_issues(file_size_kb, file_size_mb, format_name)
                }
                
                return analysis
                
        except Exception as e:
            return {
                'error': f'Image analysis error: {str(e)}',
                'quality_level': 'error',
                'color_code': 'gray'
            }
    
    def determine_quality_level(self, dpi, pixels):
        """Determine quality level based on DPI and pixels"""
        thresholds = self.config['quality_thresholds']
        
        if dpi >= thresholds['excellent']['min_dpi'] and pixels >= thresholds['excellent']['min_pixels']:
            return 'excellent'
        elif dpi >= thresholds['good']['min_dpi'] and pixels >= thresholds['good']['min_pixels']:
            return 'good'
        elif dpi >= thresholds['acceptable']['min_dpi'] and pixels >= thresholds['acceptable']['min_pixels']:
            return 'acceptable'
        else:
            return 'poor'
    
    def get_quality_color(self, quality_level):
        """Return color code for quality level"""
        color_map = {
            'excellent': 'green',
            'good': 'lightgreen', 
            'acceptable': 'orange',
            'poor': 'red',
            'error': 'gray'
        }
        return color_map.get(quality_level, 'gray')
    
    def get_print_quality_description(self, quality_level):
        """Print quality description"""
        descriptions = {
            'excellent': 'Excellent quality for A5 printing (≥300 DPI)',
            'good': 'Good quality for A5 printing (≥200 DPI)', 
            'acceptable': 'Acceptable quality for A5 printing (≥150 DPI)',
            'poor': 'Insufficient quality for A5 printing (<150 DPI)',
            'error': 'Image analysis error'
        }
        return descriptions.get(quality_level, 'Unknown quality')
    
    def get_recommendations(self, quality_level, dpi):
        """Return improvement recommendations"""
        if quality_level == 'excellent':
            return ['Perfect image for A5 printing']
        elif quality_level == 'good':
            return ['Sufficient quality for A5 printing', 'Consider higher resolution for optimal quality']
        elif quality_level == 'acceptable':
            return ['Minimum acceptable quality', f'Current DPI: {dpi:.1f}, recommended: ≥200 DPI']
        else:
            return [
                'Insufficient quality for A5 printing',
                f'Current DPI: {dpi:.1f}, minimum required: 150 DPI',
                'Use a scanner or camera with better resolution'
            ]
    
    def check_validation_issues(self, file_size_kb, file_size_mb, format_name):
        """Check validation issues"""
        issues = []
        rules = self.config['validation_rules']
        
        if file_size_kb < rules['min_file_size_kb']:
            issues.append(f'File too small: {file_size_kb:.1f} KB (minimum: {rules["min_file_size_kb"]} KB)')
        
        if file_size_mb > rules['max_file_size_mb']:
            issues.append(f'File too large: {file_size_mb:.1f} MB (maximum: {rules["max_file_size_mb"]} MB)')
        
        if format_name not in rules['supported_formats']:
            issues.append(f'Unsupported format: {format_name} (supported: {", ".join(rules["supported_formats"])})')
        
        return issues
    
    def should_accept_upload(self, quality_level, has_existing_images=False):
        """Determine if upload should be accepted according to rules"""
        rules = self.config['validation_rules']
        
        if quality_level == 'error':
            return False, "Image analysis error"
        
        if quality_level in ['excellent', 'good', 'acceptable']:
            return True, "Acceptable quality"
        
        # Poor quality
        if quality_level == 'poor':
            if not has_existing_images and rules['allow_poor_if_no_existing']:
                return True, "Poor quality accepted because no existing image"
            elif has_existing_images and rules['reject_poor_if_existing']:
                return False, "Insufficient quality and existing images present"
            else:
                return True, "Poor quality accepted"
        
        return False, "Unknown quality"
    
    def get_config(self):
        """Return current configuration"""
        return self.config
    
    def update_config(self, new_config):
        """Update configuration"""
        self.config.update(new_config)
        self.save_config()
