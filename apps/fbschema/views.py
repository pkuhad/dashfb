import logging

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse

from apps.fbschema.models import *

from django_facebook.api import require_persistent_graph


logger = logging.getLogger(__name__)


def table_user(request):
    '''
    To Fetch, Parse and Store user table data
    '''
    graph = require_persistent_graph(request)
    response_data = graph.fql(FacebookUser.fql_query('WHERE uid=me()'))

    response_data_dict = response_data[0]
    data_dict = FacebookUser.prepare_dict(response_data_dict)
    facebook_user = FacebookUser( user=request.user, **data_dict )
    facebook_user.save()
    return HttpResponse("<h2>Step 1. Successfully downloaded 'user' table. Now to download 'friend' table click here : <a href='%s'>/table/friend</a></h2> " % reverse('fbschema_table_friend'))


def table_friend(request):
    '''
    To Fetch, Parse and Store user table data
    '''
    graph = require_persistent_graph(request)
    response_data = graph.fql(FacebookFriend.fql_query('WHERE uid1=me()'))
    print("Hello")

    for response_data_dict in response_data:
        data_dict = FacebookFriend.prepare_dict(response_data_dict) 
        facebook_friend = FacebookFriend( user=request.user, **data_dict )
        facebook_friend.save()

    return HttpResponse("<h2>Step 2. Successfully downloaded 'friend' table. Now we will download all friends' profiles and store them in facebook_user table. Importing all friends in a single request will throw facebookapi timeout error, hence we do 100 at a time. To start it click here : <a href='%s'>/table/user_friends_batch</a>. You can always look at your command terminal while django's testserver is printing mysterious things, it just feels good. " % reverse('fbschema_table_user_friends_batch'))



import pprint
pp = pprint.PrettyPrinter(indent=4)


def table_user_friends_batch(request):
    '''
    I am using batch queries, let us taste performance gain
    '''
    graph = require_persistent_graph(request)
    query_dict = {}
    for friend in FacebookFriend.objects.all()[:100]: 
        # Conclusion 100 batched queries at a time are enough for a while
        # My current problem is not to use broker, so deferring it. What I can do with data and for the problem is the question.
        query_dict[friend.id] = FacebookUser.fql_query("WHERE uid=%d" % friend.uid2)
   

    response_dataset = graph.batch_fql(query_dict)
    for response_data in response_dataset.values():
        try:
            response_data_dict = response_data[0]
            data_dict = FacebookUser.prepare_dict(response_data_dict)
            facebook_user = FacebookUser( user=request.user, **data_dict )
            facebook_user.save()
        except IndexError:
            logger.info("A user query returned no information")
    #pp.pprint(response_data)
    return HttpResponse("<h2>Step 3. Congratulations! You have downloaded profiles of your first hundred friends. Don't believe me ? You can always look at these profiles using django's admin interface. Just don't forget to login into admin using different browser not messing up with this session. Now we will download 'like' table, click here : <a href='%s'>/table/table_like</a>." % reverse('fbschema_table_like'))


def table_like(request):
    '''
    User Likes
    '''
    graph = require_persistent_graph(request)
    response_data = graph.fql(FacebookLike.fql_query('WHERE user_id=me()'))

    for response_data_dict in response_data:
        data_dict = FacebookLike.prepare_dict(response_data_dict, request) 
        print data_dict
        facebook_like = FacebookLike(**data_dict) 
        facebook_like.save()
    return HttpResponse("<h2>Step 4. We have downloaded your like table. Facebook doesn't allow you to download your friends like information without their permission. Now we will start downloading 'album' table. First all your albums, click here to start with 'album' FQL table : <a href='%s'>/table/table_album</a>." % reverse('fbschema_table_album'))
    

def table_like_friends_batch(request):
    '''
    table_like => me and my friends => my friends in batch queries => table_like_friends_batch
    Warning: work under construction
    '''
    # OpenFacebookException at /table/like_friends_batch
    # The indexed user_id queried on must be the logged in user
    # Note: that means we can fetch user_id[s?] if we have object_id, but we cannot fetch all object_ids for a give user_id [ makes sense ]

    graph = require_persistent_graph(request)
    query_dict = {}
    for friend in FacebookFriend.objects.all()[:100]: 
        query_dict[friend.id] = FacebookLike.fql_query("WHERE user_id=%d" % friend.uid2)
   
    response_dataset = graph.batch_fql(query_dict)
    for response_data in response_dataset.values():
        response_data_dict = response_data[0]
        data_dict = FacebookLike.prepare_dict(response_data_dict, request)
        facebook_like = FacebookLike(**data_dict) 
        facebook_like.save()

    return HttpResponse("Hello World")


def table_album(request):
    '''
    table album
    '''
    context_model = FacebookAlbum
    graph = require_persistent_graph(request)
    response_data = graph.fql(context_model.fql_query_me())
    context_model.save_update_delete(request, response_data)
    return HttpResponse("<h2>Step 5. We have downloaded your album information. Now we do the same for your first hundred friends i.e. we are downloading album information of your first hundred friends ( Not all at once ). Click here to start with 'album' FQL table for your friends' albums : <a href='%s'>/table/table_album_friends_batch</a>." % reverse('fbschema_table_album_friends_batch'))


