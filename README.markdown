Heapkeeper will be an editable mailing list web application.

Heapkeeper will be used at http://heapkeeper.org.

Installation
============

This section describes how to set up a Heapkeeper server on Debian or Ubuntu Linux using the nginx web server and the sqlite database engine. These steps apply only if you want to run no other web service. If you do want that, then you can adjust these steps accordingly.

Install the prerequisites
-------------------------

        $ sudo apt-get install nginx python-flup
        $ sudo apt-get install python-sqlite sqlite3

Get Django: https://docs.djangoproject.com/en/1.3/topics/install/#installing-an-official-release

We used the following versions of these programs:

* Python: 2.7
* Django: 1.3
* nginx: 0.8
* sqlite3: 3.7

All of these are the default on the latest Ubuntu except for Django.

Set up ExponWords and run it in debug mode
------------------------------------------

1. Create a Django project (this will create a directory called `Heapkeeper` with some Python files):

        $ django-admin.py startproject Heapkeeper

2. Clone the Heapkeeper repository as a Django application called `hk`:

        $ cd Heapkeeper
        $ git clone git://github.com/hcs42/heapkeeper.git hk

   If you forked the Heapkeeper repository, use your own repository instead:

        $ cd Heapkeeper
        $ git clone git@github.com:<username>/heapkeeper.git

3. Edit `settings.py` (you will find an example in `hk/setup/settings.py`):

   * `DATABASES`: fill it in according to the database you want to use. I used sqlite.
   * `ADMIN_ROOT`: change it to `'/admin/media/'`
   * `LOGIN_REDIRECT_URL`: set it to `'..'`
   * `MIDDLEWARE_CLASSES`: insert `'django.middleware.locale.LocaleMiddleware'` after `SessionMiddleware`
   * `INSTALLED_APPS`: append `'django.contrib.admin'` and `'hk'`
   * Anything else you want to customize (e.g. timezone)
   * Move the `DEBUG` and `TEMPLATE_DEBUG` variables into `debug_settings.py` (see the next step)

4. Create `debug_settings.py` (you will find an example in `hk/setup/debug_settings.py`):

   * `DATABASES`: fill it in
   * Move the `DEBUG` and `TEMPLATE_DEBUG` variables here from `settings.py` (see the previous step)

5. Overwrite `urls.py` with the one in the `setup` directory:

        $ cp hk/setup/urls.py .

6. Set up the database files. When asked about whether to create a superuser, create them.

        $ python manage.py syncdb
        $ python manage.py syncdb --settings=debug_settings

7. Copy the startup scripts and change the ports in them if you need to:

        $ cp hk/setup/start_production.sh hk/setup/start_debug.sh .
        $ vim hk/setup/start_production.sh hk/setup/start_debug.sh

8. Start the server in debug mode:

        $ ./start_debug.sh

   Try it from the browser:

        $ google-chrome http://localhost:8002

   Finally close it:

        Kill `start_debug.sh` with CTRL-C

UNTESTED: Set up the nginx web server and run Heapkeeper in production mode
---------------------------------------------------------------------------

1. Perform the following steps as root:

   Rename the original nginx configuration file:

        # mv /etc/nginx/nginx.conf{,.old}

   Copy the provided config file instead and modify its content to match your paths:

        # cp hk/setup/nginx.conf /etc/nginx/nginx.conf
        # vim /etc/nginx/nginx.conf

   Restart nginx:

        # /etc/init.d/nginx restart

2. Start the production server, try it and kill it:

        $ ./start_production
        $ google-chrome http://localhost/
        Kill start_production with CTRL-C

UNTESTED: Set up email sending
------------------------------

1. Set up the name of your site:

        $ python manage.py shell
        >>> from django.contrib.sites.models import Site
        >>> s = Site.objects.get(pk=1)
        >>> s.domain = 'mysite.org'
        >>> s.name = 'Heapkeeper'
        >>> s.save()

2. Set up SMTP server and configure Django to use it. See more information
   here: https://docs.djangoproject.com/en/1.3/topics/email/


UNTESTED: Start Heapkeeper automatically after boot
---------------------------------------------------

In Debian or Ubuntu, Heapkeeper can be set to start up automatically by performing the following steps as root.

1. Copy the provided init script to the directory of the init scripts:

        # cp hk/setup/heapkeeper.d /etc/init.d/heapkeeper

2. Modify the `SITE_PATH` variable in it to `<path to heapkeeper>/Heapkeeper` and modify `RUN_AS` to your Linux username:

        # vim /etc/init.d/heapkeeper

3. Try the script:

        # /etc/init.d/heapkeeper start
        $ google-chrome http://localhost/   # web page is there
        # /etc/init.d/heapkeeper stop
        $ google-chrome http://localhost/   # web page is not there

4. Run `update-rc.d` to create symbolic links in the `/etc/rc*.d/` directories, which will make operating system call `/etc/init.d/heapkeeper` automatically with the `start` parameter after the system has booted, and with the `stop` parameter before it shuts down.

        # update-rc.d heapkeeper defaults

NOT YET: Usage
==============

You will be able to read the user documentation at http://heapkeeper.org/help.
