import asyncio
import json
from pathlib import Path
import aiohttp
from playwright.async_api import async_playwright

# New modular imports
from app.integrations.century21.data_scraper import Century21RobustScraper
from app.integrations.century21.image_scraper import scrape_images
from app.integrations.facebook.login import get_logged_in_page
from app.core.automation.facebook.marketplace import open_marketplace_housing
from app.core.automation.facebook.housing import fill_marketplace_housing_form, upload_photos_to_fb_form
from app.core.credential_manager import get_facebook_credentials

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def download_image(session, url, path):
    """Asynchronously downloads an image from a URL and saves it to a path."""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                with open(path, 'wb') as f:
                    f.write(await response.read())
                return True
            else:
                logging.warning(f"Failed to download {url}: Status {response.status}")
                return False
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")
        return False

async def main(property_url: str):
    """
    Orquesta el scraping de datos, el scraping de imágenes y la creación de un listado
    utilizando la nueva arquitectura modular.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 1. Scrape data
    logger.info(f"Iniciando el flujo para la URL: {property_url}")
    data_scraper = Century21RobustScraper(concurrency=8)
    scraped_data = await data_scraper.run([property_url])
    property_data = scraped_data[0] if scraped_data and isinstance(scraped_data, list) else {}

    if not property_data or "error" in property_data:
        logging.error(f"Failed to scrape property data from {property_url}.")
        return

    # Scrape image URLs
    image_urls = await scrape_images(property_url)

    # Create a temporary directory for images
    temp_image_dir = Path("temp_images")
    temp_image_dir.mkdir(exist_ok=True)
    
    downloaded_image_paths = []
    if image_urls:
        logging.info(f"Downloading {len(image_urls)} images...")
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, img_url in enumerate(image_urls):
                image_path = temp_image_dir / f"image_{i}.jpg"
                tasks.append(download_image(session, img_url, image_path))
                downloaded_image_paths.append(str(image_path))
            await asyncio.gather(*tasks)
        logging.info("Image download complete.")

    # 3. Create Facebook Listing using new modular approach
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        try:
            # Get a logged-in page
            page = await get_logged_in_page(context)

            if not page:
                logger.error("No se pudo iniciar sesión en Facebook.")
                return

            # Open the housing creator form
            page = await open_marketplace_housing(page)
            logger.info("Formulario de creación de vivienda abierto.")

            # Prepare data for the form-filling function
            form_data = {
                "recamaras": property_data.get("recámaras") or property_data.get("recamaras"),
                "banos": property_data.get("baños"),
                "precio": property_data.get("precio"),
                "direccion": property_data.get("direccion"),
                "estacionamiento": property_data.get("estacionamientos"),
            }
            
            description_text = property_data.get("descripcion", "")
            property_type_val = property_data.get("tipo_propiedad", "Casa")
            
            logger.info("Llenando el formulario con los datos extraídos...")
            # Fill the form
            await fill_marketplace_housing_form(
                page,
                data=form_data,
                listing_kind="Venta",
                property_type=property_type_val,
                description=description_text,
                fill_location=True,
                fill_price=True,
                fill_numbers=True,
            )
            logger.info("Formulario llenado.")

            # Upload photos
            if downloaded_image_paths:
                logger.info("Subiendo imágenes...")
                await upload_photos_to_fb_form(page, temp_image_dir)
                logger.info("Imágenes subidas.")

        except Exception as e:
            logger.error(f"Ocurrió un error durante la automatización de Facebook: {e}", exc_info=True)
        finally:
            # Clean up downloaded images
            for img_path_str in downloaded_image_paths:
                img_path = Path(img_path_str)
                if img_path.exists():
                    img_path.unlink()
            if temp_image_dir.exists():
                temp_image_dir.rmdir()
            
            logger.info("El script ha finalizado. El navegador permanecerá abierto durante 5 minutos para revisión manual.")
            await asyncio.sleep(300) # Keep browser open for 5 minutes


if __name__ == "__main__":
    # The URL is hardcoded for this example.
    property_url = "https://century21mexico.com/propiedad/591129_departamento-en-venta-en-lomas-de-costa-azul-acapulco-gro"
    asyncio.run(main(property_url))