def table_album_friends_batch(request):
    '''
    table album for friends
    '''
    graph = require_persistent_graph(request)
    query_dict = {}
    for friend in FacebookFriend.objects.all()[:100]: # 100
        query_dict[friend.id] = FacebookAlbum.fql_query("WHERE owner=%d" % friend.uid2)
   
    response_dataset = graph.batch_fql(query_dict)
    for response_data in response_dataset.values():
        for response_data_dict in response_data:
            data_dict = FacebookAlbum.prepare_dict(response_data_dict, request)
            facebook_album = FacebookAlbum(user=request.user, **data_dict) 
            facebook_album.save()
    return HttpResponse("<h2>Step 6. Cool! You now have all album information of some of your friends, checkout the django admin or mysql table. Now we will do the same thing with 'photo' table. To start with your own photos information, click here : <a href='%s'>/table/table_photo</a>." % reverse('fbschema_table_photo'))


def table_photo(request):
    '''
    table photo
    '''
    # depends on Album  i.e. for a photo its parent album should exist
    context_model = FacebookPhoto
    graph = require_persistent_graph(request)
    response_data = graph.fql(context_model.fql_query_me())
    context_model.save_update_delete(request, response_data)

    '''
    graph = require_persistent_graph(request)
    response_data = graph.fql(FacebookPhoto.fql_query('WHERE owner=me() limit 5000'))

    for response_data_dict in response_data:
        data_dict = FacebookPhoto.prepare_dict(response_data_dict, request) 
        #print data_dict
        facebook_photo = FacebookPhoto(user=request.user, **data_dict) 
        facebook_photo.save()
    '''
    return HttpResponse("<h2>Step 7. Great, now you have all your facebook photos information. We do the same for your friends, and this time we process 2 friends at a time ( have a look in code ) as photo counts can be huge for each friend. Click here : <a href='%s'>/table/table_photo_friends_batch</a>." % reverse('fbschema_table_photo_friends_batch'))



def table_photo_friends_batch(request):
    '''
    table photo for friends
    '''
    context_model = FacebookPhoto
    
    graph = require_persistent_graph(request)
    query_dict = {}
    for friend in FacebookFriend.objects.all()[2:4]: # 2
        query_dict[friend.id] = context_model.fql_query_my_friends(friend.uid2)
    
    response_dataset = graph.batch_fql(query_dict)
    for response_data in response_dataset.values():
        if response_data:
            context_model.save_update_delete(request, response_data)

    return HttpResponse("<h2>Step 8. Now to download 'notification' table. Click here : <a href='%s'>/table/table_notification</a>." % reverse('fbschema_table_notification'))


def table_notification(request):
    '''
    table notification
    '''
    context_model = FacebookNotification
    graph = require_persistent_graph(request)
    response_data = graph.fql(context_model.fql_query_me())
    context_model.save_update_delete(request, response_data, stream_nature=True)
    return HttpResponse("<h2>Step 9. Facebook deletes all notifications older than 7 days, we have downloaded all available. But we can download all your shared links on facebook from 'link' FQL table ! Click here - : <a href='%s'>/table/table_link</a>." % reverse('fbschema_table_link'))
    


def table_link(request):
    '''
    table link
    '''
    #@see table_link_save_update
    return HttpResponse("Hello World")


def table_link_friends_batch(request):
    '''
    table link for friends
    '''
    context_model = FacebookLink
    
    graph = require_persistent_graph(request)
    query_dict = {}
    for friend in FacebookFriend.objects.all()[:3]: # 3
        query_dict[friend.id] = context_model.fql_query_my_friends(friend.uid2)
    
    response_dataset = graph.batch_fql(query_dict)
    for response_data in response_dataset.values():
        if response_data:
            context_model.save_update_delete(request, response_data)

    return HttpResponse("<h2>Step 11. Finally in this alpha demo we download your stream posts from 'stream' FQL table. Click here - : <a href='%s'>/table/table_stream</a>." % reverse('fbschema_table_stream'))



def table_stream(request):
    '''
    table stream
    '''
    context_model = FacebookStream    
    graph = require_persistent_graph(request)
    response_data = graph.fql(context_model.fql_query_me())
    context_model.save_update_delete(request, response_data, stream_nature=True)
    return HttpResponse("<h2>Successfully done. Do checkout the project on github and help me to implement more fql tables and do more awesome things with locally hosted fql tables.")

### Save update labs :
def table_link_save_update(request):
    '''
    table link : Save update
    '''
    context_model = FacebookLink
    graph = require_persistent_graph(request)
    response_data = graph.fql(context_model.fql_query_me())
    context_model.save_update_delete(request, response_data)

    return HttpResponse("<h2>Step 10. Now to download all shared links by your friends (3 at a time)  ! Click here - : <a href='%s'>/table/table_link_friends_batch</a>." % reverse('fbschema_table_link_friends_batch'))


