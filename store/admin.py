from django.contrib import admin
from django.contrib import *
from .models import *

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'user_id',
        'first_name',
        'email_id',
        'contact_no',
        'dob_date'
    )

    search_fields = ('first_name', 'email_id', 'contact_no')
    list_filter = ('dob_date',)
    ordering = ('-user_id',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name',)

# Inline Images inside Product
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'is_primary')
    show_change_link = True




@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'is_primary')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'warranty_years')
    list_filter = ('category',)
    inlines = [ProductImageInline]
    filter_horizontal = ('features',) 

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total', 'payment_method', 'razorpay_payment_id', 'status')
    list_filter = ('status', 'payment_method')
    search_fields = ('id', 'user__username', 'email')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity')

