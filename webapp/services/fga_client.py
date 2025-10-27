
from openfga_sdk import ClientConfiguration
from openfga_sdk.sync import OpenFgaClient 
from openfga_sdk.credentials import Credentials, CredentialConfiguration
from openfga_sdk.client.models import ClientTuple, ClientWriteRequest, ClientCheckRequest
from django.conf import settings

class FGAService:
    def __init__(self):
        cfg = ClientConfiguration(
            api_url=settings.FGA_API_URL,
            store_id=settings.FGA_STORE_ID,
            authorization_model_id=settings.FGA_AUTHORIZATION_MODEL_ID,
            credentials=Credentials(
                method="client_credentials",
                configuration=CredentialConfiguration(
                    api_issuer=settings.FGA_API_TOKEN_ISSUER,
                    api_audience=settings.FGA_API_AUDIENCE,
                    client_id=settings.FGA_CLIENT_ID,
                    client_secret=settings.FGA_CLIENT_SECRET,
                ),
            ),
        )
        self.client = OpenFgaClient(cfg)  

    def add_public_access(self, document_id, relation="viewer"):
        """Allow anyone to view this document."""
        self.client.write(
            ClientWriteRequest(
                writes=[ClientTuple(
                     user="user:*",
                    relation=relation,
                    object=f"doc:{document_id}"
                )]
            )
        )
        print(f"[FGA] Document {document_id} is now public ({relation})")


    def add_relation(self, user_id: str, document_id: str, relation="owner"):
        """
        Adds a relation in OpenFGA. user_id can be request.user.id or email.
        document_id is Document.id
        """
        try:
            self.client.write(
                ClientWriteRequest(
                    writes=[ClientTuple(
                        user=f"user:{user_id}",
                        relation=relation,
                        object=f"doc:{document_id}"
                    )]
                )
            )
            print(f"[FGA] Successfully added {relation} for user:{user_id}, doc:{document_id}")
        except Exception as e:
          
            error_msg = str(e)
            if "400" in error_msg:
                print(f"[FGA] Invalid tuple error: {error_msg}. Check prefixes, relation '{relation}', or auth model.")
            else:
                print(f"[FGA] Unexpected error: {error_msg}")
            raise  

    def check_relation(self, user_id: str, document_id: str, relation="viewer") -> bool:
        """
        Checks if the user has a specific relation (e.g. 'viewer' or 'owner') with a document.
        Returns True or False.
        """
        try:
            response = self.client.check(
                ClientCheckRequest(
                    user=f"user:{user_id}",
                    relation=relation,
                    object=f"doc:{document_id}",
                )
            )
            allowed = response.allowed
            print(f"[FGA] Check → user:{user_id} relation:{relation} doc:{document_id} = {allowed}")
            return allowed
        except Exception as e:
            print(f"[FGA] Error during relation check: {e}")
            return False
fga_service = FGAService()