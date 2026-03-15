# Atlas - Field Application Specialist AI Agent Backend

## 1. Descripción general del repositorio

Atlas es la API backend de la aplicación web Field Application Specialist (FAS) AI Agent.
Expone servicios REST que son consumidos por Website 3.0, el frontend de la aplicación, y actúa como la capa de orquestación para el acceso y la gestión de la base de datos PostgreSQL, coordinando todas las operaciones de persistencia.

Atlas funciona como la capa de negocio y de datos del sistema, encapsulando la lógica de dominio necesaria para el funcionamiento del agente de inteligencia artificial FAS. A través de esta API, los usuarios autenticados pueden cargar documentos, procesar su contenido, generar metadatos enriquecidos y ejecutar distintas operaciones orientadas a soporte técnico, análisis y automatización.

El servicio centraliza:
    - La lógica de negocio del sistema
    - La persistencia de datos en PostgreSQL
    - La integración con servicios externos (envio de correo electrónico, uso de LLMs, almacenamiento, etc.)

De este modo, el frontend queda desacoplado de la lógica interna, limitándose a la presentación, validación básica y comunicación con la API.

Este documento está dirigido a desarrolladores responsables del mantenimiento y evolución del backend Atlas, y describe la arquitectura, responsabilidades y puntos de extensión necesarios para añadir nuevas funcionalidades o modificar el comportamiento existente.

---

## 2. Stack tecnológico utilizado

## 2.1 Stack tecnológico Principal

| Categoría        | Tecnología | Versión | ¿Por qué se ha elegido está tecnología y versión? |
|------------------|------------|---------|--------------------------------------|
| **Lenguaje**     | Python | 3.12.3 | Se utiliza esta versión por su estabilidad, mejoras de rendimiento y compatibilidad completa con el ecosistema moderno sin asumir riesgos de versiones recién lanzadas. |
| **Framework** | FastAPI | 0.135.1 | Se elige por su soporte nativo para programación asíncrona, tipado estricto mediante Pydantic y alto rendimiento ASGI, adecuado para APIs de alto throughput. Además, proporciona una buena experiencia de desarrollo para quienes ya conocen Python, con una curva de aprendizaje menor que otros frameworks equivalentes. Incluye generación automática de documentación OpenAPI/Swagger, lo que permite visualizar y probar los endpoints de forma nativa. |
| **Servidor ASGI**| Uvicorn | 0.41.0 | Se utiliza por ser el servidor ASGI de referencia para FastAPI, con bajo overhead y buen rendimiento en entornos async.|
| **Email**        | Resend SDK | última | Se utiliza por su API simple, fiable y orientada a servicios backend modernos sin necesidad de SMTP propio. |
| **LLM**          | OpenAI / Anthropic / Google GenAI SDK | 2.26.0 / 0.84.0 / 1.67.0 | Se usan SDKs oficiales para mantener control directo sobre llamadas, costes y latencia sin abstracciones como LangChain |
| **Formatter**    | Black | 26.3.1 | Se usa para garantizar formato consistente automático en todo el repositorio. |
| **Linter**       | Ruff | 0.15.6 | Se elige por su velocidad y capacidad de reemplazar múltiples linters tradicionales. |
| **Tests**        | pytest | 9.0.2 | Framework de testing maduro, flexible y estándar en proyectos Python. |
| **Base de datos**| PostgreSQL | 16.10 | Se elige por su robustez, soporte ACID completo y capacidades avanzadas adecuadas para aplicaciones backend críticas.SDe |

## 2.2 Dependencias Secundarias poyo

