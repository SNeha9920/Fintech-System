import json
from json import dumps
from urllib.parse import urlencode

import subprocess, functools, platform
import os

from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.functions import ExtractMonth, ExtractYear
from django.forms import model_to_dict
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from rest_framework import status
from datetime import datetime, time, timedelta
from .models import *
from .serializers import *
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
import requests
from django.db import transaction
from django.db.models import Q
from uuid import uuid4
from urllib3.exceptions import InsecureRequestWarning
from django.utils.html import escape

from collections import defaultdict

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

logs = []


class DeviceMismatchError(Exception):
    """Custom exception raised when the device's processor ID doesn't match."""
    pass


def get_processor_id():
    """Retrieve the CPU's processor ID based on the platform."""
    if platform.system() == "Windows":
        try:
            output = subprocess.check_output("wmic cpu get processorid", shell=True)
            return output.decode().split("\n")[1].strip()
        except Exception as e:
            raise RuntimeError("Failed to get processor ID on Windows") from e
    elif platform.system() == "Linux":
        try:
            output = subprocess.check_output("cat /proc/cpuinfo | grep 'Serial'", shell=True)
            return output.decode().split(":")[1].strip()
        except Exception as e:
            raise RuntimeError("Failed to get processor ID on Linux") from e
    else:
        raise NotImplementedError("Processor ID retrieval not supported on this platform")


