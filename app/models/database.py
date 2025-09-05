"""Database models for storing property and listing data."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Property(Base):
    """Model for storing property information."""
    
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float)
    currency = Column(String(10), default="MXN")
    
    # Property details
    property_type = Column(String(50))  # Casa, Departamento, etc.
    listing_type = Column(String(20))   # Venta, Renta
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    area = Column(Float)  # in square meters
    
    # Location
    location = Column(String(255))
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Features and amenities
    features = Column(JSON)  # List of features
    amenities = Column(JSON)  # List of amenities
    
    # Images
    image_urls = Column(JSON)  # List of image URLs
    local_image_paths = Column(JSON)  # List of local image file paths
    
    # Source information
    source_url = Column(String(500))
    source_platform = Column(String(50))
    external_id = Column(String(100))  # ID from source platform
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scraped_at = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_published = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Property(id={self.id}, title='{self.title}', price={self.price})>"
    
    def to_dict(self):
        """Convert property to dictionary for form filling."""
        return {
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'property_type': self.property_type,
            'listing_type': self.listing_type,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'area': self.area,
            'location': self.location,
            'features': self.features or [],
            'amenities': self.amenities or [],
            'image_paths': self.local_image_paths or []
        }


class MarketplaceListing(Base):
    """Model for tracking Facebook Marketplace listings."""
    
    __tablename__ = "marketplace_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, nullable=False)  # Reference to Property
    
    # Facebook-specific data
    facebook_listing_id = Column(String(100))
    facebook_url = Column(String(500))
    
    # Publishing status
    status = Column(String(20), default="draft")  # draft, published, failed, deleted
    publish_attempts = Column(Integer, default=0)
    last_publish_attempt = Column(DateTime)
    
    # Error tracking
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime)
    
    def __repr__(self):
        return f"<MarketplaceListing(id={self.id}, property_id={self.property_id}, status='{self.status}')>"


class ScrapingSession(Base):
    """Model for tracking scraping sessions."""
    
    __tablename__ = "scraping_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Session details
    source_platform = Column(String(50), nullable=False)
    source_url = Column(String(500))
    
    # Results
    properties_found = Column(Integer, default=0)
    properties_scraped = Column(Integer, default=0)
    properties_failed = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default="running")  # running, completed, failed
    
    # Error tracking
    errors = Column(JSON)  # List of errors encountered
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    def __repr__(self):
        return f"<ScrapingSession(id={self.id}, platform='{self.source_platform}', status='{self.status}')>"


class PublishingSession(Base):
    """Model for tracking publishing sessions to Facebook Marketplace."""
    
    __tablename__ = "publishing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Session details
    total_properties = Column(Integer, default=0)
    published_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default="running")  # running, completed, failed
    
    # Configuration used
    config_snapshot = Column(JSON)  # Snapshot of settings used
    
    # Error tracking
    errors = Column(JSON)  # List of errors encountered
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    def __repr__(self):
        return f"<PublishingSession(id={self.id}, published={self.published_count}/{self.total_properties})>"
