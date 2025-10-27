# LegalMind AI - Document Chat System

An intelligent document management system focused on legal documents, allowing users to securely upload, share, and query documents using AI. Built for the Auth0 for AI Agents Challenge, demonstrating secure AI agent authentication, authorization, and RAG pipelines.

---

## 🚀 Features

1. **User Authentication**
   - Secure login using Auth0.
   - Session management with encrypted cookies.

2. **Document Management**
   - Upload private or public documents (PDFs).
   - Share documents with specific users.
   - Public documents are accessible to all new users.

3. **AI-Powered Chat**
   - Ask questions about uploaded documents.
   - Answers generated using OpenAI models (GPT-3.5/4) with context from authorized documents.
   - Responses include citations of source documents.

4. **Audit Logging**
   - Every AI query is logged with:
     - Timestamp
     - Question asked
     - Documents used
     - User/agent ID

5. **Role-Based Permissions**
   - All users can upload and query documents.
   - Private documents are visible only to the owner.
   - Shared documents are accessible by selected users.

---

##  Tech Stack

- **Framework:** Django 5
- **Authentication:** Auth0
- **AI Model:** OpenAI 
- **Database:** PostgreSQL
- **File Storage:** Cloudinary
- **Frontend:** Bootstrap 5 and Django
- **Vector Store / Embeddings:** LangChain

---


## Outcome

- **User Authentication:** Secure authentication via Auth0.
- **RAG Authorization:** Fine-grained access control for AI queries.
- **Role-Based Access Control:** Users can only see or query documents they have access to.
- **Audit Trail:** Full logging of all AI queries and document access.

---

git clone <repository-url>
cd legalmind-ai
