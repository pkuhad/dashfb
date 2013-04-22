from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'views.home', name='home'),
    # url(r'^fb_client/', include('foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    
    # App 'Index'
    url(r"^", include('apps.index.urls'), name="index"),

    # App 'Home'
    url(r"^", include('apps.home.urls'), name="home"),
    
    # App 'Fbschema'
    url(r"^", include('apps.fbschema.urls'), name="fbschema"),

    # Third party App 'Django Facebook'
    url(r'^facebook/', include('django_facebook.urls')),
    url(r'^accounts/', include('django_facebook.auth_urls')), 
)

