import xml.etree.ElementTree as ET
from datetime import datetime

class FeedItem:
    def __init__(self, title=None, link=None, description=None, pub_date=None):
        self.title = title
        self.link = link
        self.description = description
        self.pub_date = pub_date

def parse_rss_to_standard_object(rss_content):
    try:
        root = ET.fromstring(rss_content)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return []

    # Variaciones posibles para cada campo
    ITEM_VARIANTS = ['item', 'entry', 'post']
    TITLE_VARIANTS = ['title', 'name', 'headline']
    LINK_VARIANTS = ['link', 'url', 'href']
    DESCRIPTION_VARIANTS = ['description', 'summary', 'content', 'subtitle']
    PUB_DATE_VARIANTS = ['pubDate', 'pub_date', 'published', 'updated', 'dc:date', 'lastBuildDate', 'date']

    items = []

    # Buscar elementos que representen "items" usando las variantes
    for item_variant in ITEM_VARIANTS:
        item_elements = root.findall(f'.//{item_variant}')
        if item_elements:
            break  # Si encontramos una variante que funciona, no seguimos buscando

    if not item_elements:
        print("No items found in the feed.")
        return []

    for item in item_elements:
        # Buscar título
        title = None
        for title_variant in TITLE_VARIANTS:
            title = item.findtext(title_variant)
            if title:
                break

        # Buscar enlace
        link = None
        for link_variant in LINK_VARIANTS:
            link_text = item.findtext(link_variant)
            if link_text:
                link = link_text
                break
            # Caso especial para <link> como atributo href
            link_elem = item.find(f'.//{link_variant}')
            if link_elem is not None and 'href' in link_elem.attrib:
                link = link_elem.attrib['href']
                break

        # Buscar descripción
        description = None
        for desc_variant in DESCRIPTION_VARIANTS:
            description = item.findtext(desc_variant)
            if description:
                break

        # Buscar fecha de publicación
        pub_date = None
        for date_variant in PUB_DATE_VARIANTS:
            date_text = item.findtext(date_variant)
            if date_text:
                # Intentar parsear diferentes formatos de fecha
                for date_format in [
                    '%a, %d %b %Y %H:%M:%S %Z',       # Ej: Thu, 27 Mar 2025 04:43:28 GMT
                    '%a, %d %b %Y %H:%M:%S %z',       # Ej: Wed, 26 Mar 2025 16:36:13 +0000 (nuevo)
                    '%Y-%m-%d %H:%M:%S %Z',           # Ej: 2025-03-27 04:43:28 GMT
                    '%Y-%m-%dT%H:%M:%SZ',             # Ej: 2025-03-27T04:43:28Z (ISO)
                    '%a, %d %b %Y %H:%M %Z',          # Ej: Thu, 27 Mar 2025 04:43 GMT
                    '%a, %d %b %Y %H:%M:%S',          # Ej: Thu, 08 Dec 2016 12:05:00 (sin zona horaria)
                    '%Y-%m-%d %H:%M:%S',              # Ej: 2025-03-27 04:43:28 (sin zona horaria)
                    '%a, %d %b %Y %H:%M:%S %z %Z',    # Ej: Wed, 26 Mar 2025 16:36:13 +0000 UTC (raro, pero posible)
                ]:
                    try:
                        pub_date = datetime.strptime(date_text.strip(), date_format)
                        break
                    except ValueError as e:
                        print(f"Error parsing date '{date_text}': {e}")
                        continue
                if pub_date:
                    break

        # Crear objeto estandarizado
        feed_item = FeedItem(
            title=title,
            link=link,
            description=description,
            pub_date=pub_date
        )
        items.append(feed_item)

    return items

# # Ejemplo de uso con tu RSS
# rss_content = """<rss ... tu contenido XML aquí ... </rss>"""  # Coloca tu XML completo aquí

# # Parsear y obtener los objetos
# parsed_items = parse_rss_to_standard_object(rss_content)

# # Mostrar resultados
# for item in parsed_items:
#     print(f"Título: {item.title}")
#     print(f"Link: {item.link}")
#     print(f"Descripción: {item.description}")
#     print(f"Fecha: {item.pub_date}")
#     print("---")