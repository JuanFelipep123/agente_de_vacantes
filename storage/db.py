import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict
from models.vacante import Vacante

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "vacantes.db"

class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._inicializar()

    def _conectar(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def _inicializar(self):
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vacantes (
                    hash_id TEXT PRIMARY KEY,
                    id_origen TEXT,
                    fuente TEXT,
                    titulo TEXT,
                    empresa TEXT,
                    url TEXT,
                    modalidad TEXT,
                    ubicacion TEXT,
                    match_score INTEGER,
                    razones_match TEXT,
                    habilidades_faltantes TEXT,
                    notificada INTEGER DEFAULT 0,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skills_radar (
                    skill TEXT PRIMARY KEY,
                    conteo INTEGER DEFAULT 1,
                    ultima_aparicion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def existe(self, hash_id: str) -> bool:
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM vacantes WHERE hash_id = ?", (hash_id,))
            return cursor.fetchone() is not None

    def guardar_vacante(self, vacante: Vacante, notificada: bool = False):
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO vacantes (
                    hash_id, id_origen, fuente, titulo, empresa, url, 
                    modalidad, ubicacion, match_score, razones_match, 
                    habilidades_faltantes, notificada
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vacante.hash_id,
                vacante.id_origen,
                vacante.fuente,
                vacante.titulo,
                vacante.empresa,
                vacante.url,
                vacante.modalidad,
                vacante.ubicacion,
                vacante.match_score,
                json.dumps(vacante.razones_match, ensure_ascii=False),
                json.dumps(vacante.habilidades_faltantes, ensure_ascii=False),
                1 if notificada else 0
            ))

            # Registrar habilidades faltantes en el radar
            for skill in vacante.habilidades_faltantes:
                cursor.execute("""
                    INSERT INTO skills_radar (skill, conteo, ultima_aparicion)
                    VALUES (?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(skill) DO UPDATE SET 
                        conteo = conteo + 1,
                        ultima_aparicion = CURRENT_TIMESTAMP
                """, (skill.lower().strip(),))

            conn.commit()

    def marcar_notificada(self, hash_id: str):
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE vacantes SET notificada = 1 WHERE hash_id = ?", (hash_id,))
            conn.commit()

    def obtener_top_skills_a_estudiar(self, limite: int = 5) -> List[Dict[str, int]]:
        with self._conectar() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT skill, conteo 
                FROM skills_radar 
                ORDER BY conteo DESC 
                LIMIT ?
            """, (limite,))
            return [{"skill": row[0], "frecuencia": row[1]} for row in cursor.fetchall()]
