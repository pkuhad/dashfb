from django.db import models

class StructAgeRange(models.Model):
    min             = models.IntegerField()
    max             = models.IntegerField( blank=True, null=True )

class StructCommentInfo(models.Model):
    can_comment     = models.NullBooleanField( blank=True, null=True, help_text="Whether the comments are allowed on the object" )
    comment_count   = models.IntegerField( blank=True, null=True, help_text="The number of comments on this object." )
    #comment_order  = models.CharField( max_length=500, blank=True, null=True, help_text="The order that these comments are displayed on site.")
    #comment_list   = models.TextField( blank=True, null=True, help_text="The list of comments on the post")
    #TODO: In next pass uncomment this line ^

class StructLikeInfo(models.Model):
    can_like        = models.NullBooleanField( blank=True, null=True, help_text="Whether the viewer can like the object" )
    like_count      = models.IntegerField( blank=True, null=True, help_text="The number of likes on this object." )
    user_likes      = models.NullBooleanField( blank=True, null=True, help_text="Whether the viewer likes this object" )
    