| Categoría        | Tecnología | Versión | ¿Por qué se ha elegido esta versión? |
|------------------|------------|---------|--------------------------------------|
| **Servidor ASGI**| Uvicorn | 0.41.0 | Se utiliza por ser el servidor ASGI de referencia para FastAPI, con bajo overhead y buen rendimiento en entornos async. |
| **Driver DB**    | asyncpg | 0.31.0 | Se utiliza por ser el driver async más eficiente para PostgreSQL en Python, con menor latencia que psycopg en modo async. |
| **ORM**          | SQLAlchemy | 2.0.48 | Se usa por su API moderna orientada a async y control explícito de sesiones, evitando patrones implícitos problemáticos. |
| **Autenticación**| python-jose / PyJWT / passlib | 3.5.0 / 2.12.0 / 1.7.4 | Se eligen librerías ligeras y estándar que permiten implementar autenticación JWT sin depender de frameworks externos. |
| **Rate limiting**| SlowAPI | 0.1.9 | Se elige por su integración directa con Starlette/FastAPI y soporte de limitación mediante middleware. |
| **Validación**   | Pydantic | 2.12.5 | Se usa por su validación basada en typing, alto rendimiento y compatibilidad directa con FastAPI. |
| **Config**       | pydantic-settings | 2.13.1 | Permite gestión tipada de configuración desde variables de entorno sin lógica adicional. |
| **PDF**          | pdfplumber / pypdf | 0.11.9 / 6.8.0 | Se utilizan por su estabilidad y control directo sobre parsing sin dependencias pesadas. |
| **HTTP client**  | httpx | 0.28.1 | Se utiliza por su soporte async nativo y compatibilidad con testing ASGI. |
| **Uploads**      | python-multipart | 0.0.22 | Necesario para manejo de formularios y archivos en FastAPI sin middleware adicional. |
| **Env**          | python-dotenv | 1.2.2 | Permite cargar variables de entorno en desarrollo y en producción |
| **Async tests**  | pytest-asyncio | 1.3.0 | Permite ejecutar tests async sin hacks ni event loops manuales. |
| **API tests**    | httpx | 0.28.1 | Permite testear aplicaciones ASGI sin levantar servidor real. |
| **Runtime**      | CPython | 3.12 | Runtime oficial con máxima compatibilidad con librerías C y drivers. |


La fecha de la última actualización es **15/03/2026**. Durante el desarrollo se ha hecho mucho hincapié en la actualización y el parcheo de las distintas versiones de las librerías utilizadas para que no haya errores de seguridad. 


## 2.3 Dependencias Futuras

En el futuro se tiene contemplado utilizar esta librería, ya que, una vez desplegada la aplicación en producción, los datos almacenados en la base de datos deberán modificarse con frecuencia. Se trata de una aplicación con un alto nivel de incertidumbre, por lo que los cambios en el diseño son constantes.

| Categoría        | Tecnología | Versión | ¿Por qué se ha elegido esta versión? |
|------------------|------------|---------|--------------------------------------|
| **Migraciones**  | Alembic | 1.13.x | Se utiliza por ser la herramienta oficial del ecosistema SQLAlchemy y permitir versionado controlado del esquema. |


---
## 3. Instalación y ejecución

### 3.1 Instalación en local

#### 3.1.1 Descarga del código

El código debe descargarse desde el repositorio público en GitHub: https://github.com/MishellRamosAcaro/Atlas

A continuación, se describen los pasos necesarios para ejecutar el proyecto en un entorno local.

> **Nota:** Los comandos mostrados a continuación están precedidos por el símbolo `$` y deben ejecutarse en la terminal. 

1. Abrir una terminal en el directorio donde se desee descargar el proyecto.

