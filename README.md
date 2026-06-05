# How to run the project

# 0. Prerequites

## Alembic
Project uses Alembic for migration management with SQL-Alchemy. Since there is an Alembic version control table in the project DB, it may be better to copy the original project db. If not required delete alembic/versions and start a migration from scratch.

## Telegram API
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

# 2. For testing (Flask development server in debug mode)
Execute the script:
~~~
./run
~~~

You may need to use if the system do not recognize as executable program:
~~~
sudo chmod+x ./run
~~~