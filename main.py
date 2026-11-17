import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Asegurar UTF-8 en stdout/stderr para Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Cargar variables de entorno desde .env
load_dotenv()

from config import *
from storage.db import Database
from collectors.getonbrd import GetOnBrdCollector
from collectors.computrabajo import CompuTrabajoCollector
from filters.matcher import ProfileMatcher
from notifiers.telegram import TelegramNotifier

BASE_DIR = Path(__file__).resolve().parent
PERFIL_PATH = BASE_DIR / "config" / "perfil.yaml"

def main():
    parser = argparse.ArgumentParser(description="Agente Recolector y Calificador de Vacantes")
    parser.add_argument("--radar", action="store_true", help="Muestra y envía el radar de habilidades más demandadas a estudiar")
    parser.add_argument("--test-telegram", action="store_true", help="Envía un mensaje de prueba al bot de Telegram")
    args = parser.parse_args()

    db = Database()
    notifier = TelegramNotifier()

    # Opción: Probar conexión con Telegram
    if args.test_telegram:
        print("[*] Probando envío de mensaje a Telegram...")
        if not notifier.esta_configurado():
            print("[!] Por favor edita el archivo .env con tu TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.")
            sys.exit(1)
        exito = notifier.enviar_mensaje("🤖 <b>¡Conexión exitosa!</b> Tu Agente de Vacantes está listo para notificarte.")
        if exito:
            print("[✓] Mensaje de prueba enviado exitosamente a tu Telegram.")
        else:
            print("[!] No se pudo enviar el mensaje. Verifica tus credenciales en el archivo .env.")
        return

    # Opción: Reporte de radar de estudio
    if args.radar:
        top_skills = db.obtener_top_skills_a_estudiar(limite=5)
        print("\n=== TOP HABILIDADES MÁS DEMANDADAS A ESTUDIAR ===")
        if not top_skills:
            print("Aún no hay suficientes vacantes registradas en el radar. Ejecuta primero una recolección.")
            return
        for i, s in enumerate(top_skills, 1):
            print(f"{i}. {s['skill']} ({s['frecuencia']} veces encontrada)")
        if notifier.esta_configurado():
            notifier.notificar_radar_estudio(top_skills)
            print("[✓] Reporte del radar enviado a Telegram.")
        return

    print("=" * 60)
    print("🚀 INICIANDO BÚSQUEDA Y EVALUACIÓN DE VACANTES")
    print("=" * 60)

    # 1. Cargar perfil y matcher
    matcher = ProfileMatcher(perfil_path=PERFIL_PATH)
    queries = matcher.perfil.get("busqueda", {}).get("roles_interes", ["junior", "practicante"])

    # 2. Recolectores
    recolectores = [
        GetOnBrdCollector(),
        CompuTrabajoCollector()
    ]

    total_nuevas = 0
    total_calificadas = 0
    total_notificadas = 0

    for recolector in recolectores:
        print(f"\n[*] Consultando fuente: {recolector.nombre.upper()}...")
        vacantes = recolector.recolectar(queries=queries[:3]) # Consultar los roles principales
        print(f"    -> Encontradas {len(vacantes)} vacantes en {recolector.nombre}.")

        for vacante in vacantes:
            # Deduplicación: ¿ya la vimos antes?
            if db.existe(vacante.hash_id):
                continue

            total_nuevas += 1

            # Evaluación y scoring
            pasa_umbral, vacante_evaluada = matcher.evaluar(vacante)

            if pasa_umbral:
                total_calificadas += 1
                print(f"\n✨ [MATCH {vacante_evaluada.match_score}/100] {vacante_evaluada.titulo} en {vacante_evaluada.empresa}")
                print(f"   Modalidad: {vacante_evaluada.modalidad} | Ubicación: {vacante_evaluada.ubicacion}")
                print(f"   Por qué: {', '.join(vacante_evaluada.razones_match)}")
                if vacante_evaluada.habilidades_faltantes:
                    print(f"   Para estudiar: {', '.join(vacante_evaluada.habilidades_faltantes)}")
                print(f"   Link: {vacante_evaluada.url}")

                # Notificar a Telegram si está configurado
                notificada = False
                if notifier.esta_configurado():
                    notificada = notifier.notificar_vacante(vacante_evaluada)
                    if notificada:
                        total_notificadas += 1

                # Guardar en base de datos
                db.guardar_vacante(vacante_evaluada, notificada=notificada)
            else:
                # Guardar vacante no relevante para no volver a analizarla
                db.guardar_vacante(vacante_evaluada, notificada=False)

    print("\n" + "=" * 60)
    print("📋 RESUMEN DE LA EJECUCIÓN:")
    print(f"   • Nuevas vacantes analizadas: {total_nuevas}")
    print(f"   • Vacantes con match relevante (≥ {matcher.umbral} pts): {total_calificadas}")
    print(f"   • Notificaciones enviadas a Telegram: {total_notificadas}")
    print("=" * 60)

    # Mostrar preview del radar de estudio
    top_skills = db.obtener_top_skills_a_estudiar(limite=3)
    if top_skills:
        print("\n💡 HABILIDADES QUE MÁS ESTÁN PIDIENDO EN ESTAS OFERTAS (Radar de estudio):")
        for s in top_skills:
            print(f"   - {s['skill'].upper()}: presente en {s['frecuencia']} vacante(s)")

if __name__ == "__main__":
    main()
