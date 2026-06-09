# How to run the project

# 0. Prerequites

## Alembic
Project uses Alembic for migration management with SQL-Alchemy. Since there is an Alembic version control table in the project DB, it may be better to copy the original project db. If not required delete alembic/versions and start a migration from scratch.

## Telegram API
### Configure .env file
If you DO NOT want to keep the Telegram feature on the project, go to the next section *Remove Telegram feature from project*.

When starting the project, the backend loads environment variables from the **.env** file, the file should have a content like this:

~~~
# Telegram bot id
TELEGRAM_BOT_TOKEN=<YOUR TELEGRAM BOT TOKEN>

# Test chat group id
TELEGRAM_INFINX_GROUP_ID=<YOUR TELEGRAM CHAT GROUP ID>
~~~

### Remove Telegram feature from project
**<code style="color : red">If you want to keep the Telegram feature on the project, skip this section.</code>**

Project sends JSON messages to the API URL, if not needed, you must:

1. Delete telegram_bot.py
2. Delete background_tasks.py
3. Delete scheduler module import and the relate instructinos at app/__init__.py
4. You will need to delete Telegram related blocks at routes/post.py for the post_create, post_delete and post_close view functions.

Or you may like to create a public chat group on Telegram with your own bot set as administrator. If that is the case, then create a .env file with the following envirnment variables:

1. TELEGRAM_BOT_TOKEN
2. TELEGRAM_INFINX_GROUP_ID

# 1. Python UV
Installation:

Run curl to install UV:
~~~
curl -LsSf https://astral.sh/uv/install.sh | sh
~~~

Use the following UV command to install the necessary Python version and modules:
~~~
uv sync
~~~

# 2. Alembic
Use the following command to update the project with the last migration revision:
~~~
uv run alembic upgrade head
~~~

# 3. For testing (Flask development server in debug mode)
Execute the script:
~~~
./run
~~~

You may need to use if the system do not recognize as executable program:
~~~
sudo chmod+x ./run
~~~