from .models import Category

def categories_processor(request):
    return {
        "categories": Category.objects.all()
    }
from .models import Cart

def cart_count(request):
    count = 0

    user_id = request.session.get('user_id')

    if user_id:
        count = Cart.objects.filter(user_id=user_id).count()

    return {
        'cart_count': count
    }