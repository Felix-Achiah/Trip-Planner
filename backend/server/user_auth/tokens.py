from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        
        # Add user details to the token payload
        token['email'] = user.email
        token['first_name'] = user.first_name or ''
        token['last_name'] = user.last_name or ''

        return token

def create_jwt_pair_for_user(user: User):
    refresh = CustomRefreshToken.for_user(user)

    token = {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'user_id': str(user.id),
    }

    return token
