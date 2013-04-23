# DashFB
DashFB lets you download and update all your facebook data in exact FQL table schemas as in Facebook API. This enables you to perform SQL JOINS on FQL tables and makes your own facebook data computable. This project is under strong development, as of now it is implementing some basic FQL tables to play with.

 * Created by [Paras Kuhad](http://pacificparas.org) 
 * Twitter: [@paraskuhad](http://twitter.com/paraskuhad)

## Features
Current features I am focusing on -
 * Implementing all FQL tables 
 * Asynchronous data download in FQL tables using message queuing server.
 * A simple dashboard UI that uses this mined data. We can computing amazing patterns in cleaned and saved facebook data locally.
 * Means to perodically update saved data. Data tuples just need to be added in 'stream' like tables but in other tables it has to find which data has been altered and to update it.
 * While updating, deleting or adding any data to FQL tables preparing a changelog of table so that we can fetch the fql data 'as it was on some day'. For example : We update 'user' table and this application prepares a changelog on updated 'about_me' fields for all our friends, we can track who changed his profile information and to what, we can also find who unfriended me, things like that.  
 * We can also create and host a local fql server using locally stored data.

For example you can do things like -
 * Finding out top ten albums in your social graph based on their like counts -
        
        >>> from fb_client.apps.fbschema.models import FacebookAlbum
            for i in range(0,10):
                print FacebookAlbum.objects.order_by('-like_info__like_count')[i].name
                print FacebookAlbum.objects.order_by('-like_info__like_count')[i].owner
                print FacebookAlbum.objects.order_by('-like_info__like_count')[i].like_info.like_count

 * Or you can also do some crazy thing with NLP. Here is a simple example with Python's awesome [NLTK](http://nltk.org/) - We find out top 50 used words in 'about_me' fields of 'user' table in our social graph -

        >>> import nltk
            from fb_client.apps.fbschema.models import FacebookUser
            l = []
            l = [ user.about_me for user in FacebookUser.objects.all() ]
            fdist = nltk.FreqDist(nltk.tokenize.word_tokenize("".join(l)))
            fdist.keys()[:50]

## Tools

 * [Django](http://www.djangoproject.com): Awesome web framework written in Python with [Django Facebook](https://github.com/tschellenbach/Django-facebook) by Thierry Schellenbach to interact with Facebook API
 * I will be using [Celery](http://ask.github.com/celery) & [RabbitMQ](http://www.rabbitmq.com) for asynchronous queuing server purpose. 
 * [MySQL](http://www.postgresql.com): Relational database.
 * [jQuery](http://www.jquery.com), [Twitter Bootstrap](http://twitter.github.io/bootstrap/) for UI.


## Installation Instructions

### Prerequisites

 * DashFB is a Django based application so you need to have [Django 1.5](https://www.djangoproject.com/) installed on your host and basic toolset required for it, that pretty much includes requirements like MySql, Python and MySql bindings for Python. 
 
 * You also need to install this django contributed app [Django Facebook](https://github.com/tschellenbach/Django-facebook) as a python module, you can use this command in terminal for this purpose `pip install django_facebook`.

### Developer Installation :
Current installation and usage of this application is developer oriented. Contribution on UI is invited, it would be awesome to see this application downloading all facebook data asynchronously from API with just one click.

 * You will need a Facebook Application to work with. Open up [Developer Facebook](http://developers.facebook.com/apps) and create a facebook application to work with. Don't forget to provide 'App Domain' as 'localhost' and 'Site URL' (in 'Website with Facebook Logic' section) as 'http://localhost:8000' if you are trying this project on your localhost.

 * Create a MySql Database to work with. Keep remember to choose the correct collation while creating the database otherwise you would face 'Incorrect string value' error at some point due to collation issues. In my case 'utf8_general_ci' works fine. If you are not sure which collation to go with, create the database with 'utf8_general_ci'. You can use this command in mysql terminal :

        CREATE DATABASE {your_database_name} COLLATE utf8_general_ci;

 * You need to create a local_settings.py file in folder root to provide database name and password. A template file named local_settings.py.template has been provided to start with. In this file you also need to add your `FACEBOOK_APP_ID` and `FACEBOOK_APP_SECRET` settings. 

 * Run `python manage.py syncdb` to install database tables.

 * Finally run `python manage.py runserver` to start Django's development server.

 * Open `http://localhost:8000` in your browser. If you are trying this project on your remote server then you can run testserver by `python manage.py runserver {your_ip}:8000` and also make sure that this port is accessible for outer world. So you can access application on http://{your_ip/your_domain}:8000 and then click on 'Connect with facebook' button to connect this application to your newly created facebook application. Don't forget to provide all permissions otherwise we won't be able to download facebook data.

 * After connecting if it redirects you to `http://localhost:8000/facebook/connect/#_=_` then please come back to localhost:8000. It is a known [Bug](https://github.com/tschellenbach/Django-facebook/issues/227) in django-facebook.

 * Now you will be at the home screen of application in logged in mode. This application doesn't have anything fancy on UI as of now :), you will find guided instructions on how to click and download all implemented FQL tables one by one. Once you download all your data you can do awesome things by firing SQL queries or using django console.

Currently these tables have been implemented : `user, friend, like, album, photo, notification, link and stream`. It's not possible to fetch all data of all your friends in just one api request for some tables, for example like 'photo'. So we do this in batches, how many number of friends we can cover in one batch depends on the amount of data this table can have for one friend. Check out code `fbschema/views.py` to comprehend what I exactly mean. For now I am doing this batch operation for first 'n' friends. If you alter this hardcoded 'n' in code and find this error : `Facebookuser matching query does not exist` then don't worry it just means we don't have all friends in 'user' table to join with i.e without having downloaded all friends profile we cannot download any other information for him. This 'define the number of batches and download all information batches' task has to be done asynchronously.

## Contribution Invited
I feel obliged for open source softwares, I owe them too much. If you loved this idea and have any feeback or just want to say something on this project, you are welcome. My twitter handle is [@paraskuhad](http://twitter.com/paraskuhad). Do checkout the project and I am accepting feature requests. I would be happy to contribute more code and work with potential contributors, together we can make things more awesome.

## License

DashFB is licensed under the MIT License.
