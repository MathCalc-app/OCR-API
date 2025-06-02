# Made by Benjamín Alonso Bobadilla Moya for MathCalc's OCR API. MIT License
import os
import time
import uuid

import magic
import pytesseract
from PIL import Image
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'heic'}
ALLOWED_MIME_TYPES = {'image/png', 'image/jpeg', 'image/bmp', 'image/tiff', 'image/heic'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def verify_image_content(file_path):
    mime = magic.Magic(mime=True)
    file_mime = mime.from_file(file_path)
    return file_mime in ALLOWED_MIME_TYPES


@app.route('/ocr', methods=['POST'])
@limiter.limit("30 per minute")
def ocr():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        random_filename = str(uuid.uuid4())
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        secure_name = f"{random_filename}.{file_extension}"

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
        file.save(filepath)

        try:
            if not verify_image_content(filepath):
                os.remove(filepath)
                return jsonify({'error': 'Invalid file content'}), 400

            image = Image.open(filepath)

            start_time = time.time()
            text = pytesseract.image_to_string(image)

            os.remove(filepath)

            if time.time() - start_time > 10:
                return jsonify({'error': 'Processing timeout'}), 408

            return jsonify({'text': text}), 200

        except Exception:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': 'Processing failed'}), 500
    else:
        return jsonify({'error': 'File type not allowed'}), 400


@app.route('/')
def index():
    return "Welcome to MathCalc's OCR API!"


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large'}), 413


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
