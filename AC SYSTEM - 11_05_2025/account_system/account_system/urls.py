"""
URL configuration for account_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from accountApp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.userLogin, name='login'),
    path('logout/<userid>', views.Logout, name='logout'),
    path('index/', views.index, name='index'),
    path('buyer_billing/', views.BuyerBilling, name='buyer_billing'),
    path('buyer_advance/', views.BuyerAdvance, name='buyer_advance'),
    #path('buyer_bills/', views.BuyerPendingBills, name='buyer_bills'),
    path('create_buyer/', views.CreateBuyer, name='create_buyer'),
    path('vendor_billing/', views.VendorBilling, name='vendor_billing'),
    path('vendor_advance/', views.VendorAdvance, name='vendor_advance'),
    #path('vendor_bills/', views.VendorPendingBills, name='vendor_bills'),
    path('create_vendor/', views.CreateVendor, name='create_vendor'),
    path('create_material/', views.CreateMaterial, name='create_material'),
    path('see_buyer/', views.SeeBuyer, name='see_buyer'),
    path('see_vendor/', views.SeeVendor, name='see_vendor'),
    path('see_guest/', views.SeeGuest, name='see_guest'),
    path('gst_stat/', views.GstStat, name='gst_stat'),
    #path('temp/', views.temp, name='temp'),
]
