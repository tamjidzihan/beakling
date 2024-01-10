from django.contrib.auth.forms import UserCreationForm
from core.models import User

class CreateUserFrom(UserCreationForm):

    class Meta:

        model = User
        fields = ["username", "password1", "password2","first_name","last_name","email"]