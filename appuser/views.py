from django.shortcuts import render,redirect
from django.contrib import messages
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from core.models import User
from .models import Customer

from django.contrib.auth.views import PasswordResetView,PasswordResetDoneView,PasswordResetConfirmView,PasswordResetCompleteView
from django.urls import reverse_lazy

# Create your views here.


class PasswordResetViewSet(PasswordResetView):
    email_template_name = "appuser/registration/password_reset_email.html"
    template_name = "appuser/registration/password_reset_form.html"
    success_url = reverse_lazy("appuser:password_reset_done")

class PasswordResetDoneViewSet(PasswordResetDoneView): 
    template_name = "appuser/registration/password_reset_done.html"


class PasswordResetConfirmViewSet(PasswordResetConfirmView):
    template_name = "appuser/registration/password_reset_confirm.html"
    success_url = reverse_lazy("appuser:password_reset_complete")

class PasswordResetCompleteViewSet(PasswordResetCompleteView):
    template_name = "appuser/registration/password_reset_complete.html"













def register(request):
    if request.method == "POST":
        email = request.POST["email"]
        username = request.POST["username"]
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]
        
        if password == confirm_password:
            if User.objects.filter(username = username).exists():
                messages.warning(request,'Username is Alrady Exist')
                return redirect('/appuser/register')
            if User.objects.filter(email = email).exists():
                messages.warning(request,'Email is Alrady Exist')
                return redirect('/appuser/register')
            else:
                user = User.objects.create_user(
                    username = username,
                    password = password,
                    email = email
                    )
                user.set_password(password)
                user.save()
                return redirect('/appuser/log-in')
        else:
            messages.warning(request,'Password Do not Match')
            return redirect('/appuser/register')
    return render(request,'appuser/register.html')
            

def log_in(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = auth.authenticate(username = username, password = password)
        if user is not None:
            auth.login(request,user)
            return redirect('/')
        else:
            messages.warning(request,"Invalid Username And Password")
            return redirect('/appuser/log-in')
    return render(request,'appuser/login.html')



def log_out(request):
    auth.logout(request)
    return redirect('/')


@login_required(login_url='/appuser/log-in')
def user_info(request):
    user = request.user
    customer = Customer.objects.filter(user_id=user.id).first()
    context = {'user': user, 'customer': customer}
    return render(request, 'appuser/userinfo.html',context)


@login_required(login_url='/appuser/log-in')
def update_user_info(request):
    user = request.user
    customer = Customer.objects.filter(user_id=user.id).first()
    context = {'user': user, 'customer': customer}

    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        full_name = f'{first_name} {last_name}'
        address = request.POST['address']
        country = request.POST['country']
        city = request.POST['city']
        zipcode = request.POST['zipcode']
        phone = request.POST['phone']
        date_of_birth = request.POST['date_of_birth']
        print(date_of_birth)

        # Update the User instance for the current user
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        # Update the Customer instance for the current user
        if customer:
            customer.full_name = full_name
            customer.address = address
            customer.country = country
            customer.city = city
            customer.zipcode = zipcode
            customer.phone = phone
            customer.date_of_birth = date_of_birth
            customer.save()
        else:
            Customer.objects.create(
                user_id=user.id,
                full_name =full_name,
                address=address,
                country=country,
                city=city,
                zipcode=zipcode, 
                phone = phone,
                date_of_birth = date_of_birth
                )
        return redirect('appuser:user-info')
    return render(request, 'appuser/update_user_info.html', context)



def registration_error(request):
    return  render(request,'appuser/registration_error.html')



