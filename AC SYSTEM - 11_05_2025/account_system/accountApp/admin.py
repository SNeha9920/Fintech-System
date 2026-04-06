from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register([user_login, Tokens, material, buyer_details, buyer_billing, buyer_advance, vendor_details, vendor_billing, vendor_advance])