2. Clonar el repositorio desde GitHub usando el siguiente comando y verificar, mediante `git status` y `git remote -v`, que el proyecto se ha descargado correctamente:

      ```bash
      $ git clone https://github.com/MishellRamosAcaro/Atlas.git
         Cloning into 'Atlas'...
         remote: Enumerating objects: 416, done.
         remote: Counting objects: 100% (416/416), done.
         remote: Compressing objects: 100% (249/249), done.
         remote: Total 416 (delta 213), reused 337 (delta 135), pack-reused 0
         Receiving objects: 100% (416/416), 124.05 KiB | 580.00 KiB/s, done.
         Resolving deltas: 100% (213/213), done.

      $ cd Atlas
      $ git status
         On branch main
         Your branch is up to date with 'origin/main'.

         nothing to commit, working tree clean

      $ git remote -v
         origin  https://github.com/MishellRamosAcaro/Atlas.git (fetch)
         origin  https://github.com/MishellRamosAcaro/Atlas.git (push)

Si estos comandos se ejecutan sin errores y la salida es igual a la que mostramos el proyecto se ha clonado correctamente.

#### 3.1.2 Requisitos necesarios previos a la ejecución

Para poder ejecutar Atlas con uvicorn (`uvicorn app.main:app --reload`) necesitas:

- **Python 3.12 o superior.**

- **Base de datos PostgreSQL**. No es necesario crear manualmente la base de datos ni las tablas, ya que, al ejecutar Atlas por primera vez con Uvicorn, se crearán automáticamente la base de datos `atlas` y todas las tablas asociadas en caso de que no existan previamente. Esto se realiza desde la aplicación mediante **SQLAlchemy**, utilizando la función `create_all`. La URL de conexión se configura en la variable `DATABASE_URL` del archivo `.env`.

- **Archivo `.env`** en la raíz del proyecto (debe copiarse desde `.env.example`).  
El archivo `.env.example` contiene la mayoría de variables preconfiguradas para que Atlas funcione correctamente en un entorno de desarrollo, excepto `RESEND_API_KEY` y al menos una de las siguientes API keys:  
`GOOGLE_API_KEY / ANTHROPIC_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY`.

   - **Resend (email):** si deseas utilizar el registro, la verificación o el envío de correos (contacto) desde la aplicación, es necesario disponer de una cuenta en [Resend](https://resend.com) y configurar su `RESEND_API_KEY` en el archivo `.env`.  
   Si la variable está vacía, la API puede iniciarse, pero el envío de correos fallará.

   - **LLM (enriquecimiento):** si se utiliza la funcionalidad principal de enriquecimiento de archivos, es necesario configurar al menos una API key correspondiente al proveedor definido en `LLM_PRESET` (por ejemplo, `gemini-flash` requiere `GOOGLE_API_KEY`).  
     Proveedores soportados: Google (Gemini), Anthropics (Claude), DeepSeek u OpenAI.  
     No es necesario configurar todas las claves, solo la correspondiente al preset seleccionado.

> **Nota:** No es necesario tener un frontend en ejecución, ya que el backend funciona de forma independiente y puede utilizarse directamente mediante peticiones HTTP a la API desde herramientas como Postman o desde la documentación interactiva generada automáticamente (Swagger / OpenAPI).

#### 3.1.2 Creación del entorno virtual e instalación de dependencias

Desde el directorio raíz del proyecto descargado, se debe crear un entorno virtual de Python para aislar las dependencias del sistema y garantizar que el backend se ejecute con las versiones correctas de las librerías.

A continuación, se activará el entorno virtual y se instalarán todas las dependencias definidas en el archivo `requirements.txt`, que contiene las librerías necesarias para ejecutar Atlas.

Ejecutar los siguientes comandos en la terminal:

```bash
$ python -m venv .venv
$ source .venv/bin/activate   # En Windows: .venv\Scripts\activate
(.venv)$ pip install -r requirements.txt
```

#### 3.1.3 Ejecutar el servidor Uvicorn

Una vez instaladas las dependencias y activado el entorno virtual, se puede iniciar el servidor ASGI utilizando **Uvicorn**, que es el servidor instalado y recomentado para FastAPI.

Ejecutar el siguiente comando desde el directorio raíz del proyecto:

```bash
(.venv) python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
El backend se ejecuta indicando como punto de entrada `app.main:app`, donde `app` es la instancia de FastAPI definida en el archivo `main.py`. El parámetro `--reload` habilita el reinicio automático del servidor cuando se detectan cambios en el código, lo que resulta útil durante el desarrollo.La opción `--host 0.0.0.0` permite que el servidor sea accesible desde cualquier interfaz de red, y `--port 8000` define el puerto en el que se expondrá la API.

