"""
Trip management endpoints (Azure SQL-backed).

Routes
------
GET    /trips                    – List own trips            [JWT]
GET    /trips/{trip_id}          – Get single trip           [JWT, self or admin]
POST   /trips                    – Create trip manually      [JWT]
DELETE /trips/{trip_id}          – Delete trip               [JWT, self or admin]
GET    /trips/user/{user_id}     – Admin: list trips by user [JWT, admin]
"""

import json
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models import Trip
from app.schemas import TripCreate

router = APIRouter(prefix="/trips", tags=["trips"])


def _trip_payload(trip: Trip) -> dict:
    try:
        itinerary = json.loads(trip.itinerary) if trip.itinerary else []
    except (json.JSONDecodeError, TypeError):
        itinerary = []
    return {
        "id": trip.id,
        "user_id": trip.user_id,
        "detected_city": trip.detected_city,
        "image_url": trip.image_url,
        "itinerary": itinerary,
        "budget_estimate": str(trip.budget_estimate),
    }


@router.get("")
def list_my_trips(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return all trips belonging to the authenticated user."""
    user_id = current_user["user_id"]
    trips = db.scalars(select(Trip).where(Trip.user_id == user_id).order_by(Trip.id.desc())).all()
    return [_trip_payload(t) for t in trips]


@router.get("/user/{user_id}")
def list_trips_by_user(
    user_id: int,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: list all trips for a specific user."""
    trips = db.scalars(select(Trip).where(Trip.user_id == user_id).order_by(Trip.id.desc())).all()
    return [_trip_payload(t) for t in trips]


@router.get("/{trip_id}")
def get_trip(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found.")
    if trip.user_id != current_user["user_id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    return _trip_payload(trip)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_trip(
    body: TripCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually create a trip record (AI pipeline skipped)."""
    try:
        budget = Decimal(str(body.budget_estimate))
    except (InvalidOperation, ValueError, TypeError):
        budget = Decimal("0")

    trip = Trip(
        user_id=current_user["user_id"],
        detected_city=body.detected_city,
        image_url=body.image_url,
        itinerary=json.dumps(body.itinerary),
        budget_estimate=budget,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return _trip_payload(trip)


@router.delete("/{trip_id}", status_code=status.HTTP_200_OK)
def delete_trip(
    trip_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a trip (owner or admin)."""
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found.")
    if trip.user_id != current_user["user_id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    db.delete(trip)
    db.commit()
    return {"message": f"Trip {trip_id} deleted."}
