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
from flask_caching import Cache
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.utils import secure_filename

from models import db, Tool, Screenshot, User

# ── Config ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "watchtower-dev-key-change-me")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "files")
SCREENSHOT_FOLDER = os.path.join(BASE_DIR, "uploads", "screenshots")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)

# ── Database Config ───────────────────────────────────────────────
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url or f"sqlite:///{os.path.join(BASE_DIR, 'watchtower.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max upload

# ── Caching ────────────────────────────────────────────────────────
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300
cache = Cache(app)

ALLOWED_FILE_EXT = {
    "xlsx", "xlsm", "xls", "csv", "pdf", "docx", "doc", "pptx", "zip", "py", "txt",
}
ALLOWED_IMG_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

# ── Auth Config ───────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Unauthorized. Please login again."}), 401
    return redirect(url_for("login"))


db.init_app(app)

with app.app_context():
    db.create_all()

    # Basic migration to add created_by column if it's missing (e.g. existing database)
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [c["name"] for c in inspector.get_columns("tools")]
        if "created_by" not in columns:
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE tools ADD COLUMN created_by INTEGER REFERENCES users(id)"))
                conn.commit()
    except Exception as e:
        print(f"Migration error (could be expected): {e}")

    # Seed admin user if none exists
    if not User.query.first():
        admin = User(
            username="admin",
            email="admin@advantec.com",
            display_name="Admin",
            role="admin",
            department="Engineering",
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()


# ── Helpers ─────────────────────────────────────────────────────────
@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}


def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def unique_filename(filename):
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    return f"{uuid.uuid4().hex[:12]}.{ext}"


# ── Routes ──────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid email or password")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "Engineering")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not display_name or not email or not password:
            flash("All fields are required")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("register"))

        user = User(
            username=email.split("@")[0],
            email=email,
            display_name=display_name,
            department=department,
            role="viewer",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/api/tools")
@login_required
@cache.cached(query_string=True)
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
@login_required
def api_create_tool():
    """Create a new tool/resource."""
    if current_user.role != "admin":
        return jsonify({"error": "Only admins can upload resources"}), 403

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
        created_by=current_user.id,
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
    cache.clear()
    return jsonify(tool.to_dict()), 201


@app.route("/api/tools/<int:tool_id>", methods=["PUT"])
@login_required
def api_update_tool(tool_id):
    """Update an existing tool."""
    if current_user.role != "admin":
        return jsonify({"error": "Only admins can edit resources"}), 403

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
    cache.clear()
    return jsonify(tool.to_dict())


@app.route("/api/tools/<int:tool_id>", methods=["DELETE"])
@login_required
def api_delete_tool(tool_id):
    """Delete a tool and its files."""
    if current_user.role != "admin":
        return jsonify({"error": "Only admins can delete resources"}), 403

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
    cache.clear()
    return jsonify({"ok": True})


@app.route("/api/tools/<int:tool_id>/view", methods=["POST"])
@login_required
def api_view_tool(tool_id):
    """Increment view count."""
    tool = Tool.query.get_or_404(tool_id)
    tool.views += 1
    db.session.commit()
    return jsonify({"views": tool.views})


@app.route("/api/tools/<int:tool_id>/download")
@login_required
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
@login_required
def api_delete_screenshot(screenshot_id):
    """Delete a single screenshot."""
    if current_user.role != "admin":
        return jsonify({"error": "Only admins can delete screenshots"}), 403

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
@login_required
@cache.cached(timeout=60)
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