Una vez iniciado el servidor, la API estará disponible en:
    - API base → http://localhost:8000
    - Documentación Swagger / OpenAPI → http://localhost:8000/docs
    - Documentación ReDoc → http://localhost:8000/redoc

> **Nota:** La documentación interactiva solo estará disponible cuando la variable de entorno ENV esté configurada como dev, ya que en entornos de producción estas rutas pueden deshabilitarse por motivos de seguridad.

## 4. Estructura del proyecto

```
Atlas/
├── app/
│   ├── main.py                 # Punto de entrada FastAPI, CORS, rate limit, routers
│   ├── config.py                # Configuración (Pydantic Settings v2)
│   ├── limiter.py               # Instancia SlowAPI (rate limiting por IP)
│   ├── routers/                 # Endpoints por dominio
│   │   ├── auth.py              # Registro, login, verify-email, refresh, /me, borrado cuenta
│   │   ├── contact.py            # POST /contact (formulario + email en background)
│   │   ├── uploads.py           # Subida, listado, metadatos, descarga, borrado de archivos
│   │   ├── extractions.py       # Lectura/actualización del documento extraído por file_id
│   │   ├── enrichments.py       # Enriquecimiento bajo demanda por file_id
│   │   └── upload_extract_enrichment.py # Flujo único: subir → extraer → enriquecer
│   ├── services/                # Lógica de negocio
│   │   ├── auth_service.py      # Registro, verificación, login, sesiones
│   │   ├── email_service.py     # Envío de emails (Resend, plantillas)
│   │   ├── uploads_service.py   # Subida, almacenamiento, antivirus, cuota
│   │   ├── extraction_service.py # Orquesta extracción y persistencia del resultado
│   │   ├── enrichment_service.py # Enriquecimiento con LLM y persistencia
│   │   └── jwt_service.py       # Creación y validación de JWT
│   ├── repositories/           # Acceso a datos (una capa por modelo/agregado)
│   │   ├── user_repository.py
│   │   ├── user_account_status_repository.py
│   │   ├── refresh_token_repository.py
│   │   ├── login_lockout_repository.py
│   │   └── files_repository.py
│   ├── models/                  # Modelos SQLAlchemy (User, File, RefreshToken, etc.)
│   ├── schemas/                 # Esquemas Pydantic (request/response)
│   ├── middleware/              # Cookies, auth, security headers, emails
│   ├── infrastructure/          # DB engine, sesiones, almacenamiento, antivirus
│   ├── extraction/              # Pipeline de extracción de PDFs
│   │   ├── pipeline.py         # Orquestación: layout → segmentación → chunking → keywords
│   │   ├── layout_extraction.py
│   │   ├── structural_segmentation.py
│   │   ├── semantic_chunking.py
│   │   ├── document_analyzer.py
│   │   ├── keywords.py, keyword_polisher.py, keyword_refiner.py
│   │   └── block_cleaner.py, schemas.py
│   ├── llm/                     # Cliente unificado LLM (varios proveedores)
│   │   ├── config.py
│   │   └── client.py
│   ├── application/             # Capa de aplicación (puertos para evolución hexagonal)
│   │   ├── ports/               # Interfaces (repositorios, LLM, storage, antivirus)
│   │   ├── use_cases/
│   │   └── prompts/
│   ├── prompts/                 # Plantillas de prompts para enriquecimiento
│   └── templates/               # Plantillas de email (contacto, registro, etc.)
├── tests/                       # Tests unitarios e integración (pytest)
├── data/                        # Datos locales (p. ej. staging)
├── requirements.txt
├── .env.example
└── README.md
```

- **routers**: definen las rutas HTTP y delegan en servicios.
- **services**: orquestan repositorios, infraestructura y reglas de negocio.
- **repositories**: abstraen el acceso a PostgreSQL.
- **infrastructure**: motor de BD, almacenamiento de archivos, escáner antivirus.
- **extraction**: pipeline de PDF (layout → segmentos → secciones → keywords).
- **llm**: abstracción sobre varios proveedores de LLM para enriquecimiento.
- **application/ports**: interfaces para una futura arquitectura hexagonal.

