
from django.template.defaultfilters import slugify

from mezzanine.conf import settings
from mezzanine.pages.page_processors import processor_for
from mezzanine.utils.views import paginate

from mezzanine.core.managers import SearchableQuerySet

from cartridge.shop.models import Category, Product

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import redirect

from stores.utils import send_customer_subscription_email
from stores.forms import NoStoresForm
from stores.checkout import find_stores, cart_get_products, get_products_and_stores, get_categories_and_products
from stores.location_utils import getAddress, getLocation

from stores.forms import ProductFilterForm

import ast, json

@processor_for(Category)
def category_processor(request, page):
    """
    Add paging/sorting to the products for the category.
    """
    settings.use_editable()

    if 'new location' not in request.session and 'location' not in request.session:
        return HttpResponseRedirect('/')

    elif 'new location' in request.session and 'age' in request.session:
        loc = getLocation(request.session['new location'])
        request.session['location'] = (loc[0],loc[1])
        address = getAddress(loc[0],loc[1])
        request.session['address'] = address
        del request.session['new location']

	if 'store ids' in request.session:
            del request.session['store ids']
            del request.session['store names']
            del request.session['store locs']


    elif 'location' in request.session and 'age' in request.session:
        loc = request.session['location']
	address = request.session['address']

    else:
        return HttpResponseRedirect('/')

    if 'map' in request.session:
        map_required = True
        del request.session['map']
    else:
        map_required = False

    if 'cart loaded' in request.session:
        cart_loaded = True
        published_products, avail_stores, avail_store_names, stores, store_locs = cart_get_products(request, page, loc)
	closed_store_names, closed_locs = [], []
	store_slug = request.session['store slug']	

    else:
	cart_loaded = False
	store_slug = False

	if 'new query' in request.session:
	    return redirect('search')

    	if 'store ids' in request.session:
	    avail_store_ids, avail_store_names, store_locs = request.session['store ids'], request.session['store names'], request.session['store locs']
	    closed_store_ids, closed_store_names, closed_locs = request.session['closed store ids'], request.session['closed store names'], request.session['closed store locs']
	else:
            avail_store_ids, avail_store_names, store_locs, closed_store_ids, closed_store_names, closed_locs = find_stores(request, loc)

    	if avail_store_ids or closed_store_ids:
            published_products, avail_stores, stores, store_locs = get_products_and_stores(request, page, avail_store_ids, loc)
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

            context = {'map' : map_required, 'lat' : loc[0], 'lon' : loc[1], 'form': form, 'store_locs': [], "address": address}
            return context

    liquor1, liquor2, form1_name, form2_name, prefix1, prefix2 = get_categories_and_products(published_products)

    prod_ids, form1, form2 = [], [], []

    filter_form = False
    if liquor1:
	filter_form = True
        if request.method == 'POST':
            form1 = ProductFilterForm(request.POST, products=liquor1)
            if form1.is_valid():
                for liquor in liquor1:
                    if form1.cleaned_data["%s" % liquor]:
			prod_ids.extend([p.id for p in published_products.filter(product_type__exact="%s %s" % (prefix1, liquor))])
			
        else:
            form1 = ProductFilterForm(products=liquor1)

    if liquor2:
	filter_form = True
        if request.method == 'POST':
            form2 = ProductFilterForm(request.POST, products=liquor2)
            if form2.is_valid():
                for liquor in liquor2:
                    if form2.cleaned_data["%s" % liquor]:
			prod_ids.extend([p.id for p in published_products.filter(product_type__exact="%s %s" % (prefix2, liquor))])
        else:
            form2 = ProductFilterForm(products=liquor2)

    if not prod_ids:
        products = published_products
    else:
    	products = Product.objects.filter(id__in=prod_ids)

    sort_options = [(slugify(option[0]), option[1])
                for option in settings.SHOP_PRODUCT_SORT_OPTIONS]
    sort_by = request.GET.get("sort", sort_options[0][1])
    products = paginate(products.order_by(sort_by),
                    request.GET.get("page", 1),
                    settings.SHOP_PER_PAGE_CATEGORY,
                    settings.MAX_PAGING_LINKS)
    products.sort_by = sort_by

    sub_categories = [p.titles for p in page.category.children.published()]
    avail_stores = list(set(sub_categories) & set(avail_store_names))
    child_categories = Category.objects.filter(titles__in=avail_stores)

    closed_stores = list(set(sub_categories) & set(closed_store_names))
    closed_child_categories = Category.objects.filter(titles__in=closed_stores)

    context = {'map' : map_required, 'lat' : loc[0], 'lon' : loc[1], 'store_locs': store_locs, "cart_loaded" : cart_loaded,
               "stores" : stores, "products": products, "child_categories": child_categories, "store_slug": store_slug,
	       "form1": form1, "form2": form2, "form1_name": form1_name, "form2_name": form2_name, "address": address,
	       "filter_form": filter_form, "closed_child_categories": closed_child_categories, 'closed_locs': closed_locs}
    return context

