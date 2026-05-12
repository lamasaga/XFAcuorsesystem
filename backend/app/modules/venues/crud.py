from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional

def get_venue(db: Session, venue_id: int):
    return db.query(models.Venue).filter(models.Venue.id == venue_id).first()

def get_venues(
    db: Session, 
    skip: int = 0, 
    limit: int = 100
):
    return db.query(models.Venue).offset(skip).limit(limit).all()

def create_venue(db: Session, venue: schemas.VenueCreate):
    db_venue = models.Venue(**venue.model_dump())
    db.add(db_venue)
    db.commit()
    db.refresh(db_venue)
    return db_venue

def delete_venue(db: Session, venue_id: int):
    venue = get_venue(db, venue_id)
    if venue:
        db.delete(venue)
        db.commit()
    return venue

def update_venue(db: Session, venue_id: int, venue_update: schemas.VenueUpdate):
    db_venue = get_venue(db, venue_id)
    if not db_venue:
        return None
    
    update_data = venue_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_venue, key, value)
    
    db.commit()
    db.refresh(db_venue)
    return db_venue
