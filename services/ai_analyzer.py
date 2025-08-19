import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
# Importar la excepción específica para una mejor gestión de errores
from google.api_core import exceptions as google_exceptions
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.pydantic_v1 import BaseModel, Field
from .vector_store_manager import get_vector_store_retriever, get_mongo_collection
from langchain_core.output_parsers import StrOutputParser


def get_iso_controls_from_db() -> list:
    """
    Obtiene la lista completa de controles de la ISO 27001 desde la base de datos MongoDB.
    """
    try:
        controls_collection = get_mongo_collection("iso_27001_controls")
        # Proyectamos para excluir el _id de MongoDB y solo devolver id y description
        controls = list(controls_collection.find({}, {"_id": 0, "id": 1, "description": 1}))
        if not controls:
            print("ADVERTENCIA: La colección de controles 'iso_27001_controls' está vacía o no existe.")
            print("Por favor, ejecuta el script 'scripts/seed_database.py' para poblarla.")
            return []
        return controls
    except Exception as e:
        print(f"Error al obtener los controles de la base de datos: {e}")
        return []

# Definir la estructura de salida deseada con Pydantic para mayor robustez.
class ControlAnalysis(BaseModel):
    status: str = Field(description="Uno de: 'Covered', 'Partially Covered', 'Not Covered', 'Not Applicable'")
    justification: str = Field(description="Explicación concisa del razonamiento basado en el documento.")

def analyze_document_coverage(document_text: str, applicable_control_ids: list) -> list:
    """
    Analiza el texto de un documento contra los controles de la ISO 27001,
    considerando cuáles han sido marcados como aplicables por el usuario.
    """
    api_key = os.getenv("API_KEY_GEMINI")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        print("Error: La API Key de Gemini no está configurada.")
        return [{"error": "API Key no configurada."}]

    # Si no se pasaron IDs, se asume que todos son aplicables (comportamiento por defecto)
    all_applicable = not bool(applicable_control_ids)
    iso_controls = get_iso_controls_from_db()
    if not iso_controls:
        return [{"error": "No se pudieron cargar los controles de la ISO 27001 desde la base de datos. Ejecuta el script de inicialización 'scripts/seed_database.py'."}]

    try:
        # ACTUALIZACIÓN DEFINITIVA:
        # A petición del usuario, y como mejor práctica, cambiamos a un modelo más reciente y específico.
        # 'gemini-1.5-flash-latest' es rápido, potente y obliga a usar la API moderna,
        # lo que debería resolver el persistente error 'v1beta'.
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key, temperature=0)

        prompt_template = """
        Eres un experto auditor de ciberseguridad especializado en la norma ISO 27001:2022.
        Tu tarea es analizar el texto del documento proporcionado y determinar si cubre el control específico del Anexo A.

        DOCUMENTO: 
        ---
        {document_text}
        ---

        CONTROL A ANALIZAR:
        - ID: {control_id}
        - Descripción: {control_description}

        RESPONDE ÚNICAMENTE con un objeto JSON que se ajuste al siguiente esquema. No añadas texto antes o después del JSON.
        {format_instructions}
        """

        # Usar un parser de JSON para una salida estructurada y fiable.
        output_parser = JsonOutputParser(pydantic_object=ControlAnalysis)
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["document_text", "control_id", "control_description"],
            partial_variables={"format_instructions": output_parser.get_format_instructions()},
        )
        
        chain = prompt | llm | output_parser

        results = []
        for control in iso_controls:
            if all_applicable or control["id"] in applicable_control_ids:
                # Si el control es aplicable, se analiza con la IA
                analysis_result = chain.invoke({"document_text": document_text, "control_id": control["id"], "control_description": control["description"]})
                results.append({**control, **analysis_result})
            else:
                # Si no es aplicable, se marca como tal sin llamar a la IA
                results.append({
                    **control, 
                    "status": "Not Applicable", 
                    "justification": "Definido como no aplicable por el usuario en la Declaración de Aplicabilidad."})

        return results

    except google_exceptions.NotFound as e:
        # Capturamos el error específico 404 y devolvemos un mensaje claro.
        print(f"ERROR: Modelo de IA no encontrado. Esto suele ser un problema de versión de la librería. {e}")
        error_message = "El modelo 'gemini-pro' no fue encontrado. Esto indica un problema con las versiones de las librerías de IA. Por favor, sigue las instrucciones para actualizar las dependencias."
        return [{"error": error_message}]
    except Exception as e:
        # Capturamos cualquier otro error durante la llamada a la IA.
        print(f"Ha ocurrido un error inesperado durante el análisis de la IA: {e}")
        return [{"error": f"Error inesperado de la API: {e}"}]

