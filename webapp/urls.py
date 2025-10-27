from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard_chat, name='dashboard_chat'),
    path('django-admin', admin.site.urls),
    path('callback', views.callback, name='callback'),

    path('chat/', views.chat_documents, name='chat_documents'),
    path('public/', views.public_documents, name='public_documents'),
    path('documents/', views.documents, name='documents'),
    path('logs/', views.user_audit_logs, name='user_audit_logs'),

    path('documents/upload/', views.upload_document, name='upload_document'),
    
    path('pdf-page/<str:doc_id>/', views.pdf_page, name='pdf_page'),
    path('documents/<str:doc_id>/share/', views.share_document, name='share_document'),

    path('login', views.login, name='login'),
    path('signup', views.signup, name='signup'),
    path('logout', views.logout, name='logout'),
]

handler404 = views.page_not_found_view

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
