import requests
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime
from collectors.base import BaseCollector
from models.vacante import Vacante

class CompuTrabajoCollector(BaseCollector):
    BASE_URL = "https://co.computrabajo.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9"
    }

    def __init__(self):
        super().__init__(nombre="computrabajo")

    def recolectar(self, queries: List[str]) -> List[Vacante]:
        vacantes: List[Vacante] = []
        vistos_ids = set()

        for query in queries:
            slug = query.strip().lower().replace(" ", "-")
            url = f"{self.BASE_URL}/trabajo-de-{slug}"

            try:
                res = requests.get(url, headers=self.HEADERS, timeout=6)
                if res.status_code != 200:
                    continue

                soup = BeautifulSoup(res.text, "html.parser")
                articulos = soup.select("article.box_offer")

                for art in articulos:
                    data_id = art.get("data-id")
                    if not data_id or data_id in vistos_ids:
                        continue
                    vistos_ids.add(data_id)

                    enlace_elem = art.select_one("h2 a.js-o-link")
                    if not enlace_elem:
                        continue

                    titulo = enlace_elem.text.strip()
                    href = enlace_elem.get("href", "")
                    job_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

                    # Empresa
                    empresa_elem = art.select_one("p.dFlex a")
                    empresa = empresa_elem.text.strip() if empresa_elem else "Empresa Confidencial"

                    # Ubicación precisa
                    ubicacion = "Colombia"
                    for p in art.select("p.fs16"):
                        if not p.select_one("span.fwB") and not p.select_one("a[offer-grid-article-company-url]"):
                            texto_p = p.text.strip()
                            if texto_p and texto_p != empresa:
                                ubicacion = texto_p
                                break

                    # Descripción / snippet
                    parrafos = [p.text.strip() for p in art.select("p") if p.text.strip()]
                    descripcion = "\n".join(parrafos)

                    # Detección de modalidad
                    texto_completo = f"{titulo} {descripcion}".lower()
                    if any(w in texto_completo for w in ["remoto", "teletrabajo", "home office", "desde casa", "100% remoto"]):
                        modalidad = "remoto"
                    elif any(w in texto_completo for w in ["híbrido", "hibrido", "alternancia", "semi-presencial"]):
                        modalidad = "hibrido"
                    else:
                        modalidad = "presencial"

                    vacante = Vacante(
                        id_origen=data_id,
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
                print(f"[!] Error recolectando en CompuTrabajo con '{query}': {e}")

        return vacantes
