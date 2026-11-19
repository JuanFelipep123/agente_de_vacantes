import requests
from typing import List
from datetime import datetime
from collectors.base import BaseCollector
from models.vacante import Vacante

class RemoteOKCollector(BaseCollector):
    BASE_URL = "https://remoteok.com/api"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    def __init__(self):
        super().__init__(nombre="remoteok")

    def recolectar(self, queries: List[str] = None) -> List[Vacante]:
        vacantes: List[Vacante] = []
        try:
            res = requests.get(self.BASE_URL, headers=self.HEADERS, timeout=15)
            if res.status_code != 200:
                return []

            datos = res.json()
            # El primer elemento de RemoteOK es un objeto legal/metadata, las vacantes empiezan en index 1
            items = [item for item in datos if isinstance(item, dict) and "position" in item]

            keywords_interes = ["junior", "intern", "entry", "trainee", "associate", "developer", "backend", "python", "software"]

            for item in items:
                posicion = item.get("position", "")
                tags = [t.lower() for t in item.get("tags", [])]
                texto_posicion = f"{posicion} {' '.join(tags)}".lower()

                # Filtrar solo si tiene relación con roles formativos/junior o desarrollo
                es_relevante = any(k in texto_posicion for k in keywords_interes)
                if not es_relevante:
                    continue

                job_id = str(item.get("id", item.get("slug", posicion)))
                job_url = item.get("url") or f"https://remoteok.com/remote-jobs/{job_id}"
                empresa = item.get("company", "Empresa Tech")
                ubicacion = item.get("location") or "100% Remoto"
                descripcion = item.get("description", "")

                vacante = Vacante(
                    id_origen=f"rok_{job_id}",
                    fuente=self.nombre,
                    titulo=posicion,
                    empresa=empresa,
                    url=job_url,
                    descripcion=descripcion,
                    modalidad="remoto",
                    ubicacion=ubicacion,
                    fecha_publicacion=datetime.now(),
                    tags=tags
                )
                vacantes.append(vacante)

        except Exception as e:
            print(f"[!] Error recolectando en RemoteOK: {e}")

        return vacantes
