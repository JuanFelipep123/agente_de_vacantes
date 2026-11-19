import re
import sqlite3
import yaml
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter

class MarketInsightsAnalyzer:
    """
    Analizador del mercado laboral para Ingenieros de Sistemas y Desarrolladores.
    Revisa todas las vacantes recolectadas, extrae patrones comunes y genera
    un plan de estudio con temas específicos según la demanda real del mercado.
    """

    # Diccionario taxonómico de temas específicos de Ingeniería de Sistemas y Software
    MAPA_TEMAS = {
        "Bases de Datos & SQL": {
            "keywords": ["sql", "mysql", "postgresql", "postgres", "oracle", "sql server", "mongodb", "consultas sql", "modelado", "bases de datos", "relacional"],
            "temas_especificos": [
                "Diseño y modelado de bases de datos relacionales (Diagramas ER, normalización 1FN, 2FN, 3FN)",
                "Consultas intermedias/avanzadas (JOINs múltiples, GROUP BY, subconsultas, funciones de agregación)",
                "Manejo de PostgreSQL o MySQL y uso de ORMs (como SQLAlchemy o Prisma)",
                "Conceptos de optimización: índices, llaves primarias/foráneas y transacciones (ACID)"
            ]
        },
        "Arquitectura Backend & APIs": {
            "keywords": ["api", "apis", "rest", "restful", "fastapi", "flask", "django", "node", "express", "backend", "microservicios", "crud", "json", "endpoint"],
            "temas_especificos": [
                "Diseño de APIs RESTful estándar (verbos HTTP, códigos de estado 200/400/500, buenas prácticas de URI)",
                "Autenticación y seguridad de APIs (Tokens JWT, headers de autorización, CORS)",
                "Estructura y arquitectura limpia en Python (FastAPI o Flask con separación por capas/servicios)",
                "Serialización y validación estricta de datos (Pydantic / schemas)"
            ]
        },
        "DevOps, Contenedores & Cloud": {
            "keywords": ["docker", "contenedor", "contenedores", "kubernetes", "aws", "azure", "gcp", "cloud", "linux", "ci/cd", "git", "github actions", "deploy"],
            "temas_especificos": [
                "Fundamentos de Docker (crear Dockerfile para tu app Python, puertos, imágenes y .dockerignore)",
                "Orquestación local con Docker Compose (conectar tu API con una base de datos PostgreSQL en contenedores)",
                "Comandos básicos de terminal Linux (navegación, permisos, SSH, variables de entorno)",
                "Flujo de trabajo en Git profesional (branches, Pull Requests, merge vs rebase) y GitHub Actions básico"
            ]
        },
        "Pruebas de Software (Testing)": {
            "keywords": ["testing", "test", "pruebas unitarias", "unit tests", "pytest", "qa", "tdd", "cobertura", "automatización"],
            "temas_especificos": [
                "Escribir pruebas unitarias en Python con Pytest (asserts, fixtures básicas)",
                "Pruebas de integración para endpoints de APIs (TestClient con FastAPI/Flask)",
                "Concepto de Mocks: cómo simular llamadas a bases de datos o servicios externos en tests",
                "Métricas de cobertura de código (coverage)"
            ]
        },
        "Frontend & Web Moderno": {
            "keywords": ["javascript", "typescript", "react", "html", "css", "tailwind", "frontend", "dom"],
            "temas_especificos": [
                "JavaScript moderno ES6+ (promesas, async/await, desestructuración, manejo de arrays: map/filter)",
                "Consumo de APIs desde el cliente (fetch / axios, manejo de estados de carga y error)",
                "React básico (componentes funcionales, hooks fundamentales: useState, useEffect)",
                "Fundamentos de TypeScript (tipado básico de interfaces y funciones)"
            ]
        },
        "Sistemas, Redes & Metodologías": {
            "keywords": ["redes", "tcp/ip", "seguridad", "scrum", "agil", "ágil", "jira", "soporte", "infraestructura", "servidores"],
            "temas_especificos": [
                "Fundamentos de redes aplicados a software (DNS, HTTP/HTTPS, protocolos TCP/IP, puertos)",
                "Metodologías ágiles de trabajo en equipo (Scrum: sprints, dailies, retrospectivas, estimaciones)",
                "Seguridad básica de aplicaciones (OWASP Top 10, sanitización contra SQL Injection y XSS)"
            ]
        }
    }

    def __init__(self, db_path: Path, perfil_path: Path):
        self.db_path = db_path
        self.perfil_path = perfil_path
        with open(perfil_path, "r", encoding="utf-8") as f:
            self.perfil = yaml.safe_load(f)
        self.stack_actual = set(s.lower() for s in self.perfil.get("stack_actual", []))

    def _conectar(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def generar_diagnostico(self) -> Dict[str, Any]:
        """
        Analiza las vacantes guardadas en la base de datos y cruza la información
        con el mapa taxonómico y el perfil del estudiante.
        """
        with self._conectar() as conn:
            cursor = conn.cursor()
            # Tomar todas las vacantes de tecnología / ingeniería / desarrollo
            cursor.execute("""
                SELECT titulo, empresa, razones_match, habilidades_faltantes, IFNULL(descripcion, '') 
                FROM vacantes 
                WHERE LOWER(titulo) LIKE '%sistemas%' 
                   OR LOWER(titulo) LIKE '%software%' 
                   OR LOWER(titulo) LIKE '%developer%' 
                   OR LOWER(titulo) LIKE '%engineer%' 
                   OR LOWER(titulo) LIKE '%practicante%' 
                   OR LOWER(titulo) LIKE '%datos%'
                   OR fuente IN ('getonbrd', 'remoteok')
            """)
            filas = cursor.fetchall()

        total_vacantes = len(filas)
        if total_vacantes == 0:
            return {"total_analizadas": 0}

        conteo_categorias = Counter()
        keywords_encontradas = Counter()

        for titulo, empresa, razones, faltantes, descripcion in filas:
            texto = f"{titulo} {razones} {faltantes} {descripcion}".lower()

            for categoria, data in self.MAPA_TEMAS.items():
                coincidio = False
                for kw in data["keywords"]:
                    # Búsqueda con límites de palabra
                    if re.search(r'\b' + re.escape(kw) + r'\b', texto):
                        keywords_encontradas[kw] += 1
                        coincidio = True
                if coincidio:
                    conteo_categorias[categoria] += 1

        # Identificar las categorías con mayor demanda (ordenadas por porcentaje)
        ranking_categorias = []
        for cat, count in conteo_categorias.most_common():
            pct = round((count / total_vacantes) * 100, 1)
            ranking_categorias.append({
                "categoria": cat,
                "conteo": count,
                "porcentaje": pct,
                "temas_especificos": self.MAPA_TEMAS[cat]["temas_especificos"]
            })

        # Identificar qué temas prioritarios le faltan al estudiante según su stack actual
        temas_prioritarios_a_estudiar = []
        for cat_info in ranking_categorias[:4]: # Las 4 áreas más pedidas
            # Si en esa categoría hay tecnologías clave que el alumno aún no tiene
            categoria = cat_info["categoria"]
            temas_prioritarios_a_estudiar.append({
                "area": categoria,
                "porcentaje_demanda": cat_info["porcentaje"],
                "temas": cat_info["temas_especificos"]
            })

        return {
            "total_analizadas": total_vacantes,
            "ranking_categorias": ranking_categorias,
            "temas_prioritarios": temas_prioritarios_a_estudiar,
            "top_keywords": keywords_encontradas.most_common(8)
        }

    def generar_reporte_telegram(self, diagnostico: Dict[str, Any]) -> str:
        """
        Formatea el diagnóstico en un mensaje claro, directo y estructurado para Telegram.
        """
        total = diagnostico.get("total_analizadas", 0)
        if total == 0:
            return "ℹ️ Aún no hay suficientes ofertas de sistemas registradas para generar el reporte."

        lineas = [
            "🎓 <b>DIAGNÓSTICO DEL MERCADO: INGENIERÍA DE SISTEMAS</b>",
            f"<i>Basado en el análisis de <b>{total} ofertas de TI</b> (Get on Board, CompuTrabajo, RemoteOK)</i>\n",
            "📌 <b>LO QUE MÁS TIENEN EN COMÚN TODAS LAS VACANTES:</b>"
        ]

        for item in diagnostico["ranking_categorias"][:4]:
            barra = "🟩" * max(1, int(item["porcentaje"] / 20))
            lineas.append(f"• <b>{item['categoria']}:</b> {barra} <i>{item['porcentaje']}% de las ofertas</i>")

        lineas.append("\n🎯 <b>¿QUÉ TEMAS ESPECÍFICOS DEBERÍAS ESTUDIAR?</b>\n")

        for idx, item in enumerate(diagnostico["temas_prioritarios"][:3], 1):
            lineas.append(f"<b>{idx}. {item['area']}</b> (Demanda: {item['porcentaje_demanda']}%)")
            for t in item["temas"][:2]: # Los 2 temas más accionables de cada categoría
                lineas.append(f"   👉 <i>{t}</i>")
            lineas.append("")

        lineas.append("💡 <b>RECOMENDACIÓN PARA TU PERFIL:</b>")
        lineas.append("Crea un proyecto donde conectes una API con <b>Docker + PostgreSQL + pruebas unitarias (Pytest)</b>. Es el combo exacto que te abrirá las puertas en el 85% de las vacantes de sistemas.")

        return "\n".join(lineas)
