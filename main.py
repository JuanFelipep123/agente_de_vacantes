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

from storage.db import Database
from collectors.getonbrd import GetOnBrdCollector
from collectors.computrabajo import CompuTrabajoCollector
from collectors.magneto import MagnetoCollector
from collectors.remoteok import RemoteOKCollector
from filters.matcher import ProfileMatcher
from notifiers.telegram import TelegramNotifier
from analyzers.market_insights import MarketInsightsAnalyzer

BASE_DIR = Path(__file__).resolve().parent
PERFIL_PATH = BASE_DIR / "config" / "perfil.yaml"
DB_PATH = BASE_DIR / "data" / "vacantes.db"

def main():
    parser = argparse.ArgumentParser(description="Agente Recolector y Calificador de Vacantes")
    parser.add_argument("--radar", action="store_true", help="Muestra y envía el radar de habilidades más demandadas a estudiar")
    parser.add_argument("--que-estudiar", action="store_true", help="Analiza a profundidad las vacantes de sistemas y envía los temas específicos a estudiar")
    parser.add_argument("--test-telegram", action="store_true", help="Envía un mensaje de prueba al bot de Telegram")
    parser.add_argument("--notify-summary", action="store_true", help="Envía mensaje de resumen a Telegram incluso si no hay vacantes relevantes")
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

    # Opción: Reporte de radar de estudio rápido
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

    # Opción: Diagnóstico profundo de temas específicos para Ingeniería de Sistemas
    if args.que_estudiar:
        print("\n[*] Analizando vacantes de Sistemas y Software en la base de datos...")
        analyzer = MarketInsightsAnalyzer(db_path=DB_PATH, perfil_path=PERFIL_PATH)
        diagnostico = analyzer.generar_diagnostico()
        total = diagnostico.get("total_analizadas", 0)

        if total == 0:
            print("[!] Aún no hay suficientes vacantes en la base de datos. Ejecuta primero 'python main.py'.")
            return

        print(f"\n" + "=" * 65)
        print(f"🎓 DIAGNÓSTICO DEL MERCADO: INGENIERÍA DE SISTEMAS ({total} ofertas)")
        print("=" * 65)
        print("\n📌 ÁREAS MÁS DEMANDADAS EN COMÚN:")
        for item in diagnostico["ranking_categorias"]:
            print(f"   • {item['categoria']}: {item['porcentaje']}% de las ofertas")

        print("\n🎯 TEMAS ESPECÍFICOS QUE DEBERÍAS ESTUDIAR:")
        for idx, item in enumerate(diagnostico["temas_prioritarios"], 1):
            print(f"\n{idx}. {item['area'].upper()} (Demanda: {item['porcentaje_demanda']}%)")
            for tema in item["temas"]:
                print(f"   👉 {tema}")

        if notifier.esta_configurado():
            reporte_msg = analyzer.generar_reporte_telegram(diagnostico)
            exito = notifier.enviar_mensaje(reporte_msg)
            if exito:
                print("\n[✓] Diagnóstico y plan de estudio enviado exitosamente a tu Telegram.")
            else:
                print("\n[!] No se pudo enviar el reporte a Telegram.")
        return

    print("=" * 60)
    print("🚀 INICIANDO BÚSQUEDA Y EVALUACIÓN MULTI-FUENTE DE VACANTES")
    print("=" * 60)

    # 1. Cargar perfil y matcher
    matcher = ProfileMatcher(perfil_path=PERFIL_PATH)

    # Queries especializadas por tipo de plataforma
    queries_colombia = ["practicante sistemas", "practicante software", "practicante desarrollo", "desarrollador junior"]
    queries_tech_latam = ["junior", "trainee", "intern", "developer junior"]

    # 2. Configurar recolectores y sus fuentes
    fuentes_trabajo = [
        (GetOnBrdCollector(), ["junior", "intern", "trainee"]),
        (CompuTrabajoCollector(), ["practicante sistemas", "practicante software", "desarrollador junior"]),
        (RemoteOKCollector(), [])
    ]

    total_nuevas = 0
    total_calificadas = 0
    total_notificadas = 0

    for recolector, queries in fuentes_trabajo:
        print(f"\n[*] Consultando fuente: {recolector.nombre.upper()}...")
        try:
            vacantes = recolector.recolectar(queries=queries) if queries else recolector.recolectar()
            print(f"    -> Encontradas {len(vacantes)} vacantes en {recolector.nombre}.")
        except Exception as e:
            print(f"    [!] Error en fuente {recolector.nombre}: {e}")
            continue

        for vacante in vacantes:
            # Deduplicación: ¿ya la vimos antes?
            if db.existe(vacante.hash_id):
                continue

            total_nuevas += 1

            # Evaluación y scoring
            pasa_umbral, vacante_evaluada = matcher.evaluar(vacante)

            if pasa_umbral:
                total_calificadas += 1
                print(f"\n✨ [MATCH {vacante_evaluada.match_score}/100] {vacante_evaluada.titulo} en {vacante_evaluada.empresa} ({vacante.fuente})")
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

    # Si se ejecutó manualmente desde GitHub Actions o con flag, avisar por Telegram si no hubo novedades
    es_disparo_manual = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
    if (es_disparo_manual or getattr(args, "notify_summary", False)) and total_notificadas == 0 and notifier.esta_configurado():
        resumen_txt = (
            f"🤖 <b>Agente ejecutado con éxito</b>\n\n"
            f"🔍 <b>Vacantes nuevas analizadas hoy:</b> {total_nuevas}\n"
            f"📍 <b>Fuentes monitoreadas:</b> CompuTrabajo, Magneto (Bancolombia, etc.), Get on Board y RemoteOK.\n"
            f"📍 <b>Filtro activo:</b> Presencial solo en Manizales/Pereira, o 100% Remoto.\n\n"
            f"ℹ️ Ninguna de las ofertas nuevas cumplió con los filtros estrictos de tu zona o perfil formativo.\n\n"
            f"🛡️ <i>El agente sigue vigilando en segundo plano cada 3 horas.</i>"
        )
        notifier.enviar_mensaje(resumen_txt)

    # Mostrar preview del radar de estudio
    top_skills = db.obtener_top_skills_a_estudiar(limite=3)
    if top_skills:
        print("\n💡 HABILIDADES QUE MÁS ESTÁN PIDIENDO EN ESTAS OFERTAS (Radar de estudio):")
        for s in top_skills:
            print(f"   - {s['skill'].upper()}: presente en {s['frecuencia']} vacante(s)")

if __name__ == "__main__":
    main()
