import logging

from django.db import models
from django.contrib.auth.models import User
from django.db import IntegrityError

from fb_client.apps.fbschema.struct_models import *
from fb_client.apps.fbschema.utils import get_fql_from_model

from fb_client.apps.fbschema.utils import compare_keys_with_fields

logger = logging.getLogger(__name__)

class BaseFbModel(models.Model):
    '''
    Abstract class to define some common method helping us to generate queries 
    '''
    ignore_fields=['id', 'user']

    @classmethod
    def fql_query(self, clause):
        '''
        Returns the fql query made from model's fields. As it is operated on class itself 
        rater than its instance hence @classmethod
        '''
        return get_fql_from_model(self, clause)

    @classmethod
    def fql_query_me(self):
        '''
        Returns the fql query using fql_query method. Clause is specific to return data tuples which are 
        associated directly with user itself, i.e. owner = me() in fql
        '''
        return self.fql_query(self.me_clause)

    @classmethod
    def fql_query_my_friends(self, friend_uid):
        '''
        Returns the fql query using fql_query method. Clause is specific to return data tuples which are 
        associated directly with user's freinds, i.e. owner = %d  in fql
        '''
        return self.fql_query(self.my_friend_clause % friend_uid)
    
    @classmethod
    def local_fql_query(self, request, context_uid):
        '''
        Returns user related tuple from database model if no friend_uid is mentioned
        Returns user's friend related tuple from database model if friend_uid has ben mentioned
        These returned tuple will be used to generate model_sets so that we can compare it with result sets
        '''
        if not context_uid:
            logger.info("context_uid is None due to owner_identifier=ONLY_SESSION_USER, fetching last `facebook_row_limit` tuples to compare with result data set")
            print("context_uid is None due to owner_identifier=ONLY_SESSION_USER, fetching last `facebook_row_limit` tuples to compare with result data set")
            return self.objects.all()[:self.facebook_row_limit]

        facebookuser = FacebookUser.objects.get(user=request.user, uid=context_uid)
        kwargs = { self.owner_identifier : facebookuser }
        return self.objects.filter(user=request.user, **kwargs)

    @classmethod
    def primary_identifier_class(self):
        '''
        Returns the class name of primary identifier for a particular model, useful when we want to perform cleaning operation
        '''
        return [ field for field in self._meta.fields if getattr(field, 'name') == self.primary_identifier ][0]

    @classmethod
    def prepare_dict(self, response_data_dict, request=None):
        from fb_client.apps.fbschema.parse_utils import parse_clean_field_value
        '''
        Receives the response from fql graph query. Cleans/Parses the data and returns a valid
        dict that can be used to create and save a tuple/data-record.
        Applied operations on data in this process is in context with the model in concern, hence
        it should be called with proper database model, otherwise compare key function will fail
        '''
        if not compare_keys_with_fields(self, response_data_dict.keys()): #TODO: This compare test is happening for each tuple, can we do better ?
            raise ValueError #TODO: Use proper exception

        model = self # Just to make code more readable

        data_dict = {}
        fields = [field for field in model._meta.fields if getattr(field, 'name') not in model.ignore_fields]
        for field in fields:
            field_name = getattr(field, 'name')
            key = field_name
            value = parse_clean_field_value(field, response_data_dict[key], request)
            data_dict[key] = value

        return data_dict

    @classmethod
    def save_update_delete(self, request, response_data, stream_nature=False):
        from fb_client.apps.fbschema.parse_utils import parse_clean_field_value
        ''' 
        Main function which saves, updates and deletes on updated result sets 
        This function is always called with subclasses 
        @stream_nature = For example facebook stream is a stream of incoming items. If we compare last 'n' number of database items with incoming
                         response items and if we don't define stream_nature then existing code will delete those old database items assuming 
                         they don't exist, hence is a stream in which we always save and update, we never delete
        @ONLY_SESSION_USER = local_fql_query uses 'owner_identifier' so that it can bring database items in context to compare with response items.
                             context_uid is usally me() or a freind's uid, but in some tables only session user is allowed so there is no need of 
                             context_uid so we return 'n' last number of records OR all records
        '''
        if self.owner_identifier == "ONLY_SESSION_USER":
            context_uid = None
        else:
            context_uid = response_data[0][self.owner_identifier]
            #Assumptions response_data (list) has some values (dict)

        model_data_list = self.local_fql_query(request, context_uid) 

        primary_identifier = self.primary_identifier
    
        #Response data set of 'primary key', we also need to make sure that data we are compared are 'cleaned'
        response_data_set = set([parse_clean_field_value( self.primary_identifier_class(), response_data_dict[primary_identifier] ) \
                                for response_data_dict in response_data])
    
        #Model data set of 'primary key'
        model_data_set = set([getattr(model_data, primary_identifier) for model_data in model_data_list])
   
        #Delete list
        if stream_nature:
            delete_list = []
        else:
            delete_list = list(model_data_set.difference(response_data_set))
        #Add List
        add_list = list(response_data_set.difference(model_data_set))
        #Update List
        update_list = list(response_data_set.intersection(model_data_set))
        print response_data_set
        print model_data_set
        print add_list
        print update_list
        

        for response_data_dict in response_data:
            data_dict = self.prepare_dict(response_data_dict, request) 
            if data_dict[primary_identifier] in add_list:
                #Add here
                try:
                    data_tuple = self(user=request.user, **data_dict) 
                    data_tuple.save()
                except IntegrityError:
                    '''
                    There are some cases where due to facebook data nature we expect integrity error within ids being saved.
                    This exception should be handled by that particular model which is expecting this case.
                    A use case : FacebookStream
                    with some post_id : 'x' changed his profile picture
                    with same post_id : 'x' and seven others changed profile pictures
                    '''
                    logger.info("Integrity Exception handled, Model = %s" % self.__class__)
                    print("Integrity Exception handled, Model = %s" % self.__class__)
                    data_tuple = self.handle_integrity_exception(request, data_dict)
                    data_tuple.save()
            elif data_dict[primary_identifier] in update_list:
                #Update here
                kwargs = { primary_identifier : data_dict[primary_identifier] }
                data_tuple = self.objects.get(user=request.user, **kwargs)
                data_tuple = self(user=request.user, id=data_tuple.id, **data_dict) 
                data_tuple.save()
    

    class Meta:
        abstract = True


