from abc import ABC, abstractmethod
from typing import List
from models.vacante import Vacante

class BaseCollector(ABC):
    def __init__(self, nombre: str):
        self.nombre = nombre

    @abstractmethod
    def recolectar(self, queries: List[str]) -> List[Vacante]:
        """Recolecta vacantes para las palabras clave dadas."""
        pass
