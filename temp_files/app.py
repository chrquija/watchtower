import os
import uuid
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    jsonify,
    flash,
)
from werkzeug.utils import secure_filename

from models import db, Tool, Screenshot

# ── Config ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "watchtower-dev-key-change-me")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "files")
SCREENSHOT_FOLDER = os.path.join(BASE_DIR, "uploads", "screenshots")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'watchtower.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

ALLOWED_FILE_EXT = {
    "xlsx", "xlsm", "xls", "csv", "pdf", "docx", "doc", "pptx", "zip", "py", "txt",
}
ALLOWED_IMG_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

db.init_app(app)

with app.app_context():
    db.create_all()


# ── Helpers ─────────────────────────────────────────────────────────
def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def unique_filename(filename):
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    return f"{uuid.uuid4().hex[:12]}.{ext}"


# ── Routes ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tools")
def api_tools():
    """Return all tools as JSON."""
    dept = request.args.get("department", "All")
    search = request.args.get("search", "").strip().lower()
    sort = request.args.get("sort", "recent")

    query = Tool.query

    if dept and dept != "All":
        query = query.filter_by(department=dept)

    if search:
        query = query.filter(
            db.or_(
                Tool.name.ilike(f"%{search}%"),
                Tool.description.ilike(f"%{search}%"),
                Tool.tags.ilike(f"%{search}%"),
            )
        )

    if sort == "downloads":
        query = query.order_by(Tool.downloads.desc())
    elif sort == "views":
        query = query.order_by(Tool.views.desc())
    elif sort == "name":
        query = query.order_by(Tool.name.asc())
    else:
        query = query.order_by(Tool.upload_date.desc())

    tools = query.all()
    return jsonify([t.to_dict() for t in tools])


@app.route("/api/tools", methods=["POST"])
def api_create_tool():
    """Create a new tool/resource."""
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name or not description:
        return jsonify({"error": "Name and description are required"}), 400

    tool = Tool(
        name=name,
        description=description,
        department=request.form.get("department", "Engineering"),
        version=request.form.get("version", "1.0.0"),
        resource_type=request.form.get("resource_type", "Excel Tool"),
        link=request.form.get("link", "").strip(),
        tags=request.form.get("tags", ""),
        changelog=request.form.get("changelog", ""),
    )

    # Handle file upload
    file = request.files.get("file")
    if file and file.filename and allowed_file(file.filename, ALLOWED_FILE_EXT):
        safe_name = secure_filename(file.filename)
        stored_name = unique_filename(safe_name)
        file.save(os.path.join(UPLOAD_FOLDER, stored_name))
        tool.file_name = safe_name
        tool.stored_file_name = stored_name
        tool.file_size = os.path.getsize(os.path.join(UPLOAD_FOLDER, stored_name))

    db.session.add(tool)
    db.session.flush()  # get tool.id before screenshots

    # Handle screenshot uploads
    screenshots = request.files.getlist("screenshots")
    for img in screenshots:
        if img and img.filename and allowed_file(img.filename, ALLOWED_IMG_EXT):
            stored_name = unique_filename(secure_filename(img.filename))
            img.save(os.path.join(SCREENSHOT_FOLDER, stored_name))
            shot = Screenshot(tool_id=tool.id, stored_name=stored_name)
            db.session.add(shot)

    db.session.commit()
    return jsonify(tool.to_dict()), 201


@app.route("/api/tools/<int:tool_id>", methods=["PUT"])
def api_update_tool(tool_id):
    """Update an existing tool."""
    tool = Tool.query.get_or_404(tool_id)

    tool.name = request.form.get("name", tool.name).strip()
    tool.description = request.form.get("description", tool.description).strip()
    tool.department = request.form.get("department", tool.department)
    tool.version = request.form.get("version", tool.version)
    tool.resource_type = request.form.get("resource_type", tool.resource_type)
    tool.link = request.form.get("link", tool.link).strip()
    tool.tags = request.form.get("tags", tool.tags)
    tool.changelog = request.form.get("changelog", tool.changelog)
    tool.upload_date = datetime.utcnow()

    # Replace file if new one uploaded
    file = request.files.get("file")
    if file and file.filename and allowed_file(file.filename, ALLOWED_FILE_EXT):
        # Delete old file
        if tool.stored_file_name:
            old_path = os.path.join(UPLOAD_FOLDER, tool.stored_file_name)
            if os.path.exists(old_path):
                os.remove(old_path)
        safe_name = secure_filename(file.filename)
        stored_name = unique_filename(safe_name)
        file.save(os.path.join(UPLOAD_FOLDER, stored_name))
        tool.file_name = safe_name
        tool.stored_file_name = stored_name
        tool.file_size = os.path.getsize(os.path.join(UPLOAD_FOLDER, stored_name))

    # Add new screenshots (keep existing ones unless explicitly removed)
    screenshots = request.files.getlist("screenshots")
    for img in screenshots:
        if img and img.filename and allowed_file(img.filename, ALLOWED_IMG_EXT):
            stored_name = unique_filename(secure_filename(img.filename))
            img.save(os.path.join(SCREENSHOT_FOLDER, stored_name))
            shot = Screenshot(tool_id=tool.id, stored_name=stored_name)
            db.session.add(shot)

    db.session.commit()
    return jsonify(tool.to_dict())


@app.route("/api/tools/<int:tool_id>", methods=["DELETE"])
def api_delete_tool(tool_id):
    """Delete a tool and its files."""
    tool = Tool.query.get_or_404(tool_id)

    # Delete uploaded file
    if tool.stored_file_name:
        path = os.path.join(UPLOAD_FOLDER, tool.stored_file_name)
        if os.path.exists(path):
            os.remove(path)

    # Delete screenshots
    for shot in tool.screenshots:
        path = os.path.join(SCREENSHOT_FOLDER, shot.stored_name)
        if os.path.exists(path):
            os.remove(path)

    db.session.delete(tool)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/tools/<int:tool_id>/view", methods=["POST"])
def api_view_tool(tool_id):
    """Increment view count."""
    tool = Tool.query.get_or_404(tool_id)
    tool.views += 1
    db.session.commit()
    return jsonify({"views": tool.views})


@app.route("/api/tools/<int:tool_id>/download")
def api_download_tool(tool_id):
    """Download a tool's file and increment count."""
    tool = Tool.query.get_or_404(tool_id)
    tool.downloads += 1
    db.session.commit()

    if not tool.stored_file_name:
        return jsonify({"error": "No file attached"}), 404

    return send_from_directory(
        UPLOAD_FOLDER,
        tool.stored_file_name,
        as_attachment=True,
        download_name=tool.file_name,
    )


@app.route("/api/screenshots/<int:screenshot_id>", methods=["DELETE"])
def api_delete_screenshot(screenshot_id):
    """Delete a single screenshot."""
    shot = Screenshot.query.get_or_404(screenshot_id)
    path = os.path.join(SCREENSHOT_FOLDER, shot.stored_name)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(shot)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/uploads/screenshots/<filename>")
def serve_screenshot(filename):
    return send_from_directory(SCREENSHOT_FOLDER, filename)


@app.route("/api/stats")
def api_stats():
    """Overall portal stats."""
    total_tools = Tool.query.count()
    total_views = db.session.query(db.func.sum(Tool.views)).scalar() or 0
    total_downloads = db.session.query(db.func.sum(Tool.downloads)).scalar() or 0
    return jsonify(
        {"tools": total_tools, "views": total_views, "downloads": total_downloads}
    )


# ── Run ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
