# Standard library
import json
import os
import uuid
import traceback
from urllib.parse import quote_plus, unquote, urlencode

# Django core
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template import loader
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Third-party
from authlib.integrations.django_client import OAuth
from asgiref.sync import async_to_sync
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from auth0_ai_langchain import FGARetriever
from openfga_sdk.client.models import ClientBatchCheckItem

# Local app imports
from .forms import DocumentUploadForm
from .models import Document, AuditLog
from .services.chat_service import ChatService
from .services.embeddings import get_vector_store
from .services.fga_client import fga_service
from .services.search_service import search_documents
from webapp.helpers.read_documents import read_documents


embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
chat_service = ChatService()

@csrf_exempt
@require_http_methods(["GET", "POST"])
def chat_documents(request):
    email = request.user.email
    chat_history = request.session.get("chat_history", [])

    if request.method == "POST":
        
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                question = data.get("question", "").strip()
            except json.JSONDecodeError:
                return JsonResponse({"answer": "Invalid JSON."}, status=400)

            if not question:
                return JsonResponse({"answer": "No question provided—try again."}, status=400)

            try:
           
                answer, source_str, _ = chat_service.get_response(email, question, chat_history)

               
                chat_history.append({"role": "user", "content": question})
                chat_history.append({"role": "assistant", "content": f"{answer} {source_str}"})
                request.session["chat_history"] = chat_history[-20:]
                request.session.modified = True

                return JsonResponse({"answer": answer, "sources": source_str})

            except Exception as e:
                print(f"[CHAT] Error: {e}")
                import traceback
                traceback.print_exc()
                return JsonResponse({"answer": "Sorry, something went wrong. Try rephrasing!", "sources": ""}, status=500)

        else:
           
            question = request.POST.get("q", "").strip()
            if not question:
                chat_history.append({"role": "system", "content": "No question provided—try again."})
                request.session["chat_history"] = chat_history
                request.session.modified = True
                return render(request, "documents/chat.html", {"chat_history": chat_history})

           
            answer, source_str, _ = chat_service.get_response(email, question, chat_history)
            chat_history.append({"role": "user", "content": question})
            chat_history.append({"role": "assistant", "content": f"{answer} {source_str}"})
            request.session["chat_history"] = chat_history[-20:]
            request.session.modified = True
            return render(request, "documents/chat.html", {"chat_history": chat_history})

   
    return render(request, "documents/chat.html", {"chat_history": chat_history})

# @login_required
def documents(request):
    """
    Renders upload page (GET) and handles document upload (AJAX POST).
    """

    # documents = Document.objects.filter(user=request.user).order_by('-created_at')
    all_docs = Document.objects.all().order_by("-created_at")
    accessible_docs = [
        doc for doc in all_docs
        if fga_service.check_relation(request.user.email, doc.id, relation="viewer")
    ]

    return render(request, "documents/documents.html", {
      
        "documents": accessible_docs
    })

@login_required
def public_documents(request):
    """
    Renders only documents that are public (shared=True).
    """

    
    public_docs = Document.objects.filter(shared=True).order_by("-created_at")
    print(f"[PUBLIC DOCS] Found {public_docs.count()} shared documents.")

    # accessible_docs = [
    #     doc for doc in public_docs
    #     if fga_service.check_relation("user:*", doc.id, relation="viewer")
    # ]

    return render(request, "documents/public_documents.html", {
        "documents": public_docs
    })


@login_required
def upload_document(request):
    """
    Renders upload page (GET) and handles document upload (AJAX POST).
    """
    if request.method == "POST":
        try:
            form = DocumentUploadForm(request.POST, request.FILES)
            if form.is_valid():
                document = form.save(commit=False)
                document.user = request.user
                document.shared = form.cleaned_data.get("shared", False)
                document.save()
                print(f"[UPLOAD] File URL: {document.file.url}")

                # Add public access if shared
                if document.shared:
                    try:
                        fga_service.add_public_access(document.id)
                    except Exception as fga_err:
                        print(f"[FGA ERROR] {fga_err}")
                        return JsonResponse({
                            "success": False,
                            "message": f"Document uploaded but failed to update FGA: {fga_err}",
                            'file_url': document.file_url
                        }, status=500)

                return JsonResponse({
                    "success": True,
                    "message": "Document uploaded successfully!",
                    'file_url': document.file_url
                })

            else:
                return JsonResponse({
                    "success": False,
                    "message": "Invalid form submission.",
                    "errors": form.errors
                }, status=400)

        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            print(f"[UPLOAD ERROR] {traceback_str}")
            return JsonResponse({
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "trace": traceback_str
            }, status=500)

    # --- GET request: render the page ---
    form = DocumentUploadForm()
    return render(request, "documents/upload.html", {
        "form": form,
    })



