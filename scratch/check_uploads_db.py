import sys, os
sys.path.insert(0, os.path.abspath("."))
from app import app
from models import UploadedImage

with app.app_context():
    imgs = UploadedImage.query.order_by(UploadedImage.created_at.desc()).limit(10).all()
    for im in imgs:
        print(f"ID: {im.id}, to_dict: {im.to_dict()}")
