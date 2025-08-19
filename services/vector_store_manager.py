import os
from pymongo import MongoClient
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DB_NAME = "ia_auditor_db"
# Modelo de embeddings que usaremos. 'all-MiniLM-L6-v2' es rápido y eficaz.
# Es importante que el número de dimensiones coincida con el índice de Atlas (384 para este modelo).
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)

def get_mongo_collection(collection_name: str):
    """Obtiene una colección de la base de datos MongoDB."""
    # Obtenemos la URI desde las variables de entorno aquí, para asegurar
    # que .env ya ha sido cargado por el script o la app que llama.
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("La variable de entorno MONGO_URI no está configurada.")
    
    try:
        client = MongoClient(mongo_uri)
        # La siguiente línea fuerza una conexión al servidor para verificar las credenciales.
        # Es el método estándar para confirmar que la conexión es válida.
        client.admin.command('ping')
        print("Conexión a MongoDB Atlas exitosa.")
    except Exception as e:
        print(f"ERROR FATAL al conectar con MongoDB Atlas: {e}")
        # Relanzamos la excepción para que el error se propague y se muestre en la UI.
        raise e

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