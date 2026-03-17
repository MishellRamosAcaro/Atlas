<p align="center">
  <img src="logo.png" alt="FAS AI Agent Logo" width="120" />
</p>

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

No hay que olvidarse de que este proyecto se encuentra actualmente en fase de **MVP**.  
Por este motivo, tanto la arquitectura como la estructura interna y los estándares de calidad del código continuarán evolucionando a medida que el sistema madure.

Se trata de un proyecto con una gran incertidumbre, en el que las decisiones técnicas y de diseño se ajustan de forma iterativa en función de las necesidades funcionales, operativas y de producto de cada momento.  
En consecuencia, la solución actual debe entenderse como una base evolutiva, diseñada para crecer y refinarse progresivamente conforme aumente la estabilidad del negocio y se consoliden los requisitos de parte del cliente. 


---

## 2. Stack tecnológico utilizado

### 2.1 Stack tecnológico Principal

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

### 2.2 Dependencias secundarias de apoyo

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


### 2.3 Dependencias futuras

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

> **Nota:** No es necesario tener un frontend en ejecución, ya que el backend funciona de forma independiente y puede utilizarse directsmente mediante peticiones HTTP a la API desde herramientas como Postman o desde la documentación interactiva generada automáticamente (Swagger / OpenAPI).

#### 3.1.3 Creación del entorno virtual e instalación de dependencias

Desde el directorio raíz del proyecto descargado, se debe crear un entorno virtual de Python para aislar las dependencias del sistema y garantizar que el backend se ejecute con las versiones correctas de las librerías.

A continuación, se activará el entorno virtual y se instalarán todas las dependencias definidas en el archivo `requirements.txt`, que contiene las librerías necesarias para ejecutar Atlas.

Ejecutar los siguientes comandos en la terminal:

```bash
$ python -m venv .venv
$ source .venv/bin/activate   # En Windows: .venv\Scripts\activate
(.venv)$ pip install -r requirements.txt
```

#### 3.1.4 Ejecutar el servidor Uvicorn

Una vez instaladas las dependencias y activado el entorno virtual, se puede iniciar el servidor ASGI utilizando **Uvicorn**, que es el servidor instalado y recomentado para FastAPI.

Ejecutar el siguiente comando desde el directorio raíz del proyecto:

```bash
(.venv)$  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
El backend se ejecuta indicando como punto de entrada `app.main:app`, donde `app` es la instancia de FastAPI definida en el archivo `main.py`. El parámetro `--reload` habilita el reinicio automático del servidor cuando se detectan cambios en el código, lo que resulta útil durante el desarrollo.La opción `--host 0.0.0.0` permite que el servidor sea accesible desde cualquier interfaz de red, y `--port 8000` define el puerto en el que se expondrá la API.

Una vez iniciado el servidor, la API estará disponible en:
    - API base → http://localhost:8000
    - Documentación Swagger / OpenAPI → http://localhost:8000/docs
    - Documentación ReDoc → http://localhost:8000/redoc

> **Nota:** La documentación interactiva solo estará disponible cuando la variable de entorno ENV esté configurada como dev, ya que en entornos de producción estas rutas pueden deshabilitarse por motivos de seguridad.


#### 3.1.5 Ejecutar tests

Para ejecutar los tests es necesario disponer de una base de datos independiente para testing.  
El proyecto está configurado para usar una base de datos llamada `atlas_test`, definida en la variable de entorno `DATABASE_URL_TEST`.

Si es la primera vez que se ejecutan los tests, se debe crear la base de datos manualmente en PostgreSQL.

Ejecutar el siguiente comando desde una terminal con acceso a `psql`:

```bash
psql -U postgres -c "CREATE DATABASE atlas_test;"

Salida esperada:

CREATE DATABASE
```
Una vez creada la base de datos, se pueden ejecutar los tests con el siguiente comando `python -m pytest tests/ -v`

Este comando ejecuta todos los tests del directorio tests/ mostrando información detallada.s


```bash
(.venv)$ python -m pytest tests/-v

=============================== test session starts ================================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0 -- /home/mishellramos/projects/FASEnvDev/Atlas/.venv/bin/python                                             
cachedir: .pytest_cache
rootdir: /home/mishellramos/projects/FASEnvDev/Atlas
configfile: pytest.ini
plugins: anyio-4.12.1, asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function                                                 
collected 48 items                                                                 

