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

    def recolectar(self, queries: List[str]) -> List[Vacante]:
        vacantes: List[Vacante] = []
        vistas_ids = set()

        for query in queries:
            url = f"{self.BASE_URL}/search/jobs"
            params = {"query": query, "per_page": 20}

            try:
                res = requests.get(url, headers=self.HEADERS, params=params, timeout=8)
                if res.status_code != 200:
                    continue

                datos = res.json().get("data", [])
                for item in datos:
                    job_id = str(item.get("id"))
                    if job_id in vistas_ids:
                        continue
                    vistas_ids.add(job_id)

                    attr = item.get("attributes", {})
                    
                    # URL pública de postulación
                    job_url = item.get("links", {}).get("public_url") or f"https://www.getonbrd.com/jobs/{job_id}"

                    # Obtener nombre de empresa desde el slug de la URL de forma instantánea
                    # ej: /jobs/desarrollador-junior-empresa-bogota -> empresa
                    empresa = "Empresa Tech"
                    partes_slug = job_url.split("/jobs/")[-1].split("-")
                    if len(partes_slug) >= 2:
                        empresa = partes_slug[-2].replace("_", " ").capitalize()

                    # Modalidad y ubicación
                    es_remoto = attr.get("remote", False)
                    modality_text = "remoto" if es_remoto else "presencial"
                    ubicacion = "Remoto" if es_remoto else ", ".join(attr.get("location_cities", [])) or "LatAm"

                    # Fecha
                    pub_str = attr.get("published_at")
                    fecha_pub = datetime.now()
                    if pub_str:
                        try:
                            fecha_pub = datetime.fromtimestamp(pub_str)
                        except Exception:
                            pass

                    # Descripción consolidada
                    desc_completa = f"{attr.get('description_headline', '')}\n{attr.get('description', '')}\n{attr.get('functions', '')}\n{attr.get('desirable', '')}"

                    vacante = Vacante(
                        id_origen=f"gob_{job_id}",
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
