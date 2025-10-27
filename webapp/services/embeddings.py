# webapp/embeddings.py
import warnings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVectorStore, PGEngine
import os
import urllib.parse
from webapp.models import Embedding
import requests
import tempfile

warnings.filterwarnings("ignore", category=DeprecationWarning)


EMBEDDING_MODEL = OpenAIEmbeddings(
    model="text-embedding-3-small"
   
)

vector_store: PGVectorStore | None = None


def store_document_embeddings(document_instance):
    """
    Load PDF, split into chunks, generate embeddings, store in Embedding model.
    """
    pdf_url = document_instance.file_url
    if not pdf_url:
        raise ValueError("Document has no Cloudinary URL")
    
    response = requests.get(pdf_url)
    response.raise_for_status()

     
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(response.content)
        tmp.flush()

        
        loader = PyPDFLoader(tmp.name)
        documents = loader.load()
    
    

    
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(documents)

    
    for chunk in chunks:
        vector = EMBEDDING_MODEL.embed_query(chunk.page_content)
        Embedding.objects.create(
            document=document_instance,
            content=chunk.page_content,
            embedding=vector,
            metadata={
                "document_id": str(document_instance.id),
                "file_name": document_instance.file.name
            },
        )


async def get_vector_store():
    """
    Return a singleton PGVectorStore instance for similarity search.
    """
    global vector_store
    if vector_store is not None:
        return vector_store
    
    def get_database_url():
        DB_NAME = os.getenv("DB_NAME")
        DB_USER = os.getenv("DB_USER")
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        DB_HOST = os.getenv("DB_HOST", "127.0.0.1")  
        DB_PORT = os.getenv("DB_PORT", "5432")
        encoded_user = urllib.parse.quote_plus(DB_USER)
        encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
        
        url = f"postgresql+asyncpg://{encoded_user}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
    
        print(f"[DEBUG] Encoded DB URL: {url}")
        import socket
        try:
            socket.getaddrinfo(DB_HOST, int(DB_PORT))
            print(f"[DEBUG] Host '{DB_HOST}:{DB_PORT}' resolves OK")
        except socket.gaierror as e:
            print(f"[ERROR] Host resolution failed: {e} — Check {DB_HOST}")
            raise
        
        return url

    pg_engine = PGEngine.from_connection_string(get_database_url())

    vector_store = await PGVectorStore.create(
        engine=pg_engine,
        table_name="webapp_embedding",  
        embedding_service=EMBEDDING_MODEL,
        id_column="id",
        embedding_column="embedding",
        content_column="content",
        metadata_json_column="metadata",
    )

    return vector_store
