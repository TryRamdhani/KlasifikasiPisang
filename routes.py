import os
import uuid
import json
import logging
import numpy as np
from flask import render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from keras.preprocessing import image
import tensorflow as tf
from PIL import Image
from app import app

# Konfigurasi
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Path model dan data
MODEL_PATH = "model2/mobilenetv2_final.keras"
CLASS_INDICES_PATH = "model2/class_indices.json"
BANANA_INFO_PATH = "banana_info.json"

# Load model dan data
model = tf.keras.models.load_model(MODEL_PATH)

with open(CLASS_INDICES_PATH, "r", encoding="utf-8") as f:
    class_indices = json.load(f)

with open(BANANA_INFO_PATH, "r", encoding="utf-8") as f:
    banana_info = json.load(f)

# Mapping indeks ke label
class_labels = {v: k for k, v in class_indices.items()}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_info(filepath):
    try:
        with Image.open(filepath) as img:
            img.load()  # Pastikan bisa di-decode
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode
            }
    except Exception as e:
        logging.error(f"Error getting file info: {e}")
        return None


def detect_banana(filepath):
    try:
        file_info = get_file_info(filepath)
        if not file_info:
            return None

        img = image.load_img(filepath, target_size=(224, 224))
        img_array = image.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        prediction = model.predict(img_array)
        predicted_index = np.argmax(prediction)
        predicted_label = class_labels[predicted_index]
        confidence = float(np.max(prediction))

        if confidence < 0.5:
            return {
                'detected': False,
                'confidence': confidence,
                'banana_type': 'Tidak yakin',
                'ripeness': 'Tidak Diketahui',
                'quality': 'Tidak Diketahui',
                'recommendations': [
                    'Model tidak yakin dengan jenis pisang.',
                    f'Tingkat kepercayaan hanya {confidence * 100:.2f}% (< 50%)'
                ],
                'image_info': file_info
            }

        info = banana_info.get(predicted_label, {})
        return {
            'detected': True,
            'confidence': confidence,
            'banana_type': predicted_label.replace("_", " ").title(),
            'ripeness': info.get('asal', 'Tidak Diketahui'),
            'quality': info.get('khasiat', 'Tidak Diketahui'),
            'recommendations': [info.get('manfaat', 'Tidak tersedia')],
            'image_info': file_info
        }

    except Exception as e:
        logging.error(f"Error in detection: {e}", exc_info=True)
        return None


@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/upload')
def upload_page():
    return render_template('upload.html')


@app.route('/detect', methods=['POST'])
def detect():
    if 'file' not in request.files:
        flash('Tidak ada file yang dipilih', 'error')
        return redirect(url_for('upload_page'))

    file = request.files['file']

    if file.filename == '':
        flash('Tidak ada file yang dipilih', 'error')
        return redirect(url_for('upload_page'))

    if not allowed_file(file.filename):
        flash('Format file tidak didukung.', 'error')
        return redirect(url_for('upload_page'))

    try:
        filename = str(uuid.uuid4()) + '_' + secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Validasi file gambar
        try:
            with Image.open(filepath) as img:
                img.load()
        except Exception as e:
            logging.error(f"Invalid image file: {e}")
            os.remove(filepath)
            flash('File gambar tidak valid atau rusak.', 'error')
            return redirect(url_for('upload_page'))

        results = detect_banana(filepath)
        if results is None:
            flash('Gagal mendeteksi jenis pisang.', 'error')
            os.remove(filepath)
            return redirect(url_for('upload_page'))

        return render_template('results.html', results=results, filename=filename)

    except Exception as e:
        logging.error(f"Error in /detect: {e}", exc_info=True)
        flash('Terjadi kesalahan saat memproses gambar.', 'error')
        return redirect(url_for('upload_page'))


@app.errorhandler(413)
def too_large(e):
    flash('File terlalu besar. Maksimum ukuran adalah 16MB.', 'error')
    return redirect(url_for('upload_page'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('dashboard.html'), 404


@app.errorhandler(500)
def internal_error(e):
    flash('Terjadi kesalahan internal server.', 'error')
    return redirect(url_for('dashboard'))
