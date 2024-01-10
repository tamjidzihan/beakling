from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Category, Books,Events

def index(request):
    featured_book = Books.objects.filter(featurebook=True,category = 1).first()
    recently_updated_books = Books.objects.filter(category = 1).order_by('-updated')[:3]
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

    context = {'featured_book': featured_book,'recently_updated_books': recently_updated_books,'countdown_data': countdown_data}
    return render(request, 'shop/home.html', context )

def book_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    books = Books.objects.filter(available = True,category = 1)
    featured_book = Books.objects.filter(featurebook=True).first()
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
        books = books.filter(category=category)
    context = {'category':category,'categories':categories,'books':books,'featured_book': featured_book,'countdown_data': countdown_data}
    return render(request, 'shop/book/books.html', context)

def book_detail(request, id, slug):
    book = get_object_or_404(Books, id=id, slug=slug, available=True)
    context = {'book': book}
    return render(request, 'shop/book/bookdetail.html', context)



def product_list(request):
    categories = Category.objects.all()
    toys = Books.objects.filter(available = True,category = 2)
    accessories= Books.objects.filter(available = True,category = 3)

    context = {'categories':categories,'toys':toys,'accessories':accessories}
    return render(request, 'shop/product/porductlist.html',context)










    
def about(request):
    return render(request,'shop/book/about.html')

def termsandconditions(request):
    return render(request,'shop/book/termsandconditions.html')

