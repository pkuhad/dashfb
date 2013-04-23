'''
Facebook field cleaning and parsing function
'''
import datetime
import re

from django.db.models import CharField, DateTimeField, ForeignKey, TextField, BigIntegerField
from apps.fbschema.struct_models import *
from apps.fbschema.models import *

def parse_fbarray(fbarray):
    '''
    Parse facebook array
    '''
    return fbarray.__str__()

def parse_fbdate(fbdate):
    '''
    Parse Facebook Date
    '''
    #Check if unixtimestamp
    #pattern = re.compile('^[0-9]*$')
    #print type(fbdate)
    if(type(fbdate) is int):
        return datetime.datetime.fromtimestamp(int(fbdate))
    else:
        format = '%B %d, %Y'
        try:
            return datetime.datetime.strptime(fbdate, format)
        except ValueError:
            safe_fbdate = "%s, 1970" % fbdate 
            # TODO: What would happen to year in database
            # TODO: RuntimeWarning: DateTimeField received a naive datetime (1900-12-29 00:00:00) while time zone support is active.
            return datetime.datetime.strptime(safe_fbdate, format)


def parse_clean_field_value(field, value, request=None):
    '''
    Main function to process fields received from fql queries
    Their processing is based on what data type they are going to be here in system
    Furthermore we need some extra introspection to tackle facebook's array and structs data type
    '''
    if( (isinstance(field, CharField) or isinstance(field, TextField)) and (type(value) is not str and type(value) is not unicode)):
        # Converting facebook array into strings is solving problem as of now
        value = parse_fbarray(value)
    elif(isinstance(field, DateTimeField) and value):
        value = parse_fbdate(value)
    elif(isinstance(field, ForeignKey )):
        '''
        # What's going on here -
        print type(field.rel.to)
        print field.rel.to.__class__.__name__
        print field.rel.to.__name__
        print type(field.rel.to)
        print isinstance(field.rel.to, StructAgeRange)
        '''
        if(field.rel.to.__name__ == "StructAgeRange") and value:
                #table: user
                value = StructAgeRange.objects.get_or_create( min= value['min'] )[0] # max has to be done with exception handling
        elif(field.rel.to.__name__ == "FacebookUser"):
                #For viewer field
                #TODO: user=request.user AND uid=value => uid=value ONLY ( Also see model class: FacebookLike notes )
                value = FacebookUser.objects.get( user=request.user, uid=value )
                '''
                Field which are already supplied as parameters while saving response data in views,
                and are not in data_dict 'must' be in ignore_fields of model class
                Because then they should be at once place if supplied as parameteres then not in data_dict and vice_versa
                '''
        elif(field.rel.to.__name__ == "FacebookAlbum"):
                value = FacebookAlbum.objects.get( user=request.user, aid=value )
        elif(field.rel.to.__name__ == "StructCommentInfo") and value:
                #table: album
                value = StructCommentInfo.objects.get_or_create( can_comment=value.get('can_comment', None), \
                        comment_count=value.get('comment_count', None) or value.get('count', None) )[0] 
                '''
                value = StructCommentInfo.objects.get_or_create( can_comment=value.get('can_comment', None), \
                comment_count=value.get('comment_count', None) or value.get('count', None), \
                comment_order=value.get('comment_order', None), \
                comment_list=value.get('comment_list', None))[0] 
                #TODO: In next pass uncomment this line ^
                '''
        elif(field.rel.to.__name__ == "StructLikeInfo") and value:
                #table: album
                value = StructLikeInfo.objects.get_or_create( can_like=value.get('can_like', None), \
                        like_count=value.get('like_count', None) or value.get('count', None), \
                        user_likes=value.get('user_likes', None) )[0] 
                
    elif(isinstance(field, BigIntegerField) and not value):
        value = None
    elif(isinstance(field, BigIntegerField) and value):
        return int(value)
    return value

