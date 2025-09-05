"""Main application entry point for Facebook Marketplace agent."""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.db.session import create_tables, get_db_context
from app.models.database import Property, MarketplaceListing, PublishingSession

# Setup logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log') if Path('logs').exists() else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


async def initialize_database():
    """Initialize database tables."""
    logger.info("Initializing database...")
    try:
        create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def get_properties_to_publish() -> List[Property]:
    """Get properties that need to be published to Facebook Marketplace."""
    with get_db_context() as db:
        # Get properties that haven't been published yet
        properties = db.query(Property).filter(
            Property.is_active == True,
            Property.is_published == False
        ).limit(settings.MAX_LISTINGS_PER_SESSION).all()
        
        logger.info(f"Found {len(properties)} properties to publish")
        return properties


async def publish_to_facebook_marketplace(properties: List[Property]) -> bool:
    """Publish properties to Facebook Marketplace."""
    if not properties:
        logger.info("No properties to publish")
        return True
    
    logger.info(f"Starting to publish {len(properties)} properties to Facebook Marketplace")
    
    # Create publishing session
    with get_db_context() as db:
        session = PublishingSession(
            total_properties=len(properties),
            config_snapshot={
                'headless': settings.HEADLESS_BROWSER,
                'max_listings': settings.MAX_LISTINGS_PER_SESSION,
                'delay_between_posts': settings.DELAY_BETWEEN_POSTS
            }
        )
        db.add(session)
        db.commit()
        session_id = session.id
    
    try:
        from playwright.async_api import async_playwright
        from app.core.automation.facebook.housing import fill_marketplace_housing_form, upload_photos_to_fb_form
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=settings.HEADLESS_BROWSER,
                args=['--no-sandbox', '--disable-dev-shm-usage'] if settings.HEADLESS_BROWSER else []
            )
            
            try:
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                
                page = await context.new_page()
                
                # Navigate to Facebook Marketplace
                logger.info("Navigating to Facebook Marketplace...")
                await page.goto('https://www.facebook.com/marketplace/create/item')
                
                # Wait for login if needed
                await page.wait_for_load_state('networkidle')
                
                # Check if we need to login
                if 'login' in page.url.lower():
                    logger.warning("Facebook login required. Please login manually and restart.")
                    if not settings.HEADLESS_BROWSER:
                        input("Please login to Facebook and press Enter to continue...")
                    else:
                        logger.error("Cannot login in headless mode")
                        return False
                
                published_count = 0
                failed_count = 0
                
                for i, property_obj in enumerate(properties):
                    logger.info(f"Publishing property {i+1}/{len(properties)}: {property_obj.title}")
                    
                    try:
                        # Convert property to dict for form filling
                        property_data = property_obj.to_dict()
                        
                        # Fill the form
                        success = await fill_marketplace_housing_form(page, property_data)
                        
                        if success:
                            # Upload photos if available
                            if property_data.get('image_paths'):
                                image_paths = [Path(p) for p in property_data['image_paths']]
                                await upload_photos_to_fb_form(page, image_paths)
                            
                            # Submit the form (you might want to add confirmation)
                            if settings.AUTO_SUBMIT_LISTINGS:
                                submit_button = await page.query_selector('[data-testid="marketplace-composer-publish-button"]')
                                if submit_button:
                                    await submit_button.click()
                                    await page.wait_for_load_state('networkidle')
                                    logger.info(f"Successfully published: {property_obj.title}")
                                else:
                                    logger.warning("Could not find submit button")
                            
                            # Update property status
                            with get_db_context() as db:
                                prop = db.query(Property).filter(Property.id == property_obj.id).first()
                                if prop:
                                    prop.is_published = True
                                    
                                    # Create marketplace listing record
                                    listing = MarketplaceListing(
                                        property_id=property_obj.id,
                                        status='published' if settings.AUTO_SUBMIT_LISTINGS else 'draft'
                                    )
                                    db.add(listing)
                            
                            published_count += 1
                            
                        else:
                            logger.error(f"Failed to fill form for: {property_obj.title}")
                            failed_count += 1
                        
                        # Delay between posts
                        if i < len(properties) - 1:  # Don't delay after the last property
                            logger.info(f"Waiting {settings.DELAY_BETWEEN_POSTS} seconds before next post...")
                            await asyncio.sleep(settings.DELAY_BETWEEN_POSTS)
                        
                        # Navigate to create new listing for next property
                        if i < len(properties) - 1:
                            await page.goto('https://www.facebook.com/marketplace/create/item')
                            await page.wait_for_load_state('networkidle')
                    
                    except Exception as e:
                        logger.error(f"Error publishing property {property_obj.title}: {e}")
                        failed_count += 1
                        continue
                
                # Update publishing session
                with get_db_context() as db:
                    session = db.query(PublishingSession).filter(PublishingSession.id == session_id).first()
                    if session:
                        session.published_count = published_count
                        session.failed_count = failed_count
                        session.status = 'completed'
                        session.completed_at = asyncio.get_event_loop().time()
                
                logger.info(f"Publishing completed. Published: {published_count}, Failed: {failed_count}")
                return failed_count == 0
                
            finally:
                await browser.close()
                
    except Exception as e:
        logger.error(f"Publishing failed: {e}")
        
        # Update session with error
        with get_db_context() as db:
            session = db.query(PublishingSession).filter(PublishingSession.id == session_id).first()
            if session:
                session.status = 'failed'
                session.errors = [str(e)]
                session.completed_at = asyncio.get_event_loop().time()
        
        return False


async def main():
    """Main application entry point."""
    logger.info("Starting Facebook Marketplace Agent")
    
    try:
        # Initialize database
        await initialize_database()
        
        # Get properties to publish
        properties = await get_properties_to_publish()
        
        if not properties:
            logger.info("No properties found to publish. Exiting.")
            return
        
        # Publish to Facebook Marketplace
        success = await publish_to_facebook_marketplace(properties)
        
        if success:
            logger.info("✅ All properties published successfully!")
        else:
            logger.error("❌ Some properties failed to publish")
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
