from .embeddings import get_vector_store
from auth0_ai_langchain import FGARetriever
from openfga_sdk.client.models import ClientBatchCheckItem
from asgiref.sync import async_to_sync

@async_to_sync
async def search_documents(user_email,query):
    vector_store = await get_vector_store()
    if not vector_store:
        return []

    
    retriever = FGARetriever(
        retriever=vector_store.as_retriever(),
        build_query=lambda doc: ClientBatchCheckItem(
            user=f"user:{user_email}",
            object=f"doc:{doc.metadata.get('document_id')}",
            relation="can_view",
        ),
    )

    results = retriever.invoke(query)
    print(f"Search results: {results}")
    return [doc.page_content for doc in results]