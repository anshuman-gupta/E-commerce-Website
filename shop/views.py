from django.shortcuts import render,redirect
from django.http import HttpResponse
from.models import Product,Contact,Orders,OrderUpdate
from math import ceil
import json
from django.views.decorators.csrf import csrf_exempt
from PayTm import Checksum
from django.contrib import messages
from django.contrib.auth.models import User,auth
MERCHANT_KEY = 'Enter your Key here'
def index(request):
    products = Product.objects.all()
    #print(products)
    #n=len(products)
    #nSlides=n//4+ceil((n/4)-(n//4))
    #params={'no_of_slides':nSlides,'range':range(1,nSlides),'product':products}
    #allProds = [[products, range(1, nSlides), nSlides],
     #            [products, range(1, nSlides), nSlides]]


    allProds = []
    catprods = Product.objects.values('category', 'id')
    cats = {item['category'] for item in catprods}
    for cat in cats:
        prod = Product.objects.filter(category=cat)
        n = len(prod)
        nSlides = n // 4 + ceil((n / 4) - (n // 4))
        allProds.append([prod, range(1, nSlides), nSlides])
        #print(allProds)

    params = {'allProds': allProds}
    return render(request,"shop/index.html",params)


def searchMatch(query, item):
    '''return true only if query matches the item'''
    if query in item.desc.lower() or query in item.product_name.lower() or query in item.category.lower():
        return True
    else:
        return False

def search(request):
    query = request.GET.get('search')
    allProds = []
    catprods = Product.objects.values('category', 'id')
    cats = {item['category'] for item in catprods}
    for cat in cats:
        prodtemp = Product.objects.filter(category=cat)
        prod = [item for item in prodtemp if searchMatch(query, item)]

        n = len(prod)
        nSlides = n // 4 + ceil((n / 4) - (n // 4))
        if len(prod) != 0:
            allProds.append([prod, range(1, nSlides), nSlides])
    params = {'allProds': allProds, "msg": ""}
    if len(allProds) == 0 or len(query)<4:
        params = {'msg': "Please make sure to enter relevant search query"}
    return render(request, 'shop/search.html', params)


def about(request):
    return render(request,"shop/about.html")
def contact(request):
    if request.method=="POST":
        #print(request)
        name=request.POST.get('name','')
        email = request.POST.get('email','')
        phone = request.POST.get('phone','')
        desc = request.POST.get('desc','')
        contact=Contact(name=name,email=email,phone=phone,desc=desc)
        contact.save()
    return render(request, "shop/contact.html")


def tracker(request):
    if request.method=="POST":
        orderId = request.POST.get('orderId', '')
        email = request.POST.get('email', '')
        try:
            order = Orders.objects.filter(order_id=orderId, email=email)
            if len(order)>0:
                update = OrderUpdate.objects.filter(order_id=orderId)
                updates = []
                for item in update:
                    updates.append({'text': item.update_desc, 'time': item.timestamp})
                    response = json.dumps({"status":"success", "updates": updates, "itemsJson": order[0].items_json}, default=str)
                return HttpResponse(response)
            else:
                return HttpResponse('{"status":"noitem"}')
        except Exception as e:
            return HttpResponse('{"status":"error"}')

    return render(request, 'shop/tracker.html')

def productview(request,myid):
    #Fetch the product using id
    product = Product.objects.filter(id=myid)
    return render(request, "shop/prodview.html",{"product":product[0]})


def checkout(request):
    if request.method=="POST":
        items_json = request.POST.get('itemsJson', '')
        name = request.POST.get('name', '')
        amount = request.POST.get('amount', '')
        email = request.POST.get('email', '')
        address = request.POST.get('address1', '') + " " + request.POST.get('address2', '')
        city = request.POST.get('city', '')
        state = request.POST.get('state', '')
        zip_code = request.POST.get('zip_code', '')
        phone = request.POST.get('phone', '')
        order = Orders(items_json=items_json, name=name, email=email, address=address, city=city,
                       state=state, zip_code=zip_code, phone=phone, amount=amount)
        order.save()
        update = OrderUpdate(order_id=order.order_id, update_desc="The order has been placed")
        update.save()
        thank = True
        id = order.order_id
        # return render(request, 'shop/checkout.html', {'thank':thank, 'id': id})
        # Request paytm to transfer the amount to your account after payment by user
        param_dict = {

                'MID': 'Enter your id here',
                'ORDER_ID': str(order.order_id),
                'TXN_AMOUNT': str(amount),
                'CUST_ID': email,
                'INDUSTRY_TYPE_ID': 'Retail',
                'WEBSITE': 'WEBSTAGING',
                'CHANNEL_ID': 'WEB',
                'CALLBACK_URL':'http://127.0.0.1:8000/shop/handlerequest/',

        }
        param_dict['CHECKSUMHASH'] = Checksum.generate_checksum(param_dict, MERCHANT_KEY)
        return render(request, 'shop/paytm.html', {'param_dict': param_dict})

    return render(request, 'shop/checkout.html')


@csrf_exempt
def handlerequest(request):
    # paytm will send you post request here
    form = request.POST
    response_dict = {}
    for i in form.keys():
        response_dict[i] = form[i]
        if i == 'CHECKSUMHASH':
            checksum = form[i]

    verify = Checksum.verify_checksum(response_dict, MERCHANT_KEY, checksum)
    if verify:
        if response_dict['RESPCODE'] == '01':
            print('order successful')
        else:
            print('order was not successful because' + response_dict['RESPMSG'])
    return render(request, 'shop/paymentstatus.html', {'response': response_dict})



def register(request):
    if request.method == 'POST':
        first_name=request.POST['first_name']
        last_name=request.POST['last_name']
        username=request.POST['username']
        password1=request.POST['password1']
        password2=request.POST['password2']
        email=request.POST['email']

        if len(password1)>=8:
            if password1==password2:
                if User.objects.filter(username=username).exists():
                    messages.error(request,"username taken pleaser enter another username")
                    return redirect('/')
                elif User.objects.filter(email=email).exists():
                    messages.error(request,"This email is already registered with us please change the email")
                    return redirect('/')

                else:
                    user=User.objects.create_user(username=username,password=password1,email=email,first_name=first_name,last_name=last_name)
                    user.save()    
                    return redirect('/')

            else:
                messages.error(request,"password not matched please enter again")
                return redirect('/')
        else:
            messages.error(request,"password is too short it must be 8 character long")
            return redirect('/')
        return redirect('/')



    else:
        return HttpResponse("error 404:")


def login(request):
    if request.method =='POST':
        username=request.POST['usernamel']
        password=request.POST['password']

        user=auth.authenticate(username=username,password=password)

        if user is not None:
            auth.login(request,user)
            return redirect("/")
        else:
            messages.error(request,"invalid credential")
            return redirect("/")

    else:
        return HttpResponse("error:404")

def logout(request):
    auth.logout(request)
    return redirect('/')