'''
Until unless 'Facebook' Prefix is specified the model names and field names are exact as facebook schemas. Target is to avoid any confusion, we are just
looking for the data
'''
class FacebookAlbum(BaseFbModel):
    '''
    Album Table
    '''
    '''
    Interesting:
    1) uid can be me and my friends, that means this model is going to store all albums in my social graph ( or more than that : out of focus right now )
    2) #Me and #My Friends = Two UID clusters
    '''
    fqlname             = "album"
    primary_identifier  = "aid"
    owner_identifier    = "owner"
    me_clause           = "WHERE owner=me()"
    my_friend_clause    = "WHERE owner=%d" 
    
    ## Django Application specific fields
    user                = models.ForeignKey(User, help_text="Data belongs with this system user: Viewer") 

    ## Fb Schema specific fields
    aid                 = models.CharField( db_index=True, max_length=100, help_text="The album ID" ) 
    #TODO: aid is not biginteger ? invalid literal for int() with base 10: '100000001295087_31004'
    backdated_time      = models.DateTimeField( blank=True, null=True, help_text="Time that the album is backdated to" )
    can_backdate        = models.NullBooleanField( blank=True, null=True, help_text="Can the album be backdated on Timeline" )
    can_upload          = models.NullBooleanField( blank=True, null=True, help_text="Determines whether a given UID can upload to the album. It is true\
                          if the following conditions are met: The user owns the album, the album is not a special album like the profile pic\
                          album, the album is not full.")
    comment_info        = models.ForeignKey( StructCommentInfo, blank=True, null=True)
    cover_object_id     = models.BigIntegerField( help_text="The album cover photo object_id" )
    cover_pid           = models.BigIntegerField( help_text="The album cover photo ID string" )
    created             = models.DateTimeField( blank=True, null=True, help_text="The time the photo album was initially created expressed as UNIX time." )
    description         = models.TextField( blank=True, null=True, help_text="The description of the album")
    edit_link           = models.CharField( max_length=500, blank=True, null=True, help_text="The URL for editing the album")
    is_user_facing      = models.NullBooleanField( blank=True, null=True, help_text="Determines whether or not the album should be shown to users." )
    like_info           = models.ForeignKey( StructLikeInfo, blank=True, null=True )
    link                = models.CharField( max_length=500, blank=True, null=True, help_text="A link to this album on Facebook")
    location            = models.CharField( max_length=100, blank=True, null=True, help_text="The location of the album")
    modified            = models.DateTimeField( blank=True, null=True, help_text="The last time the photo album was updated expressed as UNIX time." )
    modified_major      = models.DateTimeField( blank=True, null=True, help_text="Indicates the time a major update (like addition of photos)\
                          was last made to the album expressed as UNIX time." )
    name                = models.TextField( blank=True, null=True, help_text="The title of the album")
    object_id           = models.BigIntegerField( db_index=True, help_text="The object_id of the album on Facebook.") 
    owner               = models.ForeignKey('FacebookUser', related_name="albums", help_text="The user ID of the owner of the album")
    owner_cursor        = models.CharField( max_length=100, blank=True, null=True, help_text="Cursor for the owner field")
    photo_count         = models.IntegerField( blank=True, null=True, help_text="The number of photos in the album" )
    place_id            = models.BigIntegerField( blank=True, null=True, help_text="Facebook ID of the place associated with the album, if any.") 
    type                = models.CharField( max_length=50, blank=True, null=True, help_text="The type of photo album. Can be one of profile:\
                          The album containing profile pictures, mobile: The album containing mobile uploaded photos, wall: The album\
                          containing photos posted to a user's Wall, normal: For all other albums.")
    video_count         = models.IntegerField( blank=True, null=True, help_text="The number of videos in the album" )
    visible             = models.CharField( max_length=50, blank=True, null=True, help_text="Visible only to the album owner. \
                          Indicates who can see the album. The value can be one of friends, friends-of-friends, networks, everyone,\
                          custom (if the visibility doesn't match any of the other values" )

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = (("user", "object_id", "owner"),)


