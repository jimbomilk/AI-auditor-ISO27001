import os
from pymongo import MongoClient
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import MongoDBAtlasVectorSearch

DB_NAME = "ia_auditor_db"
# Modelo de embeddings que usaremos. 'all-MiniLM-L6-v2' es rápido y eficaz.
# Es importante que el número de dimensiones coincida con el índice de Atlas (384 para este modelo).
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

# Se utiliza la clase recomendada y actualizada de langchain-huggingface.
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

# --- Refactorización: Cliente de MongoDB Singleton ---
# Se crea una única instancia del cliente de MongoDB para ser reutilizada en toda la aplicación.
# Esto evita crear una nueva conexión a la base de datos en cada petición, mejorando el rendimiento.
_mongo_client = None

def _get_mongo_client():
    """Inicializa y devuelve una instancia singleton del cliente de MongoDB."""
    global _mongo_client
    if _mongo_client is None:
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("La variable de entorno MONGO_URI no está configurada.")
        
        try:
            print("Creando nueva conexión a MongoDB Atlas...")
            _mongo_client = MongoClient(mongo_uri)
            # La siguiente línea fuerza una conexión al servidor para verificar las credenciales.
            _mongo_client.admin.command('ping')
            print("Conexión a MongoDB Atlas exitosa.")
        except Exception as e:
            print(f"ERROR FATAL al conectar con MongoDB Atlas: {e}")
            raise e # Relanzar para que el error se propague
    return _mongo_client

def get_mongo_collection(collection_name: str):
    """Obtiene una colección de la base de datos MongoDB."""
    client = _get_mongo_client()
    db = client[DB_NAME]
    return db[collection_name]

def create_vector_store(document_text: str, collection_name: str):
    """
    Divide el texto, crea embeddings y los almacena en MongoDB Atlas.
    Borra los documentos antiguos de la colección para mantenerla actualizada.
    """
    collection = get_mongo_collection(collection_name)
    
    # Borrar datos antiguos para este documento para evitar duplicados
    collection.delete_many({})

    # Dividir el documento en trozos (chunks) manejables
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs = text_splitter.split_text(document_text)

    # Crear la base de datos vectorial y almacenar los documentos y sus embeddings
    MongoDBAtlasVectorSearch.from_texts(
        texts=docs,
        embedding=embeddings,
        collection=collection,
        index_name="default" # Este es el nombre del índice que crearemos en Atlas
    )
    print(f"Base de datos vectorial creada/actualizada para la colección '{collection_name}' con {len(docs)} fragmentos.")

def get_vector_store_retriever(collection_name: str):
    """Obtiene un retriever para hacer búsquedas de similitud en la base de datos vectorial."""
    collection = get_mongo_collection(collection_name)
    vector_store = MongoDBAtlasVectorSearch(collection, embeddings, index_name="default")
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})