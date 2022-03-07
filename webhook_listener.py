#!/usr/bin/python3
# small web server that instruments "GET" but then serves up files
# to server files with zero lines of code,  do
#
#   python -m http.server -d /home/user/git_repo -p 9007     # python 3
#
# Initial gist was shamelessly snarfed from Gary Robinson
#    http://www.garyrobinson.net/2004/03/one_line_python.html
#
import asyncio
import http.server
import argparse
import json

PATH = "."
PORT = 9007


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
        self.wfile.write(json.dumps(sResponse).encode('utf-8'))


parser = argparse.ArgumentParser(description='Description of your program')
parser.add_argument('-p', '--port', help='Port running the server', type=int, default=PORT)
parser.add_argument('-d', '--dir', help='Path to execute git pull command', type=str, default=PATH)
args = parser.parse_args()

PORT = args.port
PATH = args.dir

server = http.server.HTTPServer(('', PORT), Handler)
print(f"Listening to port: {PORT}")
server.serve_forever()