class FacebookPhoto(BaseFbModel):
    '''
    Photo Table
    '''
    fqlname             = "photo"
    primary_identifier  = "pid"
    owner_identifier    = "owner" # for some models object_id is going to behave like owner
    me_clause           = "WHERE owner=me() limit 5000"
    my_friend_clause    = "WHERE owner=%d limit 5000" 
    
    ## Django Application specific fields
    user                = models.ForeignKey(User, help_text="Data belongs with this system user: Viewer") 

    ## Fb Schema specific fields
    aid                 = models.ForeignKey( FacebookAlbum, blank=True, null=True, related_name="photos", help_text="The ID of the album containing the \
                          photo being queried. The aid cannot be longer than 50 characters.")

    aid_cursor          = models.CharField( max_length=100, blank=True, null=True, help_text="A cursor used to paginated through \
                          a query that is indexed on the aid")

    album_object_id     = models.BigIntegerField( db_index=True, help_text="The object_id of the album the photo belongs to") 
    album_object_id_cursor = models.CharField( max_length=100, blank=True, null=True, help_text="A cursor used to paginate through\
                          a query that is indexed on the album_object_id")
    backdated_time      = models.DateTimeField( blank=True, null=True, help_text="The time the photo was backdated to in Timeline" )
    backdated_time_granularity = models.CharField( max_length=100, blank=True, null=True, help_text="A string representing the backdated \
                          granularity. Valid values are year, month, day, hour, or minute" )
    can_backdate        = models.NullBooleanField( blank=True, null=True, help_text="true if the viewer is able to backdate the photo" )
    can_delete          = models.NullBooleanField( blank=True, null=True, help_text="true if the viewer is able to delete the photo" )
    can_tag             = models.NullBooleanField( blank=True, null=True, help_text="true if the viewer is able to tag the photo" )
    caption             = models.TextField( blank=True, null=True, help_text="The caption for the photo being queried")
    caption_tags        = models.TextField( blank=True, null=True, help_text="An array indexed by offset of arrays of the tags in the \
                          caption of the photo, containing the id of the tagged object, the name of the tag, the offset of where the \
                          tag occurs in the message and the length of the tag.")
    comment_info        = models.ForeignKey( StructCommentInfo, blank=True, null=True, help_text="The comment information of the photo \
                          being queried. This is an object containing can_comment and comment_count")
    created             = models.DateTimeField( blank=True, null=True, help_text="The date when the photo being queried was added." )
    images              = models.TextField( blank=True, null=True, help_text="An array of objects containing width, height, source each \
                          representing the various photo sizes.")
    like_info           = models.ForeignKey( StructLikeInfo, blank=True, null=True )
    link                = models.CharField( max_length=500, blank=True, null=True, help_text="The URL to the page containing the photo being queried.")
    modified            = models.DateTimeField( blank=True, null=True, help_text="The date when the photo being queried was last modified." )
    object_id           = models.BigIntegerField( db_index=True, help_text="The object_id of the photo") 
    offline_id          = models.BigIntegerField( blank=True, null=True, help_text="The object_id of the photo") 
    owner               = models.ForeignKey('FacebookUser', related_name="myphotos", help_text="The user ID of the photo being queried")
    owner_cursor        = models.CharField( max_length=100, blank=True, null=True, help_text="A cursor used to paginate through\
                          a query that is indexed on the owner" )
    page_story_id       = models.BigIntegerField( blank=True, null=True, help_text="The ID of the feed story about this photo if itbelongs to a page") 
    pid                 = models.BigIntegerField( db_index=True, blank=True, null=True, help_text="The ID of the photo being queried. \
                          The pid cannot be longer than 50 characters." ) 
    place_id            = models.BigIntegerField( blank=True, null=True, help_text="Facebook ID of the place associated with the photo, if any.") 
    position            = models.IntegerField( blank=True, null=True, help_text="The position of the photo in the album." ) 
    src                 = models.CharField( max_length=500, blank=True, null=True, help_text="The URL to the album view version of the photo \
                          being queried. The image can have a maximum width or height of 130px" )
    src_big             = models.CharField( max_length=500, blank=True, null=True, help_text="The URL to the full-sized version of the photo \
                          being queried. The image can have a maximum width or height of 720px, increasing to 960px on 1st March 2012" )
    src_big_height      = models.IntegerField( blank=True, null=True, help_text="Height of the full-sized version, in px. This field may be blank." ) 
    src_big_width       = models.IntegerField( blank=True, null=True, help_text="Width of the full-sized version, in px" ) 
    src_height          = models.IntegerField( blank=True, null=True, help_text="Height of the album view version, in px" ) 
    src_small           = models.CharField( max_length=500, blank=True, null=True, help_text="The URL to the thumbnail version of the photo \
                          being queried. The image can have a maximum width of 75px and a maximum height of 225px." )
    src_small_height    = models.IntegerField( blank=True, null=True, help_text="Height of the thumbnail version, in px. This field may be blank." ) 
    src_small_width     = models.IntegerField( blank=True, null=True, help_text="Width of the thumbnail version, in px" ) 
    src_width           = models.IntegerField( blank=True, null=True, help_text="Width of the album view version, in px" ) 
    target_id           = models.BigIntegerField( blank=True, null=True, help_text="The ID of the target the photo is posted to" ) 
    target_type         = models.CharField( max_length=100, blank=True, null=True, help_text="The type of target the photo is posted to" )
    
    class Meta:
        unique_together = (("user", "pid", "owner"),)


