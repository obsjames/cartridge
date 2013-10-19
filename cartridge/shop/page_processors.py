
from django.template.defaultfilters import slugify

from mezzanine.conf import settings
from mezzanine.pages.page_processors import processor_for
from mezzanine.utils.views import paginate

from cartridge.shop.models import Category, Product

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from stores.utils import send_customer_subscription_email
from stores.forms import NoStoresForm
from stores.checkout import new_location_get_ids, new_location_get_categories, cart_loaded_get_details
from stores.checkout import cart_not_loaded_get_details, have_location_get_categories_products
from stores.location_utils import getAddress, getLocation

import ast, json

@processor_for(Category)
def category_processor(request, page):
    """
    Add paging/sorting to the products for the category.
    """
    settings.use_editable()

    if 'map' in request.session:
        map_required = True
        del request.session['map']
    else:
        map_required = False

    if 'new location' not in request.session and 'location' not in request.session:
        return HttpResponseRedirect('/')

    elif 'new location' in request.session and 'age' in request.session:
        loc = getLocation(request.session['new location'])
        request.session['location'] = (loc[0],loc[1])
        address = getAddress(loc[0],loc[1])
        request.session['address'] = address
        del request.session['new location']

        avail_store_ids, avail_store_names, avail_liquor_types, loc, store_locs = new_location_get_ids(request, loc)

        if avail_store_ids:
            child_categories = new_location_get_categories(request, page, avail_store_names, avail_liquor_types)
            context = {'map' : map_required, 'lat' : loc[0], 'lon' : loc[1], 'store_locs': store_locs,
                       "child_categories": child_categories, "products": True}        #Products True?
            return context

        else:
            form = NoStoresForm()
            context = {'map' : map_required, 'lat' : loc[0], 'lon' : loc[1], 'store_locs': store_locs, 'form': form,
                       "products": False}
            return context

    elif 'location' in request.session and 'age' in request.session:

        loc = request.session['location']

        if 'cart loaded' in request.session:
            cart_loaded = True
            published_products, avail_stores, avail_store_names, avail_liquor_types, stores, store_locs = cart_loaded_get_details(request, page, loc)

        else:
            cart_loaded = False
            avail_store_ids = request.session['store ids']

            if avail_store_ids:
                published_products, avail_stores, avail_store_names, avail_liquor_types, stores, store_locs = cart_not_loaded_get_details(request, page, avail_store_ids, loc)
            else:
                if request.method == 'POST': # If the form has been submitted...
                    form = NoStoresForm(request.POST) # A form bound to the POST data
                    if form.is_valid():
                            first_name = form.cleaned_data['first_name']
                            last_name = form.cleaned_data['last_name']
                            email = form.cleaned_data['email']
                            local_store = form.cleaned_data['local_store']

                            send_customer_subscription_email(request,first_name,last_name,email,local_store)

                            return HttpResponseRedirect('/subscribe/thanks/') # Redirect after POST      
                else:
                    form = NoStoresForm() # An unbound form

                context = {'map' : map_required, 'lat' : loc[0], 'lon' : loc[1], 'form': form,
                           "products": False}
                return context

        products, child_categories = have_location_get_categories_products(request, page, published_products, avail_stores, avail_store_names, avail_liquor_types)

        context = {'map' : map_required, 'lat' : loc[0], 'lon' : loc[1], 'store_locs': store_locs, "cart_loaded" : cart_loaded,
                   "stores" : stores, "products": products, "child_categories": child_categories}
        return context

    else:
        return render(request, '/')

