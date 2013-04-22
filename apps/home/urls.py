from django.conf.urls.defaults import *

urlpatterns = patterns('fb_client.apps.home.views',
    url(r'home$', 'logged_home', name='home_logged_home'),
)   

