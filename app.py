
import os
import re
import hmac
from pathlib import Path

from flask import Flask, request, Response, abort
from markupsafe import escape
from werkzeug.utils import secure_filename

app = Flask(__name__)

# NIGHT HEX configuration
UPLOAD_FOLDER = Path(
    os.environ.get("UPLOAD_FOLDER", "/tmp/nighthex")
)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


def make_page(content, title="NIGHT HEX"):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
* {{ box-sizing: border-box; }}
body {{
    margin: 0;
    padding: 22px;
    background: #080d18;
    color: #e8eefc;
    font-family: Arial, sans-serif;
}}
main {{
    max-width: 620px;
    margin: 40px auto;
    padding: 28px;
    background: #111a2b;
    border: 1px solid #263653;
    border-radius: 16px;
}}
h1 {{ color: #38e8a5; }}
p {{ color: #b8c6dc; line-height: 1.6; }}
input, button {{
    width: 100%;
    padding: 13px;
    margin-top: 12px;
    border-radius: 8px;
    font-size: 16px;
}}
input {{
    background: #080d18;
    color: white;
    border: 1px solid #344766;
}}
button {{
    background: #38e8a5;
    color: #07110e;
    border: 0;
    font-weight: bold;
    cursor: pointer;
}}
a {{ color: #38e8a5; overflow-wrap: anywhere; }}
.small {{ font-size: 13px; }}
footer {{
    border-top: 1px solid #263653;
    margin-top: 28px;
    padding-top: 18px;
    text-align: center;
}}
footer p {{ margin: 8px 0; }}
</style>
</head>
<body>
<main>
{content}
<footer>
    <p>Need help or support?</p>
    <p>
      <a href="https://t.me/NightHex_X"
         target="_blank"
         rel="noopener noreferrer">
         ✈ Telegram: @NightHex_X
      </a>
    </p>
    <p class="small">© NIGHT HEX — Free HTML Hosting</p>
</footer>
</main>
</body>
</html>"""


@app.get("/")
def home():
    return make_page("""
<h1>NIGHT HEX</h1>
<p>Free HTML Hosting Platform</p>
<p>Upload your HTML file and get a shareable link.</p>

<form action="/upload" method="post"
      enctype="multipart/form-data">
    <label>Admin Password</label>
    <input type="password" name="password"
           autocomplete="current-password" required>

    <label>Choose HTML File</label>
    <input type="file" name="file"
           accept=".html,.htm" required>

    <button type="submit">Upload &amp; Host</button>
</form>

<p class="small">
HTML files only. Maximum file size: 10 MB.
</p>
""")


@app.post("/upload")
def upload():
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    supplied_password = request.form.get("password", "")

    if not admin_password:
        return make_page(
            "<h1>Setup Required</h1>"
            "<p>Configure ADMIN_PASSWORD in Render Environment.</p>"
        ), 503

    if not hmac.compare_digest(supplied_password, admin_password):
        return make_page(
            "<h1>Access Denied</h1>"
            "<p>Incorrect admin password.</p>"
        ), 401

    uploaded = request.files.get("file")

    if not uploaded or not uploaded.filename:
        abort(400)

    filename = secure_filename(uploaded.filename)

    if not filename.lower().endswith((".html", ".htm")):
        return make_page("<h1>HTML files only</h1>"), 400

    slug = Path(filename).stem.lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-")

    if not slug or slug in {"upload", "admin"}:
        return make_page("<h1>Invalid filename</h1>"), 400

    target = UPLOAD_FOLDER / f"{slug}.html"

    if target.exists():
        return make_page(
            "<h1>Name Already Exists</h1>"
            "<p>Rename the file and try again.</p>"
        ), 409

    data = uploaded.read(MAX_FILE_SIZE + 1)

    if len(data) > MAX_FILE_SIZE:
        return make_page("<h1>File Too Large</h1>"), 413

    target.write_bytes(data)

    link = request.url_root.rstrip("/") + "/" + slug

    return make_page(
        "<h1>Upload Successful!</h1>"
        "<p>Your website link:</p>"
        f'<p><a href="{escape(link)}">{escape(link)}</a></p>'
        f'<p><button onclick="navigator.clipboard.writeText('
        f'\'{escape(link)}\')">Copy Link</button></p>'
        '<p><a href="/">Back to NIGHT HEX</a></p>',
        "Upload Complete"
    ), 201


@app.get("/<slug>")
def hosted_page(slug):
    if not re.fullmatch(r"[a-z0-9-]{1,100}", slug):
        abort(404)

    target = UPLOAD_FOLDER / f"{slug}.html"

    if not target.is_file():
        abort(404)

    response = Response(
        target.read_bytes(),
        content_type="text/html; charset=utf-8"
    )

    response.headers["Content-Security-Policy"] = (
        "sandbox allow-scripts; "
        "default-src 'self' https: http: data: blob: 'unsafe-inline'; "
        "object-src 'none'; base-uri 'none';"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    return response


@app.errorhandler(413)
def file_too_large(error):
    return make_page(
        "<h1>File Too Large</h1>"
        "<p>Maximum upload size is 10 MB.</p>"
    ), 413


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000"))
    )

