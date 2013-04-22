from django.contrib import admin
from fb_client.apps.fbschema.models import *

class FacebookUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'about_me')

class FacebookAlbumAdmin(admin.ModelAdmin):
    list_display = ('owner', 'name', 'description', 'user')

class FacebookPhotoAdmin(admin.ModelAdmin):
    list_display = ('owner', 'caption', 'src_big', 'aid', 'user')

class FacebookLinkAdmin(admin.ModelAdmin):
    list_display = ('owner', 'title', 'summary', 'url')
    list_filter = ('owner',)

admin.site.register(FacebookUser, FacebookUserAdmin)
admin.site.register(FacebookAlbum, FacebookAlbumAdmin)
admin.site.register(FacebookPhoto, FacebookPhotoAdmin)
admin.site.register(FacebookLink, FacebookLinkAdmin)