---

## 5. Funcionalidades principales

1. **Autenticación y usuarios**  
   Registro con email y contraseña, verificación por código de 6 dígitos, login con JWT en cookies HttpOnly, refresh de tokens, límite de sesiones, bloqueo por intentos fallidos, actualización de perfil y contraseña, borrado de cuenta.

2. **Subida y gestión de archivos**  
   Subida de PDFs con validación de tipo y tamaño, cuota por usuario (ej. 5 archivos), almacenamiento en disco (dev) o GCS (prod), escaneo antivirus en producción, listado, metadatos, descarga (solo archivos CLEAN) y borrado.

3. **Extracción de documentos**  
   Pipeline que a partir del PDF obtiene bloques de layout, los segmenta, genera secciones semánticas y keywords, y persiste el resultado (documento + secciones) en almacenamiento.

4. **Enriquecimiento con LLM**  
   Toma el documento extraído y, usando el cliente LLM configurado, genera metadatos a nivel documento (tipo, contexto técnico, riesgo, audiencia) y por sección (resumen, keywords). Resultado persistido y expuesto por API.

5. **Flujo upload-extract-enrichment**  
   Un solo endpoint que sube el archivo, ejecuta la extracción y el enriquecimiento y devuelve el documento enriquecido y las secciones (usado por el frontend para “analizar archivos”).

6. **Formulario de contacto**  
   POST con validación, honeypot anti-spam y rate limiting; el envío del email se hace en background vía Resend.

7. **Seguridad y calidad**  
   CORS según entorno, cabeceras de seguridad (HSTS, X-Content-Type-Options, etc.), rate limiting por IP, cookies seguras y configuración lista para TLS en producción.

---

## 6. Scripts disponibles



| Comando | Descripción |
|---------|-------------|
| `uvicorn app.main:app --reload` | Arranca la API en modo desarrollo con recarga |
| `pytest tests/ -v` | Ejecuta todos los tests (usar `.venv` o `python -m pytest`) |
| `black .` | Formatea el código (Black) |
| `ruff check .` | Linting (Ruff) |

En desarrollo local se debe usar siempre el entorno virtual (por ejemplo `source .venv/bin/activate` o `.venv/bin/python -m pytest`).

---

## 7. Buenas prácticas usadas en el proyecto

- **Arquitectura en capas**: separación clara entre routers → services → repositories → infrastructure, preparada para una evolución hexagonal con puertos en `application/ports`.
- **Configuración tipada**: uso de Pydantic Settings v2 para variables de entorno y validación.
- **Async**: base de datos y cliente HTTP en modo asíncrono (asyncpg, SQLAlchemy async).
- **Seguridad**: JWT en cookies HttpOnly, CORS restrictivo en producción, cabeceras de seguridad, rate limiting, bloqueo por intentos de login fallidos.
- **Calidad de código**: Black y Ruff; convenciones PEP; imports absolutos; docstrings al estilo NumPy donde aplica.
- **Tests**: pytest con pytest-asyncio; tests unitarios e integración; recursos externos mockeados; cobertura mínima objetivo 80%.
- **API**: recursos en plural, tags y descripciones en OpenAPI, respuestas de error estandarizadas con `HTTPException`.
- **Cumplimiento**: consideraciones GDPR/LOPDGDD; cifrado en tránsito fuera del entorno local.

---

## 8. Autor e información adicional

- **Servicio**: Atlas  
- **Documentación de gobierno técnico**: ver `AGENTS.MD` en la raíz del repositorio para reglas de ingeniería, seguridad, testing y despliegue.  
- **Producción**: pensado para ejecución en Docker (imagen base recomendada `python:alpine`) y despliegue en **Google Cloud Run**, con secretos en Google Cloud Secret Manager.
