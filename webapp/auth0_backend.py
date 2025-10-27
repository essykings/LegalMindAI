from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

class Auth0Backend(BaseBackend):
    """
    Custom Auth0 authentication backend.
   """

    def authenticate(self, request, token=None):
        if not token:
            return None

        
        user_info = token.get('userinfo', {})
        auth0_id = user_info.get('sub')
        if not auth0_id:
            raise ValueError("Auth0 user ID ('sub') is missing!")

      
        username = auth0_id.replace('|', '_')

       
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': user_info.get('email'),
                'first_name': user_info.get('name', '')
            }
        )


       
        request.session['id_token'] = token.get('id_token')
        request.session['access_token'] = token.get('access_token')
        request.session['refresh_token'] = token.get('refresh_token')

        return user

    def get_user(self, user_id):
        """
        Retrieves a user by primary key.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
