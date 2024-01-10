from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from shop.models import Books
from order.models import Order,Cart


# Create your views here.

def add_to_cart(request, pk):
    item = get_object_or_404(Books, id = pk)
    if request.user.is_authenticated:
        order_qs = Order.objects.filter(user = request.user, ordered = False )
        order_item = Cart.objects.get_or_create(item = item,user = request.user, purchased = False)
    else:
        messages.warning(request, "Please log in to add items to your cart.")
        return redirect('/appuser/log-in')

    if order_qs.exists():
        order = order_qs[0]
        if order.orderitems.filter(item = item).exists():
            order_item[0].quantity += 1
            order_item[0].save()
            return redirect('/')
        else:
            order.orderitems.add(order_item[0])
            return redirect('/')
    else:
        order = Order(user = request.user)
        order.save()
        order.orderitems.add(order_item[0])
        return redirect('/')



@login_required(login_url='/appuser/log-in')
def car_view(request):
    carts= Cart.objects.filter(user = request.user,purchased = False)
    orders = Order.objects.filter(user = request.user,ordered = False )
    if carts.exists() and orders.exists():
        order = orders[0]
        context = {
            'carts':carts,
            'order':order
        }
        return render(request, 'order/cart.html',context)
    else:
        return redirect('/')


def increase_cart_item(request,pk):
    item = get_object_or_404(Books,pk=pk)
    order_qs = Order.objects.filter(user = request.user,ordered = False)
    if order_qs.exists():
        order = order_qs[0]
        if order.orderitems.filter(item=item).exists():
            order_items = Cart.objects.filter(item = item,user = request.user,purchased = False)[0]
            if order_items.quantity>=0:
                order_items.quantity +=1
                order_items.save()
                return redirect('order:cart-view')
        else:
            messages.success(request,f"{order_items} does not exists in yor cart")
            return redirect('order:cart-view')
    else:
        return redirect('/')

    
def decrease_cart_item(request,pk):
    item = get_object_or_404(Books,pk=pk)
    order_qs = Order.objects.filter(user = request.user,ordered = False)
    if order_qs.exists():
        order = order_qs[0]
        if order.orderitems.filter(item=item).exists():
            order_items = Cart.objects.filter(item = item,user = request.user,purchased = False)[0]
            if order_items.quantity>1:
                order_items.quantity -=1
                order_items.save()
                return redirect('order:cart-view')
            else:
                order.orderitems.remove(order_items)
                order_items.delete()
                messages.success(request,f"{order_items} removed from your cart")
                return redirect('order:cart-view')
        else:
            messages.success(request,f"{order_items} does not exists in yor cart")
            return redirect('order:cart-view')
    else:
        return redirect('/')




def remove_cart_item(request,pk):
    item = get_object_or_404(Books, pk = pk)
    orders = Order.objects.filter(user = request.user,ordered = False )
    if orders.exists():
        order = orders[0]
        if order.orderitems.filter(item = item).exists():
            order_item = Cart.objects.filter(item=item, user = request.user,purchased = False)[0]
            order.orderitems.remove(order_item)
            order_item.delete()
            messages.success(request,f"{order_item} removed from your cart")
            return redirect('order:cart-view')
        else:
            redirect('order:cart-view')
    else:
        return redirect('order:cart-view')

