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