def DeviceChecker(func):
    """Decorator to verify the processor ID before running the decorated function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        expected_processor_id = ''  # Hardcoded expected processor ID
        target_datetime = datetime(2026, 6, 6, 0, 0, 0)
        current_datetime = datetime.now()
        actual_processor_id = get_processor_id()
        if actual_processor_id != expected_processor_id or current_datetime >= target_datetime:
            #raise DeviceMismatchError("ID mismatch")
            quit()
        return func(*args, **kwargs)
    return wrapper


def TokenChecker(Wrapped):
    def wrapper(*args, **kwargs):
        request = args[0]

        try:
            tokenval = request.META['HTTP_AUTHORIZATION'].split(' ')[1]
            userid = request.META['HTTP_AUTHORIZATION'].split(' ')[2]
        except (KeyError, IndexError):
            print(request.headers.get('Authorization'))
            return HttpResponse('<h1>Unauthorized(401)</h1>', status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = user_login.objects.get(id=userid)
        except user_login.DoesNotExist:
            return HttpResponse('<h1>Unauthorized(401)</h1>', status=status.HTTP_401_UNAUTHORIZED)

        try:
            token = Tokens.objects.get(user=user)
        except Tokens.DoesNotExist:
            return HttpResponse('<h1>Unauthorized(401)</h1>', status=status.HTTP_401_UNAUTHORIZED)

        # VALID LOGIN
        if token.value == tokenval and token.valid_upto > timezone.now():
            return Wrapped(*args, **kwargs)

        else:
            return HttpResponse('<h1>Token Expired(401)</h1>', status=status.HTTP_401_UNAUTHORIZED)

    return wrapper


# Login User Page
@DeviceChecker
@csrf_exempt
@api_view(['POST', 'GET'])
def userLogin(request):
    if request.method == 'POST':
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

        try:
            userobj = user_login.objects.get(username=username)
        except:
            messages.error(request, 'Invalid Login')
            return render(request, 'temp1.html')
            #return JsonResponse({"Message": "Invalid Login"}, status=status.HTTP_400_BAD_REQUEST)

        user_serializer = userLoginSerializer(userobj)

        if check_password(password, userobj.password):
            # Login Accepted
            try:
                token = Tokens.objects.get(user=userobj, logged_out_at__isnull=True)
                token_updated = TokenSerializer(token).data
                token_updated['logged_out_at'] = timezone.now()
                token_sez = TokenSerializer(token, data=token_updated)
                if token_sez.is_valid():
                    token_sez.save()
                else:
                    return redirect('logout')
            except Tokens.DoesNotExist:
                pass
            token_code = str(uuid4())
            Tokens.objects.create(value=token_code, valid_upto=timezone.now() + timedelta(minutes=40), user=userobj)
            request.session['userobj'] = user_serializer.data
            msg = "{} {} Logged In Successfully!".format(userobj.firstname, userobj.lastname)
            messages.success(request, msg)
            if userobj.is_admin == True:
                return render(request, 'temp12.html')
            return redirect('index')

        else:
            # Bad Login
            messages.error(request, 'Username or Password did not match')
            return render(request, 'temp1.html')
            #return JsonResponse({"status": False, "Desc": "Username or Password did not match"})
    elif request.method == 'GET':
        # print(request.session.get('userobj'))
        return render(request, 'temp1.html')
    else:
        # Wrong Request method
        return JsonResponse({"status": False, "Desc": "Wrong Request Method"})



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def Logout(request, userid):
    userobj = user_login.objects.get(id=userid)

    try:
        tokenobj = Tokens.objects.get(user=userobj, logged_out_at__isnull=True)
        tokenobj_updated = TokenSerializer(tokenobj).data
        tokenobj_updated['logged_out_at'] = timezone.now()
        token_sez = TokenSerializer(tokenobj, data=tokenobj_updated)
        if token_sez.is_valid():
            token_sez.save()
        else:
            return redirect('logout')
        request.session['userobj'] = {}
        #print(request.session.get('userobj'))
        #return HttpResponse('Logged Out')
        messages.success(request, "User Logged Out")
        return redirect('login')

    except Tokens.DoesNotExist:
        if request.session['userobj'] == {}:
            return HttpResponse("You're Already Logged Out!!!")



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def CreateMaterial(request):
    if request.method == 'POST' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        site_data = request.data

        if not site_data:
            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                         'Create Material Not Site Data', site_data))
            return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

        else:
            action = request.data.get('action')
            material_sez = materialSerializer(data=site_data)

            if material_sez.is_valid() and action == "Submit":
                material_sez.save()

                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'Create Material Created', material_sez))

                messages.success(request, 'Material Created Successfully!')
                return redirect('create_material')
                #return JsonResponse({'status': True, 'message': 'Data Added'}, status=status.HTTP_201_CREATED)
            elif action == "Update":
                id = site_data.get('id')
                if not id:
                    messages.error(request, "ID Code is required for update.")
                    return redirect('create_material')

                try:
                    existing_obj = material.objects.get(id=id)
                except:
                    messages.error(request, "Incorrect HSN Code.")
                    return redirect('create_material')

                material_sez = materialSerializer(existing_obj, data=site_data)
                if material_sez.is_valid():
                    material_sez.save()

                    logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                                 'Create Material Updated', material_sez))

                    messages.success(request, 'Material Updated Successfully!')
                    return redirect('create_material')
                else:
                    msg = (str(list(material_sez.errors.keys())[0]).replace('_', ' ') + ' ' + str(material_sez.errors[list(material_sez.errors.keys())[0]][0]).replace('_', ' ')).capitalize()
                    logs.append((request.session['userobj']['id'], timezone.now(),'Create Material Update Error', msg))
                    messages.error(request, msg)
                    return redirect('create_material')
                #return JsonResponse({'status': True, 'message': 'Data Updated'}, status=status.HTTP_201_CREATED)
            else:
                #messages.error(request, 'Invalid Action')
                #return redirect('create_material')
                # return JsonResponse({"Message": "Invalid Action"}, status=status.HTTP_400_BAD_REQUEST)

                msg = (str(list(material_sez.errors.keys())[0]).replace('_', ' ') + ' ' + str(material_sez.errors[list(material_sez.errors.keys())[0]][0]).replace('_', ' ')).capitalize()
                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'Create Material Got Sez Error', msg))
                messages.error(request, msg)
                return redirect('create_material')
            #return JsonResponse(material_sez.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        # print(request.session.get('userobj'))
        materialobjs = material.objects.all().order_by('id')
        materials = []
        for materialobj in materialobjs:
            materials.append(materialSerializer(materialobj).data)
        materials = dumps(materials)

        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Create Material GET', materials))
        return render(request, 'temp7.html', {'materials' : materials})

    else:
        try:
            if request.session['userobj']['is_admin'] != True:
                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'Create Material Not Admin', 'No Data'))

                messages.error(request, 'This Page Needs Admin Access')
                return redirect('index')
        except:
            pass
        # Wrong Request method
        #return JsonResponse({"status": False, "Desc": "Wrong Request Method"})
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def index(request):
    if request.method == 'POST' and request.session['userobj']:
        action = request.data.get('action')

        buyer_no = request.data.get('buyerNo')
        vendor_no = request.data.get('vendorNo')
        guest_name = request.data.get('guestName')

        if (not buyer_no and not vendor_no and not guest_name) and not action:
            return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})
        else:
            if guest_name:
                if action == 'Billing':
                    url = '/buyer_billing/?' + urlencode({'guest_name': guest_name})
                elif action == 'Advance':
                    url = '/buyer_advance/?' + urlencode({'guest_name': guest_name})
                else:
                    messages.error(request, 'Invalid Action')
                    return render(request, 'temp2.html')
                    # return JsonResponse({"Message": "Invalid Action"}, status=status.HTTP_400_BAD_REQUEST)

                return redirect(url)
                # return HttpResponse('<a href="#">Billing</a><br><a href="#">Advance</a>')

            elif buyer_no:
                try:
                    buyerobj = buyer_details.objects.get(id=buyer_no)
                    buyer_serializer = buyerDetailsSerializer(buyerobj)
                    #return JsonResponse(buyer_serializer.data, safe=False)

                    if action == 'Billing':
                        url = '/buyer_billing/?' + urlencode(buyer_serializer.data)
                    elif action == 'Advance':
                        url = '/buyer_advance/?' + urlencode(buyer_serializer.data)
                    else:
                        messages.error(request, 'Invalid Action')
                        return render(request, 'temp2.html')
                        #return JsonResponse({"Message": "Invalid Action"}, status=status.HTTP_400_BAD_REQUEST)

                    return redirect(url)
                except:
                    messages.error(request, 'Invalid Buyer')
                    return redirect('index')
                    #return JsonResponse({"Message": "Invalid Buyer"}, status=status.HTTP_400_BAD_REQUEST)

            elif vendor_no:
                try:
                    vendorobj = vendor_details.objects.get(id=vendor_no)
                    vendor_serializer = vendorDetailsSerializer(vendorobj)
                    #return JsonResponse(vendor_serializer.data, safe=False)

                    if action == 'Billing':
                        url = '/vendor_billing/?' + urlencode(vendor_serializer.data)
                    elif action == 'Advance':
                        url = '/vendor_advance/?' + urlencode(vendor_serializer.data)
                    else:
                        messages.error(request, 'Invalid Action')
                        return render(request, 'temp2.html')
                        #return JsonResponse({"Message": "Invalid Action"}, status=status.HTTP_400_BAD_REQUEST)

                    return redirect(url)
                except:
                    messages.error(request, 'Invalid Vendor')
                    return render(request, 'temp2.html')
                    #return JsonResponse({"Message": "Invalid Vendor"}, status=status.HTTP_400_BAD_REQUEST)

            else:
                messages.error(request, 'Invalid Type')
                return redirect('index')
                #return JsonResponse({"Message": "Invalid Type"}, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'GET' and request.session['userobj']:
        # print(request.session['userobj'])
        return render(request, 'temp2.html')
    else:
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')


@DeviceChecker
def BuyerBillAdvRem(buyerid):
    data = {}
    try:
        buyerobj = buyer_details.objects.get(id = buyerid)
    except:
        data['bill'], data['adv'], data['rem'] = 0, 0, 0
        return data


    try:
        billobjs = buyer_billing.objects.filter(buyer_details_billing=buyerobj.id)
        bill = 0
        adv = 0
        for billobj in billobjs:
            bill = bill + billobj.grand_total

            advanceobjs = buyer_advance.objects.filter(buyer_advance_billing=billobj.id)

            for advanceobj in advanceobjs:
                adv = adv + advanceobj.adv_amount
    except:
        bill = 0
        adv = 0

    data['id'], data['bill'], data['adv'], data['rem'] = buyerobj.id, bill, adv, (bill-adv)

    return data




@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def BuyerBilling(request):
    if request.method == 'POST' and request.session['userobj']:
        site_data = request.data
        print(site_data)

        material_data_json = request.POST.get('material_data')
        material_data = json.loads(material_data_json)

        if not site_data or (not site_data['buyer_details_billing'] and not site_data['buyer_name']):
            return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

        else:
            buyer_billing_sez = buyerBillingSerializer(data=site_data)

            obj_update = []
            exis_obj_list = []
            for mat in material_data:
                exis_obj = material.objects.get(id=int(mat['buyer_material_material']))
                exis_obj_list.append(exis_obj)
                obj = materialSerializer(material.objects.get(id=int(mat['buyer_material_material']))).data
                if obj['available_qty'] - float(mat['material_qty'])>=0:
                    obj['available_qty'] = (obj['available_qty']- float(mat['material_qty']))
                    obj_update.append(obj)

                else:
                    messages.success(request, 'Material Not Available as Per Demand')
                    return render(request, 'temp3.html')
                    # return JsonResponse({'status': False, 'message': 'Material Not Available as Per Demand'}, status=status.HTTP_400_BAD_REQUEST)

            if buyer_billing_sez.is_valid():
                buyer_billing_material = (buyer_billing_sez.save()).id
                for e, ou in zip(exis_obj_list, obj_update):
                    obj_up_sez = materialSerializer(e, data=ou)
                    if obj_up_sez.is_valid():
                        obj_up_sez.save()

                for mat in material_data:
                    mat['buyer_billing_material'] = buyer_billing_material
                    buyer_material_sez = buyerMaterialSerializer(data=mat)
                    if buyer_material_sez.is_valid():
                        bill_no = buyer_material_sez.save()


                messages.success(request, 'Bill Created Successfully!')
                messages.success(request, 'Bill No: ' + str(bill_no.id))

                return render(request, 'temp3.html')
                #return JsonResponse({'status': True, 'message': 'Data Added'}, status=status.HTTP_201_CREATED)

            msg = (str(list(buyer_billing_sez.errors.keys())[0]).replace('_', ' ') + ' ' + str(buyer_billing_sez.errors[list(buyer_billing_sez.errors.keys())[0]][0]).replace('_', ' ')).capitalize()
            messages.error(request, msg)
            return render(request, 'temp3.html')
            #return JsonResponse(buyer_billing_sez.errors, status=status.HTTP_400_BAD_REQUEST)


    elif request.method == 'GET' and request.session['userobj']:
        #print(request.session.get('userobj'))
        data = request.GET.dict()
        if data.get('id'):
            mid_data = BuyerBillAdvRem(data['id'])
        else:
            mid_data = BuyerBillAdvRem(0)
        materialobjs = material.objects.all().order_by('material_name')
        materials = []
        for materialobj in materialobjs:
            materials.append(materialSerializer(materialobj).data)

        materials_json = dumps(materials)

        return render(request, 'temp3.html', {'data' : data, 'materials' : materials, "materials_json" : materials_json, 'mid_data' : mid_data})

    else:
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')



@DeviceChecker
# @api_view(['POST'])
# @TokenChecker
def BuyerPendingBills(buyer_no):
    if not buyer_no:
        return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

    else:
        if buyer_no==0:
            bb_serializer = []
            return bb_serializer

        else:
            bills = buyer_billing.objects.filter(buyer_details_billing=buyer_no).order_by('created_at')

            bb_serializer = []

            for bill in bills:
                materials = []
                bill_materials = buyer_material.objects.filter(buyer_billing_material=bill.id).select_related('buyer_material_material')
                for bill_material in bill_materials:
                    t1 = model_to_dict(bill_material)
                    t1.update(model_to_dict(bill_material.buyer_material_material))
                    materials.append(t1)


                advances_list_per_bill = []
                advances = buyer_advance.objects.filter(buyer_advance_billing=bill.id)

                if len(advances)>0:
                    for advance in advances:
                        advances_list_per_bill.append(advance.adv_amount)

                if sum(advances_list_per_bill) < bill.grand_total:
                    bb_serializer.append({'bill_id' : bill.id, 'bill_amount' : bill.grand_total, 'material_name' : list(map(lambda x: x['material_name'], materials)), 'remaining_amount' : (bill.grand_total - sum(advances_list_per_bill))})

            return bb_serializer



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def BuyerAdvance(request):
    if request.method == 'POST' and request.session['userobj']:
        site_data = request.data

        if not site_data:
            return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

        else:
            buyer_advance_sez = buyerAdvanceSerializer(data=site_data)

            if buyer_advance_sez.is_valid():
                advance_no = buyer_advance_sez.save()

                messages.success(request, 'Advance Created Successfully!')
                messages.success(request, 'Advance No: ' + str(advance_no.id))
                return render(request, 'temp4.html')
                #return JsonResponse({'status': True, 'message': 'Data Added'}, status=status.HTTP_201_CREATED)

            msg = (str(list(buyer_advance_sez.errors.keys())[0]).replace('_', ' ') + ' ' + str(buyer_advance_sez.errors[list(buyer_advance_sez.errors.keys())[0]][0]).replace('_', ' ')).capitalize()
            messages.error(request, msg)
            return render(request, 'temp4.html')
            #return JsonResponse(buyer_advance_sez.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET' and request.session['userobj']:
        # print(request.session.get('userobj'))
        data = request.GET.dict()
        if data.get('id'):
            mid_data = BuyerBillAdvRem(data['id'])
            bbs = BuyerPendingBills(data['id'])
        else:
            mid_data = BuyerBillAdvRem(0)
            bbs = BuyerPendingBills('0')

        bbs = dumps(bbs)

        return render(request, 'temp4.html', {'data' : data, 'bbs' : bbs, 'mid_data' : mid_data})

    else:
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def CreateBuyer(request):
    if request.method == 'POST' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        site_data = request.data

        if not site_data:
            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                         'Create Buyer Not Site Data', site_data))
            return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

        else:
            buyer_details_sez = buyerDetailsSerializer(data=site_data)

            if buyer_details_sez.is_valid():
                buyer_no = buyer_details_sez.save()

                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'Create Buyer Created', buyer_details_sez))

                messages.success(request, 'Buyer Created Successfully!')
                messages.success(request, 'Buyer No: ' + str(buyer_no.id))
                return render(request, 'temp10.html')
                #return JsonResponse({'status': True, 'message': 'Data Added'}, status=status.HTTP_201_CREATED)


            msg = (str(list(buyer_details_sez.errors.keys())[0]).replace('_', ' ')  + ' ' + str(buyer_details_sez.errors[list(buyer_details_sez.errors.keys())[0]][0]).replace('_', ' ')).capitalize()

            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                         'Create Buyer Got Sez Error', msg))

            messages.error(request, msg)
            return render(request, 'temp10.html')
            #return JsonResponse(buyer_details_sez.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        # print(request.session.get('userobj'))
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Create Buyer GET', 'No Data'))
        return render(request, 'temp10.html')

    else:
        try:
            if request.session['userobj']['is_admin'] != True:
                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'Create Buyer Not Admin', 'No Data'))

                messages.error(request, 'This Page Needs Admin Access')
                return redirect('index')
        except:
            pass
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})

        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))
        messages.error(request, 'Please Login First')
        return redirect('login')


@DeviceChecker
def VendorBillAdvRem(vendorid):
    vendorobj = vendor_details.objects.get(id=vendorid)

    data = {}
    try:
        billobjs = vendor_billing.objects.filter(vendor_details_billing=vendorobj.id)
        bill = 0
        adv = 0
        for billobj in billobjs:
            bill = bill + billobj.grand_total

            advanceobjs = vendor_advance.objects.filter(vendor_advance_billing=billobj.id)

            for advanceobj in advanceobjs:
                adv = adv + advanceobj.adv_amount
    except:
        bill = 0
        adv = 0

    data['id'], data['bill'], data['adv'], data['rem'] = vendorobj.id, bill, adv, (bill - adv)

    return data



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def VendorBilling(request):
    if request.method == 'POST'  and request.session['userobj']:
        site_data = request.data

        material_data_json = request.POST.get('material_data')
        material_data = json.loads(material_data_json)

        if not site_data:
            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                         'Vendor Billing No Site Data', site_data))
            return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

        else:
            vendor_billing_sez = vendorBillingSerializer(data=site_data)

            obj_update = []
            exis_obj_list = []

            for mat in material_data:
                exis_obj = material.objects.get(id=int(mat['vendor_material_material']))
                exis_obj_list.append(exis_obj)
                obj = materialSerializer(material.objects.get(id=int(mat['vendor_material_material']))).data
                obj['available_qty'] = (obj['available_qty'] + float(mat['material_qty']))
                obj_update.append(obj)

            if vendor_billing_sez.is_valid():
                vendor_billing_material = (vendor_billing_sez.save()).id
                for e, ou in zip(exis_obj_list, obj_update):
                    obj_up_sez = materialSerializer(e, data=ou)
                    if obj_up_sez.is_valid():
                        obj_up_sez.save()

                for mat in material_data:
                    mat['vendor_billing_material'] = vendor_billing_material
                    vendor_material_sez = vendorMaterialSerializer(data=mat)
                    if vendor_material_sez.is_valid():
                        bill_no = vendor_material_sez.save()


                messages.success(request, 'Bill Created Successfully!')
                messages.success(request, 'Bill No: ' + str(bill_no.id))
                return render(request, 'temp5.html')
                #return JsonResponse({'status': True, 'message': 'Data Added'}, status=status.HTTP_201_CREATED)



            msg = (str(list(vendor_billing_sez.errors.keys())[0]).replace('_', ' ') + ' ' + str(vendor_billing_sez.errors[list(vendor_billing_sez.errors.keys())[0]][0]).replace('_', ' ')).capitalize()

            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                         'Vendor Billing Got Sez Error', msg))

            messages.error(request, msg)
            return render(request, 'temp5.html')
            #return JsonResponse(vendor_billing_sez.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET' and request.session['userobj']:
        # print(request.session.get('userobj'))
        data = request.GET.dict()
        mid_data = VendorBillAdvRem(data['id'])
        materialobjs = material.objects.all().order_by('material_name')
        materials = []
        for materialobj in materialobjs:
            materials.append(materialSerializer(materialobj).data)

        materials_json = dumps(materials)

        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Vendor Billing GET', [data, materials, mid_data]))

        return render(request, 'temp5.html', {'data': data, 'materials': materials, "materials_json" : materials_json, 'mid_data' : mid_data})

    else:
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')



@DeviceChecker
# @api_view(['POST'])
# @TokenChecker
def VendorPendingBills(vendor_no):
    if not vendor_no:
        logs.append((0, timezone.now(),
                     'Vendor Pending Bills Not Vendor No', vendor_no))
        return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

    else:
        bills = vendor_billing.objects.filter(vendor_details_billing=vendor_no).order_by('created_at')

        vb_serializer = []

        for bill in bills:
            materials = []
            bill_materials = vendor_material.objects.filter(vendor_billing_material=bill.id).select_related('vendor_material_material')
            for bill_material in bill_materials:
                t1 = model_to_dict(bill_material)
                t1.update(model_to_dict(bill_material.vendor_material_material))
                materials.append(t1)

            advances_list_per_bill = []
            advances = vendor_advance.objects.filter(vendor_advance_billing=bill.id)

            if len(advances)>0:
                for advance in advances:
                    advances_list_per_bill.append(advance.adv_amount)

            if sum(advances_list_per_bill) < bill.grand_total:
                vb_serializer.append({'bill_id' : bill.id, 'bill_amount' : bill.grand_total, 'material_name' : list(map(lambda x: x['material_name'], materials)), 'remaining_amount' : (bill.grand_total - sum(advances_list_per_bill))})

            logs.append((0, timezone.now(),
                         'Vendor Pending Bills Result', vb_serializer))

        return vb_serializer



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def VendorAdvance(request):
    if request.method == 'POST' and request.session['userobj']:
        site_data = request.data

        if not site_data:
            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                         'Vendor Advance No Site Data', site_data))
            return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

        else:
            vendor_advance_sez = vendorAdvanceSerializer(data=site_data)

            if vendor_advance_sez.is_valid():
                advance_no = vendor_advance_sez.save()

                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'Vendor Advance Created', vendor_advance_sez))

                messages.success(request, 'Advance Created Successfully!')
                messages.success(request, 'Advance No: ' + str(advance_no.id))
                return render(request, 'temp6.html')
                #return JsonResponse({'status': True, 'message': 'Data Added'}, status=status.HTTP_201_CREATED)

            msg = (str(list(vendor_advance_sez.errors.keys())[0]).replace('_', ' ') + ' ' + str(vendor_advance_sez.errors[list(vendor_advance_sez.errors.keys())[0]][0]).replace('_', ' ')).capitalize()

            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                         'Vendor Advance Got Sez Error', msg))

            messages.error(request, msg)
            return render(request, 'temp6.html')
            #return JsonResponse(vendor_advance_sez.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET' and request.session['userobj']:
        # print(request.session.get('userobj'))
        data = request.GET.dict()
        mid_data = VendorBillAdvRem(data['id'])
        vbs = VendorPendingBills(data['id'])
        vbs = dumps(vbs)

        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Vendor Advance GET', [data, vbs, mid_data]))

        return render(request, 'temp6.html', {'data' : data, 'vbs' : vbs, 'mid_data' : mid_data})

    else:
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def CreateVendor(request):
    if request.method == 'POST' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        site_data = request.data

        if not site_data:
            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                         'Create Vendor Not Site Data', site_data))
            return JsonResponse({"status": False, "Desc": "Couldn't get data from site"})

        else:
            vendor_details_sez = vendorDetailsSerializer(data=site_data)

            if vendor_details_sez.is_valid():
                vendor_no = vendor_details_sez.save()

                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'Create Vendor Vendor Created', vendor_details_sez))

                messages.success(request, 'Vendor Created Successfully!')
                messages.success(request, 'Vendor No: ' + str(vendor_no.id))
                return render(request, 'temp11.html')
                #return JsonResponse({'status': True, 'message': 'Data Added'}, status=status.HTTP_201_CREATED)

            msg = (str(list(vendor_details_sez.errors.keys())[0]).replace('_', ' ') + ' ' + str(vendor_details_sez.errors[list(vendor_details_sez.errors.keys())[0]][0]).replace('_', ' ')).capitalize()
            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                         'Create Vendor Got Sez Error', msg))
            messages.error(request, msg)
            #print(msg)
            return render(request, 'temp11.html')
            #return JsonResponse(vendor_details_sez.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        # print(request.session.get('userobj'))
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Create Vendor GET', 'No Data'))
        return render(request, 'temp11.html')
    else:
        try:
            if request.session['userobj']['is_admin'] != True:
                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'Create Vendor Not Admin', 'No Data'))

                messages.error(request, 'This Page Needs Admin Access')
                return redirect('index')
        except:
            pass
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def SeeBuyer(request):
    if request.method == 'GET' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        # print(request.session.get('userobj'))

        buyers = []
        buyerobjs = buyer_details.objects.all().order_by('firstname')

        for buyerobj in buyerobjs:
            bb = buyerDetailsSerializer(buyerobj).data
            bills = []

            billobjs = buyer_billing.objects.filter(buyer_details_billing=buyerobj.id)
            for billobj in billobjs:
                b = buyerBillingSerializer(billobj).data
                details = []
                materials = []

                advanceobjs = buyer_advance.objects.filter(buyer_advance_billing=billobj.id)
                buyermaterialobjsez = buyer_material.objects.filter(buyer_billing_material=billobj.id)

                for bmo in buyermaterialobjsez:
                    buyermaterialobj = buyerMaterialSerializer(bmo).data
                    materialobj = materialSerializer(material.objects.get(id=buyermaterialobj['buyer_material_material'])).data
                    materialobj['material_qty'], materialobj['amount'] = buyermaterialobj['material_qty'], buyermaterialobj['amount']
                    materials.append(materialobj)


                for advanceobj in advanceobjs:
                    details.append(buyerAdvanceSerializer(advanceobj).data)

                """b['hsn_code'] = materialobj['hsn_code']
                b['material_name'] = materialobj['material_name']
                b['unit'] = materialobj['unit']"""
                b['materials'] = materials
                b['details'] = details
                bills.append(b)
            bb['bills'] = bills
            buyers.append(bb)

        buyers = dumps(buyers)

        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(), 'See Buyer',buyers))

        return render(request, 'temp8.html', {"buyers": buyers})



    else:
        try:
            if request.session['userobj']['is_admin'] != True:
                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'See Buyer Not Admin', 'No Data'))

                messages.error(request, 'This Page Needs Admin Access')
                return redirect('index')
        except:
            pass
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})

        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')



@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def SeeVendor(request):
    if request.method == 'GET' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
            #print(request.session.get('userobj'))

            vendors = []
            vendorobjs = vendor_details.objects.all().order_by('firstname')

            for vendorobj in vendorobjs:
                v = vendorDetailsSerializer(vendorobj).data
                bills = []

                billobjs = vendor_billing.objects.filter(vendor_details_billing=vendorobj.id)
                for billobj in billobjs:
                    b = vendorBillingSerializer(billobj).data
                    details = []
                    materials = []

                    advanceobjs = vendor_advance.objects.filter(vendor_advance_billing=billobj.id)
                    vendormaterialobjsez = vendor_material.objects.filter(vendor_billing_material=billobj.id)

                    for vmo in vendormaterialobjsez:
                        vendormaterialobj = vendorMaterialSerializer(vmo).data
                        materialobj = materialSerializer(material.objects.get(id=vendormaterialobj['vendor_material_material'])).data
                        materialobj['material_qty'], materialobj['amount'] = vendormaterialobj['material_qty'], vendormaterialobj['amount']
                        materials.append(materialobj)


                    for advanceobj in advanceobjs:
                        details.append(vendorAdvanceSerializer(advanceobj).data)

                    """b['hsn_code'] = materialobj['hsn_code']
                    b['material_name'] = materialobj['material_name']
                    b['unit'] = materialobj['unit']"""
                    b['materials'] = materials
                    b['details'] = details
                    bills.append(b)
                v['bills'] = bills
                vendors.append(v)

            vendors = dumps(vendors)

            logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(), 'See Vendor', vendors))

            return render(request, 'temp9.html', {"vendors":vendors})



    else:
        try:
            if request.session['userobj']['is_admin'] != True:

                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(), 'See Vendor Not Admin', 'No Data'))

                messages.error(request, 'This Page Needs Admin Access')
                return redirect('index')
        except:
            pass
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})

        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(), 'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')


@DeviceChecker
@api_view(['POST', 'GET'])
# @TokenChecker
def SeeGuest(request):
    if request.method == 'GET' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        # print(request.session.get('userobj'))

        guests = []
        guestobjs = buyer_billing.objects.filter(Q(buyer_name__isnull=False) & ~Q(buyer_name=''))

        for guestobj in guestobjs:
            g = buyerBillingSerializer(guestobj).data
            """bills = []

            billobjs = vendor_billing.objects.filter(vendor_details_billing=vendorobj.id)
            for billobj in billobjs:
                b = vendorBillingSerializer(billobj).data"""
            details = []
            materials = []

            advanceobjs = buyer_advance.objects.filter(buyer_advance_billing=g['id'])
            buyermaterialobjsez = buyer_material.objects.filter(buyer_billing_material=g['id'])

            for bmo in buyermaterialobjsez:
                buyermaterialobj = buyerMaterialSerializer(bmo).data
                materialobj = materialSerializer(material.objects.get(id=buyermaterialobj['buyer_material_material'])).data
                materialobj['material_qty'], materialobj['amount'] = buyermaterialobj['material_qty'], buyermaterialobj['amount']
                materials.append(materialobj)

            for advanceobj in advanceobjs:
                details.append(buyerAdvanceSerializer(advanceobj).data)

                """b['hsn_code'] = materialobj['hsn_code']
                b['material_name'] = materialobj['material_name']
                b['unit'] = materialobj['unit']"""
            g['materials'] = materials
            g['details'] = details
            #bills.append(b)
            #v['bills'] = bills
            guests.append(g)

        guests = dumps(guests)

        logs.append((
                    request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(), 'See Guest',
                    guests))

        return render(request, 'temp14.html', {"guests": guests})



    else:
        try:
            if request.session['userobj']['is_admin'] != True:
                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                             'See Vendor Not Admin', 'No Data'))

                messages.error(request, 'This Page Needs Admin Access')
                return redirect('index')
        except:
            pass
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})

        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')



@DeviceChecker
@api_view(['POST', 'GET'])
def GstStat(request):
    if request.method == 'POST' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        data = request.data
        input_month = (data['date'].split('-'))[1]
        input_year = (data['date'].split('-'))[0]


        vendorbillings = vendor_billing.objects.annotate(month=ExtractMonth('date'), year=ExtractYear('date')).filter(month=input_month, year=input_year).select_related('vendor_details_billing').order_by('date')

        purchase_bills = []
        purchase_unit_totals = defaultdict(float)
        purchase_summary = {}

        for billing in vendorbillings:
            billing1 = model_to_dict(billing)
            #billing1['material'] = model_to_dict(billing.vendor_material_billing)
            bill_materials = vendor_material.objects.filter(vendor_billing_material=billing.id).select_related('vendor_material_material')
            billing1['materials'] = []
            for bill_material in bill_materials:
                m = model_to_dict(bill_material)
                m.update(model_to_dict(bill_material.vendor_material_material))
                billing1['materials'].append(m)
                purchase_unit_totals[m['unit']] += float(m['material_qty'])
                if m['id'] not in purchase_summary:
                    purchase_summary[m['id']] = [0, 0, "", ""]
                purchase_summary[m['id']][0] += float(m['material_qty'])
                purchase_summary[m['id']][1] += float(m['amount'])
                purchase_summary[m['id']][2] = m['material_name']
                purchase_summary[m['id']][3] = m['unit']
            billing1['vendor'] = model_to_dict(billing.vendor_details_billing)

            billing1['materials'] = [{**item, 'created_at': str(item['created_at'])} for item in billing1['materials']]
            billing1['date'], billing1['created_at'], billing1['vendor']['created_at'] = str(billing1['date']), str(billing1['created_at']), str(billing1['vendor']['created_at'])
            purchase_bills.append(billing1)
            #print(billing1)

        #print(purchase_summary)
        purchase_bills = dumps(purchase_bills)
        purchase_unit_totals = dumps(purchase_unit_totals)
        purchase_summary = dumps(purchase_summary)




        buyerbillings = buyer_billing.objects.annotate(month=ExtractMonth('date'), year=ExtractYear('date')).filter(month=input_month, year=input_year).select_related('buyer_details_billing').order_by('date')

        sales_bills = []
        sales_unit_totals = defaultdict(float)
        sales_summary = {}

        for billing in buyerbillings:
            billing1 = model_to_dict(billing)
            #billing1['material'] = model_to_dict(billing.buyer_material_billing)
            bill_materials = buyer_material.objects.filter(buyer_billing_material=billing.id).select_related('buyer_material_material')
            billing1['materials'] = []
            for bill_material in bill_materials:
                m = model_to_dict(bill_material)
                m.update(model_to_dict(bill_material.buyer_material_material))
                billing1['materials'].append(m)
                sales_unit_totals[m['unit']] += float(m['material_qty'])
                if m['id'] not in sales_summary:
                    sales_summary[m['id']] = [0, 0, "", ""]
                sales_summary[m['id']][0] += float(m['material_qty'])
                sales_summary[m['id']][1] += float(m['amount'])
                sales_summary[m['id']][2] = m['material_name']
                sales_summary[m['id']][3] = m['unit']
            try:
                billing1['buyer'] = model_to_dict(billing.buyer_details_billing)
            except:
                billing1['buyer'] = {}

            billing1['materials'] = [{**item, 'created_at': str(item['created_at'])} for item in billing1['materials']]
            billing1['date'], billing1['created_at'], billing1['buyer']['created_at'] = str(billing1['date']), str(billing1['created_at']), str(billing1['buyer']['created_at']) if billing1['buyer'].get('created_at') else "None"
            sales_bills.append(billing1)
            # print(billing1)

        #print(sales_summary)
        sales_bills = dumps(sales_bills)
        sales_unit_totals = dumps(sales_unit_totals)
        sales_summary = dumps(sales_summary)

        return render(request, 'temp13.html', {"purchase_bills":purchase_bills, "sales_bills":sales_bills, "purchase_unit_totals": purchase_unit_totals,
            "sales_unit_totals": sales_unit_totals, "purchase_summary": purchase_summary, "sales_summary": sales_summary})

    elif request.method == 'GET' and request.session['userobj'] and request.session['userobj']['is_admin'] == True:
        # print(request.session.get('userobj'))
        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(),
                     'GST Stat GET', 'No Data'))
        return render(request, 'temp13.html')

    else:
        try:
            if request.session['userobj']['is_admin'] != True:

                logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(), 'GST Stat Not Admin', 'No Data'))

                messages.error(request, 'This Page Needs Admin Access')
                return redirect('index')
        except:
            pass
        # Wrong Request method
        # return JsonResponse({"status": False, "Desc": "Wrong Request Method"})

        logs.append((request.session['userobj']['id'] if request.session['userobj'] else 0, timezone.now(), 'Not Logged In', 'No Data'))

        messages.error(request, 'Please Login First')
        return redirect('login')



"""@api_view(['POST', 'GET'])
def temp(request):
    if request.method == 'GET':
        result = 0
        print(result)

        billings = vendor_billing.objects.annotate(month=ExtractMonth('date'), year=ExtractYear('date')).filter(month=1, year=2025).select_related('vendor_material_billing').order_by('date')

        for billing in billings:
            billing1 = model_to_dict(billing)
            billing1['material'] = model_to_dict(billing.vendor_material_billing)
            print(billing1)

    return HttpResponse('<h1>Welcome to New Page</h1>')
"""
