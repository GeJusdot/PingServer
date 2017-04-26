#!/usr/bin/env python
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient
import tornado.gen
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
import time
import ping
import json
import logging
from tornado.options import define, options

ALLOW_IPS = ("127.0.0.1","localhost")


define("port", default=8181, help="run on the given port", type=int)
class PingHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(2)

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        client_ip =  self.request.remote_ip
        if client_ip not in ALLOW_IPS :
            self.send_error(403)
        host = self.get_argument('host')
        host = host.lower().strip().rstrip('/').lstrip('http://').lstrip("https://")
        timeout = float(self.get_argument('timeout',1))
        count = int(self.get_argument('count',5))
        res = yield self.ping(host, timeout, count)
        self.write(json.dumps(res))
        self.finish()

    @run_on_executor
    def ping(self, host,time,count):
        return ping.quiet_ping(host,time,count)

class TestHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("test!")
        
if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = tornado.web.Application(handlers=[
            (r"/getping", PingHandler), (r"/test", TestHandler)])
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    #http_server.listen(options.port)
    http_server.bind(options.port)
    http_server.start(0)
    tornado.ioloop.IOLoop.instance().start()


