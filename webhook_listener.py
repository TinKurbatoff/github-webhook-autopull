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
import logging

# Gets or creates a logger
logger = logging.getLogger(__name__)  
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s : %(levelname)s : %(name)s : %(message)s')


PATH = "."
PORT = 9007
SECRET = ""
SERVICE = ""


async def git_pull(cmd):
    """ Executes `git pull` command in specified directory """
    result = {"stdout": "", "stderr": ""}
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return_code = proc.returncode

    logger.info(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        result["stdout"] = stdout.decode()
        logger.info(f'[stdout]\n{result["stdout"]}')
    if stderr:
        result["stderr"] = stderr.decode()
        result['error_code'] = return_code
        logger.info(f'[stderr] (EC={return_code})\n{result["stderr"]}')
    return result


def validate_signature(payload, secret, signature_header):
    # Get the signature from the payload
    # Borrowed at 
    #     https://gist.github.com/andrewfraley/0229f59a11d76373f11b5d9d8c6809bc
    if signature_header:
        sha_name, github_signature = signature_header.split('=')
        if sha_name != 'sha256':
            logger.info('ERROR: X-Hub-Signature in payload headers was not sha1=****')
            return False
    else:
        return False
      
    # Create our own signature
    local_signature = hmac.new(secret.encode('utf-8'), msg=payload, digestmod=hashlib.sha256)
    logger.info(f"LOCAL:  {local_signature.hexdigest()}")
    logger.info(f"REMOTE: {github_signature}")
    # See if they match
    return hmac.compare_digest(local_signature.hexdigest(), github_signature)  # Slow compare for safety
    # return local_signature.hexdigest() == github_signature
    

class Handler(http.server.SimpleHTTPRequestHandler):
    # A new Handler is created for every incoming request tho do_XYZ
    # methods correspond to different HTTP methods.

    def add_headers(self):
        """ Adds default headers for a proper response  """
        self.send_header('Content-type', 'text/html;char=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        return

    def do_GET(self):
        """ Serves GET requests from everywhere for validation  """
        self.send_response(200)
        # this below is the new header
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b"<html><H3>GitHub listener works ok.</H3></html>")

    def do_POST(self):
        """ Serves POST requests from GitHub """
        global PATH
        global SECRET
        response_code = 200  # Default response code
        logger.info('-----------------------')
        logger.info('GET %s (from client %s)' % (self.path, self.client_address))
        logger.info(self.headers)
        
        try:
            length = int(self.headers['Content-Length'] or 0)

            # Validate signature
            payload = self.rfile.read(length)
            if validate_signature(payload, SECRET, signature_header=self.headers["X-Hub-Signature-256"]):
                logger.info("Correct secret")
            else:
                logger.warning("Incorrect secret!")
                self.send_response(code=400)
                self.add_headers()
                return self.wfile.write(json.dumps({"result": "incorrect secret"}).encode('utf-8'))
            
            # Call git pull request
            cmd = f"cd {PATH} && git pull"
            if SERVICE:
                cmd = f"{cmd} && sudo /bin/systemctl restart {SERVICE}"
            logger.info(f"...executing: `{cmd}`")
            sResponse = asyncio.run(git_pull(cmd=cmd))
            logger.info(f"Result (json): `{sResponse}`")
            if sResponse["stderr"]:
                # There is an error while processing git pull
                if sResponse['error_code'] != 0:
                    # Return error only if error code is not zero
                    response_code = 400
                
        except Exception as e:
            logger.info(f"[ERROR] {e}")
            sResponse = {"message": f"{e}"} 
        logger.info(f"sResponse: {sResponse}")
        # Add headers
        logger.info(f"Response code: {response_code}")
        self.send_response(code=response_code)
        logger.info("Adding headers to response")
        self.add_headers()
        return self.wfile.write(json.dumps(sResponse).encode('utf-8'))


parser = argparse.ArgumentParser(description='This mini-server listens for GitHub web-hooks')
parser.add_argument('-p', '--port', help='Port running the server', type=int, default=PORT)
parser.add_argument('-d', '--dir', help='Path to execute git pull command', type=str, default=PATH)
parser.add_argument('-s', '--secret', help='GitHub secret string', type=str, default=SECRET)
parser.add_argument('-r', '--restart', help='Restart service if needed', type=str, default=SERVICE)
args = parser.parse_args()

SECRET = args.secret
PORT = args.port
PATH = args.dir
SERVICE = args.restart

server = http.server.HTTPServer(('', PORT), Handler)
logger.info(f"Listening to port: {PORT}")
server.serve_forever()
