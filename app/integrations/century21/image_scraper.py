import asyncio
from playwright.async_api import async_playwright

async def scrape_images(url):
    """
    Navega a la página de una propiedad, abre la galería de imágenes,
    la recorre y extrae las URLs de las imágenes.
    """
    print("Lanzando el navegador...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Lista para almacenar las URLs de las imágenes
        image_urls = []

        # Evento para capturar las respuestas de red
        def handle_response(response):
            if "propiedades" in response.url and response.url.endswith(".jpg"):
                image_urls.append(response.url)

        page.on("response", handle_response)

        print(f"Navegando a {url}...")
        await page.goto(url, wait_until='networkidle')

        # Obtener el número de fotos del botón
        photo_count = 38 # Valor por defecto
        try:
            photo_count_text = await page.inner_text('button.btn-primary:has-text("Fotos")', timeout=5000)
            photo_count = int("".join(filter(str.isdigit, photo_count_text)))
            print(f"Número de fotos detectado en el botón: {photo_count}")
        except Exception as e:
            print(f"No se pudo leer el número de fotos del botón, se usará el valor por defecto ({photo_count}). Error: {e}")

        print("Abriendo la galería de imágenes...")
        try:
            await page.wait_for_selector('div#fotos img', timeout=10000)
            await page.click('div#fotos img')
            print("Galería abierta. Recorriendo las imágenes...")
            await asyncio.sleep(1) # Pequeña pausa para asegurar que la galería está lista para recibir eventos de teclado.

        except Exception as e:
            print(f"No se pudo hacer clic en la imagen para abrir la galería: {e}")
            await browser.close()
            return []

        print(f"Recorriendo la galería de {photo_count} imágenes...")
        for i in range(photo_count):
            await page.keyboard.press('ArrowRight')
            await asyncio.sleep(0.1)  # Pequeña espera para que la imagen cargue

        await browser.close()

        # Filtrar para obtener URLs únicas basadas en el nombre del archivo
        unique_image_files = {}
        for url in image_urls:
            filename = url.split('/')[-1]
            if filename not in unique_image_files:
                unique_image_files[filename] = url
        
        unique_urls = list(unique_image_files.values())

        print(f"Se encontraron {len(unique_urls)} URLs de imágenes únicas.")
        return unique_urls

if __name__ == '__main__':
    property_url = 'https://century21mexico.com/propiedad/591129_departamento-en-venta-en-lomas-de-costa-azul-acapulco-gro'
    
    # Ejecutar la función asíncrona
    image_urls_found = asyncio.run(scrape_images(property_url))
    
    if image_urls_found:
        print("\n--- URLs de Imágenes Encontradas ---")
        for i, url in enumerate(image_urls_found, 1):
            print(f"{i}. {url}")
    else:
        print("No se encontraron imágenes para la URL proporcionada.")