import asyncio
import re
import time
import json
import pandas as pd
import datetime
from playwright.async_api import async_playwright, Route, BrowserContext
from bs4 import BeautifulSoup, Tag, NavigableString
import logging
import sys

# --- Configuración Básica de Logging ---
# Nivel INFO muestra el progreso.
logging.basicConfig(level=logging.INFO, format='%(message)s')

# --- Configuración Global ---
CONCURRENCY_LIMIT = 8
TIMEOUT = 30000
HEADLESS = True
RESOURCES_TO_BLOCK = ["image", "stylesheet", "media", "font", "other"]

class Century21RobustScraper:
    def __init__(self, concurrency):
        self.concurrency_limit = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        # Usamos 2025 como referencia basado en el contexto de la conversación
        self.current_year = 2025

    # --------------------------------------------------
    # FUNCIONES DE LIMPIEZA Y UTILIDAD (ACTUALIZADO)
    # --------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """Limpia texto reemplazando todo el whitespace por un solo espacio. Ideal para campos de una línea."""
        if not text:
            return ""
        text = re.sub(r'[\u200b-\u200d\u2060\ufeff]', '', text)
        # Reemplaza cualquier secuencia de whitespace (incluye \n, \t) por un espacio
        return re.sub(r'\s+', ' ', text).strip()

    # --- NUEVA FUNCIÓN PARA LA DESCRIPCIÓN ---
    def _clean_description_text(self, text: str) -> str:
        """
        Limpia el texto de la descripción preservando saltos de línea y estructura, 
        pero normalizando el whitespace horizontal y vertical excesivo.
        """
        if not text:
            return ""
        # Remover caracteres invisibles
        text = re.sub(r'[\u200b-\u200d\u2060\ufeff]', '', text)
        
        # Procesar línea por línea para normalizar el whitespace horizontal.
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Usamos \s+ para colapsar espacios, tabs, etc., y hacemos trim en los bordes.
            cleaned_line = re.sub(r'\s+', ' ', line).strip()
            cleaned_lines.append(cleaned_line)
            
        # Reunir líneas
        text_joined = '\n'.join(cleaned_lines)
        
        # Normalizar whitespace vertical: Reemplazar 3 o más \n por \n\n (máximo 1 línea en blanco)
        # Esto funciona porque las líneas vacías ahora son solo '\n'.
        text_final = re.sub(r'\n{3,}', '\n\n', text_joined).strip()
        return text_final

    def _extract_number(self, text: str) -> float | None:
        if not text:
            return None
        text = text.replace(',', '')
        match = re.search(r'(\d+\.?\d*)', text)
        return float(match.group(1)) if match else None

    def _calculate_construction_year(self, year_or_age: float) -> int | None:
        if not year_or_age:
            return None
        if 1900 <= year_or_age <= self.current_year + 2:
            return int(year_or_age)
        elif 0 < year_or_age < 100:
             return int(self.current_year - year_or_age)
        return None

    # --------------------------------------------------
    # FUNCIONES DE PARSING ESTRUCTURAL
    # --------------------------------------------------
    # (No hay cambios en _parse_main_summary ni _parse_details_and_features)

    def _parse_main_summary(self, content_area: Tag) -> dict:
        """Extrae características del bloque principal (M², Baños, etc.)."""
        data = {}
        summary_block = content_area.find('div', class_=re.compile(r"row fw-bold"))
        if not summary_block:
            return data

        items = summary_block.find_all('div', class_=re.compile(r"col my-2"))
        for item in items:
            key_tag = item.find('span', class_='text-muted')
            if key_tag:
                key = self._clean_text(key_tag.text).lower().replace(' ', '_')
                
                # Navegación DOM Robusta
                value_text = ""
                current_element = key_tag.next_sibling
                
                while current_element:
                    if isinstance(current_element, NavigableString):
                        value_text += current_element.strip() + " "
                    elif isinstance(current_element, Tag) and current_element.name == 'i':
                         break
                    current_element = current_element.next_sibling

                value_text = self._clean_text(value_text)
                data[key] = self._extract_number(value_text)
        return data

    def _parse_details_and_features(self, content_area: Tag) -> dict:
        """
        Extrae detalles (clave-valor), amenidades estructurales, 
        Y genera la 'descripcion_amenidades' narrativa preservando el orden.
        """
        data = {}
        amenities = []
        amenities_description_parts = []

        selectors = [
            'div[class*="col-sm-12 col-md-6 my-1"]',
            'div[class*="col-sm-12 col-md-6 col-lg-4 my-2"]'
        ]
        # .select() mantiene el orden del documento HTML
        items = content_area.select(','.join(selectors))

        for item in items:
            key_text = ""
            value_text = ""
            value_tag = item.find('span', class_='fw-bold')

            # --- Lógica de extracción ---
            if value_tag:
                value_text = self._clean_text(value_tag.text)
                for content in item.contents:
                    if content == value_tag:
                        break
                    if isinstance(content, NavigableString):
                        key_text += content.strip() + " "
                key_text = self._clean_text(key_text).rstrip(':').strip()
            
            if not key_text:
                 text = self._clean_text(item.get_text(separator=' ', strip=True))
                 if ':' in text and not value_text:
                     parts = text.split(':', 1)
                     key_text = self._clean_text(parts[0])
                     value_text = self._clean_text(parts[1])
                 elif text:
                     key_text_parts = []
                     for content in item.contents:
                         if isinstance(content, Tag) and content.name == 'i':
                             continue
                         if isinstance(content, NavigableString):
                             key_text_parts.append(content.strip())
                     key_text = " ".join(key_text_parts).strip()
                     value_text = ""

            # --- Procesamiento y Generación de Narrativa ---
            if key_text:
                key_normalized = key_text.lower().replace(' ', '_')

                # --- Generación Narrativa ---
                narrative_part = None
                # Excluir elementos financieros o de operación
                is_excluded = 'precio' in key_normalized or 'operacion' in key_normalized or 'cuota' in key_normalized
                
                if not is_excluded:
                    if value_text:
                        # Formato: "clave valor" (ej. "cocina integral")
                        narrative_part = f"{key_text.lower()} {value_text.lower()}"
                    else:
                        # Simple amenity (ej. "alberca")
                        narrative_part = key_text.lower()

                if narrative_part:
                     amenities_description_parts.append(narrative_part)

                # --- Extracción Estructurada ---
                if value_text:
                    numeric_value = self._extract_number(value_text)
                    if 'precio_de_venta' in key_normalized:
                        data['operacion'] = 'Venta'
                    elif 'precio_de_renta' in key_normalized:
                        data['operacion'] = 'Renta'
                    elif 'precio' not in key_normalized:
                         data[key_normalized] = numeric_value if numeric_value is not None else value_text
                else:
                    if key_text:
                        amenities.append(key_text)

        # --- Consolidación de la Descripción Narrativa ---
        if amenities_description_parts:
            # Eliminar duplicados manteniendo el orden (usando dict.fromkeys en Python >= 3.7)
            unique_parts = list(dict.fromkeys(amenities_description_parts))
            
            description_text = ", ".join(unique_parts)
            
            # Reemplazar la última coma por ' y'
            if ', ' in description_text:
                last_comma_index = description_text.rfind(', ')
                description_text = description_text[:last_comma_index] + ' y ' + description_text[last_comma_index+2:]

            data['descripcion_amenidades'] = f"La propiedad cuenta con {description_text}"

        # Guardar la lista de amenidades estructurales
        if amenities:
            filtered_amenities = [a for a in amenities if a.lower().replace(' ', '_') not in data]
            data['amenidades_estructurales'] = filtered_amenities

        return data

    # --------------------------------------------------
    # FUNCIONES DE PARSING HEURÍSTICO (DESCRIPCIÓN PRINCIPAL)
    # --------------------------------------------------
    # (No hay cambios en _find_header ni _parse_description_heuristics, ya que están diseñadas para trabajar con texto que incluye saltos de línea)

    def _find_header(self, text: str) -> re.Match | None:
        """Helper para identificar si una línea es un encabezado de sección."""
        # Usamos una versión limpia (una línea) para la detección heurística si es necesario
        text_cleaned = self._clean_text(text)
        header_match = re.match(r'^([\w\s]{2,40}?)\s*[:]?$', text_cleaned)
        if header_match:
            return header_match
        return re.match(r'^(Cercanias|Cercanías|Planta Alta|Planta Baja|Equipamiento|Distribución|Servicios en la zona).*$', text_cleaned, re.IGNORECASE)

    def _parse_description_heuristics(self, description_raw: str) -> dict:
        """Analiza la descripción de texto libre extrayendo listas y características."""
        data = {}
        current_section = 'amenidades_extraidas'
        data[current_section] = []
        caracteristicas_adicionales = {}

        if not description_raw:
            return data

        # Limpieza inicial básica para el análisis
        description_cleaned = re.sub(r'[\u200b-\u200d\u2060\ufeff]', '', description_raw)

        # Manejo de descripciones sin saltos de línea (ej. meta tags)
        if '\n' not in description_cleaned.strip() and re.search(r'[\u2022*>-]', description_cleaned):
             description_cleaned = re.sub(r'(?<!^)\s*([\u2022*>-])', r'\n\1', description_cleaned)

        lines = description_cleaned.split('\n')
        for line_raw in lines:
            line_stripped = line_raw.strip()
            if not line_stripped:
                continue

            # Detección de Keywords (Usamos _clean_text para normalizar la comparación)
            line_cleaned = self._clean_text(line_stripped) 
            is_keyword_line = False
            if "*precio a tratar*" in line_cleaned.lower() or "precio a tratar" in line_cleaned.lower() or "precio negociable" in line_cleaned.lower():
                 caracteristicas_adicionales["precio_negociable"] = True
                 is_keyword_line = True
            if "no paga mantenimiento" in line_cleaned.lower():
                 caracteristicas_adicionales["no_paga_mantenimiento"] = True
                 is_keyword_line = True

            # Normalización de Viñetas (SOLO al inicio de la línea)
            line_normalized = re.sub(r'^[\u2022*>]', '-', line_stripped)

            # Detección de Encabezados
            header_match = self._find_header(line_normalized)
            if header_match:
                header_text = header_match.group(1) if header_match.groups() and header_match.group(1) else line_normalized
                header_text = header_text.rstrip(':').strip()

                if re.match(r'^(Cercanias|Cercanías|Servicios en la zona)', header_text, re.IGNORECASE):
                    current_section = 'cercanias'
                elif re.match(r'^(Equipamiento)', header_text, re.IGNORECASE):
                     current_section = 'equipamiento'
                else:
                    current_section = self._clean_text(header_text).lower().replace(' ', '_')
                
                if current_section not in data:
                    data[current_section] = []
                continue

            # Detección de Elementos de Lista (-)
            item_match = re.match(r'^-\s*(.+)', line_normalized)
            if item_match:
                # Limpiamos el ítem extraído
                item = self._clean_text(item_match.group(1))
                if item and not is_keyword_line:
                    data[current_section].append(item)
            
            # Manejo de líneas sin bullet dentro de secciones específicas
            elif len(line_cleaned.split()) < 15 and current_section != 'amenidades_extraidas':
                 if line_cleaned and not is_keyword_line:
                    data[current_section].append(line_cleaned)

        # --- Consolidación Heurística ---
        final_data = {}
        if caracteristicas_adicionales:
            final_data['caracteristicas_adicionales'] = caracteristicas_adicionales

        amenities = data.pop('amenidades_extraidas', [])
        known_sections = ['cercanias', 'planta_baja', 'planta_alta', 'equipamiento']

        for key, value in data.items():
            if value:
                normalized_key = key
                if 'cercania' in key: normalized_key = 'cercanias'
                elif 'planta_baja' in key: normalized_key = 'planta_baja'
                elif 'planta_alta' in key: normalized_key = 'planta_alta'

                if normalized_key in known_sections:
                     if normalized_key in final_data:
                         final_data[normalized_key].extend(value)
                     else:
                         final_data[normalized_key] = value
                else:
                    amenities.extend(value)

        if amenities:
            filtered_amenities = [a for a in amenities if len(a) > 2]
            final_data['amenidades_extraidas'] = filtered_amenities

        return final_data

    # --------------------------------------------------
    # ORQUESTADOR PRINCIPAL (ACTUALIZADO)
    # --------------------------------------------------

    def parse_property_html(self, html_content: str, url: str) -> dict:
        soup = BeautifulSoup(html_content, 'lxml')
        data = {"url": url}

        content_area = soup.find('div', id='detallePropiedad')
        if not content_area:
            content_area = soup.body

        # --- Extracción Estructural Básica ---
        data['titulo'] = self._clean_text(content_area.find('h1').text) if content_area.find('h1') else None
        subtitle_tag = content_area.find('h5', class_=re.compile(r'fs-4'))
        data['subtitulo'] = self._clean_text(subtitle_tag.text) if subtitle_tag else None
        address_tag = content_area.find('h6', class_='small')
        data['direccion'] = self._clean_text(address_tag.text) if address_tag else None
        
        # Precio
        price_tag = content_area.find('h6', class_=re.compile(r"fs-3 fw-bold"))
        if price_tag:
            price_text = self._clean_text(price_tag.text)
            data['precio'] = self._extract_number(price_text)
            data['moneda'] = 'MXN' if 'mxn' in price_text.lower() else ('USD' if 'usd' in price_text.lower() else None)
        
        # --- Extracción Estructural Detallada ---
        data.update(self._parse_main_summary(content_area))
        data.update(self._parse_details_and_features(content_area))

        # --- Extracción Heurística (Descripción Principal) ---
        description_raw = None

        # Estrategia 1: Selector principal
        description_tag = content_area.find('p', class_=re.compile(r"text-muted.*white-space"))
        if description_tag:
            # Usamos separator='\n' para que BeautifulSoup reemplace <br> y fines de bloque por saltos de línea.
            description_raw = description_tag.get_text(separator='\n')

        # Estrategia 2: Fallback Meta Tags
        if not description_raw:
            meta_desc = soup.find('meta', property="og:description")
            if meta_desc and meta_desc.get('content'):
                description_raw = meta_desc['content']
                logging.debug("Usando fallback de meta tag (og:description).")

        # Procesar la descripción
        if description_raw:
            # Primero, corremos la heurística sobre el texto casi crudo (funciona bien con saltos de línea)
            data.update(self._parse_description_heuristics(description_raw))
            
            # --- CAMBIO PRINCIPAL ---
            # Luego, guardamos la descripción usando la función especializada para respetar el formato.
            data['descripcion'] = self._clean_description_text(description_raw)

        # --- Consolidación y Limpieza Final ---

        # Fusionar Amenidades (Estructural + Extraídas + Equipamiento)
        all_amenities = data.pop('amenidades_estructurales', [])
        if 'amenidades_extraidas' in data:
            all_amenities.extend(data.pop('amenidades_extraidas'))
        if 'equipamiento' in data and isinstance(data['equipamiento'], list):
             all_amenities.extend(data.pop('equipamiento'))

        
        # Limpieza final de amenidades (ordenar, deduplicar, capitalizar)
        if all_amenities:
            # Aseguramos que cada amenidad esté limpia antes de capitalizar
            cleaned_amenities = [self._clean_text(a).capitalize() for a in all_amenities if a]
            data['amenidades'] = sorted(list(set(cleaned_amenities)))

        # Manejo de 'Año de Construcción'
        if 'año_de_construcción' in data and isinstance(data['año_de_construcción'], (int, float)):
            data['año_de_construcción'] = self._calculate_construction_year(data['año_de_construcción'])

        # Mapeo de sinónimos y normalización de claves
        key_mapping = {
            'terreno': 'm²_terreno',
            'construcción': 'm²_construcción',
            'tipo': 'tipo_propiedad',
            'edo._conservación': 'edo_conservacion', # Manejo de claves con puntos
        }

        final_data = {}
        for k, v in data.items():
            final_key = key_mapping.get(k, k)
            
            # Lógica para claves duplicadas
            if final_key in final_data:
                if v is not None and final_data[final_key] is None:
                    final_data[final_key] = v
            else:
                final_data[final_key] = v

        # Eliminar claves completamente vacías
        return {k: v for k, v in final_data.items() if v not in [None, [], "", {}]}


    # --------------------------------------------------
    # GESTOR DE PLAYWRIGHT (Sin cambios)
    # --------------------------------------------------
    async def _intercept_route(self, route: Route):
        if route.request.resource_type in RESOURCES_TO_BLOCK:
            await route.abort()
            return
        url = route.request.url
        if "google-analytics" in url or "facebook" in url or "googletagmanager" in url:
            await route.abort()
            return
        await route.continue_()

    async def fetch_and_parse(self, url: str, context: BrowserContext):
        async with self.semaphore:
            logging.info(f"Fetching {url}...")
            page = await context.new_page()
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
                
                # Wait for Header
                try:
                    await page.wait_for_selector("h1, h6[class*='fs-3 fw-bold']", timeout=8000)
                except Exception:
                    logging.warning(f"  -> WARNING: Header elements did not load quickly for {url}")

                # Wait for Description/Features (Optional)
                try:
                    # Esperamos la descripción O los bloques de características (my-1, my-2)
                    await page.wait_for_selector("p[class*='text-muted'][class*='white-space'], div[class*='my-1'], div[class*='my-2']", timeout=5000)
                except Exception:
                    pass


                html_content = await page.content()
                data = self.parse_property_html(html_content, page.url) 
                logging.info(f"  -> SUCCESS: Parsed '{data.get('titulo', 'N/A')}'")
                return data
            except Exception as e:
                logging.error(f"Error processing {url}: {e}")
                return {"url": url, "error": str(e)}
            finally:
                await page.close()

    async def run(self, urls):
        start_time = time.time()
        logging.info(f"Iniciando scraping de {len(urls)} URLs...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=HEADLESS)
            
            # Configuración de Idioma (Forzar Español)
            context = await browser.new_context(
                 user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                 locale="es-MX", 
                 extra_http_headers={"Accept-Language": "es-MX,es;q=0.9"}
            )

            await context.route("**/*", self._intercept_route)
            tasks = [self.fetch_and_parse(url, context) for url in urls]
            results = await asyncio.gather(*tasks)
            await browser.close()

        end_time = time.time()
        logging.info(f"\nScraping completado en {end_time - start_time:.2f} segundos.")
        return results

# --------------------------------------------------
# EJECUCIÓN
# --------------------------------------------------
async def main():
    # Pedir al usuario que ingrese una URL
    try:
        # input() lee de stdin
        print("Por favor, ingresa la URL de la propiedad que deseas scrapear: ")
        url_input = input()
    except EOFError:
        # Manejo si stdin se cierra inesperadamente
        print("No se recibió entrada. Terminando ejecución.")
        return
    
    if not url_input or not url_input.startswith("http"):
        print("URL no válida. Por favor, ingresa una URL completa.")
        return

    urls_to_scrape = [url_input.strip()]

    scraper = Century21RobustScraper(CONCURRENCY_LIMIT)
    scraped_data = await scraper.run(urls_to_scrape)
    
    # --- Procesamiento de Resultados ---
    if scraped_data:
        successful_data = [item for item in scraped_data if item and 'error' not in item]
        
        if successful_data:
            # Solo mostrar resultados en terminal, sin guardar archivos
            print("\n" + "="*60)
            print("📊 DATOS EXTRAÍDOS (JSON)")
            print("="*60)
            # Usamos ensure_ascii=False para mostrar correctamente los caracteres especiales.
            # Los saltos de línea se mostrarán como '\n' en el JSON.
            print(json.dumps(successful_data[0], indent=2, ensure_ascii=False))
            print("="*60)

            # Impresión bonita de la descripción para verificar el formato visualmente:
            print("\n" + "-"*30)
            print("🔎 Verificación del Formato de Descripción:")
            print("-"*30)
            print(successful_data[0].get('descripcion', 'N/A'))
            print("-"*30)

            print(f"\n✅ Extracción exitosa. Total de propiedades procesadas: {len(successful_data)}")

        else:
            print("\n❌ No se pudo extraer ningún dato exitosamente.")
            if scraped_data[0].get('error'):
                print(f"Error reportado: {scraped_data[0]['error']}")

if __name__ == '__main__':
    try:
        # Si estás en Windows y asyncio da problemas (Event loop closed), prueba descomentar lo siguiente:
        # if sys.platform.startswith('win'):
        #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Ejecución estándar de asyncio
        asyncio.run(main())

    except RuntimeError as e:
        # Manejo de errores comunes de asyncio al cerrar el script, especialmente en entornos interactivos.
        if "Event loop is closed" in str(e) or "Cannot run the event loop" in str(e):
             logging.info("Manejando error de loop de asyncio.")
        else:
            raise