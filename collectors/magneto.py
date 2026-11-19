import re
import requests
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime
from collectors.base import BaseCollector
from models.vacante import Vacante

class MagnetoCollector(BaseCollector):
    BASE_URL = "https://www.magneto365.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    def __init__(self):
        super().__init__(nombre="magneto")

    def recolectar(self, queries: List[str]) -> List[Vacante]:
        vacantes: List[Vacante] = []
        vistos_urls = set()

        for query in queries:
            # Formatear slug para Next.js: ej. "practicante sistemas" -> "practicante-sistemas"
            slug = query.strip().lower().replace(" ", "-")
            url = f"{self.BASE_URL}/co/trabajos/search/{slug}"

            try:
                res = requests.get(url, headers=self.HEADERS, timeout=6)
                if res.status_code != 200:
                    continue

                soup = BeautifulSoup(res.text, "html.parser")
                # En Magneto los enlaces a empleos contienen '/co/empleos/'
                enlaces_empleos = [a for a in soup.find_all("a") if "/co/empleos/" in a.get("href", "")]

                for enlace in enlaces_empleos:
                    job_url = enlace.get("href", "")
                    if not job_url or job_url in vistos_urls:
                        continue
                    if not job_url.startswith("http"):
                        job_url = f"{self.BASE_URL}{job_url}"
                    vistos_urls.add(job_url)

                    titulo = enlace.text.strip()
                    if not titulo:
                        continue

                    # Extraer ID desde la URL (ej: /estudiante-tecnico-...-1135751 -> 1135751)
                    match_id = re.search(r'-(\d+)$', job_url)
                    job_id = match_id.group(1) if match_id else job_url

                    # Extraer contenedor padre con los datos adicionales
                    contenedor = enlace.find_parent("div", class_=lambda c: c and ("cursor-pointer" in c or "border" in c)) or enlace.parent.parent
                    partes = [p.strip() for p in contenedor.get_text(" | ").split(" | ") if p.strip()]

                    # Estructura típica: [Título, Empresa, Tipo contrato, Salario, Ubicación, ...]
                    empresa = "Empresa Confidencial"
                    ubicacion = "Colombia"
                    if len(partes) >= 2 and partes[1] != titulo:
                        empresa = partes[1]
                    if len(partes) >= 4:
                        # La ubicación suele ser el cuarto o quinto elemento
                        ubicacion = partes[4] if len(partes) > 4 else partes[3]

                    modalidad = "remoto" if "remoto" in f"{titulo} {ubicacion}".lower() else "presencial"
                    descripcion = " | ".join(partes)

                    vacante = Vacante(
                        id_origen=f"mag_{job_id}",
                        fuente=self.nombre,
                        titulo=titulo,
                        empresa=empresa,
                        url=job_url,
                        descripcion=descripcion,
                        modalidad=modalidad,
                        ubicacion=ubicacion,
                        fecha_publicacion=datetime.now()
                    )
                    vacantes.append(vacante)

            except Exception as e:
                print(f"[!] Error recolectando en Magneto con '{query}': {e}")

        return vacantes