class FacebookLink(BaseFbModel):
    '''
    Link Table
    '''
    fqlname             = "link"
    primary_identifier  = "link_id"
    owner_identifier    = "owner" # for some models object_id is going to behave like owner
    me_clause           = "WHERE owner=me() limit 5000"
    my_friend_clause    = "WHERE owner=%d limit 5000" 
    
    ## Django Application specific fields
    user                = models.ForeignKey(User, help_text="Data belongs with this system user: Viewer") 

    ## Fb Schema specific fields
    backdated_time      = models.DateTimeField( blank=True, null=True, help_text="Time that the link is backdated to." )
    can_backdate        = models.NullBooleanField( blank=True, null=True, help_text="Can the link be backdated on Timeline" )
    caption             = models.TextField( blank=True, null=True, help_text="The caption of the link")
    comment_info        = models.ForeignKey( StructCommentInfo, blank=True, null=True, help_text="The comment information of the link being queried." )
    created_time        = models.DateTimeField( blank=True, null=True, help_text="The time the user posted the link." )
    image_urls          = models.TextField( blank=True, null=True, help_text="The URLs to the images associated with the link, \
                          as taken from the site's link tag." )
    like_info           = models.ForeignKey( StructLikeInfo, blank=True, null=True ) #Skipping privacy struct as of now
    link_id             = models.BigIntegerField( db_index=True, help_text="The unique identifier for the link." ) 
    owner               = models.ForeignKey('FacebookUser', related_name="links", help_text="The user ID for the user who posted the link.")
    owner_comment       = models.TextField( blank=True, null=True, help_text="The comment the owner made about the link." )
    owner_cursor        = models.CharField( max_length=100, blank=True, null=True, help_text="Cursor for the owner field" )
    picture             = models.CharField( max_length=500, blank=True, null=True, help_text="The URL to the thumbnail image that is displayed by default" )
    summary             = models.TextField( blank=True, null=True, help_text="A summary of the link, as taken from the site's description meta tag." )
    title               = models.TextField( blank=True, null=True, help_text="The title of the link, as taken from the site's title meta tag." )
    url                 = models.CharField( max_length=500, blank=True, null=True, help_text="The actual URL for the link." )
    via_id              = models.BigIntegerField( blank=True, null=True, help_text="The unique identifier of the original link poster." ) 

    class Meta:
        unique_together = (("user", "link_id"),)



