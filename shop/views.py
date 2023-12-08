from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Category, Product,Events

def index(request):
    featured_product = Product.objects.filter(featureproduct=True).first()
    recently_updated_books = Product.objects.filter().order_by('-updated')[:3]
    upcoming_events = Events.objects.filter(
        event_name=Events.DEAL_OF_THE_WEEK,
        event_time__gt=timezone.now()
        ).order_by('event_time')

    countdown_data = []
    for event in upcoming_events:
        time_remaining = event.event_time - timezone.now()
        days, seconds = divmod(time_remaining.total_seconds(), 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        
        countdown_data.append({
            'event_name': event.get_event_name_display(),
            'days': int(days),
            'hours': int(hours),
            'minutes': int(minutes),
        })

    context = {'featured_product': featured_product,'recently_updated_books': recently_updated_books,'countdown_data': countdown_data}
    return render(request, 'shop/product/home.html', context )

def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available = True)
    featured_product = Product.objects.filter(featureproduct=True).first()
    upcoming_events = Events.objects.filter(
        event_name=Events.FLASH_SALE,
        event_time__gt=timezone.now()
        ).order_by('event_time')

    countdown_data = []
    for event in upcoming_events:
        time_remaining = event.event_time - timezone.now()
        days, seconds = divmod(time_remaining.total_seconds(), 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        
        countdown_data.append({
            'event_name': event.get_event_name_display(),
            'days': int(days),
            'hours': int(hours),
            'minutes': int(minutes),
        })

    if category_slug:
        category = get_object_or_404(Category,slug = category_slug)
        products = products.filter(category=category)
    context = {'category':category,'categories':categories,'products':products,'featured_product': featured_product,'countdown_data': countdown_data}
    return render(request, 'shop/product/books.html', context)

def product_detail(request, id, slug):
    product = get_object_or_404(Product, id=id, slug=slug, available=True)
    context = {'product': product}
    return render(request, 'shop/product/bookdetail.html', context)
    


