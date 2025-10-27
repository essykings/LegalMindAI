# webapp/services/chat_service.py

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from asgiref.sync import async_to_sync
from .embeddings import get_vector_store
from auth0_ai_langchain import FGARetriever
from openfga_sdk.client.models import ClientBatchCheckItem
from ..models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)

        
        prompt_template = """
        You are an AI assistant specialized in answering questions about private legal and corporate documents. 
        Your responses should:

        1. Be concise, factual, and based only on the provided documents (context).
        2. Respect data privacy: do not invent or speculate about documents not included in the context.
        3. Reference prior chat messages when needed to maintain coherent conversation.
        4. Clearly indicate if the information is not available in the provided documents: 
        use the phrase "I don't have details on that from your documents."
        5. Limit answers to relevant sections; avoid unnecessary commentary.

        Chat History:
        {chat_history}

        Context (from authorized documents only):
        {context}

        User Question:
        {question}

        Answer:
        """

        self.PROMPT = PromptTemplate(
            input_variables=["chat_history", "context", "question"],
            template=prompt_template,
        )

    def _build_retriever(self, email: str):
        """Build FGA-filtered retriever."""
        vector_store = async_to_sync(get_vector_store)()
        if not vector_store:
            raise ValueError("No vector store available.")
        
        base_retriever = vector_store.as_retriever(search_kwargs={"k": 4})
        return FGARetriever(
            retriever=base_retriever,
            build_query=lambda doc: ClientBatchCheckItem(
                user=f"user:{email}",
                object=f"doc:{doc.metadata.get('document_id')}",
                relation="viewer",
            ),
        )

    def get_response(self, email: str, question: str, history: List[Dict[str, Any]]) -> tuple[str, str, List[Dict[str, Any]]]:
        """
        Generate chat response.
        :param email: User email for FGA checks.
        :param question: Current question.
        :param history: List of message dicts from session.
        :return: (answer, sources_str, updated_history)
        """
        try:
            
            from langchain.schema import HumanMessage, AIMessage

            
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            if history:
                
                messages = []
                for msg in history:
                    if msg.get('role') == 'user':  
                        messages.append(HumanMessage(content=msg['content']))
                    elif msg.get('role') == 'assistant':
                        messages.append(AIMessage(content=msg['content']))
                memory.chat_memory.add_messages(messages)

        
            retriever = self._build_retriever(email)
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=memory,
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": self.PROMPT},
                verbose=False,
            )

        
            result = qa_chain({"question": question})
            answer = result["answer"].strip()

            
            updated_history = memory.chat_memory.messages


            
            source_docs = result.get("source_documents", [])
            print(f"[CHAT SERVICE] Retrieved {len(source_docs)} documents for user {email}:")
            for doc in source_docs:
                doc_id = doc.metadata.get("document_id", "Unknown")
                title = doc.metadata.get("title", "No title")
                # print(f" - Doc ID: {doc_id}, Title: {title}")

            
            source_docs = result.get("source_documents", [])
            sources = list(set(doc.metadata.get("document_id", "Unknown") for doc in source_docs))
            source_str = f"Sources: {', '.join(sources)}" if sources else ""
            try:
                user_obj = User.objects.get(email=email)
                AuditLog.objects.create(
                    user=user_obj,
                    question=question,
                    document_ids=sources, 
                    agent_id="query agent"  
                    
                )
                # print(f"[AUDIT LOG] Logged query for user {email} with docs: {sources}")
            except Exception as e:
                print(f"[AUDIT LOG] Failed to log query: {e}")



            
            history_dicts = []
            for msg in updated_history:
                history_dicts.append({
                    "role": "user" if isinstance(msg, HumanMessage) else "assistant",                  "content": msg.content
                })

            return answer, source_str, history_dicts

        except Exception as e:
            print(f"[CHAT SERVICE] Error: {e}")
            import traceback
            traceback.print_exc()
            return "Sorry, something went wrong. Try rephrasing!", "", history  