class FacebookNotification(BaseFbModel):
    '''
    Notification Table
    '''
    fqlname             = "notification"
    primary_identifier  = "notification_id"
    owner_identifier    = "ONLY_SESSION_USER" 
    #owner_identifier=receipient_id is possible here but notification's nature is more like stream nature
    #so for a long notification table it wouldn't make sense to compare with all data sets again and again 
    #as compared with photo or album objects
    facebook_row_limit  = 500 #TODO : enough for now
    me_clause           = "WHERE recipient_id=me()"
    
    ## Django Application specific fields
    user                = models.ForeignKey(User, help_text="Data belongs with this system user: Viewer") 

    ## Fb Schema specific fields
    app_id              = models.BigIntegerField( blank=True, null=True, help_text="The ID of the application associated with the \
                          notification. This may be a third-party application or a Facebook application (for example, Wall)." ) 
    body_html           = models.TextField( blank=True, null=True, help_text="Any additional content the notification includes, in HTML." )
    body_text           = models.TextField( blank=True, null=True, help_text="The plaintext version of body_html, with all HTML tags stripped out." )
    created_time        = models.DateTimeField( blank=True, null=True, help_text="The time the notification was originally sent. Notifications\
                          older than 7 days are deleted and will not be returned via this table." )
    href                = models.CharField( max_length=500, blank=True, null=True, help_text="The URL associated with the notification. \
                          This is usually a location where the user can interact with the subject of the notification." )
    icon_url            = models.CharField( max_length=500, blank=True, null=True, help_text="The URL associated with the notification's icon." )
    is_hidden           = models.IntegerField( blank=True, null=True, help_text="Indicates whether the user hid the associated application's notifications." ) 
    is_unread           = models.IntegerField( blank=True, null=True, help_text="Indicates whether the notification has been marked as read.\
                          Use notifications.markRead to mark a notification as read." ) 
    notification_id     = models.BigIntegerField( unique=True, blank=True, null=True, help_text="The ID of the notification. This ID is not globally unique, \
                          so the recipient_id must be specified in addition to it." )
    object_id           = models.CharField( max_length=500, blank=True, null=True, help_text="The object id of the notification." )
    object_type         = models.CharField( max_length=50, blank=True, null=True, help_text="The object type (e.g. stream, photo, event etc.) \
                          of the notification." )
    recipient_id        = models.ForeignKey( 'FacebookUser', related_name="notifications", help_text="The user ID of the recipient of the\
                          notification. It is always the current session user." )
    sender_id           = models.BigIntegerField( blank=True, null=True, help_text="The user ID of the sender of the notification." )
    #^Not a ForeignKey, some users might be out of our social graph, and for performance gain because
    # Even if we want to store there user tuple in FacebookUser table we will have to afford a http query cycle
    # and that thing can be done later, all things apart we have the 'id' if we want to do something on this
    title_html          = models.TextField( blank=True, null=True, help_text="The main body of the notification in HTML." )
    title_text          = models.TextField( blank=True, null=True, help_text="The plaintext version of title_html, with all HTML tags stripped out." )
    updated_time        = models.DateTimeField( blank=True, null=True, help_text="The time the notification was originally sent, or the time the \
                          notification was updated, whichever is later." )


