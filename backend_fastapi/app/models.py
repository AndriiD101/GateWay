from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    detected_city = Column(String(255), nullable=False)
    image_url = Column(String(1024), nullable=False)
    itinerary = Column(Text, nullable=False)
    budget_estimate = Column(Numeric(12, 2), nullable=False)

    user = relationship("User", back_populates="trips")
