import re
import yaml
from pathlib import Path
from typing import Dict, Any, Tuple, List
from models.vacante import Vacante

class ProfileMatcher:
    # Catálogo amplio de tecnologías del mercado para detectar demanda y qué estudiar
    CATALOGO_TECH = [
        "python", "javascript", "typescript", "java", "c#", ".net", "php",
        "sql", "postgresql", "mysql", "mongodb", "oracle", "redis",
        "docker", "kubernetes", "aws", "azure", "gcp", "linux",
        "react", "angular", "vue", "node", "django", "fastapi", "flask", "spring boot",
        "git", "ci/cd", "rest", "graphql", "devops", "testing", "pytest",
        "power bi", "tableau", "excel", "seguridad", "redes"
    ]

    def __init__(self, perfil_path: Path):
        with open(perfil_path, "r", encoding="utf-8") as f:
            self.perfil: Dict[str, Any] = yaml.safe_load(f)

        self.roles_interes = [r.lower() for r in self.perfil.get("busqueda", {}).get("roles_interes", [])]
        self.palabras_excluir = [p.lower() for p in self.perfil.get("busqueda", {}).get("palabras_excluir", [])]
        self.stack_actual = [s.lower() for s in self.perfil.get("stack_actual", [])]
        self.stack_interes = [s.lower() for s in self.perfil.get("stack_interes", [])]
        self.modalidades = [m.lower() for m in self.perfil.get("busqueda", {}).get("modalidades_permitidas", [])]
        self.umbral = self.perfil.get("scoring", {}).get("umbral_notificacion", 50)

        # Palabras clave de nivel inicial
        self.keywords_entry = ["practicante", "pasante", "práctica", "practicas", "trainee", "intern", "junior", "jr", "aprendiz"]
        # Palabras de área tecnológica
        self.keywords_tech = ["sistemas", "software", "desarrollo", "programador", "programación", "developer", "backend", "frontend", "fullstack", "tecnología", "ti", "computación", "datos", "data", "qa", "informática"]

    def _contiene(self, texto: str, palabra: str) -> bool:
        patron = r'\b' + re.escape(palabra) + r'\b'
        return bool(re.search(patron, texto, re.IGNORECASE))

    def evaluar(self, vacante: Vacante) -> Tuple[bool, Vacante]:
        titulo_lower = vacante.titulo.lower()
        desc_lower = vacante.descripcion.lower()
        texto_completo = f"{titulo_lower}\n{desc_lower}"

        # 1. Filtro duro de exclusión
        for palabra in self.palabras_excluir:
            if self._contiene(titulo_lower, palabra):
                return False, vacante

        # 2. Filtro de modalidad
        if vacante.modalidad.lower() not in self.modalidades:
            return False, vacante

        score = 0
        razones: List[str] = []
        faltantes: List[str] = []

        # A. Detección de nivel (Entry / Practicante / Junior)
        es_entry = any(self._contiene(titulo_lower, k) for k in self.keywords_entry)
        if es_entry:
            score += 35
            razones.append("Rol orientado a practicante/junior/entry")
        elif any(self._contiene(desc_lower, k) for k in self.keywords_entry):
            score += 15
            razones.append("La descripción menciona perfil formativo/junior")

        # B. Detección de área tecnológica
        es_tech_area = any(self._contiene(titulo_lower, k) for k in self.keywords_tech)
        if es_tech_area:
            score += 25
            razones.append("Título afín a Tecnología / Software / Sistemas")

        # C. Match con tecnologías del stack actual
        skills_encontradas = [tech for tech in self.stack_actual if self._contiene(texto_completo, tech)]
        if skills_encontradas:
            pts_tech = min(30, len(skills_encontradas) * 10)
            score += pts_tech
            razones.append(f"Coincide con tu stack: {', '.join(skills_encontradas)}")

        # D. Detección de tecnologías que piden que NO dominas aún (para el radar y estudio)
        for tech in self.CATALOGO_TECH:
            if tech not in self.stack_actual and self._contiene(texto_completo, tech):
                faltantes.append(tech)

        # E. Puntos por modalidad remota
        if vacante.modalidad.lower() == "remoto":
            score += 10
            razones.append("Modalidad Remota")

        # Asignar resultados
        vacante.match_score = min(100, score)
        vacante.razones_match = razones
        vacante.habilidades_faltantes = faltantes

        pasa_umbral = vacante.match_score >= self.umbral
        return pasa_umbral, vacante
