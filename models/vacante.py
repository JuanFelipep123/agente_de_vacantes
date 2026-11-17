from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
import hashlib

class Vacante(BaseModel):
    id_origen: str = Field(description="ID original en la plataforma")
    fuente: str = Field(description="Nombre de la plataforma fuente, ej. getonbrd")
    titulo: str
    empresa: str
    url: str
    descripcion: str
    modalidad: str = "remoto"  # remoto, hibrido, presencial
    ubicacion: str = "No especificada"
    fecha_publicacion: Optional[datetime] = None
    tags: List[Any] = Field(default_factory=list)

    # Campos calculados por el motor de scoring
    match_score: int = 0
    razones_match: List[str] = Field(default_factory=list)
    habilidades_faltantes: List[str] = Field(default_factory=list)

    @property
    def hash_id(self) -> str:
        """Genera un hash único basado en empresa y título normalizados para evitar duplicados."""
        clave = f"{self.empresa.strip().lower()}_{self.titulo.strip().lower()}"
        return hashlib.sha256(clave.encode("utf-8")).hexdigest()[:16]
