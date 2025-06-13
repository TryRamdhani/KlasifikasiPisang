import os
import uuid
from flask import render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import logging
from app import app

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_info(filepath):
    """Get basic file information"""
    try:
        with Image.open(filepath) as img:
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode
            }
    except Exception as e:
        logging.error(f"Error getting file info: {e}")
        return None

def mock_banana_detection(filepath):
    """
    Mock banana detection function - replace this with your actual AI model
    Returns mock detection results
    """
    try:
        file_info = get_file_info(filepath)
        if not file_info:
            return None
        
        # Mock detection results - replace with your actual model inference
        mock_results = {
            'detected': True,
            'confidence': 0.87,
            'banana_count': 2,
            'banana_type': 'Cavendish',
            'ripeness': 'Matang',
            'quality': 'Baik',
            'recommendations': [
                'Pisang ini dalam kondisi baik untuk dikonsumsi',
                'Tingkat kematangan optimal',
                'Disarankan untuk dimakan dalam 2-3 hari'
            ],
            'image_info': file_info
        }
        
        return mock_results
    except Exception as e:
        logging.error(f"Error in mock detection: {e}")
        return None

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/upload')
def upload_page():
    """Image upload page"""
    return render_template('upload.html')

@app.route('/detect', methods=['POST'])
def detect():
    """Handle image upload and detection"""
    if 'file' not in request.files:
        flash('Tidak ada file yang dipilih', 'error')
        return redirect(url_for('upload_page'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Tidak ada file yang dipilih', 'error')
        return redirect(url_for('upload_page'))
    
    if not allowed_file(file.filename):
        flash('Format file tidak didukung. Gunakan PNG, JPG, JPEG, GIF, BMP, atau WEBP', 'error')
        return redirect(url_for('upload_page'))
    
    try:
        # Generate unique filename
        filename = str(uuid.uuid4()) + '_' + secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file
        file.save(filepath)
        
        # Run detection (mock)
        results = mock_banana_detection(filepath)
        
        if results is None:
            flash('Terjadi kesalahan saat memproses gambar', 'error')
            # Clean up file
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect(url_for('upload_page'))
        
        # Clean up file after processing
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return render_template('results.html', results=results, filename=file.filename)
        
    except Exception as e:
        logging.error(f"Error in detection: {e}")
        flash('Terjadi kesalahan saat memproses gambar', 'error')
        return redirect(url_for('upload_page'))

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    flash('File terlalu besar. Maksimal ukuran file adalah 16MB', 'error')
    return redirect(url_for('upload_page'))

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('dashboard.html'), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    flash('Terjadi kesalahan internal. Silakan coba lagi.', 'error')
    return redirect(url_for('dashboard'))
