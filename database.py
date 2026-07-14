"""
database.py — SQLAlchemy + SQLite setup
========================================
Creates the SQLAlchemy `db` instance and configures the Flask app to
connect to a local SQLite file (app.db) in the project root.
"""

from flask_sqlalchemy import SQLAlchemy

# The single shared SQLAlchemy instance used across the project.
db = SQLAlchemy()


def init_db(app):
    """
    Bind the SQLAlchemy instance to a Flask app and create all tables.
    Call this once during app startup, before the first request.
    """
    # SQLite file stored in the project root next to app.py
    app.config.setdefault(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///app.db"
    )
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    db.init_app(app)

    # Import models so SQLAlchemy knows about them before create_all()
    from models import UploadedImage, JobHistory  # noqa: F401

    with app.app_context():
        db.create_all()

        # Safe migration: add new columns to existing DB if they don't exist yet.
        # SQLite doesn't support ALTER TABLE ... ADD COLUMN IF NOT EXISTS,
        # so we check the column list first.
        with db.engine.connect() as conn:
            from sqlalchemy import text, inspect as sa_inspect
            inspector = sa_inspect(db.engine)
            existing_cols = {c["name"] for c in inspector.get_columns("uploaded_images")}
            for col_def in [
                ("width",  "INTEGER DEFAULT 0"),
                ("height", "INTEGER DEFAULT 0"),
            ]:
                if col_def[0] not in existing_cols:
                    conn.execute(text(f"ALTER TABLE uploaded_images ADD COLUMN {col_def[0]} {col_def[1]}"))
            conn.commit()
