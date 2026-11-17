import requests
from typing import List, Dict, Optional
from datetime import datetime
from collectors.base import BaseCollector
from models.vacante import Vacante

class GetOnBrdCollector(BaseCollector):
    BASE_URL = "https://www.getonbrd.com/api/v0"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    def __init__(self):
        super().__init__(nombre="getonbrd")
        self._cache_empresas: Dict[int, str] = {}

    def _obtener_nombre_empresa(self, company_id: Optional[int]) -> str:
        if not company_id:
            return "Empresa Confidencial"
        if company_id in self._cache_empresas:
            return self._cache_empresas[company_id]
        
        try:
            url = f"{self.BASE_URL}/companies/{company_id}"
            res = requests.get(url, headers=self.HEADERS, timeout=5)
            if res.status_code == 200:
                nombre = res.json().get("data", {}).get("attributes", {}).get("name", "Empresa")
                self._cache_empresas[company_id] = nombre
                return nombre
        except Exception:
            pass
        return "Empresa"

    def recolectar(self, queries: List[str]) -> List[Vacante]:
        vacantes: List[Vacante] = []
        vistas_ids = set()

        for query in queries:
            url = f"{self.BASE_URL}/search/jobs"
            params = {"query": query, "per_page": 25}

            try:
                res = requests.get(url, headers=self.HEADERS, params=params, timeout=10)
                if res.status_code != 200:
                    continue

                datos = res.json().get("data", [])
                for item in datos:
                    job_id = str(item.get("id"))
                    if job_id in vistas_ids:
                        continue
                    vistas_ids.add(job_id)

                    attr = item.get("attributes", {})
                    company_data = attr.get("company", {}).get("data", {})
                    company_id = company_data.get("id")
                    empresa = self._obtener_nombre_empresa(company_id)

                    # Modalidad y ubicación
                    es_remoto = attr.get("remote", False)
                    modality_text = "remoto" if es_remoto else "presencial"
                    ubicacion = "Remoto" if es_remoto else ", ".join(attr.get("location_cities", [])) or "LatAm"

                    # Fecha
                    pub_str = attr.get("published_at")
                    fecha_pub = None
                    if pub_str:
                        try:
                            fecha_pub = datetime.fromtimestamp(pub_str)
                        except Exception:
                            pass

                    # Descripción consolidada para análisis
                    desc_completa = f"{attr.get('description_headline', '')}\n{attr.get('description', '')}\n{attr.get('functions', '')}\n{attr.get('desirable', '')}"

                    # URL pública de postulación
                    job_url = item.get("links", {}).get("public_url") or f"https://www.getonbrd.com/jobs/{item.get('id')}"

                    vacante = Vacante(
                        id_origen=job_id,
                        fuente=self.nombre,
                        titulo=attr.get("title", "Sin título"),
                        empresa=empresa,
                        url=job_url,
                        descripcion=desc_completa,
                        modalidad=modality_text,
                        ubicacion=ubicacion,
                        fecha_publicacion=fecha_pub,
                        tags=attr.get("tags", {}).get("data", [])
                    )
                    vacantes.append(vacante)
            except Exception as e:
                print(f"[!] Error recolectando en Get on Board con query '{query}': {e}")

        return vacantes