@login_required
def share_document(request, doc_id):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")

        if not email:
            return JsonResponse({"success": False, "message": "Email is required."}, status=400)

        # Add FGA relation
        try:
            fga_service.add_relation(user_id=email, document_id=doc_id, relation="viewer")
            return JsonResponse({"success": True, "message": f"Document shared with {email}."})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
def serve_pdf(request, filepath):
    filepath = unquote(filepath)  # decode URL-encoded characters
    full_path = os.path.join(settings.MEDIA_ROOT, filepath)
    if os.path.exists(full_path):
        response = FileResponse(open(full_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(full_path)}"'
        response['X-Frame-Options'] = 'SAMEORIGIN'  # ✅ allow embedding
        return response
    else:
        raise Http404("File not found")
  


@login_required
def pdf_page(request, doc_id):
    """
    Render the PDF viewer page for a given document ID.
    """
    document = get_object_or_404(Document, id=doc_id)
    pdf_url = document.file.url  

    return render(request, "documents/pdf_view.html", {"pdf_url": pdf_url})

oauth = OAuth()

oauth.register(
    "auth0",
    client_id=settings.AUTH0_CLIENT_ID,
    client_secret=settings.AUTH0_CLIENT_SECRET,
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f"https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration",

)


def callback(request):
    token = oauth.auth0.authorize_access_token(request)
    user = auth.authenticate(request, token=token)
    if user:
        auth.login(request, user)
        return redirect (request.build_absolute_uri(reverse("dashboard_chat")))
    return HttpResponse("Could not authenticate user", status=400)
def login(request):
    return oauth.auth0.authorize_redirect(
        request,
        request.build_absolute_uri(reverse("callback")),
    )
def signup(request):
    return oauth.auth0.authorize_redirect(
        request,
        request.build_absolute_uri(reverse("callback")),
        screen_hint ="signup"
    )
def logout(request):
    request.session.clear()

    return redirect(
        f"https://{settings.AUTH0_DOMAIN}/v2/logout?"
        + urlencode(
            {
                "returnTo": request.build_absolute_uri(reverse("index")),
                "client_id": settings.AUTH0_CLIENT_ID,
            },
            quote_via=quote_plus,
        ),
    )

def index(request):
    template = loader.get_template('home/index.html')
    context = { }
    return HttpResponse(template.render(context, request))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def dashboard_chat(request):
    email = request.user.email
   
   
    chat_history = request.session.get("chat_history", [])

    if request.method == "POST":
      
        
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body)
                question = data.get("question", "").strip()
            except json.JSONDecodeError:
                return JsonResponse({"answer": "Invalid JSON."}, status=400)

            if not question:
                return JsonResponse({"answer": "No question provided—try again."}, status=400)

            try:
               
                answer, source_str, _ = chat_service.get_response(email, question, chat_history)

              
                chat_history.append({"role": "user", "content": question})
                chat_history.append({"role": "assistant", "content": f"{answer} {source_str}"})
                request.session["chat_history"] = chat_history[-20:]
                request.session.modified = True

                return JsonResponse({"answer": answer, "sources": source_str})

            except Exception as e:
                print(f"[CHAT] Error: {e}")
                import traceback
                traceback.print_exc()
                return JsonResponse({"answer": "Sorry, something went wrong. Try rephrasing!", "sources": ""}, status=500)

        else:
           
            question = request.POST.get("q", "").strip()
            if not question:
                chat_history.append({"role": "system", "content": "No question provided—try again."})
                request.session["chat_history"] = chat_history
                request.session.modified = True
                return render(request, "dashboard/index.html", {"chat_history": chat_history})

           
            answer, source_str, _ = chat_service.get_response(email, question, chat_history)
            chat_history.append({"role": "user", "content": question})
            chat_history.append({"role": "assistant", "content": f"{answer} {source_str}"})
            request.session["chat_history"] = chat_history[-20:]
            request.session.modified = True
            return render(request, "dashboard/index.html", {"chat_history": chat_history})

   
    return render(request, "dashboard/index.html", {"chat_history": chat_history})





@login_required
def user_audit_logs(request):
    """
    Render audit logs with document titles for the current user.
    """
    logs = AuditLog.objects.filter(user=request.user).order_by('-timestamp')
    logs_data = []

    for log in logs:
      
        documents = Document.objects.filter(id__in=log.document_ids)
        doc_info = [{"id": doc.id, "title": doc.title} for doc in documents]

        log_dict = {
            "timestamp": log.timestamp.isoformat(),
            "question": log.question,
            "documents": doc_info,  
            "agent_id": log.agent_id,
        }

        logs_data.append(log_dict)

    return render(request, "Logs/index.html", {"logs_data": logs_data})

def page_not_found_view(request, *args, **kwargs):
    template = loader.get_template('404.html')
    return HttpResponse(template.render(None, request))



