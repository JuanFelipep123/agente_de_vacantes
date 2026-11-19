# 🎯 Agente Inteligente de Vacantes y Radar de Habilidades

Agente autónomo en Python para recolectar, calificar, alertar vacantes tech relevantes (prácticas, pasantías y roles junior) y analizar brechas de habilidades para saber qué estudiar.

---

## 📁 Estructura del Proyecto

```
agente_postulador/
├── config/
│   └── perfil.yaml          # Tu perfil, stack, roles buscados y exclusiones
├── collectors/
│   ├── base.py              # Interfaz base para recolectores
│   └── getonbrd.py          # Recolector API pública Get on Board
├── filters/
│   └── matcher.py           # Motor de scoring, filtrado duro y detección de brechas
├── notifiers/
│   └── telegram.py          # Envío de alertas y reportes de radar a Telegram
├── storage/
│   └── db.py                # Persistencia SQLite (deduplicación y estadísticas)
├── models/
│   └── vacante.py           # Modelo Pydantic unificado de vacante
├── .env.example             # Plantilla de variables de entorno
├── requirements.txt         # Dependencias
└── main.py                  # Orquestador del flujo
```

---

## ⚡ Guía Rápida para Configurar Telegram (2 Minutos)

1. **Crear tu Bot de Telegram:**
   - Abre Telegram y busca `@BotFather`.
   - Envía `/newbot`, ponle nombre (ej: `Mi Agente de Empleos`) y un username (ej: `mi_agente_empleos_bot`).
   - Copia el **HTTP API Token** que te entrega.

2. **Obtener tu Chat ID:**
   - Busca en Telegram a `@userinfobot` y envíale cualquier mensaje (o `/start`).
   - Copia el número que dice `Id:` (ej: `123456789`).

3. **Configurar tu `.env`:**
   Abre el archivo `.env` en la raíz y coloca tus datos:
   ```env
   TELEGRAM_BOT_TOKEN=tu_token_aqui
   TELEGRAM_CHAT_ID=tu_id_aqui
   ```

4. **Probar la conexión:**
   ```bash
   python main.py --test-telegram
   ```

---

## 🚀 Comandos Disponibles

- **Buscar y alertar vacantes:**
  ```bash
  python main.py
  ```
- **Diagnóstico profundo de temas a estudiar para Ingeniería de Sistemas:**
  ```bash
  python main.py --que-estudiar
  ```
- **Ver el Radar rápido de habilidades más demandadas:**
  ```bash
  python main.py --radar
  ```
- **Probar conexión con Telegram:**
  ```bash
  python main.py --test-telegram
  ```
