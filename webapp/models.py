# webapp/models.py
from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField
from nanoid import generate
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from cloudinary_storage.storage import RawMediaCloudinaryStorage

def nanoid_default():
    return generate()


class Document(models.Model):
    id = models.CharField(primary_key=True, max_length=191, default=nanoid_default)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploads/", storage=RawMediaCloudinaryStorage(resource_type='raw'), validators=[FileExtensionValidator(['pdf'])])
    file_type = models.CharField(max_length=50, blank=True, default='pdf')
    shared = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.title} ({self.id})"
    @property
    def file_url(self):
        if self.file:
            return self.file.url  
        return None


class Embedding(models.Model):
    id = models.CharField(primary_key=True, max_length=191, default=nanoid_default)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="embeddings")
    content = models.TextField()
    metadata = models.JSONField(default=dict)
    embedding = VectorField(dimensions=1536)

    def __str__(self):
        return f"Embedding {self.id} for doc {self.document_id}"
    


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    question = models.TextField()
    document_ids = models.JSONField(default=list)  
    agent_id = models.CharField(max_length=100, default="default_chat_agent") 

    def __str__(self):
        return f"{self.user.email} asked '{self.question}' at {self.timestamp}"
    
