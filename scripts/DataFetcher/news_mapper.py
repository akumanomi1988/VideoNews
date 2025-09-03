import xml.etree.ElementTree as ET
from datetime import datetime
from dateutil import parser as date_parser
from typing import List, Optional
import logging

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Constantes de variantes de campos RSS
ITEM_VARIANTS = ['item', 'entry', 'post']
TITLE_VARIANTS = ['title', 'name', 'headline']
LINK_VARIANTS = ['link', 'url', 'href']
DESCRIPTION_VARIANTS = ['description', 'summary', 'content', 'subtitle']
PUB_DATE_VARIANTS = [
    'pubDate', 'pub_date', 'published', 'updated', 'dc:date', 'lastBuildDate', 'date'
]


class FeedItem:
    """
    Representa un ítem estandarizado de un feed RSS.
    """
    def __init__(
        self,
        title: Optional[str] = None,
        link: Optional[str] = None,
        description: Optional[str] = None,
        pub_date: Optional[datetime] = None
    ):
        self.title = title
        self.link = link
        self.description = description
        self.pub_date = pub_date

    def __repr__(self) -> str:
        return (
            f"FeedItem(title={self.title!r}, link={self.link!r}, "
            f"description={self.description!r}, pub_date={self.pub_date!r})"
        )


def _find_first_text(element: ET.Element, variants: List[str]) -> Optional[str]:
    """
    Busca el primer texto disponible en el elemento para las variantes dadas.
    """
    for variant in variants:
        text = element.findtext(variant)
        if text:
            return text
    return None


def _find_link(element: ET.Element) -> Optional[str]:
    """
    Busca el enlace en el elemento, considerando variantes y atributos.
    """
    for variant in LINK_VARIANTS:
        link_text = element.findtext(variant)
        if link_text:
            return link_text
        link_elem = element.find(f'.//{variant}')
        if link_elem is not None and 'href' in link_elem.attrib:
            return link_elem.attrib['href']
    return None


def _parse_pub_date(element: ET.Element) -> Optional[datetime]:
    """
    Busca y parsea la fecha de publicación usando variantes y dateutil.
    """
    for variant in PUB_DATE_VARIANTS:
        date_text = element.findtext(variant)
        if date_text:
            try:
                return date_parser.parse(date_text.strip())
            except (ValueError, TypeError) as e:
                logging.warning(f"Error parsing date '{date_text}': {e}")
                continue
    return None


def _find_item_elements(root: ET.Element) -> List[ET.Element]:
    """
    Busca los elementos que representan ítems en el feed.
    """
    for variant in ITEM_VARIANTS:
        items = root.findall(f'.//{variant}')
        if items:
            return items
    return []


def parse_rss_to_standard_object(rss_content: str) -> List[FeedItem]:
    """
    Parsea el contenido RSS/XML y devuelve una lista de objetos FeedItem estandarizados.

    Args:
        rss_content (str): Contenido XML del feed RSS.

    Returns:
        List[FeedItem]: Lista de ítems estandarizados.
    """
    try:
        root = ET.fromstring(rss_content)
    except ET.ParseError as e:
        logging.error(f"Error parsing XML: {e}")
        return []

    item_elements = _find_item_elements(root)
    if not item_elements:
        logging.info("No items found in the feed.")
        return []

    items: List[FeedItem] = []
    for item in item_elements:
        title = _find_first_text(item, TITLE_VARIANTS)
        link = _find_link(item)
        description = _find_first_text(item, DESCRIPTION_VARIANTS)
        pub_date = _parse_pub_date(item)

        feed_item = FeedItem(
            title=title,
            link=link,
            description=description,
            pub_date=pub_date
        )
        items.append(feed_item)

    return items