tests/test_api_auth.py::test_auth_router_mount PASSED                        [  2%]
...
tests/test_uploads.py::test_post_uploads_infected_removes_file_and_record PASSED [100%]                                                                                 

================================= warnings summary =================================
.venv/lib/python3.12/site-packages/passlib/utils/__init__.py:854
  /home/mishellramos/projects/FASEnvDev/Atlas/.venv/lib/python3.12/site-packages/passlib/utils/__init__.py:854: DeprecationWarning: 'crypt' is deprecated and slated for removal in Python 3.13                                                             
    from crypt import crypt as _crypt
...
========================= 48 passed, 3 warnings in 10.37s ==========================
```

#### 3.1.6 Formateo de código con Black

Black se utiliza para mantener un formato de código consistente en todo el proyecto.
El formateo no modifica la lógica del programa, únicamente el estilo. Se ejecuta desde la raiz del proyecto:

```bash
(.venv)$  black .

reformatted app/application/use_cases/__init__.py
reformatted app/application/__init__.py
...
All done! 47 files reformatted, 48 files left unchanged.
```

#### 3.1.7 Análisis estático con Ruff

Ruff se utiliza como linter principal para detectar errores, imports no usados y problemas de estilo antes de ejecutar el código.

```bash
(.venv)$  ruff check .

F401 `DOCUMENT_TYPE_VALUES` imported but unused
--> app/extraction/document_analyzer.py:24:5

Found 26 errors.
14 fixable with the --fix option.

(.venv)$ ruff check .