class FacebookStream(BaseFbModel):
    '''
    Stream Table
    '''
    fqlname             = "stream"
    primary_identifier  = "post_id"
    owner_identifier    = "ONLY_SESSION_USER" # for some models object_id is going to behave like owner
    facebook_row_limit  = 50
    me_clause           = "WHERE filter_key in (SELECT filter_key FROM stream_filter WHERE uid=me())"

    '''
    On facebookstream table there is no owner_identifier that means -
    There is no 'context_user' filter
    '''

    ## Django Application specific fields
    user                = models.ForeignKey(User, help_text="Data belongs with this system user: Viewer") 

    ## Fb Schema specific fields
    action_links        = models.TextField( blank=True, null=True, help_text="An array containing the text and URL for each action link" )
    actor_id            = models.BigIntegerField( blank=True, null=True, help_text="The ID of the user, page, group, or event that published the post" )
    attribution         = models.CharField( max_length=500, blank=True, null=True, help_text="For posts published by apps, the full name of that app" )
    created_time        = models.DateTimeField( blank=True, null=True, help_text="The time the post was published" )
    description         = models.TextField( blank=True, null=True, help_text="Text of stories not intentionally generated by users, \
                          such as those generated when two users become friends. You must have the 'Include recent activity stories'\
                          migration enabled in your app to retrieve this field" )
    description_tags    = models.TextField( blank=True, null=True, help_text="The list of tags in the post description" )
    expiration_timestamp= models.DateTimeField( blank=True, null=True, help_text="UNIX timestamp of when the offer expires" )
    filter_key          = models.CharField( max_length=500, blank=True, null=True, help_text="The filter key to fetch data with" )
    impressions         = models.IntegerField( blank=True, null=True, help_text="Number of impressions of this post." ) 
    is_hidden           = models.NullBooleanField( blank=True, null=True, help_text="Whether a post has been set to hidden" )
    is_published        = models.NullBooleanField( blank=True, null=True, help_text="Whether the post is published" )
    message             = models.TextField( blank=True, null=True, help_text="The message written in the post" )
    message_tags        = models.TextField( blank=True, null=True, help_text="The list of tags in the post mssage" )
    parent_post_id      = models.CharField( max_length=500, blank=True, null=True, help_text="ID of the parent post" ) 
    permalink           = models.CharField( max_length=500, blank=True, null=True, help_text="The URL of the post" )
    place               = models.BigIntegerField( blank=True, null=True, help_text="ID of the place associated with the post" ) 
    post_id             = models.CharField( max_length=255, blank=True, null=True, help_text="The ID of the post" ) 
    share_count         = models.IntegerField( blank=True, null=True, help_text="Number of times the post has been shared" ) 
    source_id           = models.BigIntegerField( db_index=True, blank=True, null=True, help_text="The ID of the user, page, group, \
                          or event whose wall the post is on" ) 
    subscribed          = models.NullBooleanField( blank=True, null=True, help_text="Whether user is subscribed to the post" )
    tagged_ids          = models.TextField( blank=True, null=True, help_text="An array of IDs tagged in the message of the post." )
    target_id           = models.BigIntegerField( db_index=True, blank=True, null=True, help_text="The user, page, group, or event to whom the post was directed" )
    timeline_visibility = models.CharField( max_length=500, blank=True, null=True, help_text="Timeline visibility information of the post" )
    type                = models.IntegerField( blank=True, null=True, help_text="The type of this story" ) 
    updated_time        = models.DateTimeField( blank=True, null=True, help_text="The time the post was last updated, which occurs when a user \
                          comments on the post, expressed as a UNIX timestamp" )
    via_id              = models.BigIntegerField( blank=True, null=True, help_text="ID of the user or Page the post was shared from" )
    viewer_id           = models.BigIntegerField( blank=True, null=True, help_text="The ID of the current session user" )
    with_location       = models.NullBooleanField( blank=True, null=True, help_text="ID of the location associated with the post" )
    with_tags           = models.TextField( blank=True, null=True, help_text="An array of IDs of entities (e.g. users) tagged in this post" )
    xid                 = models.BigIntegerField( blank=True, null=True, help_text="When querying for the feed of a live stream box, \
                          this is the xid associated with the Live Stream box (you can provide 'default' if one is not available)" )

    @classmethod
    def handle_integrity_exception(self, request, data_dict):
        '''
        Handles some rare cases of integrity exceptions. In case we are expecting this error we define this method in model class
        '''
        kwargs = { self.primary_identifier : data_dict[self.primary_identifier] }
        data_tuple = self.objects.get(user=request.user, **kwargs)
        data_tuple = self(user=request.user, id=data_tuple.id, **data_dict) 
        return data_tuple

    class Meta:
        unique_together = (("user", "post_id"),)


