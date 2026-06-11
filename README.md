# How to run the project

# 0. Prerequites

## System setup
The project has been tested in a Debian 13 host and on a Win 11 host running Debian 13 from WSL.

## Alembic
Project uses Alembic for migration management with SQL-Alchemy. Since there is an Alembic version control table in the project DB, it may be better to copy the original project db. If not required delete alembic/versions and start a migration from scratch.

## Telegram API
### Configure .env file
If you DO NOT want to keep the Telegram feature on the project, go to the next section *Remove Telegram feature from project*.

When starting the project, the backend loads environment variables from a **.env** file, Create the following **.env** file:

~~~
# Program blocking flag
ENABLE_TELEGRAM=YES

# Telegram bot id
TELEGRAM_BOT_TOKEN=<YOUR TELEGRAM BOT TOKEN>

# Test chat group id
TELEGRAM_INFINX_GROUP_ID=<YOUR TELEGRAM CHAT GROUP ID>
~~~

### Remove Telegram feature from project
**<code style="color : red">If you want to keep the Telegram feature on the project, skip this section.</code>**

Create the following **.env** file:

~~~
# Program blocking flag
ENABLE_TELEGRAM=YES

# Telegram bot id
TELEGRAM_BOT_TOKEN=EMPTY

# Test chat group id
TELEGRAM_INFINX_GROUP_ID=EMPTY
~~~

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
You may need to set app.db permissions as:
~~~
sudo chmod +w app.db 
~~~

Then open app.db (I use VS code SQLite3 Editor extension) and update the alembic version table value to the last version at alembic/versions.

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
sudo chmod +x ./run
~~~

# 4 Setup NGINX
## Installation
Install prerequisites:
~~~
sudo apt install curl gnupg2 ca-certificates lsb-release debian-archive-keyring
~~~
Import an official nginx signing key so apt could verify the packages authenticity. Fetch the key:
~~~
curl https://nginx.org/keys/nginx_signing.key | gpg --dearmor \
    | sudo tee /usr/share/keyrings/nginx-archive-keyring.gpg >/dev/null
~~~
Verify that the downloaded file contains the proper key:
~~~
gpg --dry-run --quiet --no-keyring --import --import-options import-show /usr/share/keyrings/nginx-archive-keyring.gpg
~~~
If *gdp* command fails, force the necessary directories creation with the following command:
~~~
gpg --list-keys
~~~
Set up the apt repository for stable nginx packages, run the following command:
~~~
echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] \
https://nginx.org/packages/debian `lsb_release -cs` nginx" \
    | sudo tee /etc/apt/sources.list.d/nginx.list
~~~
Install NGINX with apt:
~~~
sudo apt update
sudo apt install nginx
~~~
## Setup and start NGINX service
Ensures nginx starts on boot up:
~~~
sudo systemctl enable nginx
~~~
Start nginx service:
~~~
sudo systemctl start nginx
~~~
Checkout if it is running:
~~~
sudo systemctl status nginx
~~~
Checkout if it is enabled on boot up:
~~~
systemctl is-enabled nginx
~~~

## Setup static files
Create the following file:
~~~
sudo nano /etc/nginx/conf.d/infix.conf
~~~

Write the following content:
~~~
server {
    listen 80;
    server_name localhost 172.19.1.95;

    # Define where static files are located
    location /static/ {
        alias /home/tebix/apps/infinx_andon/app/static/;
        expires 5d; # Optional: Tells the browser to cache files for 30 days
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Add these lines to disable the temp file buffering
        proxy_buffering off;
        proxy_request_buffering off;
    }

}
~~~
Run the following command to verify syntax:
~~~
sudo nginx -t
~~~
Run the following command to apply new configuration file changes:
~~~
sudo systemctl reload nginx
~~~

## Setup permissions
Run the following command:

~~~
sudo chown -R www-data:www-data /var/cache/nginx/
sudo chmod -R 700 /var/cache/nginx/
sudo systemctl restart nginx
~~~

# 5 Setup Gunicorn

## Installation

Install from project root:
~~~
uv add gunicorn
~~~

Tell Gunicorn where is your app instance (defaults looks for a app.py file):
~~~
uv run gunicorn "app:start_app()"
~~~

## Setup service
Create the new app service.
~~~
sudo nano /etc/systemd/system/infinx.service
~~~

Workers formula:
$$(2 \times \text{num\_cores}) + 1$$

In my case I have an Intel Core 3 CPU with 4 cores, that is:

$$(2 \times 4) + 1 = \mathbf{9 \text{ workers}}$$

So my file content is:
~~~
[Unit]
Description=Gunicorn instance for InfinX Andon App
After=network.target

[Service]
User=tebix
Group=www-data
WorkingDirectory=/home/tebix/apps/infinx_andon
# Use the path to your .venv created by uv
Environment="PATH=/home/tebix/apps/infinx_andon/.venv/bin:/usr/bin:/bin"
ExecStart=/home/tebix/apps/infinx_andon/.venv/bin/gunicorn --workers 9 --bind 127.0.0.1:8000 "app:start_app()"

[Install]
WantedBy=multi-user.target
~~~

Run the following commands to tell Linux to launch service on boot:
~~~
# Reload to read the new file
sudo systemctl daemon-reload

# Enable to start on boot
sudo systemctl enable infinx

# Start it now
sudo systemctl start infinx
~~~

## Update production code
Reload the service every time the code is updated.
~~~
sudo systemctl restart infinx
~~~

# Bridge Debian WSL network with Windows 11 host
From Bash run to get the WSL IP address:
~~~
hostname -I
~~~
From Powershell run:
~~~
netsh interface portproxy add v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=80 connectaddress=<WSL_IP>
~~~
From Powershell allow traffic at port 80:
~~~
New-NetFirewallRule -DisplayName "Allow Andon Web Traffic" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
~~~