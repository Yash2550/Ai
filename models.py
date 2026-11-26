"""
models.py — SQLAlchemy ORM Models
===================================
Defines the database tables for the Label Inpainter project.

Tables:
  - UploadedImage : every image the user uploads
  - JobHistory    : every prompt + result pair
"""

from datetime import datetime
from database import db


class UploadedImage(db.Model):
    """
    Stores metadata for every image uploaded by the user.

    Columns:
      id            : auto-increment primary key
      filename      : the saved filename on disk (e.g. "abc123_label.png")
      original_name : the original name as uploaded by the user
      file_path     : relative path under static/ (e.g. "static/uploads/abc123_label.png")
      description   : short description (populated from the first prompt used with this image)
      created_at    : UTC timestamp of upload
    """
    __tablename__ = "uploaded_images"

    id            = db.Column(db.Integer, primary_key=True)
    filename      = db.Column(db.String(256), nullable=False)
    original_name = db.Column(db.String(256), nullable=False)
    file_path     = db.Column(db.String(512), nullable=False)
    description   = db.Column(db.Text, default="")
    width         = db.Column(db.Integer, default=0)   # pixel width of the image
    height        = db.Column(db.Integer, default=0)   # pixel height of the image
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # One image can have many job results
    jobs = db.relationship("JobHistory", backref="image", lazy=True, cascade="all, delete-orphan")

    def __init__(
        self,
        filename=None,
        original_name=None,
        file_path=None,
        description="",
        width=0,
        height=0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if filename is not None:
            self.filename = filename
        if original_name is not None:
            self.original_name = original_name
        if file_path is not None:
            self.file_path = file_path
        if description is not None:
            self.description = description
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        return {
            "id":            self.id,
            "filename":      self.filename,
            "original_name": self.original_name,
            "file_path":     self.file_path,
            "description":   self.description,
            "width":         self.width,
            "height":        self.height,
            "created_at":    self.created_at.strftime("%Y-%m-%d %H:%M"),
            "url":           f"/static/uploads/{self.filename}",
        }


class JobHistory(db.Model):
    """
    Stores every AI edit / generation job that was run.

    Columns:
      id              : auto-increment primary key
      image_id        : FK to UploadedImage (NULL for text-to-image jobs)
      prompt          : the prompt the user typed
      result_filename : the result image filename in static/results/
      api_provider    : "recraft" | "nanobanana"
      mode            : "remove" | "add" | "replace" | "generate"
      created_at      : UTC timestamp
    """
    __tablename__ = "job_history"

    id              = db.Column(db.Integer, primary_key=True)
    image_id        = db.Column(db.Integer, db.ForeignKey("uploaded_images.id"), nullable=True)
    prompt          = db.Column(db.Text, nullable=False)
    result_filename = db.Column(db.String(256), nullable=False)
    api_provider    = db.Column(db.String(64), default="recraft")
    mode            = db.Column(db.String(32), default="remove")
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(
        self,
        image_id=None,
        prompt="",
        result_filename="",
        api_provider="recraft",
        mode="remove",
        **kwargs,
    ):
        super().__init__(**kwargs)
        if image_id is not None:
            self.image_id = image_id
        if prompt is not None:
            self.prompt = prompt
        if result_filename is not None:
            self.result_filename = result_filename
        if api_provider is not None:
            self.api_provider = api_provider
        if mode is not None:
            self.mode = mode
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        return {
            "id":              self.id,
            "image_id":        self.image_id,
            "prompt":          self.prompt,
            "result_filename": self.result_filename,
            "result_url":      f"/static/results/{self.result_filename}",
            "api_provider":    self.api_provider,
            "mode":            self.mode,
            "created_at":      self.created_at.strftime("%Y-%m-%d %H:%M"),
            "original_url":    f"/static/uploads/{self.image.filename}" if self.image else None,
            "original_name":   self.image.original_name if self.image else "Text-to-Image",
        }


class SavedProject(db.Model):
    """
    Stores complete editable design projects for GOMZI BOB AI Studio.
    """
    __tablename__ = "saved_projects"

    id              = db.Column(db.String(128), primary_key=True)
    title           = db.Column(db.String(256), nullable=False, default="Untitled Project")
    product         = db.Column(db.String(128), default="Whey Protein Standard")
    container       = db.Column(db.String(128), default="1 kg Muscle Tub · 45.2 × 14.2 cm")
    brand_name      = db.Column(db.String(128), default="GOMZI NUTRITION")
    container_color = db.Column(db.String(32), default="#18181b")
    canvas_json     = db.Column(db.Text, default="{}")
    thumbnail       = db.Column(db.Text, default="")
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_canvas=False):
        import json
        data = {
            "id":              self.id,
            "title":           self.title,
            "product":         self.product,
            "container":       self.container,
            "brand_name":      self.brand_name,
            "container_color": self.container_color,
            "thumbnail":       self.thumbnail or "",
            "created_at":      self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at":      self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }
        if include_canvas:
            try:
                data["canvas_json"] = json.loads(self.canvas_json) if self.canvas_json else {}
            except Exception:
                data["canvas_json"] = {}
        return data


class ApiUsageLog(db.Model):
    """
    Tracks real AI API calls, provider/model usage, latency, status, and estimated cost.
    Never fabricates usage metrics.
    """
    __tablename__ = "api_usage_logs"

    id            = db.Column(db.Integer, primary_key=True)
    provider      = db.Column(db.String(64), nullable=False)
    model         = db.Column(db.String(128), default="")
    mode          = db.Column(db.String(64), default="generate")
    status        = db.Column(db.String(32), default="success")  # success | failed
    latency_ms    = db.Column(db.Integer, default=0)
    estimated_usd = db.Column(db.Float, default=0.0)
    error_message = db.Column(db.Text, default="")
    prompt_preview = db.Column(db.String(256), default="")
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":             self.id,
            "provider":       self.provider,
            "model":          self.model,
            "mode":           self.mode,
            "status":         self.status,
            "latency_ms":     self.latency_ms,
            "estimated_usd":  round(float(self.estimated_usd or 0.0), 4),
            "error_message":  self.error_message or "",
            "prompt_preview": self.prompt_preview or "",
            "created_at":     self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }


class BrandKitProfile(db.Model):
    """Stores merchant brand kits (Brand name, colors, fonts, logo path)."""
    __tablename__ = "brand_kits"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(128), nullable=False, default="GOMZI NUTRITION")
    primary_color = db.Column(db.String(32), default="#74883D")
    secondary_color = db.Column(db.String(32), default="#25372A")
    font_family = db.Column(db.String(64), default="Montserrat")
    logo_url   = db.Column(db.String(512), default="/static/assets/gomzi_logo.svg")
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":              self.id,
            "name":            self.name,
            "primary_color":   self.primary_color,
            "secondary_color": self.secondary_color,
            "font_family":     self.font_family,
            "logo_url":        self.logo_url,
            "is_default":      bool(self.is_default),
        }


