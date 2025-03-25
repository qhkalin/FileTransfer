# SecureFileVault - Secure File Sharing Web Application

A secure file sharing web application with 64-byte key locking, QR code sharing, and organized folder system.

## Features

- **Secure 64-byte Key Encryption**: Lock your files with a secure 64-byte key
- **Folder Organization**: Create, rename, and delete folders to organize your files
- **File Management**: Upload, download, and delete files easily
- **Mobile Upload via QR Code**: Scan a QR code to upload files from mobile devices
- **Zip Download**: Download entire folders as zip archives
- **Folder Visibility Control**: Hide/show folders based on lock status
- **Folder Retrieval**: Access folders using a 64-byte key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/secure-file-vault.git
cd secure-file-vault
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the dependencies:
```bash
pip install -r app_requirements.txt
```

4. Set up the PostgreSQL database and update the DATABASE_URL in the environment.

5. Run the application:
```bash
gunicorn --bind 0.0.0.0:5000 main:app
```

## Usage

1. **Generate a 64-byte Key**: Click on "Generate Key" to create a secure key for your folder.
2. **Upload Files**: Drag and drop files into the drop zone or use the "Upload Files" button.
3. **Create Folders**: Use the "Create Folder" button to create new folders for organization.
4. **Lock/Unlock Folders**: Use your 64-byte key to lock and unlock your folders.
5. **Download Files**: Click on a file to view details and download it.
6. **Mobile Upload**: Scan the QR code with a mobile device to upload files directly.
7. **Rename Folders**: Use the "Rename" button to rename your folders.
8. **Download as Zip**: Download entire folders as zip archives.

## Security Features

- AES-256 encryption for secure file storage
- 64-byte key (512 bits) for strong security
- Session-based access control
- Secure folder visibility management

## Requirements

- Python 3.11+
- Flask 3.1.0+
- PostgreSQL database
- Other dependencies listed in app_requirements.txt

## License

[MIT License](LICENSE)