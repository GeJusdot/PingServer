from tornado.ioloop import IOLoop
import tornado.web
import time
from tornado.httpserver import HTTPServer

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        print "get"
        time.sleep(10)
        self.write("Hello, world")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

if __name__ == "__main__":
    '''
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
    '''
    app = make_app()
    server = HTTPServer(app)
    server.bind(8888)
    server.start(0)  # Forks multiple sub-processes
    IOLoop.current().start()


