from app import app

# Apply ProxyFix to handle large file uploads
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
