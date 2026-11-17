import os
import requests
from typing import List, Dict
from models.vacante import Vacante

class TelegramNotifier:
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def esta_configurado(self) -> bool:
        return bool(self.token and self.chat_id and self.token != "tu_bot_token_aqui")

    def enviar_mensaje(self, texto: str) -> bool:
        if not self.esta_configurado():
            print("[i] Telegram no configurado todavía en .env")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        try:
            res = requests.post(self.api_url, json=payload, timeout=10)
            if res.status_code == 200:
                return True
            else:
                print(f"[!] Error enviando a Telegram: {res.status_code} - {res.text}")
                return False
        except Exception as e:
            print(f"[!] Excepción enviando a Telegram: {e}")
            return False

    def notificar_vacante(self, vacante: Vacante) -> bool:
        # Indicador visual de match
        if vacante.match_score >= 80:
            badge = "🔥 <b>MATCH ALTO</b>"
        elif vacante.match_score >= 60:
            badge = "✨ <b>OPORTUNIDAD RELEVANTE</b>"
        else:
            badge = "📌 <b>NUEVA VACANTE</b>"

        razones_str = "\n".join([f"  • {r}" for r in vacante.razones_match]) or "  • Coincidencia con criterios generales"
        
        brechas_str = ""
        if vacante.habilidades_faltantes:
            skills_str = ", ".join(vacante.habilidades_faltantes)
            brechas_str = f"\n💡 <b>Piden para estudiar:</b> <code>{skills_str}</code>"

        mensaje = (
            f"{badge}\n\n"
            f"💼 <b>Puesto:</b> {vacante.titulo}\n"
            f"🏢 <b>Empresa:</b> {vacante.empresa}\n"
            f"📍 <b>Modalidad / Ubicación:</b> {vacante.modalidad.capitalize()} ({vacante.ubicacion})\n"
            f"🎯 <b>Match Score:</b> {vacante.match_score}/100\n\n"
            f"🔍 <b>Por qué encaja:</b>\n{razones_str}"
            f"{brechas_str}\n\n"
            f"👉 <a href='{vacante.url}'>Postularme en {vacante.fuente.capitalize()}</a>"
        )

        return self.enviar_mensaje(mensaje)

    def notificar_radar_estudio(self, top_skills: List[Dict[str, int]]) -> bool:
        if not top_skills:
            return False

        lineas = []
        for i, item in enumerate(top_skills, 1):
            lineas.append(f"{i}. <code>{item['skill']}</code> — pedida en {item['frecuencia']} vacantes")

        resumen = "\n".join(lineas)
        mensaje = (
            f"📊 <b>RADAR DE HABILIDADES DEL MERCADO</b>\n\n"
            f"Estas son las tecnologías más demandadas en las ofertas analizadas que aún puedes reforzar:\n\n"
            f"{resumen}\n\n"
            f"💡 <i>Consejo: Dedica unas horas esta semana a crear un mini proyecto o leer la documentación de la #1 para aumentar tu tasa de selección.</i>"
        )
        return self.enviar_mensaje(mensaje)
