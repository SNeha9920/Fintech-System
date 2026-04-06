from rest_framework import serializers
from .models import *

class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'tokens'
        model = Tokens
        abstract = True
        fields = '__all__'

class userLoginSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'user_login'
        model = user_login
        abstract = True
        fields = '__all__'

class materialSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'material'
        model = material
        abstract = True
        fields = '__all__'

class buyerDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'buyer_details'
        model = buyer_details
        abstract = True
        fields = '__all__'


class buyerBillingSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'buyer_billing'
        model = buyer_billing
        abstract = True
        fields = '__all__'


class buyerMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'buyer_material'
        model = buyer_material
        abstract = True
        fields = '__all__'


class buyerAdvanceSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'buyer_advance'
        model = buyer_advance
        abstract = True
        fields = '__all__'


class vendorDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'vendor_details'
        model = vendor_details
        abstract = True
        fields = '__all__'


class vendorBillingSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'vendor_billing'
        model = vendor_billing
        abstract = True
        fields = '__all__'



class vendorMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'vendor_material'
        model = vendor_material
        abstract = True
        fields = '__all__'




class vendorAdvanceSerializer(serializers.ModelSerializer):
    class Meta:
        db_table: 'vendor_advance'
        model = vendor_advance
        abstract = True
        fields = '__all__'