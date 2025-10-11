from datetime import datetime
from ..extensions import db


class News(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(255), nullable=False)
  excerpt = db.Column(db.String(500))
  content = db.Column(db.Text)
  image_url = db.Column(db.String(500))
  status = db.Column(db.String(20), default="pending")  # pending | published | rejected
  order_index = db.Column(db.Integer, default=0)
  category = db.Column(db.String(50), default="comunicados")  # comunicados | prensa | blog
  created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
  created_at = db.Column(db.DateTime, default=datetime.utcnow)

  def to_dict(self):
      """Convertir a diccionario para API"""
      return {
          "id": self.id,
          "title": self.title,
          "excerpt": self.excerpt,
          "content": self.content,
          "image_url": self.image_url,
          "status": self.status,
          "order_index": self.order_index,
          "category": self.category,
          "created_at": self.created_at.isoformat() if self.created_at else None,
          "created_by_user_id": self.created_by_user_id
      }


