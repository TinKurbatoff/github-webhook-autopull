#Simple HTTP GitHub webhook listener

This is a very simple yet convenient tool for catching webhooks from GitHub. Once the call is received, the device executes a command to update the local repository.
Starts a constantly running web server that listens for a POST request and automatically creates a pull request in the specified directory.

```
~$git pull git@github.com:TinKurbatoff/github-webhook-autopull.git
~$cd github-webhook-autopull 
~$nohup python3 webhook_listener.py -d /home/user/github_repo -p 9007 &
```

PROFIT!!