All checks passed!
```

Para corregir automáticamente los errores que lo permitan:
```bash
(.venv)$  ruff check . --fix
```

## 4. Estructura del proyecto y arquitectura aplicada

El proyecto sigue una organización **modular, desacoplada y orientada a responsabilidades**, con el fin de facilitar el mantenimiento, la evolución funcional y la incorporación de nuevas capacidades sin degradar la coherencia del sistema.

Atlas no se organiza como un monolito alrededor del framework, sino como un backend con separación explícita entre **interfaz HTTP**, **lógica de aplicación**, **dominio funcional**, **persistencia** e **integraciones externas**. Con ello se reduce el acoplamiento entre capas, se mejora la trazabilidad de cambios y cada parte del sistema puede evolucionar con impacto acotado.


### 4.1 Arquitectura utilizada

La arquitectura se describe como **por capas con evolución hacia un enfoque hexagonal**. El sistema se divide en:

- **Capa de entrada**: expone la API REST y gestiona el contrato HTTP.
- **Capa de servicios o aplicación**: orquesta los casos de uso y concentra la lógica operativa.
- **Capa de persistencia**: encapsula el acceso a PostgreSQL y evita que la lógica de negocio dependa de consultas o detalles del ORM.
- **Capa de infraestructura**: implementa almacenamiento, base de datos, antivirus, correo y clientes LLM.
- **Capa de extracción y enriquecimiento**: encapsula pipelines de procesamiento documental y uso de LLMs.
- **Capa de aplicación/puertos**: define interfaces que preparan la evolución hacia arquitectura hexagonal y permiten sustituir implementaciones sin alterar la lógica de negocio.


#### Evolución hacia arquitectura hexagonal

La capa `application` con puertos y casos de uso orienta el diseño hacia una arquitectura más desacoplada y basada en interfaces. La lógica de aplicación depende de contratos, no de implementaciones concretas, lo que facilita:

- Sustituir repositorios.
- Cambiar proveedores LLM.
- Modificar almacenamiento.
- Introducir nuevos adaptadores.
- Aislar mejor las pruebas.

El proyecto sigue siendo pragmático y orientado a entrega; esta base evita que el crecimiento derive en una arquitectura rígida o excesivamente acoplada al framework.


### 4.2 Decisión arquitectónica

La estructura no aplica patrones de forma dogmática, sino que resuelve un problema concreto: un backend que combina API REST, persistencia relacional, procesamiento documental e integración con IA sin convertirse en un monolito difícil de mantener. En resumen:

- **Arquitectura modular por capas**.
- **Separación explícita** entre API, aplicación, persistencia e infraestructura.
- **Dominios funcionales** bien delimitados.
- **Preparación para evolución hacia arquitectura hexagonal** donde aporta valor.

### 4.3 Mejoras y evolución futura

La estructura actual es sólida para el estado presente y está preparada para evolucionar. Mejoras razonables a futuro:

- Consolidar la **capa de casos de uso**, desplazando la orquestación desde servicios hacia una capa de aplicación más explícita.
- Completar la transición a **arquitectura hexagonal**, con dependencias externas únicamente a través de puertos definidos.
- Reorganizar por **bounded contexts** más explícitos si el sistema crece (p. ej. identidad, documentos, extracción y enriquecimiento como dominios independientes).
- Introducir **eventos de dominio o colas asíncronas** para procesos costosos (extracción, antivirus, enriquecimiento con LLM).
- Reforzar el aislamiento entre componentes con **contratos internos más estrictos**, sobre todo en flujos de procesamiento documental.
- Incorporar observabilidad avanzada: **tracing, métricas técnicas y auditoría funcional**.
- Formalizar decisiones estructurales con **ADRs (Architecture Decision Records)**.

En conjunto, la estructura actual cubre las necesidades presentes de Atlas y establece una base técnica para crecer sin perder control sobre la complejidad del sistema.

---

## 5. Funcionalidades principales

En esta sección se describen las capacidades del backend desde un punto de vista técnico, junto con los endpoints asociados.  
Se ha decidido vincular cada caso de uso con su endpoint correspondiente, ya que estos definen de forma exacta las operaciones que puede realizar un cliente.

Cada endpoint se ha asociado a su caso de uso completo, ya que representa la unidad funcional desde el inicio hasta el fin de la operación. De esta forma, el path define de manera explícita el flujo que sigue el cliente para realizar una acción, lo que facilita la comprensión del sistema, mejora la mantenibilidad y asegura la coherencia entre la documentación, la API expuesta y el comportamiento real del backend.

Se utiliza la técnica Given/When/Then para definir de forma estructurada las funcionalidades principales y los requisitos del sistema.

### 5.1 Autenticación y Sesiones

El backend es la única fuente de verdad para identidad y sesión. Gestiona el proceso de autenticación (registro, verificación, login, refresh de tokens) y aplica políticas de seguridad como límite de sesiones, bloqueo por intentos fallidos y almacenamiento seguro de credenciales.

**Casos de uso y endpoints expuestos por la API**

- Registro de usuario  
  Endpoint: POST /auth/register  
  - Given: El usuario no tiene una cuenta registrada.
  - When: El usuario envía su email y contraseña al endpoint de registro.
  - Then: El backend crea el usuario en estado pendiente y envía un código de verificación al correo indicado.

- Verificación de email  
  Endpoint: POST /auth/verify-email  
  - Given: El usuario ha recibido un código de verificación por email.
  - When: El usuario envía el código al endpoint de verificación.
  - Then: El backend valida el código y activa la cuenta si es correcto.2

- Solicitud de nuevo código de verificación  
  Endpoint: POST /auth/resend-verification-code  
  - Given: El usuario tiene una cuenta pendiente de verificación.
  - When: El usuario solicita un nuevo código.
  - Then: El backend envía un nuevo código de verificación aplicando rate limiting por dirección de email.

- Login con credenciales  
  Endpoint: POST /auth/token (grant_type=password)  
  - Given: El usuario tiene una cuenta válida y verificada.
  - When: El usuario envía email y contraseña.
  - Then: El backend genera tokens JWT (access y refresh) y los devuelve en cookies HttpOnly.

- Renovación de sesión  
  Endpoint: POST /auth/token (grant_type=refresh_token o cookie)  
  - Given: El usuario tiene un refresh token válido almacenado en cookie HttpOnly.
  - When: El cliente solicita renovar la sesión.
  - Then: El backend genera un nuevo access token si la sesión sigue siendo válida y respeta el límite de sesiones activas.

- Cierre de sesión  
  Endpoint: POST /auth/logout  
  - Given: El usuario tiene una sesión activa.
  - When: El usuario solicita cerrar sesión.
  - Then: El backend invalida la sesión actual o todas las sesiones activas del usuario.


---

### 5.2 Gestión de perfil y cuenta de usuario

El backend gestiona los datos persistentes asociados al usuario autenticado y garantiza que solo el propietario de la cuenta pueda consultar o modificar su información.

**Casos de uso y endpoints expuestos por la API**

- Consulta del perfil del usuario autenticado  
  Endpoint: GET /auth/me  
  - Given: El usuario tiene una sesión válida.
  - When: El cliente solicita la información del perfil.
  - Then: El backend devuelve los datos del usuario autenticado.

- Actualización de datos de perfil  
  Endpoint: PATCH /auth/me  
  - Given: El usuario está autenticado.
  - When: El usuario envía nuevos datos de perfil (nombre, apellido,correo).
  - Then: El backend valida la información y actualiza los datos almacenados.En el caso del correo vuelve a verificar que es un correo válido. 

- Cambio de contraseña  
  Endpoint: PATCH /auth/me/password  
  - Given: El usuario está autenticado y conoce su contraseña actual.
  - When: El usuario envía la contraseña actual y la nueva contraseña.
  - Then: El backend valida la contraseña, la actualiza y cierra todas las sesiones activas.

- Desactivación de la cuenta  
  Endpoint: POST /auth/me/deactivate  
  - Given: El usuario tiene una sesión activa.
  - When: El usuario solicita desactivar su cuenta.
  - Then: El backend desactiva la cuenta y cierra la sesión en todos los dispositivos.

- Borrado definitivo de la cuenta  
  Endpoint: DELETE /auth/me  
  - Given: El usuario está autenticado.
  - When: El usuario solicita eliminar su cuenta y confirma con la contraseña.
  - Then: El backend elimina la cuenta y todos los datos asociados.


### 5.3 Subida y gestión de archivos

Validar tipo y tamaño de archivo, aplicar cuota por usuario, persistir el binario en almacenamiento (local o cloud), ejecutar escaneo antivirus en producción y mantener metadatos y estado del archivo en PostgreSQL.

**Casos de uso y endpoints expuestos por la API**

- Subida de archivo  
  Endpoint: POST /files  
  - Given: El usuario está autenticado.
  - When: El usuario envía un archivo en formato multipart.
  - Then: El backend valida el formato (PDF), comprueba el tamaño máximo permitido y la cuota de archivos por usuario, y almacena el archivo si cumple las restricciones.

- Listado de archivos del usuario  
  Endpoint: GET /files  
  - Given: El usuario tiene una sesión válida.
  - When: El cliente solicita el listado de archivos.
  - Then: El backend devuelve los archivos asociados al usuario con su estado (CLEAN, PENDING_SCAN, INFECTED) y sus metadatos (nombre, tamaño, fecha).

- Descarga de archivo  
  Endpoint: GET /files/{file_id}/download  
  - Given: El usuario es propietario del archivo.
  - When: El usuario solicita descargar el archivo.
  - Then: El backend permite la descarga solo si el estado del archivo es CLEAN; los archivos en cuarentena o infectados no pueden descargarse 

- Borrado de archivo  
  Endpoint: DELETE /files/{file_id}  
  - Given: El usuario es propietario del archivo.
  - When: El usuario solicita eliminar el archivo.
  - Then: El backend elimina el registro en la base de datos y el contenido almacenado.


- **Funcionalidades futuras**
  - Almacenamiento: en desarrollo se usa un directorio local configurado por variable de entorno; en el futuro se pretende usar Google Cloud Storage (GCS), configurado mediante bucket y credenciales.
  - Antivirus: en el futuro se pretende ejecutar un escáner sobre el archivo subido; si el resultado es infectado, el archivo y el registro se eliminan y se devuelve error al cliente. Se ha dejado preprarada la estructura para poder realizarlo. Ahora todos los archivos tienen el estado CLEAN. 

### 5.4 Extracción de documentos

Ejecutar la extracción del contenido del documento (actualmente PDF) para generar una representación estructurada persistente, utilizada posteriormente como entrada del proceso de enriquecimiento mediante LLM.  
La extracción previa permite reducir el número de tokens consumidos durante el enriquecimiento, evitando enviar el documento completo al modelo.

Pipeline interno:
- Extracción de layout mediante pdfplumber / pypdf.
- Segmentación estructural del documento.
- Chunking semántico por secciones.
- Extracción de keywords por sección.

Resultado:
Se produce un JSON estructurado con el documento y sus secciones (heading, content, keywords), que se almacena en el sistema de almacenamiento y se referencia desde el registro del archivo en la base de datos.

**Casos de uso y endpoints expuestos por la API**

- Ejecución de extracción sobre un archivo subido  
  Endpoint: POST /extractions/{file_id}  
  - Given: El usuario es propietario del archivo y el archivo está en estado CLEAN.
  - When: El cliente solicita ejecutar la extracción para ese archivo.
  - Then: El backend ejecuta el pipeline de extracción, persiste el JSON (documento + secciones) en almacenamiento, actualiza la referencia en BD y devuelve el resultado.

- Consulta del documento extraído  
  Endpoint: GET /extractions/{file_id}/document  
  - Given: El usuario es propietario del archivo y existe extracción previa.
  - When: El cliente solicita los metadatos a nivel documento (source, document_type, technical_context, risk_level, audience, etc.).
  - Then: El backend lee el JSON desde almacenamiento y devuelve la sección document.

- Actualización de campos del documento extraído  
  Endpoint: PATCH /extractions/{file_id}/document  
  - Given: El usuario es propietario del archivo y existe extracción.
  - When: El usuario envía campos a actualizar (source, document_type, technical_context, risk_level, audience, state, effective_date, owner_team).
  - Then: El backend actualiza el JSON en almacenamiento y, si se modifica source.file_name, sincroniza el filename en la tabla de archivos.

### 5.5 Enriquecimiento con LLM

Ejecutar el proceso de enriquecimiento sobre un documento previamente extraído, invocando al proveedor de LLM configurado para generar metadatos a nivel de documento y de sección, y persistiendo el resultado enriquecido.  

Pipeline interno:
- Lectura del JSON estructurado almacenado (documento + secciones).
- Selección del proveedor LLM según el preset configurado en variables de entorno.
- Generación de metadatos a nivel de documento (tipo, contexto técnico, nivel de riesgo, audiencia).
- Procesamiento por secciones en paralelo con límite de concurrencia configurable.
- Generación de resumen y refinamiento de keywords por sección; asignación de score a cada keyword en función del documento (frecuencia en la sección, aparición en el encabezado, peso técnico a nivel de sección; frecuencia global, número de secciones donde aparece y aparición en título o intended use a nivel de documento).
- Invocación del cliente LLM unificado (Google Gemini, Anthropic Claude, DeepSeek, OpenAI).
- Ejecución de llamadas en thread pool con política de reintentos ante errores.
- Validación del resultado antes de persistencia.

Resultado:
Se genera un JSON enriquecido que contiene metadatos a nivel de documento y por sección. Las keywords se devuelven con un score numérico: a nivel de sección, cada keyword tiene score según frecuencia en el contenido (TF local), aparición en el encabezado de la sección y peso por término técnico; a nivel de documento, el score combina frecuencia global en el texto, número de secciones donde aparece el término y aparición en título o sección de intended use. Las keywords se exponen en formato `{"term": string, "score": float}`; a nivel documento además se ofrece una jerarquía por categoría (keywords_hierarchy). El resultado se almacena en el sistema de almacenamiento y queda referenciado en el registro del archivo en la base de datos.


**Casos de uso y endpoints expuestos por la API**

- Enriquecimiento con LLM de un documento extraído  
  Endpoint: POST /enrichments/{file_id}  
  - Given: El usuario es propietario del archivo y existe extracción previa.
  - When: El cliente solicita enriquecer el documento.
  - Then: El backend invoca al LLM configurado, genera metadatos a nivel documento y por sección, asigna un score a cada keyword (por sección: TF local, aparición en encabezado y peso técnico; por documento: TF global, secciones donde aparece y aparición en título/intended use), persiste el JSON enriquecido y devuelve documento (incl. keywords y keywords_hierarchy con scores) y secciones (incl. keywords con score por término).

- Consulta de variable global de enriquecimiento  
  Endpoint: GET /enrichments/export_global_variable/{variable_name}  
  - Given: El usuario está autenticado y el nombre de variable está permitido (DOCUMENT_TYPE_VALUES, RISK_LEVEL_VALUES, AUDIENCE_VALUES, STATE_VALUES).
  - When: El cliente solicita el valor de una variable global.
  - Then: El backend devuelve el valor; error si el nombre no está permitido.

### 5.6 Flujo único: subida, extracción y enriquecimiento

Ofrecer un único endpoint que orqueste en secuencia:  
(1) subida y validación del archivo,  
(2) ejecución del pipeline de extracción,  
(3) enriquecimiento mediante LLM,  
permitiendo que el frontend analice un archivo completo en una sola petición.

Pipeline interno:
- Recepción del archivo.
- Validación de formato, tamaño máximo y cuota de archivos por usuario.
- Almacenamiento del archivo y creación del registro en base de datos.
- Ejecución del pipeline de extracción estructural.
- Generación del JSON con documento y secciones.
- Ejecución del pipeline de enriquecimiento utilizando el proveedor LLM configurado.
- Persistencia del resultado enriquecido en almacenamiento.
- Actualización del estado del archivo y de los metadatos asociados.

Resultado:
El archivo queda almacenado junto con su representación estructurada y el resultado enriquecido.  
El registro del archivo en la base de datos referencia tanto el contenido original como el JSON extraído y el JSON enriquecido, permitiendo su consulta posterior sin repetir el procesamiento.

**Casos de uso y endpoints expuestos por la API**

- Subida, extracción y enriquecimiento en una sola petición  
  Endpoint: POST /upload-extract-enrichment  
  - Given: El usuario está autenticado.
  - When: El usuario envía un archivo en formato multipart (PDF).
  - Then: El backend sube el archivo, ejecuta la extracción y el enriquecimiento, y devuelve el documento enriquecido y las secciones (document_type, technical_context, risk_level, audience, section_summary, keywords). Rate limiting aplicado (p. ej. 10/minuto por IP).

### 5.7 Formulario de contacto

Recibir el payload del formulario (nombre, email, empresa, mensaje), validarlo, aplicar medidas anti-abuso y encolar el envío del correo en segundo plano sin bloquear la respuesta HTTP.

**Casos de uso y endpoints expuestos por la API**

- Envío del formulario de contacto  
  Endpoint: POST /contact  
  - Given: El cliente tiene los datos del formulario (nombre, email, empresa, mensaje) y el honeypot no está rellenado.
  - When: El cliente envía un POST con el body validado.
  - Then: El backend responde de forma inmediata con éxito o error de validación; el envío del email se encola en background (BackgroundTasks) vía Resend.

---

## 6. Buenas prácticas usadas en el proyecto

- **Arquitectura en capas**: separación clara entre routers → services → repositories → infrastructure, preparada para una evolución hexagonal con puertos en `application/ports`.
- **Configuración tipada**: uso de Pydantic Settings v2 para variables de entorno y validación.
- **Async**: base de datos y cliente HTTP en modo asíncrono (asyncpg, SQLAlchemy async).
- **Seguridad**: JWT en cookies HttpOnly, CORS restrictivo en producción, cabeceras de seguridad, rate limiting, bloqueo por intentos de login fallidos.
- **Calidad de código**: Black y Ruff; convenciones PEP; imports absolutos; docstrings al estilo NumPy donde aplica.
- **Tests**: pytest con pytest-asyncio; tests unitarios e integración; recursos externos mockeados; cobertura mínima objetivo 80%.
- **Cumplimiento**: consideraciones GDPR/LOPDGDD; cifrado en tránsito fuera del entorno local.


### 6.1 Seguridad, CORS y cabeceras

- **CORS:**  
  La política de CORS se configura mediante variables de entorno.  
  En entorno de desarrollo se permite el acceso desde cualquier origen para facilitar la integración, mientras que en producción se restringe a una lista explícita de orígenes autorizados (por ejemplo, el dominio del frontend).  
  El envío de credenciales mediante cookies solo se habilita para los dominios permitidos.

- **Cabeceras de seguridad:**  
  Se aplica un middleware que añade cabeceras HTTP de seguridad en todas las respuestas, incluyendo  
  `X-Content-Type-Options: nosniff`,  
  `X-Frame-Options: DENY` y  
  `Referrer-Policy: strict-origin-when-cross-origin`.  
  En entornos de producción puede habilitarse HSTS para forzar el uso de HTTPS.

- **Rate limiting:**  
  Se aplica limitación de peticiones por IP utilizando SlowAPI.  
  Los límites se definen por endpoint (registro, login, contacto, subida de archivos, flujo combinado, etc.) con el objetivo de mitigar abuso, ataques de fuerza bruta y uso excesivo de recursos.

- **Cookies:**  
  Los atributos de las cookies (Domain, Secure y SameSite) se configuran por entorno.  
  En producción se recomienda `Secure=true` y `SameSite=Strict` o `Lax`, siempre bajo HTTPS, para evitar exposición de sesión en contextos inseguros.

- **Documentación OpenAPI:**  
  En modo desarrollo se exponen los endpoints `/docs` y `/redoc` para facilitar pruebas e integración.  
  En producción pueden deshabilitarse mediante variable de entorno para evitar exponer la estructura interna de la API.

- **Documentación de gobierno técnico:**  
  Las reglas de ingeniería, seguridad, testing y despliegue se defieron previamente en el archivo `AGENTS.md` situado en la raíz del repositorio.  
  Este documento actúa como referencia técnica para mantener coherencia en la evolución del backend y cualquier aportación este enmarcada por determinadas reglas.  