from django.db import models
from django.utils import timezone

# Login Page dataabse
class user_login(models.Model):
    id = models.AutoField(primary_key=True)
    firstname = models.CharField(max_length=50, null=False)
    lastname = models.CharField(max_length=50, null=False)
    username = models.CharField(max_length=50, null=False)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(auto_now=True)
    password = models.CharField(max_length=128)
    is_admin = models.BooleanField(default="false")
    status = models.BooleanField(default=True)

    class Meta:
        db_table = "user_login"

# Tokens
class Tokens(models.Model):
    id = models.AutoField(primary_key=True)
    value = models.CharField(max_length=255)
    valid_upto = models.DateTimeField(blank=True, null=True)
    login_at = models.DateTimeField(default=timezone.now)
    logged_out_at = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(user_login, related_name='TOKEN', on_delete=models.CASCADE)

    class Meta:
        db_table = 'tokens'



#Details of Materials Database
class material(models.Model):
    id = models.AutoField(primary_key=True)
    hsn_code = models.IntegerField(null=False, blank=False)
    material_name = models.CharField(max_length=100, null=False, blank=False)
    unit = models.CharField(max_length=10, null=False, blank=False)
    available_qty = models.FloatField(null=False, default=0)
    price_per_unit = models.FloatField(null=False, blank=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'material'



# Details of Buyer Database
class buyer_details(models.Model):
    id = models.AutoField(primary_key=True)
    firstname = models.CharField(max_length=50, null=False, blank=False)
    lastname = models.CharField(max_length=50, null=False, blank=False)
    mobile_no = models.BigIntegerField(max_length=12, null=False, blank=False)
    email = models.EmailField(null=False, blank=False)
    firm_name = models.CharField(max_length=100, null=False, blank=False)
    firm_address = models.CharField(max_length=300, null=False, blank=False)
    firm_gst_no = models.CharField(unique=True, max_length=20, null=False, blank=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'buyer_details'

# Details of Billing of Buyer Database
class buyer_billing(models.Model):
    id = models.AutoField(primary_key=True)
    buyer_details_billing = models.ForeignKey(buyer_details, related_name='BUYER_DB', on_delete=models.CASCADE, null=True, blank=True)
    buyer_name = models.CharField(max_length=150, null=True, blank=True)
    date = models.DateField(null=False, blank=False)
    bill_amount = models.FloatField(null=False, blank=False)
    loading_unloading_charges = models.FloatField(null=True, blank=True)
    cgst_9 = models.BooleanField(null=True, blank=True)
    sgst_9 = models.BooleanField(null=True, blank=True)
    cgst_14 = models.BooleanField(null=True, blank=True)
    sgst_14 = models.BooleanField(null=True, blank=True)
    igst_18 = models.BooleanField(null=True, blank=True)
    extra_010 = models.BooleanField(null=True, blank=True)
    grand_total = models.FloatField(null=False, blank=False)
    note = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'buyer_billing'

# Details of Materials of Buyer Billing of Buyer Database
class buyer_material(models.Model):
    id = models.AutoField(primary_key=True)
    buyer_billing_material = models.ForeignKey(buyer_billing, related_name='BUYER_BM', on_delete=models.CASCADE, null=False, blank=False)
    buyer_material_material = models.ForeignKey(material, related_name='BUYER_MM', on_delete=models.CASCADE, null=False, blank=False)
    material_qty = models.FloatField(null=False, blank=False)
    amount = models.FloatField(null=False, blank=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'buyer_material'

# Details of Advance of Buyer Database
class buyer_advance(models.Model):
    id = models.AutoField(primary_key=True)
    buyer_advance_billing = models.ForeignKey(buyer_billing, related_name='BUYER_AB', on_delete=models.CASCADE, null=False, blank=False)
    type = models.CharField(max_length=50, null=False, blank=False)
    type_no = models.CharField(max_length=50, null=True, blank=True)
    date = models.DateField(null=False, blank=False)
    adv_amount = models.PositiveIntegerField(null=False, blank=False)
    note = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'buyer_advance'




# Details of Vendor Database
class vendor_details(models.Model):
    id = models.AutoField(primary_key=True)
    firstname = models.CharField(max_length=50, null=False, blank=False)
    lastname = models.CharField(max_length=50, null=False, blank=False)
    mobile_no = models.BigIntegerField(max_length=12, null=False, blank=False)
    email = models.EmailField(null=False, blank=False)
    firm_name = models.CharField(max_length=100, null=False, blank=False)
    firm_address = models.CharField(max_length=300, null=False, blank=False)
    firm_gst_no = models.CharField(unique=True, max_length=20, null=False, blank=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'vendor_details'

# Details of Billing of Vendor Database
class vendor_billing(models.Model):
    id = models.AutoField(primary_key=True)
    vendor_details_billing = models.ForeignKey(vendor_details, related_name='VENDOR_DB', on_delete=models.CASCADE, null=False, blank=False)
    date = models.DateField(null=False, blank=False)
    bill_amount = models.PositiveIntegerField(null=False, blank=False)
    loading_unloading_charges = models.FloatField(null=True, blank=True)
    cgst_9 = models.BooleanField(null=True, blank=True)
    sgst_9 = models.BooleanField(null=True, blank=True)
    cgst_14 = models.BooleanField(null=True, blank=True)
    sgst_14 = models.BooleanField(null=True, blank=True)
    igst_18 = models.BooleanField(null=True, blank=True)
    extra_010 = models.BooleanField(null=True, blank=True)
    grand_total = models.FloatField(null=False, blank=False)
    note = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vendor_billing'


# Details of Materials of Vendor Billing of Vendor Database
class vendor_material(models.Model):
    id = models.AutoField(primary_key=True)
    vendor_billing_material = models.ForeignKey(vendor_billing, related_name='VENDOR_BM', on_delete=models.CASCADE, null=False, blank=False)
    vendor_material_material = models.ForeignKey(material, related_name='VENDOR_MM', on_delete=models.CASCADE, null=False, blank=False)
    material_qty = models.FloatField(null=False, blank=False)
    amount = models.FloatField(null=False, blank=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vendor_material'


# Details of Advance of Vendor Database
class vendor_advance(models.Model):
    id = models.AutoField(primary_key=True)
    vendor_advance_billing = models.ForeignKey(vendor_billing, related_name='VENDOR_AB', on_delete=models.CASCADE, null=False, blank=False)
    type = models.CharField(max_length=50, null=False, blank=False)
    type_no = models.CharField(max_length=50, null=True, blank=True)
    date = models.DateField(null=False, blank=False)
    adv_amount = models.PositiveIntegerField(null=False, blank=False)
    note = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vendor_advance'
