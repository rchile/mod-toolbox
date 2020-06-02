## r/Chile Moderators Toolbox

This is a tailor-made tool for the r/Chile moderation team, which allows
to retrieve info about the mod actions on the sub and help to take decisions.

It's made with Django and uses a MongoDB database.

### Pre-requisites and execution

* You need the latest version of Python 3 with pip and virtualenv.
* On the project folder, activate a virtualenv and install the requirements.
* **Copy** (don't move) "local_setttings.ex.py" to "local_settings.py" and
fill the required settings.
  * You'll need to create an app on the [reddit apps website](https://www.reddit.com/prefs/apps)
  to get an app ID and secret.
  * You'll also need to fetch a permanent refresh token, using the
  "refresh_token.py" script, which will help you to get said token, using
  the previously created reddit app. Run that script and follow its instructions.
* Run database migrations, to create session tables on the default Sqlite3
database, created by Django: `python manage.py migrate`.

### Modlog database worker

This application includes a "worker" that will sync the modlog with a
configured MongoDB database, from where the system will fetch all the data.

Setup a MongoDB instance, and configure the `MODLOG_MONGODB_URI` setting.

Then, having the other Reddit credentials ready, run the following command,
which will run the script that will keep the modlog database up-to-date:

* `python manage.py worker`

### Running in production

To keep it simple: set the `DEBUG` variable to `False`, run the `collectstatic`
manager command every time when updating this project, keep the worker running 
in background, and serve the application with uWSGI or gunicorn and the 
static files directly with a web server, like nginx.
