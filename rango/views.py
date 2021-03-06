from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render

from rango.bing_search import run_query
from rango.forms import CategoryForm
from rango.forms import PageForm
from rango.models import Category, UserProfile
from rango.models import Page


def index(request):
    # Query the database for a list of ALL categories currently stored.
    # Order the categories by no. likes in descending order.
    # Retrieve the top 5 only - or all if less than 5.
    # Place the list in our context_dict dictionary which will be passed to the template engine.
    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories': category_list, 'pages': page_list}

    # Get the number of visits to the site.
    # We use the COOKIES.get() function to obtain the visits cookie.
    # If the cookie exists, the value returned is casted to an integer.
    # If the cookie doesn't exist, we default to zero and cast that.
    visits = request.session.get('visits')
    if not visits:
        visits = 1
    reset_last_visit_time = False

    last_visit = request.session.get('last_visit')
    if last_visit:
        last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")

        if (datetime.now() - last_visit_time).days > 0:
            # ...reassign the value of the cookie to +1 of what it was before...
            visits = visits + 1
            # ...and update the last visit cookie, too.
            reset_last_visit_time = True
    else:
        # Cookie last_visit doesn't exist, so create it to the current date/time.
        reset_last_visit_time = True

    if reset_last_visit_time:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = visits
    context_dict['visits'] = visits


    response = render(request,'rango/index.html', context_dict)

    return response

def about(request):

    # Construct a dictionary to pass to the template engine as its context.
    # Note the key boldmessage is the same as {{ boldmessage }} in the template!
    context_dict = {'standardmessage': "This tutorial has been put together by Enzo Roiz, 2161561."}
    
    # If the visits session varible exists, take it and use it.
    # If it doesn't, we haven't visited the site so set the count to zero.
    if request.session.get('visits'):
        visits = request.session.get('visits')
    else:
        visits = 0
    
    context_dict['visits'] = visits

    # Return a rendered response to send to the client.
    # We make use of the shortcut function to make our lives easier.
    # Note that the first parameter is the template we wish to use.

    return render(request, 'rango/about.html', context_dict)

def category(request, category_name_slug):

    # Create a context dictionary which we can pass to the template rendering engine.
    context_dict = {}
   
    try:
        # Can we find a category name slug with the given name?
        # If we can't, the .get() method raises a DoesNotExist exception.
        # So the .get() method returns one model instance or raises an exception.
        category = Category.objects.get(slug=category_name_slug)
        context_dict['category_name'] = category.name
        
        # Count the category views
        try:
            category.views = category.views + 1
            category.save()
        except:
                pass

        # Retrieve all of the associated pages.
        # Note that filter returns >= 1 model instance.
        pages = Page.objects.filter(category=category).order_by('-views')
        
        # Adds our results list to the template context under name pages.
        context_dict['pages'] = pages
        # We also add the category object from the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category

        #Category Slug
        context_dict['category_slug'] = category.slug

    except Category.DoesNotExist:
        # We get here if we didn't find the specified category.
        # Don't do anything - the template displays the "no category" message for us.
        pass

    # Go render the response and return it to the client.
    return render(request, 'rango/category.html', context_dict)

@login_required
def add_category(request):
    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            # Save the new category to the database.
            form.save(commit=True)

            # Now call the index() view.
            # The user will be shown the homepage.
            return index(request)
        else:
            # The supplied form contained errors - just print them to the terminal.
            print form.errors
    else:
        # If the request was not a POST, display the form to enter details.
        form = CategoryForm()

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render(request, 'rango/add_category.html', {'form': form})

@login_required
def add_page(request, category_name_slug):

    try:
        cat = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
                cat = None

    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if cat:
                page = form.save(commit=False)
                page.category = cat
                page.views = 0
                page.save()
                # probably better to use a redirect here.
                return category(request, category_name_slug)
        else:
            print form.errors
    else:
        form = PageForm()

    context_dict = {'form':form, 'category': cat}

    def clean(self):
        cleaned_data = self.cleaned_data
        url = cleaned_data.get('url')

        # If url is not empty and doesn't start with 'http://', prepend 'http://'.
        if url and not url.startswith('http://'):
            url = 'http://' + url
            cleaned_data['url'] = url

        return cleaned_data

    return render(request, 'rango/add_page.html', context_dict)

