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
