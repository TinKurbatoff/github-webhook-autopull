#!/usr/bin/python3
# small web server that instruments "GET" but then serves up files
# to server files with zero lines of code,  do
#
#   python3 webhook_listener.py -d /home/user/github_repo -p 9007     # python 3
#
# Initial gist was shamelessly snarfed from Gary Robinson
#    http://www.garyrobinson.net/2004/03/one_line_python.html
#
import asyncio
import http.server
import argparse
import json
import hmac
import hashlib

PATH = "."
PORT = 9007
SECRET = ""


async def git_pull(path):
    """ Executes `git pull` command in specified directory """
    result = {"stdout": "", "stderr": ""}
    cmd = f"cd {path} && git pull"
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        result["stdout"] = stdout.decode()
        print(f'[stdout]\n{result["stdout"]}')
    if stderr:
        result["stderr"] = stderr.decode()
        print(f'[stderr]\n{result["stderr"]}')
    return result


def validate_signature(payload, secret, signature_header):
    # Get the signature from the payload
    # Borrowed at 
    #     https://gist.github.com/andrewfraley/0229f59a11d76373f11b5d9d8c6809bc
    sha_name, github_signature = signature_header.split('=')
    if sha_name != 'sha256':
        print('ERROR: X-Hub-Signature in payload headers was not sha1=****')
        return False
      
    # Create our own signature
    # payload = json.dumps(payload).encode('utf-8')
    local_signature = hmac.new(secret.encode('utf-8'), msg=payload, digestmod=hashlib.sha256)
    print(f"LOCAL:  {local_signature.hexdigest()}")
    print(f"REMOTE: {github_signature}")
    # See if they match
    # return hmac.compare_digest(local_signature.hexdigest(), github_signature)  # Slow compare for safety
    return local_signature.hexdigest() == github_signature
    

class Handler(http.server.SimpleHTTPRequestHandler):
    # A new Handler is created for every incoming request tho do_XYZ
    # methods correspond to different HTTP methods.

    def do_GET(self):
        self.send_response(200)
        # this below is the new header
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b"<html><H3>GitHub listener works ok.</H3></html>")

    def do_POST(self):
        global PATH
        global SECRET
        print('-----------------------')
        print('GET %s (from client %s)' % (self.path, self.client_address))
        print(self.headers)
        
        length = int(self.headers['Content-Length'])
        # payload = json.loads(self.rfile.read(length))
        payload = self.rfile.read(length)
        if validate_signature(payload, SECRET, signature_header=self.headers["X-Hub-Signature-256"]):
            print("Correct secret")
        else:
            print("incorrect secret")
            self.send_response(code=400)
            return self.wfile.write(json.dumps({"result": "incorrect secret"}).encode('utf-8'))
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        # sResponse = {}
        sResponse = asyncio.run(git_pull(path=PATH))
        if sResponse["stderr"]:
            # There is an error while processing git pull
            self.send_response(code=400)
        else:
            self.send_response(code=200)
        return self.wfile.write(json.dumps(sResponse).encode('utf-8'))


parser = argparse.ArgumentParser(description='This mini-server listens for GitHub web-hooks')
parser.add_argument('-p', '--port', help='Port running the server', type=int, default=PORT)
parser.add_argument('-d', '--dir', help='Path to execute git pull command', type=str, default=PATH)
parser.add_argument('-s', '--secret', help='GitHub secret string', type=str, default=SECRET)
args = parser.parse_args()

# h = hashlib.new('sha1')
# h.update(bytes(SECRET.encode("UTF-8")))
# SECRET = h.hexdigest()

SECRET = args.secret
PORT = args.port
PATH = args.dir

server = http.server.HTTPServer(('', PORT), Handler)
print(f"Listening to port: {PORT}")
server.serve_forever()
