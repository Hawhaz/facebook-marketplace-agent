"""Facebook Marketplace housing form automation."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from playwright.async_api import Page, Locator

from app.utils.money import fmt_money, m2, plural

logger = logging.getLogger(__name__)


async def fill_marketplace_housing_form(page: Page, property_data: Dict[str, Any]) -> bool:
    """
    Fill the Facebook Marketplace housing form with property data.
    
    Args:
        page: Playwright page object
        property_data: Dictionary containing property information
        
    Returns:
        True if form was filled successfully, False otherwise
    """
    try:
        logger.info("Starting to fill housing form with property data")
        
        # Wait for the form to be ready
        await page.wait_for_selector('[data-testid="marketplace-composer-title-input"]', timeout=10000)
        
        # Fill title
        title = property_data.get('title', '')
        if title:
            await page.fill('[data-testid="marketplace-composer-title-input"]', title)
            logger.info(f"Filled title: {title}")
        
        # Fill price
        price = property_data.get('price')
        if price:
            price_str = str(price).replace('$', '').replace(',', '').replace(' MXN', '')
            await page.fill('[data-testid="marketplace-composer-price-input"]', price_str)
            logger.info(f"Filled price: {price_str}")
        
        # Fill description
        description = _build_description(property_data)
        if description:
            await page.fill('[data-testid="marketplace-composer-description-input"]', description)
            logger.info("Filled description")
        
        # Select category (Housing)
        await _select_housing_category(page)
        
        # Fill housing-specific fields
        await _fill_housing_details(page, property_data)
        
        # Fill location
        location = property_data.get('location', '')
        if location:
            await _fill_location(page, location)
        
        logger.info("Successfully filled housing form")
        return True
        
    except Exception as e:
        logger.error(f"Error filling housing form: {e}")
        return False


def _build_description(property_data: Dict[str, Any]) -> str:
    """
    Build a comprehensive description from property data.
    
    Args:
        property_data: Property information dictionary
        
    Returns:
        Formatted description string
    """
    parts = []
    
    # Basic info
    bedrooms = property_data.get('bedrooms', 0)
    bathrooms = property_data.get('bathrooms', 0)
    area = property_data.get('area')
    
    if bedrooms or bathrooms:
        room_info = []
        if bedrooms:
            room_info.append(f"{bedrooms} {plural(bedrooms, 'recámara', 'recámaras')}")
        if bathrooms:
            room_info.append(f"{bathrooms} {plural(bathrooms, 'baño', 'baños')}")
        parts.append(" • ".join(room_info))
    
    if area:
        parts.append(f"Área: {m2(area)}")
    
    # Features
    features = property_data.get('features', [])
    if features:
        parts.append("\n🏠 Características:")
        for feature in features[:10]:  # Limit to 10 features
            parts.append(f"• {feature}")
    
    # Additional description
    extra_desc = property_data.get('description', '')
    if extra_desc:
        parts.append(f"\n{extra_desc}")
    
    # Contact info
    parts.append("\n📞 ¡Contáctanos para más información!")
    
    return "\n".join(parts)


async def _select_housing_category(page: Page) -> None:
    """
    Select the housing category in the marketplace form.
    
    Args:
        page: Playwright page object
    """
    try:
        # Look for category selector
        category_selector = '[data-testid="marketplace-composer-category-selector"]'
        await page.wait_for_selector(category_selector, timeout=5000)
        await page.click(category_selector)
        
        # Wait for category options and select housing
        housing_option = 'text="Vivienda en venta o alquiler"'
        await page.wait_for_selector(housing_option, timeout=5000)
        await page.click(housing_option)
        
        logger.info("Selected housing category")
        
    except Exception as e:
        logger.warning(f"Could not select housing category: {e}")


async def _fill_housing_details(page: Page, property_data: Dict[str, Any]) -> None:
    """
    Fill housing-specific form fields.
    
    Args:
        page: Playwright page object
        property_data: Property information dictionary
    """
    try:
        # Property type (Casa, Departamento, etc.)
        property_type = property_data.get('property_type', '')
        if property_type:
            await _select_dropdown_option(page, 'property-type', property_type)
        
        # Listing type (Venta/Renta)
        listing_type = property_data.get('listing_type', 'Venta')
        await _select_dropdown_option(page, 'listing-type', listing_type)
        
        # Bedrooms
        bedrooms = property_data.get('bedrooms')
        if bedrooms:
            await _fill_number_field(page, 'bedrooms', bedrooms)
        
        # Bathrooms
        bathrooms = property_data.get('bathrooms')
        if bathrooms:
            await _fill_number_field(page, 'bathrooms', bathrooms)
        
        # Area
        area = property_data.get('area')
        if area:
            await _fill_number_field(page, 'area', area)
        
        logger.info("Filled housing details")
        
    except Exception as e:
        logger.warning(f"Could not fill all housing details: {e}")


async def _select_dropdown_option(page: Page, field_name: str, value: str) -> None:
    """
    Select an option from a dropdown field.
    
    Args:
        page: Playwright page object
        field_name: Name/identifier of the field
        value: Value to select
    """
    try:
        # This is a generic approach - actual selectors may vary
        dropdown_selector = f'[data-testid="{field_name}-dropdown"]'
        await page.click(dropdown_selector)
        
        option_selector = f'text="{value}"'
        await page.click(option_selector)
        
    except Exception as e:
        logger.warning(f"Could not select {field_name} option '{value}': {e}")


async def _fill_number_field(page: Page, field_name: str, value: int) -> None:
    """
    Fill a numeric input field.
    
    Args:
        page: Playwright page object
        field_name: Name/identifier of the field
        value: Numeric value to fill
    """
    try:
        field_selector = f'[data-testid="{field_name}-input"]'
        await page.fill(field_selector, str(value))
        
    except Exception as e:
        logger.warning(f"Could not fill {field_name} field with value {value}: {e}")


async def _fill_location(page: Page, location: str) -> None:
    """
    Fill the location field.
    
    Args:
        page: Playwright page object
        location: Location string
    """
    try:
        location_selector = '[data-testid="marketplace-composer-location-input"]'
        await page.fill(location_selector, location)
        
        # Wait for location suggestions and select the first one
        await asyncio.sleep(2)
        suggestion_selector = '[data-testid="location-suggestion-0"]'
        try:
            await page.click(suggestion_selector, timeout=3000)
        except:
            # If no suggestions appear, that's okay
            pass
        
        logger.info(f"Filled location: {location}")
        
    except Exception as e:
        logger.warning(f"Could not fill location: {e}")


async def upload_photos_to_fb_form(page: Page, image_paths: List[Path]) -> bool:
    """
    Upload photos to the Facebook Marketplace housing form.
    
    Args:
        page: Playwright page object
        image_paths: List of image file paths to upload
        
    Returns:
        True if photos were uploaded successfully, False otherwise
    """
    try:
        if not image_paths:
            logger.warning("No image paths provided for upload")
            return False
        
        logger.info(f"Starting to upload {len(image_paths)} photos")
        
        # Look for the photo upload button/area
        upload_selectors = [
            '[data-testid="marketplace-composer-media-upload"]',
            '[aria-label="Add Photos"]',
            'input[type="file"][accept*="image"]',
            '[data-testid="media-upload-button"]'
        ]
        
        upload_element = None
        for selector in upload_selectors:
            try:
                upload_element = await page.wait_for_selector(selector, timeout=3000)
                if upload_element:
                    break
            except:
                continue
        
        if not upload_element:
            logger.error("Could not find photo upload element")
            return False
        
        # Convert paths to strings
        file_paths = [str(path.absolute()) for path in image_paths if path.exists()]
        
        if not file_paths:
            logger.error("No valid image files found")
            return False
        
        # Upload files
        await upload_element.set_input_files(file_paths)
        
        # Wait for upload to complete
        await asyncio.sleep(2)
        
        # Verify upload by checking for uploaded images
        uploaded_images = await page.query_selector_all('[data-testid="uploaded-image"]')
        
        logger.info(f"Successfully uploaded {len(uploaded_images)} photos")
        return len(uploaded_images) > 0
        
    except Exception as e:
        logger.error(f"Error uploading photos: {e}")
        return False
