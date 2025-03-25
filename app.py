import os
import logging
import zipfile
import shutil
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import qrcode
from io import BytesIO
import base64
from werkzeug.utils import secure_filename
import secrets
import uuid
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import time
from utils import get_file_icon, format_file_size

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", secrets.token_hex(32))

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///filelock.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Register custom Jinja2 filters
app.jinja_env.filters['file_icon'] = get_file_icon
app.jinja_env.filters['format_size'] = format_file_size
db.init_app(app)

# Configure file uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload

# Import models after db initialization
with app.app_context():
    from models import User, Folder, File
    db.create_all()

@app.route('/')
def index():
    user_id = session.get('user_id')
    if not user_id:
        # Create a new anonymous user
        user = User(username=str(uuid.uuid4()))
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        user_id = user.id
    
    # Generate QR code for mobile upload
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    upload_url = url_for('mobile_upload', user_id=user_id, _external=True)
    qr.add_data(upload_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    qr_code = base64.b64encode(buffered.getvalue()).decode()
    
    # Get user's root folder
    user = User.query.get(user_id)
    root_folder = Folder.query.filter_by(user_id=user_id, parent_id=None).first()
    
    if not root_folder:
        # Create root folder if it doesn't exist
        root_folder = Folder(name="Root", user_id=user_id)
        db.session.add(root_folder)
        db.session.commit()
    
    # Get subfolders and files
    subfolders = Folder.query.filter_by(parent_id=root_folder.id).all()
    files = File.query.filter_by(folder_id=root_folder.id).all()
    
    return render_template('index.html', 
                          qr_code=qr_code, 
                          user=user, 
                          root_folder=root_folder, 
                          subfolders=subfolders, 
                          files=files,
                          folder_locked=session.get('folder_locked', False))

@app.route('/generate_key', methods=['POST'])
def generate_key():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    # Generate a secure 64-byte key
    key = secrets.token_bytes(64)
    key_hex = key.hex()
    
    user = User.query.get(user_id)
    if user:
        user.key_hash = key_hex  # In a real app, you'd hash this
        db.session.commit()
        
    return jsonify({'key': key_hex})

@app.route('/lock_folder', methods=['POST'])
def lock_folder():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    key = request.form.get('key')
    if not key or len(key) != 128:  # 64 bytes = 128 hex chars
        flash('Invalid key. Please generate a valid 64-byte key.')
        return redirect(url_for('index'))
    
    user = User.query.get(user_id)
    if user.key_hash == key:
        # Set the session variables to indicate folder is locked and user has the key
        session['folder_locked'] = True
        session['has_key'] = True
        
        # Hide all files and folders when locked
        root_folder = Folder.query.filter_by(user_id=user_id, parent_id=None).first()
        if root_folder:
            # Hide the main folder
            root_folder.is_visible = False
            
            # Update visibility of all subfolders recursively
            def set_folder_visibility(folder_id, visible):
                # Update subfolders
                subfolders = Folder.query.filter_by(parent_id=folder_id).all()
                for subfolder in subfolders:
                    subfolder.is_visible = visible
                    set_folder_visibility(subfolder.id, visible)
            
            # Hide all subfolders
            set_folder_visibility(root_folder.id, False)
            db.session.commit()
            
        flash('Your folder has been securely locked and hidden.')
    else:
        flash('Invalid key. Could not lock folder.')
    
    return redirect(url_for('index'))

@app.route('/unlock_folder', methods=['POST'])
def unlock_folder():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    key = request.form.get('key')
    if not key or len(key) != 128:
        flash('Invalid key. Please provide your 64-byte key.')
        return redirect(url_for('index'))
    
    user = User.query.get(user_id)
    if user.key_hash == key:
        # Set the session variables to indicate folder is unlocked and user has the key
        session['folder_locked'] = False
        session['has_key'] = True
        
        # Show all files and folders when unlocked
        root_folder = Folder.query.filter_by(user_id=user_id, parent_id=None).first()
        if root_folder:
            # Show the main folder
            root_folder.is_visible = True
            
            # Update visibility of all subfolders recursively
            def set_folder_visibility(folder_id, visible):
                # Update subfolders
                subfolders = Folder.query.filter_by(parent_id=folder_id).all()
                for subfolder in subfolders:
                    subfolder.is_visible = visible
                    set_folder_visibility(subfolder.id, visible)
            
            # Show all subfolders
            set_folder_visibility(root_folder.id, True)
            db.session.commit()
            
        flash('Your folder has been unlocked and is now visible.')
    else:
        flash('Invalid key. Could not unlock folder.')
    
    return redirect(url_for('index'))

@app.route('/create_folder', methods=['POST'])
def create_folder():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    parent_id = request.form.get('parent_id')
    folder_name = request.form.get('folder_name')
    
    if not folder_name:
        flash('Folder name is required.')
        return redirect(url_for('index'))
    
    new_folder = Folder(name=folder_name, user_id=user_id, parent_id=parent_id)
    db.session.add(new_folder)
    db.session.commit()
    
    flash(f'Folder "{folder_name}" created successfully.')
    return redirect(url_for('index'))

@app.route('/folder/<int:folder_id>')
def view_folder(folder_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    folder = Folder.query.get_or_404(folder_id)
    
    # Security check - only allow access to user's own folders
    if folder.user_id != user_id:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    subfolders = Folder.query.filter_by(parent_id=folder.id).all()
    files = File.query.filter_by(folder_id=folder.id).all()
    
    # Get parent folders for breadcrumb navigation
    breadcrumbs = []
    current = folder
    while current:
        breadcrumbs.insert(0, current)
        if current.parent_id:
            current = Folder.query.get(current.parent_id)
        else:
            current = None
    
    return render_template('index.html', 
                          folder=folder, 
                          subfolders=subfolders, 
                          files=files, 
                          breadcrumbs=breadcrumbs,
                          folder_locked=session.get('folder_locked', False))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        folder_id = request.form.get('folder_id')
        
        if not folder_id:
            flash('Folder ID is required.')
            return redirect(url_for('index'))
        
        folder = Folder.query.get_or_404(folder_id)
        
        # Security check
        if folder.user_id != user_id:
            flash('Access denied.')
            return redirect(url_for('index'))
        
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        files = request.files.getlist('file')
        
        for file in files:
            if file.filename == '':
                flash('No selected file')
                continue
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(uuid.uuid4()) + "_" + filename)
            file.save(file_path)
            
            # Create file record in database
            new_file = File(
                name=filename,
                path=file_path,
                size=os.path.getsize(file_path),
                file_type=filename.split('.')[-1] if '.' in filename else '',
                folder_id=folder_id,
                user_id=user_id
            )
            db.session.add(new_file)
            db.session.commit()
        
        flash('File(s) uploaded successfully')
        return redirect(url_for('view_folder', folder_id=folder_id))
    
    folder_id = request.args.get('folder_id')
    if not folder_id:
        return redirect(url_for('index'))
    
    folder = Folder.query.get_or_404(folder_id)
    
    # Security check
    if folder.user_id != user_id:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    return render_template('upload.html', folder=folder)

@app.route('/mobile_upload/<int:user_id>', methods=['GET', 'POST'])
def mobile_upload(user_id):
    if request.method == 'POST':
        # Check if user exists
        user = User.query.get_or_404(user_id)
        
        # Get the root folder
        root_folder = Folder.query.filter_by(user_id=user_id, parent_id=None).first()
        if not root_folder:
            return "Error: Root folder not found", 400
        
        # Check if the post request has the file part
        if 'file' not in request.files:
            return "No file part", 400
        
        files = request.files.getlist('file')
        auto_backup = request.form.get('auto_backup') == 'true'
        
        uploaded_files = []
        for file in files:
            if file.filename == '':
                continue
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(uuid.uuid4()) + "_" + filename)
            file.save(file_path)
            
            # Create file record in database
            new_file = File(
                name=filename,
                path=file_path,
                size=os.path.getsize(file_path),
                file_type=filename.split('.')[-1] if '.' in filename else '',
                folder_id=root_folder.id,
                user_id=user_id
            )
            db.session.add(new_file)
            uploaded_files.append(filename)
        
        db.session.commit()
        
        if auto_backup:
            return jsonify({
                'success': True, 
                'message': f"Auto-backup completed. {len(uploaded_files)} files uploaded.", 
                'files': uploaded_files
            })
        else:
            return jsonify({
                'success': True, 
                'message': f"{len(uploaded_files)} files uploaded successfully.", 
                'files': uploaded_files
            })
    
    # GET request - show upload form
    return render_template('mobile_upload.html', user_id=user_id)