@login_required
def restricted(request):
    return render(request, 'rango/restricted.html')

def track_url(request):
    page_id = None
    url = '/rango/'
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                pass

    return redirect(url)

@login_required
def like_category(request):
    cat_id = None
    if request.method == 'GET':
        cat_id = request.GET['category_id']

    likes = 0
    if cat_id:
        cat = Category.objects.get(id=int(cat_id))
        if cat:
            likes = cat.likes + 1
            cat.likes =  likes
            cat.save()

    return HttpResponse(likes)

def suggest_category(request):
    
    def get_category_list(max_results=0, starts_with=''):
        cat_list = Category.objects.all()
        if starts_with:
            cat_list = Category.objects.filter(name__istartswith=starts_with)

        if max_results > 0:
            if len(cat_list) > max_results:
                cat_list = cat_list[:max_results]

        return cat_list

    starts_with = ''
    catid = None
    act_cat = None
    
    if request.method == 'GET':
        starts_with = request.GET['suggestion']
        if request.GET['catid'] != '':
            catid = request.GET['catid']
            act_cat = Category.objects.get(id=catid)
            
    cats = get_category_list(8, starts_with)
    
    return render(request, 'rango/cats.html', {'cats': cats, 'act_cat': act_cat })

def category_search(request):
    context_dict = {}
    context_dict['result_list'] = None 
    context_dict['query'] = None
    print "HERE WE ARE"
    if request.method == 'GET':
        query = request.GET['query'].strip()
        print "HERE WE GO"
        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)

            context_dict['result_list'] = result_list
            context_dict['query'] = query
    print "AFTER ALL"
    
    return render(request, 'rango/category_search.html', context_dict)

@login_required
def profile(request, username):
    act_user = User.objects.get(username=username)
    userprofile, created = UserProfile.objects.get_or_create(user=act_user)
    
    if request.method == 'POST':
        if 'is_password' in request.POST:
            print "IS_PASSWORD"
            data = {}
            if 'old_password' in request.POST:
                data['old_password'] = request.POST['old_password']
            if 'new_password1' in request.POST:
                data['new_password1'] = request.POST['new_password1']
            if 'new_password2' in request.POST:
                data['new_password2'] = request.POST['new_password2']
            form = PasswordChangeForm(act_user, data)
            if form.is_valid():
                form.save(commit=True)
                act_user.save()
                user = authenticate(username=username, password=data['new_password1'])
                login(request, user)
                messages.success(request, 'Password changed.')
                print messages
                return render(request, 'rango/profile.html', {'userprofile': userprofile, 'act_user': act_user, 'user':user })
            else:
                if form.errors:
                    print form.errors
                return render(request, 'rango/profile.html', {'userprofile': userprofile, 'act_user': act_user, 'user':act_user, 'form':form})
        else:
            if 'email' in request.POST:
                act_user.email = request.POST['email']
            if 'website' in request.POST:
                userprofile.website = request.POST["website"]
            if 'picture' in request.FILES:
                userprofile.picture = request.FILES["picture"]
            
            userprofile.save()
            act_user.save()
            messages.success(request, 'Profile details updated.')
    
    print messages, "aas"    
    
    return render(request, 'rango/profile.html', {'userprofile': userprofile, 'act_user': act_user })

@login_required
def edit_profile(request):
    user = request.user
    userprofile = UserProfile.objects.get(user=user)
    return render(request, 'rango/edit_profile.html', {'user':user, 'userprofile':userprofile})

@login_required
def change_password(request):
    user = request.user
    userprofile = UserProfile.objects.get(user=user)
    return render(request, 'rango/change_password.html', {'user':user, 'userprofile':userprofile})

@login_required
def users_profiles(request):
    user_list = User.objects.all()
    userprofile_list = UserProfile.objects.all()
    return render(request, 'rango/users_profiles.html', {'user_list' : user_list, 'userprofile_list' : userprofile_list})