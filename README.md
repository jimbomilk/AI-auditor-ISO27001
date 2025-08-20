IA-Auditor ISO 27001 (POC) 🚀
Descripción
IA-Auditor ISO 27001 es un Proof of Concept (POC) para una herramienta de auditoría asistida por Inteligencia Artificial. El objetivo de este proyecto es demostrar la viabilidad de utilizar un modelo de lenguaje grande (LLM) para analizar la documentación de una organización y realizar un análisis de brechas (gap analysis) contra los controles de la norma ISO/IEC 27001:2022.

Este sistema ayuda a los auditores y consultores a acelerar el proceso de certificación, identificar rápidamente las no conformidades y obtener recomendaciones para la mejora del Sistema de Gestión de Seguridad de la Información (SGSI).

Características Principales (Alcance del POC)
Carga de Documentos: Permite al usuario subir políticas, procedimientos y otros documentos relevantes en formato PDF o DOCX.

**Declaración de Aplicabilidad (SoA) Simulada:** Antes del análisis, el usuario puede seleccionar qué controles del Anexo A son aplicables a su organización, alineando el POC con el enfoque basado en riesgos de la norma.

Análisis de Cobertura de Controles: La IA analiza los documentos para determinar qué controles del Anexo A de la ISO 27001 están cubiertos.

Chat Interactivo (Q&A): Un asistente conversacional que responde preguntas específicas sobre la norma y su aplicación en los documentos proporcionados. Por ejemplo: "¿Mi política de control de acceso cumple con el control A.5.15?".

Generación de Informe de Brechas: Produce un informe básico que lista los controles no cubiertos o parcialmente cubiertos, junto con sugerencias iniciales.

Arquitectura Propuesta
Este POC utiliza una arquitectura monolítica simplificada, ideal para un desarrollo rápido.

Aplicación Web (Frontend + Backend): Una aplicación web desarrollada con Python y el microframework Flask. Se encarga de:

Renderizar la interfaz de usuario utilizando plantillas Jinja2.

Proveer una API REST para las interacciones con el módulo de IA.

Módulo de IA: Orquestado con LangChain, utilizando la API de Google Gemini para la generación de lenguaje y **MongoDB Atlas Vector Search** para el mecanismo de Retrieval-Augmented Generation (RAG).

Stack Tecnológico
Aplicación Web: Python, Flask, Jinja2, Tailwind CSS

Base de Datos Vectorial: MongoDB Atlas Vector Search

IA & NLP: LangChain, Google Gemini API, SentenceTransformers

Contenerización: Docker (opcional para el POC)

Instalación y Puesta en Marcha
Clonar el repositorio:

git clone https://github.com/tu_usuario/ia-auditor-iso27001.git
cd ia-auditor-iso27001

Configurar y Ejecutar la Aplicación:

```bash
# Navegar a la carpeta del proyecto
python -m venv venv
source venv/bin/activate # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuración de Google Cloud y Vertex AI

Para que la aplicación pueda comunicarse con la IA, necesitas configurar la autenticación con Google Cloud.

1.  **Crea o selecciona un proyecto** en la Consola de Google Cloud.
2.  **Habilita la API de Vertex AI** para tu proyecto.
3.  **Habilita la Facturación** para tu proyecto. **(¡Paso crucial!)** Aunque estés en el nivel gratuito, es un requisito indispensable para que las APIs de Vertex AI funcionen.
4.  **Crea una Cuenta de Servicio (Service Account)**:
    *   Ve a `IAM y Administración` > `Cuentas de servicio`.
    *   Crea una nueva cuenta de servicio (ej. `ai-auditor-app`).
    *   Asígnale el rol de **`Usuario de Vertex AI`** (`Vertex AI User`).
5.  **Genera una clave JSON**:
    *   Dentro de la cuenta de servicio, ve a la pestaña `Claves`.
    *   Crea una nueva clave de tipo `JSON`. Se descargará un fichero.
    *   Guarda este fichero en un lugar seguro dentro del proyecto (ej. en una carpeta `secrets/` que ya está en el `.gitignore`).

### Configuración del fichero .env

Copia el fichero `.env.example` a `.env` y actualízalo con la siguiente información:

```
# Ruta absoluta al fichero de credenciales JSON que descargaste.
# Ejemplo en Windows: GOOGLE_APPLICATION_CREDENTIALS='C:\ruta\a\tu\proyecto\secrets\credenciales.json'
# Ejemplo en Linux/macOS: GOOGLE_APPLICATION_CREDENTIALS='/home/usuario/proyecto/secrets/credenciales.json'
GOOGLE_APPLICATION_CREDENTIALS="RUTA_A_TU_FICHERO_DE_CREDENCIALES.json"