class FacebookUser(BaseFbModel):
    '''
    User Table
    '''
    fqlname             = "user"

    ## Django Application specific fields
    user                = models.ForeignKey(User, help_text="Data belongs with this system user") 
    #TODO: Move this foreignkey to FacebookFriends model along with 'friend relation' information
    #Moral of the story is : if in any fql schema if there is any 'viewer related' field then we will need this foreignkey 'user'

    ## Fb Schema specific fields
    about_me            = models.TextField( blank=True, null=True, help_text="More information about the user being queried")
    activities          = models.TextField( blank=True, null=True, help_text="The user's activities")
    affiliations        = models.TextField( blank=True, null=True, help_text="The networks to which the user being queried \
                          belongs. The status field within this field will only return results in English") 
                          # max_length = 3000 represents is an array ( Array doesn't have fixed fields, so for now CharField is enough )
    age_range           = models.ForeignKey(StructAgeRange, blank=True, null=True)
    allowed_restrictions= models.CharField( max_length=3000, blank=True, null=True, help_text="A comma-delimited list of demographic \
                              restriction types a user is allowed to access. Currently, alcohol is the only type that can get returned")
    birthday            = models.DateTimeField( blank=True, null=True, help_text="The user's birthday. The format of this date varies based\
                          on the user's locale")
    
    books               = models.TextField( blank=True, null=True, help_text="The user's favorite books")
    can_message         = models.NullBooleanField( blank=True, null=True, help_text="Whether the user can send a message to another user" )
    ## <Lean:Stopage> I am currently picking up fields I am interested in, and will try to basic import process which can update things
    
    devices             = models.CharField( max_length=1000, blank=True, null=True, help_text="An array of objects containing fields os")
    education           = models.TextField( blank=True, null=True, help_text="A list of the user's education history. Contains\
                          year and type fields, and school object (name, id, type, and optional year, degree, concentration array, classes array,\
                          and with array )")
    email               = models.EmailField( blank=True, null=True, help_text="A string containing the user's primary Facebook email address \
                          or the user's proxied email address, whichever address the user granted your application. Facebook recommends you query\
                          this field to get the email address shared with your application")
    first_name          = models.CharField( max_length=200, blank=True, null=True, help_text="The user's first name" )
    friend_count        = models.IntegerField( blank=True, null=True, help_text="Count of all the user's friends" )
    interests           = models.TextField( blank=True, null=True, help_text="The user's interests" )
    likes_count         = models.IntegerField( blank=True, null=True, help_text="Count of all the pages this user has liked" )
    movies              = models.TextField( blank=True, null=True, help_text="The user's favorite movies")
    mutual_friend_count = models.IntegerField( blank=True, null=True, help_text="The number of mutual friends shared by the \
                          user being queried and the session user")
    quotes              = models.TextField( blank=True, null=True, help_text="The user's favorite quotes")
    relationship_status = models.CharField( max_length=50, blank=True, null=True, help_text="The type of relationship for the user being queried")
    religion            = models.CharField( max_length=50, blank=True, null=True, help_text="The user's religion")
    sex                 = models.CharField( max_length=50, blank=True, null=True, help_text="The user's gender")
    subscriber_count    = models.IntegerField( blank=True, null=True, help_text="The user's total number of subscribers")
    movies              = models.TextField( blank=True, null=True, help_text="The user's favorite television shows")
    uid                 = models.BigIntegerField( db_index=True, help_text="The user ID") # primary_key=True ? - No if you want to make it multi-user oriented
    username            = models.CharField( max_length=500, blank=True, null=True, help_text="The user's username")
    wall_count          = models.IntegerField( blank=True, null=True, help_text="The user ID") # primary_key=True ?
    website             = models.CharField( max_length=1000, blank=True, null=True, help_text="The website")
    work                = models.TextField( max_length=3000, blank=True, null=True, help_text="A list of the user's work history.\
                          Contains employer, location, position, start_date and end_date fields")
    def __unicode__(self):
        return self.username
    
    class Meta:
        unique_together = (("user", "uid"),)
    


