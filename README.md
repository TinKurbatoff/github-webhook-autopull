![image](https://user-images.githubusercontent.com/48193889/157143336-abcfa98e-0316-4751-873b-3a24d7a11186.png)


# Simple HTTP GitHub webhook listener

This is a very simple yet convenient tool for catching webhooks from GitHub. Once the call is received, the script executes a command to update the local repository.
Starts a constantly running web server that listens for a POST request and automatically creates a pull request in the specified directory.

`-d` — directory with github repo to update from server <br />
`-p` — port to listen <br />
`-s` — [OPTIONAL] a secret string for GitHub webhook identification <br />
`-r` — [OPTIONAL] a service name that will be restarted after pull <br />

```
~$git pull git@github.com:TinKurbatoff/github-webhook-autopull.git
~$cd github-webhook-autopull 
~$nohup python3 webhook_listener.py -d /home/user/github_repo -p 9007 [-s <secret>] [-r <some.service>] &

```

PROFIT!!

----

To setup a webhook at your repository:

1. Navigate to 

`https://github.com/<github_user_name>/<your_repo>/settings/hooks`

2. Add a webhook

![image](https://user-images.githubusercontent.com/48193889/157140887-e497ef77-bc38-4aec-937a-7272751ba0a4.png)


3. Use the following settings (secret string is on you):

![image](https://user-images.githubusercontent.com/48193889/157140624-366fa886-e046-4835-97f9-e4dfa768687e.png)

4. If you are using nGinx (like me):

```
...
    location /webhook/ {
            proxy_pass_header Server;
            proxy_redirect off;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Scheme $scheme;
            include proxy_params;
            proxy_pass http://127.0.0.1:9007/;    
        }
...
```
