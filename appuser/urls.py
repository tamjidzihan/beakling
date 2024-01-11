from django.urls import path
from . import views

app_name = 'appuser'

urlpatterns = [
    path('register',views.register,name="register"),
    path('log-in',views.log_in,name="log-in"),
    path('log-out',views.log_out,name="log-out"),
    path('registration-error/',views.registration_error,name='registration-error'),

    path('user-info',views.user_info,name="user-info"),
    path('update-user-info',views.update_user_info,name="update-user-info"),

    #reset password
    path('password_reset_new/',views.PasswordResetViewSet.as_view(),name='password_reset'), #customviewset
    path('password_reset/done/',views.PasswordResetDoneViewSet.as_view(),name='password_reset_done'), #customviewset
    path('reset/<uidb64>/<token>/',views.PasswordResetConfirmViewSet.as_view(),name='password_reset_confirm'),
    path('reset/done/',views.PasswordResetCompleteViewSet.as_view(),name='password_reset_complete'),
]