import logging

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from django_facebook.api import get_persistent_graph, FacebookUserConverter, require_persistent_graph

logger = logging.getLogger(__name__)

@login_required
def logged_home(request):
  graph = require_persistent_graph(request)
  #print graph.fql("SELECT uid2 FROM friend WHERE uid1 IN ( SELECT uid FROM user WHERE uid=me() )");
  return render_to_response('home/logged-home.html', {'graph': graph, 'profile_pic': graph.my_image_url}, context_instance = RequestContext(request) );  

