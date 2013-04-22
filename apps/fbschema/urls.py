from django.conf.urls.defaults import *

urlpatterns = patterns('apps.fbschema.views',
    url(r'table/user$', 'table_user', name='fbschema_table_user'),
    url(r'table/friend$', 'table_friend', name='fbschema_table_friend'),
    url(r'table/user_friends_batch$', 'table_user_friends_batch', name='fbschema_table_user_friends_batch'),
    
    url(r'table/like$', 'table_like', name='fbschema_table_like'),
    url(r'table/like_friends_batch$', 'table_like_friends_batch', name='fbschema_table_like_friends_batch'),
    
    url(r'table/album$', 'table_album', name='fbschema_table_album'),
    url(r'table/album_friends_batch$', 'table_album_friends_batch', name='fbschema_table_album_friends_batch'),
    
    url(r'table/photo$', 'table_photo', name='fbschema_table_photo'),
    url(r'table/photo_friends_batch$', 'table_photo_friends_batch', name='fbschema_table_photo_friends_batch'),
    
    url(r'table/notification$', 'table_notification', name='fbschema_table_notification'),
    
    url(r'table/link_$', 'table_link', name='fbschema_table_link_'),
    url(r'table/link_friends_batch$', 'table_link_friends_batch', name='fbschema_table_link_friends_batch'),
    url(r'table/link$', 'table_link_save_update', name='fbschema_table_link'),
    
    url(r'table/stream$', 'table_stream', name='fbschema_table_stream'),
)   