class FacebookFriend(BaseFbModel):
    '''
    Friend Table
    '''
    fqlname             = "friend"

    ## Django Application specific fields
    user                = models.ForeignKey(User, help_text="Data belongs with this system user")

    ## Fb Schema specific fields
    uid1                = models.BigIntegerField( db_index=True, help_text="The user ID of the first user in a particular friendship link.") 
    uid2                = models.BigIntegerField( db_index=True, help_text="The user ID of the second user in a particular friendship link.") 

    class Meta:
        unique_together = (("user", "uid1", "uid2"),)



class FacebookLike(BaseFbModel):
    '''
    Like Table
    '''
    fqlname             = "like"

    ## Fb Schema specific fields
    object_id           = models.BigIntegerField( db_index=True, help_text="The object_id of a video, note, link, photo, or album. \
                          Note: For photos and albums, the object_id is a different field from the photo table pid field and the \
                          album table aid field, use the specified object_id from those tables instead.") 
    object_type         = models.CharField( max_length=50, blank=True, null=True, help_text="The type of the liked object. One of: photo, album,\
                          event, group, note, link, video, application, status, check-in, review, comment, post") 
                          #However facebook is showing only 'profile' to me 
    post_id             = models.BigIntegerField( db_index=True, blank=True, null=True, help_text="The id of a post on Facebook. This can be a stream post\
                          containing a status, video, note, link, photo, or photo album")
    user_id             = models.ForeignKey('FacebookUser', related_name="likes", help_text="The user who likes this object.")
                          #TODO: This relation is defined by request.user+user_id that means each different system user has its own set of users in 'facebookusers'
                          #and that is not an expected behaviour. As of now I am not separating them as to do that I have to alter fql schema
                          #So that I can write 'friend relation' specific information in 'friends' table rather than in 'facebookuser' table
    class Meta:
        unique_together = (("object_id", "user_id"),) #Not having 'user' tells that it's a viewer free model




