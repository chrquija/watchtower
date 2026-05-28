from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)  # Engineering, Administration, Finance
    role = db.Column(db.String(20), default="viewer")     # admin or viewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to tools created by this user
    tools = db.relationship("Tool", backref="creator", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Tool(db.Model):
    __tablename__ = "tools"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(50), default="Engineering")
    version = db.Column(db.String(20), default="1.0.0")
    resource_type = db.Column(db.String(30), default="Excel Tool")  # Excel Tool, Streamlit App, Other
    link = db.Column(db.String(500), default="")  # for Streamlit apps
    tags = db.Column(db.String(500), default="")
    changelog = db.Column(db.Text, default="")

    # Creator
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # File info
    file_name = db.Column(db.String(300), default="")       # original name
    stored_file_name = db.Column(db.String(300), default="") # uuid name on disk
    file_size = db.Column(db.Integer, default=0)             # bytes

    # Metrics
    views = db.Column(db.Integer, default=0)
    downloads = db.Column(db.Integer, default=0)

    # Timestamps
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    screenshots = db.relationship("Screenshot", backref="tool", cascade="all, delete-orphan", lazy=True)

    def file_size_display(self):
        if not self.file_size:
            return ""
        if self.file_size >= 1_048_576:
            return f"{self.file_size / 1_048_576:.1f} MB"
        if self.file_size >= 1024:
            return f"{self.file_size / 1024:.0f} KB"
        return f"{self.file_size} B"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "department": self.department,
            "version": self.version,
            "resource_type": self.resource_type,
            "link": self.link,
            "tags": [t.strip() for t in self.tags.split(",") if t.strip()] if self.tags else [],
            "changelog": self.changelog,
            "file_name": self.file_name,
            "file_size": self.file_size_display(),
            "views": self.views,
            "downloads": self.downloads,
            "upload_date": self.upload_date.isoformat() if self.upload_date else "",
            "has_file": bool(self.stored_file_name),
            "creator_name": self.creator.display_name if self.creator else "Unknown",
            "screenshots": [
                {"id": s.id, "url": f"/uploads/screenshots/{s.stored_name}"}
                for s in self.screenshots
            ],
        }


class Screenshot(db.Model):
    __tablename__ = "screenshots"

    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey("tools.id"), nullable=False)
    stored_name = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