@app.route('/download/<int:file_id>')
def download_file(file_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    file = File.query.get_or_404(file_id)
    
    # Security check
    if file.user_id != user_id:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Get the folder this file belongs to
    folder = Folder.query.get(file.folder_id)
    
    # Check if the folder is not visible (locked) and user doesn't have the key
    if not folder.is_visible and not session.get('has_key', False):
        flash('This file is in a locked folder. Please unlock the folder first to download its contents.')
        return redirect(url_for('view_folder', folder_id=file.folder_id))
    
    # Return the file for download
    directory = os.path.dirname(file.path)
    filename = os.path.basename(file.path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=file.name)

@app.route('/delete_file/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    file = File.query.get_or_404(file_id)
    
    # Security check
    if file.user_id != user_id:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    folder_id = file.folder_id
    
    # Delete the actual file from disk
    if os.path.exists(file.path):
        os.remove(file.path)
    
    # Delete the database record
    db.session.delete(file)
    db.session.commit()
    
    flash('File deleted successfully.')
    return redirect(url_for('view_folder', folder_id=folder_id))

@app.route('/delete_folder/<int:folder_id>', methods=['POST'])
def delete_folder(folder_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    folder = Folder.query.get_or_404(folder_id)
    
    # Security check
    if folder.user_id != user_id:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Don't allow deleting the root folder
    if folder.parent_id is None:
        flash('Cannot delete the root folder.')
        return redirect(url_for('index'))
    
    parent_id = folder.parent_id
    
    # Recursively delete all files and subfolders
    def delete_folder_recursive(folder_id):
        # Delete all files in this folder
        files = File.query.filter_by(folder_id=folder_id).all()
        for file in files:
            if os.path.exists(file.path):
                os.remove(file.path)
            db.session.delete(file)
        
        # Delete all subfolders
        subfolders = Folder.query.filter_by(parent_id=folder_id).all()
        for subfolder in subfolders:
            delete_folder_recursive(subfolder.id)
        
        # Delete this folder
        folder = Folder.query.get(folder_id)
        db.session.delete(folder)
    
    delete_folder_recursive(folder_id)
    db.session.commit()
    
    flash('Folder and all its contents deleted successfully.')
    return redirect(url_for('view_folder', folder_id=parent_id))

@app.route('/file_details/<int:file_id>')
def file_details(file_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    file = File.query.get_or_404(file_id)
    
    # Security check
    if file.user_id != user_id:
        return jsonify({'error': 'Access denied'})
    
    return jsonify({
        'id': file.id,
        'name': file.name,
        'size': file.size,
        'file_type': file.file_type,
        'created_at': file.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'download_url': url_for('download_file', file_id=file.id)
    })

@app.route('/download_folder/<int:folder_id>')
def download_folder(folder_id):
    """Download all files in a folder as a zip archive"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    folder = Folder.query.get_or_404(folder_id)
    
    # Security check
    if folder.user_id != user_id:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    # Check if the folder is visible (not locked) or if user has the key
    if not folder.is_visible and not session.get('has_key', False):
        flash('This folder is locked. Please unlock it first to download its contents.')
        return redirect(url_for('view_folder', folder_id=folder_id))
    
    # Create a temporary directory to store the folder structure
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{str(uuid.uuid4())}")
    os.makedirs(temp_dir)
    
    # Create a zip file in memory
    memory_file = BytesIO()
    
    try:
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            def add_folder_to_zip(current_folder, zip_path):
                # Add files in this folder
                files = File.query.filter_by(folder_id=current_folder.id).all()
                for file in files:
                    if os.path.exists(file.path):
                        # Add file to zip with its original name, preserving folder structure
                        zipf.write(file.path, os.path.join(zip_path, file.name))
                
                # Process subfolders recursively
                subfolders = Folder.query.filter_by(parent_id=current_folder.id).all()
                for subfolder in subfolders:
                    subfolder_path = os.path.join(zip_path, subfolder.name)
                    add_folder_to_zip(subfolder, subfolder_path)
            
            # Start with the requested folder
            add_folder_to_zip(folder, folder.name)
        
        # Reset file position to the beginning
        memory_file.seek(0)
        
        # Return the zip file as an attachment
        return Response(
            memory_file.getvalue(),
            mimetype='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename={folder.name}.zip'
            }
        )
    
    finally:
        # Clean up the temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.route('/rename_folder/<int:folder_id>', methods=['POST'])
def rename_folder(folder_id):
    """Rename a folder"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('index'))
    
    folder = Folder.query.get_or_404(folder_id)
    
    # Security check
    if folder.user_id != user_id:
        flash('Access denied.')
        return redirect(url_for('index'))
    
    new_name = request.form.get('folder_name')
    if not new_name:
        flash('Folder name is required.')
        return redirect(url_for('index'))
    
    folder.name = new_name
    db.session.commit()
    
    flash(f'Folder renamed to "{new_name}" successfully.')
    if folder.parent_id:
        return redirect(url_for('view_folder', folder_id=folder.parent_id))
    else:
        return redirect(url_for('index'))

@app.route('/retrieve_folder', methods=['POST'])
def retrieve_folder():
    """Retrieve a folder using a 64-byte key"""
    key = request.form.get('key')
    if not key or len(key) != 128:
        flash('Invalid key. Please provide your 64-byte key.')
        return redirect(url_for('index'))
    
    # Find user with matching key
    user = User.query.filter_by(key_hash=key).first()
    if not user:
        flash('Invalid key. No folder found with this key.')
        return redirect(url_for('index'))
    
    # Set session to this user
    session['user_id'] = user.id
    session['folder_locked'] = False  # Unlock the folder for access
    session['has_key'] = True  # Indicate user has the valid key
    
    flash('Folder retrieved successfully! You now have access to all files.')
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
