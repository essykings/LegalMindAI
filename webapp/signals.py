# webapp/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from webapp.models import Document
from webapp.services.fga_client import fga_service
from .services.embeddings import store_document_embeddings

@receiver(post_save, sender=Document)
def on_document_created(sender, instance: Document, created, **kwargs):
    if created:
        user = instance.user.email
        if user:
            
            try:
                fga_service.add_relation(user, instance.id, relation="owner")
                print(f"Added FGA owner tuple for user:{user}, doc:{instance.id}")
            except Exception as e:
                print("Error adding FGA tuple:", e)

        
            try:
                store_document_embeddings(instance)
                print(f"Stored embeddings for doc:{instance.id}")
            except Exception as e:
                print("Error storing embeddings:", e)