def answer_question_with_rag(question: str, collection_name: str) -> str:
    """
    Responde una pregunta utilizando el contexto de un documento (RAG).
    """
    try:
        api_key = os.getenv("API_KEY_GEMINI")
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key, temperature=0.1)
        
        # 1. Obtener el retriever para la colección del documento específico
        retriever = get_vector_store_retriever(collection_name)

        # 2. Definir el prompt para el chat
        prompt_template = """
        Eres un asistente experto en la norma ISO 27001. Tu tarea es responder la pregunta del usuario basándote únicamente en el contexto proporcionado.
        Si el contexto no contiene la respuesta, di "La información no se encuentra en el documento proporcionado".
        Sé claro y conciso.

        CONTEXTO:
        {context}

        PREGUNTA:
        {question}

        RESPUESTA:
        """
        prompt = PromptTemplate.from_template(prompt_template)

        # 3. Construir la cadena RAG con LCEL
        rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        return rag_chain.invoke(question)
    except Exception as e:
        print(f"Error en la cadena RAG: {e}")
        return "Ocurrió un error al procesar tu pregunta. Por favor, inténtalo de nuevo."

def generate_policy_draft(control_id: str, control_description: str) -> str:
    """
    Genera un borrador de política para un control de la ISO 27001 no cubierto.
    """
    try:
        api_key = os.getenv("API_KEY_GEMINI")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY":
            print("Error: La API Key de Gemini no está configurada.")
            return "Error: La API Key de Gemini no está configurada. Por favor, configúrala en el fichero .env."

        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key, temperature=0.3)

        prompt_template = """
        Eres un consultor experto en ciberseguridad y la norma ISO 27001:2022.
        Tu tarea es redactar un borrador de una política o procedimiento básico para una organización que necesita cubrir un control específico del Anexo A.
        El borrador debe ser claro, conciso y práctico. Debe incluir un objetivo, un alcance y las principales directrices o responsabilidades.

        CONTROL A DESARROLLAR:
        - ID: {control_id}
        - Descripción: {control_description}

        Redacta un borrador de política para este control. La política debe ser un punto de partida que la organización pueda adaptar.
        No incluyas placeholders como "[Nombre de la Empresa]". Sé genérico.
        El formato de salida debe ser texto plano en Markdown.
        """
        prompt = PromptTemplate.from_template(prompt_template)

        chain = prompt | llm | StrOutputParser()

        return chain.invoke({"control_id": control_id, "control_description": control_description})
    except Exception as e:
        print(f"Error al generar el borrador de política: {e}")
        return "Ocurrió un error al generar el borrador. Por favor, revisa la consola para más detalles."

def identify_risks_for_control(control_id: str, control_description: str) -> str:
    """
    Identifica riesgos potenciales para un control de la ISO 27001 no implementado.
    """
    try:
        api_key = os.getenv("API_KEY_GEMINI")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY":
            print("Error: La API Key de Gemini no está configurada.")
            return "Error: La API Key de Gemini no está configurada."

        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key, temperature=0.5)

        prompt_template = """
        Eres un experto en gestión de riesgos de ciberseguridad y la norma ISO 27001:2022.
        Tu tarea es identificar y describir brevemente 2 o 3 riesgos comunes que una organización enfrentaría si NO implementara el siguiente control.

        CONTROL NO IMPLEMENTADO:
        - ID: {control_id}
        - Descripción: {control_description}

        Para cada riesgo, describe:
        1.  **Nombre del Riesgo:** Un título claro y conciso.
        2.  **Descripción:** Cómo podría materializarse el riesgo y cuál sería su impacto potencial en la confidencialidad, integridad y/o disponibilidad de la información.

        Formatea la salida en Markdown. Usa encabezados para cada riesgo.
        """
        prompt = PromptTemplate.from_template(prompt_template)

        chain = prompt | llm | StrOutputParser()

        return chain.invoke({"control_id": control_id, "control_description": control_description})
    except Exception as e:
        print(f"Error al identificar riesgos: {e}")
        return "Ocurrió un error al identificar los riesgos. Por favor, revisa la consola."