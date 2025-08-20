import os
import sys
from dotenv import load_dotenv

# Add project root to the Python path to allow for correct module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Load environment variables from .env file
dotenv_path = os.path.join(project_root, '.env')
print(f"DEBUG: Buscando el fichero .env en: {dotenv_path}")
if os.path.exists(dotenv_path):
    print("DEBUG: Fichero .env encontrado. Cargando variables...")
    load_dotenv(dotenv_path=dotenv_path)
else:
    print("ERROR: No se encontró el fichero de configuración '.env' en la raíz del proyecto. Abortando.")

# --- Imports after loading .env ---
import vertexai
from vertexai.generative_models import GenerativeModel
import google.auth

def test_connection():
    """
    A minimal script to test the direct connection to Vertex AI, bypassing LangChain.
    This helps isolate configuration vs. library issues.
    """
    # 1. Verificar si la variable de credenciales fue cargada
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    print(f"DEBUG: Valor leído para GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
    if not creds_path:
        print("ERROR: La variable GOOGLE_APPLICATION_CREDENTIALS no está configurada o no se pudo leer del fichero .env.")
        return

    # 2. Verificar si la ruta del fichero de credenciales existe
    print(f"DEBUG: Verificando si la ruta de credenciales existe: '{creds_path}'")
    path_exists = os.path.exists(creds_path)
    print(f"DEBUG: ¿La ruta existe? -> {path_exists}")
    if not path_exists:
        print("ERROR: La ruta especificada en GOOGLE_APPLICATION_CREDENTIALS no existe.")
        print("CAUSA COMÚN: El uso de comillas o barras invertidas incorrectas en el fichero .env.")
        print("SOLUCIÓN RECOMENDADA: Usa barras inclinadas (/) y no uses comillas en la ruta. Ej: RUTA=C:/Users/Tu/proyecto/secrets/file.json")
        return    
    print("DEBUG: La ruta de credenciales existe.")

    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    location = os.getenv('GOOGLE_CLOUD_LOCATION')

    # Verificación más específica de las variables de entorno
    missing_vars = []
    if not project_id:
        missing_vars.append("GOOGLE_CLOUD_PROJECT")
    if not location:
        missing_vars.append("GOOGLE_CLOUD_LOCATION")

    if missing_vars:
        print(f"ERROR: Las siguientes variables de entorno no están configuradas en el fichero .env: {', '.join(missing_vars)}")
        return

    print("--- Iniciando prueba de conexión directa a Vertex AI ---")
    print(f"Proyecto: {project_id}")
    print(f"Ubicación: {location}")

    try:
        # 1. Initialize Vertex AI SDK
        vertexai.init(project=project_id, location=location)
        print("SDK de Vertex AI inicializado correctamente.")

        # 2. Instantiate a model
        # Usamos el modelo definido en las variables de entorno para consistencia.
        model_name = os.getenv('GEMINI_MODEL_NAME', 'gemini-2.5-flash')
        model = GenerativeModel(model_name)
        print(f"Instancia del modelo '{model_name}' creada.")

        # 3. Make a simple API call
        prompt = "Dime 'hola mundo' en español."
        print(f"Enviando prompt: '{prompt}'")
        response = model.generate_content(prompt)
        
        print("\n--- ¡ÉXITO! ---")
        print("La conexión directa a Vertex AI funciona.")
        print(f"Respuesta del modelo: {response.text.strip()}")
        print("\nEsto significa que el problema reside en la capa de LangChain o su configuración, no en el acceso a GCP.")

    except Exception as e:
        print("\n--- FALLO EN LA CONEXIÓN DIRECTA ---")
        print(f"Se ha producido un error: {e}")
        print("\nSi este script falla, el problema está 100% en la configuración de tu proyecto en Google Cloud.")
        print("Revisa de nuevo: API de Vertex AI habilitada, facturación vinculada y que la cuenta de servicio tenga el rol 'Usuario de Vertex AI' en la página de IAM.")

if __name__ == "__main__":
    test_connection()