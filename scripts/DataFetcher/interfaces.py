from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class NewsProvider(ABC):
    """Interface base para proveedores de noticias"""
    
    @abstractmethod
    def get_latest_news(self, 
                       category: Optional[str] = None,
                       language: Optional[str] = None,
                       limit: int = 20) -> List[Dict[str, Any]]:
        """Obtiene las últimas noticias del proveedor"""
        pass

    @abstractmethod
    def search_news(self,
                   query: str,
                   language: Optional[str] = None,
                   category: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 20) -> List[Dict[str, Any]]:
        """Busca noticias específicas en el proveedor"""
        pass