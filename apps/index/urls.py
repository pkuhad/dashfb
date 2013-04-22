from django.conf.urls.defaults import *

urlpatterns = patterns('fb_client.apps.index.views',
    url(r'^$', 'index', name='index'),
    url(r'connect$', 'connect', name='index_facebook_connect'),
    url(r'test$', 'test_view', name='index_test_view'),
)   