# ID de tu proyecto de Google Cloud
GOOGLE_CLOUD_PROJECT="tu-id-de-proyecto-gcp"

# Región de Google Cloud (ej. 'us-central1')
GOOGLE_CLOUD_LOCATION="us-central1"

# Nombre del modelo de IA a utilizar (ej. 'gemini-1.5-pro-latest')
GEMINI_MODEL_NAME="gemini-1.5-pro-latest"

# Cadena de conexión a tu clúster de MongoDB Atlas
MONGO_URI="TU_CADENA_DE_CONEXION_A_MONGODB_ATLAS"

# Clave secreta para las sesiones de Flask
SECRET_KEY="GENERAR_UNA_CLAVE_SECRETA_ALEATORIA"
```

### Configuración de MongoDB Atlas Vector Search

Este proyecto requiere un clúster de MongoDB Atlas con un índice de búsqueda vectorial.

1.  Crea una base de datos llamada `ia_auditor_db`.
2.  Dentro de esa base de datos, el sistema creará colecciones dinámicamente con el nombre de los ficheros que subas.
3.  Ve a la pestaña "Vector Search" de tu clúster y crea un nuevo índice.
4.  Selecciona la base de datos `ia_auditor_db` y la colección en la que quieras probar (o crea una colección de prueba, por ejemplo `test`). El nombre del índice debe ser `default`.
5.  Usa el editor JSON para configurar el índice con la siguiente definición, que coincide con el modelo de embeddings `all-MiniLM-L6-v2` (384 dimensiones):

```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": { "type": "vector", "dimensions": 384, "similarity": "cosine" }
    }
  }
}
```

flask run

¡Accede a http://127.0.0.1:5000 en tu navegador!

Uso (Ejemplo de Flujo)
Abre la aplicación web.
Sube tu "Política de Seguridad de la Información" en formato PDF.
El sistema te llevará a la pantalla de "Declaración de Aplicabilidad".
Selecciona los controles que consideres relevantes para tu organización.
Haz clic en "Continuar y Analizar Documento".
El sistema procesará el documento y mostrará el informe de cobertura, marcando como "No Aplicable" los controles que deseleccionaste.
Utiliza el chat para preguntar: "¿Qué evidencia necesito para el control A.8.1 sobre los activos de la organización?".
La IA te proporcionará una respuesta basada en la norma y en el contenido de tu política.

Próximos Pasos (Más allá del POC)
[ ] Integración con sistemas como Jira o Confluence para la recolección automática de evidencias.

[x] Generación automática de borradores de políticas y procedimientos faltantes.

[ ] Módulo de gestión de riesgos para ayudar en la evaluación y tratamiento de riesgos.

[ ] Dashboard avanzado con métricas de madurez del SGSI.

### Troubleshooting

**Error `404 Publisher Model ... was not found` persistente**

Si has verificado todos los pasos de configuración (API habilitada, cuenta de servicio con rol correcto, facturación activa) y sigues recibiendo un error 404, puede haber un problema en la capa de LangChain. Para diagnosticarlo, puedes ejecutar un script de prueba de conexión directa:

```bash
# Asegúrate de que tu entorno virtual está activado
python scripts/test_vertex_connection.py
```

*   Si este script **funciona**, el problema está en cómo LangChain interactúa con la API.
*   Si este script **falla**, el problema está definitivamente en la configuración de tu proyecto de Google Cloud, y debes revisar cada uno de los pasos de configuración de nuevo.