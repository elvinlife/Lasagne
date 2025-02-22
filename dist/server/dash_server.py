#!/usr/bin/env python3
"""A simple HTTP server

To start the server:
    python delayserver.py

Ipython Run:
    import BaseHTTPServer
    from delayserver import MyHTTPRequestHandler
    http = BaseHTTPServer.HTTPServer( ('localhost', 8000),
        MyHTTPRequestHandler)
    http.serve_forever()

To test with browser : 'http://198.248.242.16:8005/mpd/index.html')

To retriev from Python2.7 Shell:
    import urllib2
     urllib2.urlopen(
            "http://198.248.242.16:8006/mpd/x4ukwHdACDw.mpd").read()
To Test from client:
  from urllib2 import urlopen
  data = urlopen("http://198.248.242.16:8006/x4ukwHdACDw/video/1/seg-0001.m4f"))


To DO:
    -- Create a logging module
    -- Get the IP address of the machine automatically
    -- Directory Listing as in SimpleHTTPServer.py
    -- Guess Type of File
    -- Translate path from HTML to local path
    -- Automate the MPD and DASH file LIST generation
"""
import time
import BaseHTTPServer
import sys
import os
from virtual_video import VirtualVideo
from argparse import ArgumentParser
from collections import defaultdict
import logging
sys.path.append("./dist/util/")
from configure_log_file import configure_log_file, write_json
import config_dash

# Default values
DEFAULT_HOSTNAME = '127.0.0.1'
DEFAULT_PORT = 8006
DEFAULT_SLOW_RATE = 0.001

BLOCK_SIZE = 1024

# Values set by the option parser
PORT = DEFAULT_PORT
HOSTNAME = DEFAULT_HOSTNAME
HTTP_VERSION = "HTTP/1.1"
# 10 kbps when size is in bytes
SLOW_RATE = DEFAULT_SLOW_RATE

HTML_PAGES = ['index.html', 'list.html', 'media/my_image.png']
MPD_FILES = ["dist/sample_mpd/mot17-10-base.config",
             "dist/sample_mpd/mot17-10.config",
             "dist/sample_mpd/BigBuckBunny.mpd"]
HTML_404 = "404.html"

# dict that holds the current active sessions
# Has the Keys :
#       'session_list' = List of active session ID's = {connection_id, port}
#       'delay' : iterator to check if we need to delay or not
# connection_id -> VirtualVideo
ACTIVE_DICT = defaultdict(dict)

# DELAY Parameters
# Number of the segement to insert delay
#COUNT = 3
SLOW_COUNT = 1000
DELAY_VALUES = dict()


def delay_decision():
    """ Module to decide if the segemnt is to be delayed or not"""
    for i in range(30):
        if i % 3 == 0:
            yield 0
        yield 1


class MyHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """HTTPHandler to serve the DASH video"""

    def do_GET(self):
        """Function to handle the get message"""
        #request = self.path.strip("/").split('?')[0]
        request = self.path.split('?')[0]
        if request.startswith('/'):
            request = request[1:]
        # connection_id = client IP, dirname of file
        connection_id = self.client_address[0]
        shutdown = False
        #check if the request is for the a directory
        if request in HTML_PAGES:
            print("Request HTML %s" % request)
            duration = normal_write(self.wfile, request)
        elif request in MPD_FILES:
            print("Request for MPD %s" % request)
            print("Setup Connection: {}".format(connection_id))
            duration = normal_write(self.wfile, request)  #, **kwargs)
            # assuming that the new session always
            # starts with the download of the MPD file
            # Making sure that older sessions are not
            # in the ACTIVE_DICT
            if connection_id in ACTIVE_DICT:
                del (ACTIVE_DICT[connection_id])
            ACTIVE_DICT[connection_id] = VirtualVideo(request)
        elif request.split('.')[-1] in ['m4s', 'mp4']:
            print("\n")
            config_dash.LOG.info("Request for DASH Media %s" % request)
            if connection_id not in ACTIVE_DICT:
                print("Error: connection_id: {}".format(connection_id))
                shutdown = True
                pass
            else:
                segment_size = ACTIVE_DICT[connection_id].get_video(request)
                duration, file_size = virtual_write(self.wfile, segment_size)
                config_dash.LOG.info("Stream time: %.2fs segment_size: %d stream_rate: %dKbps" \
                    % ( duration, file_size, int(file_size / duration * 8) >> 10))
        else:
            self.send_error(404)
            return
        #self.send_response( 200 )
        #self.send_header('ContentType', 'text/plain;charset=utf-8')
        #self.send_header('Content-Length', str(os.path.getsize(request)))
        #self.send_header('Pragma', 'no-cache' )
        #self.end_headers()
        if shutdown:
            self.server.shutdown()

def virtual_write(output, size):
    """Function to write arbitrary bytes to output stream"""
    start_time = time.time()
    data_len = 0
    dummy_data = "".join(["a" for i in range(BLOCK_SIZE)])
    while True:
        if size < BLOCK_SIZE:
            data = dummy_data[:size]
        else:
            data = dummy_data
        output.write(data)
        data_len += len(data)
        size -= len(data)
        if size <= 0:
            break
    now = time.time()
    output.flush()
    return now-start_time, data_len

def normal_write(output, request):
    """Function to write the video onto output stream"""
    data = None
    try:
        with open(request, 'rb') as request_file:
            start_time = time.time()
            data_len = 0
            while True:
                data = request_file.read(BLOCK_SIZE)
                output.write(data)
                data_len += len(data)
                if len(data) < BLOCK_SIZE:
                    break
            now = time.time()
            output.flush()
    except IOError:
        with open(HTML_404, 'r') as request_file:
            start_time = time.time()
            output.write(request_file.read())
            now = time.time()
            output.flush()
    return now - start_time, data_len


def dir_write(output, data):
    """Function to write the video onto output stream"""
    start_time = time.time()
    output.write(data.read())
    now = time.time()
    output.flush()
    return now - start_time


def slow_write(output, request, rate=None):
    """Function to write the video onto output stream with interruptions in
    the stream
    """
    print("Slow write of %s" % request)
    with open(request, 'r') as request_file:
        start_time = time.time()
        data = request_file.read(BLOCK_SIZE)
        output.write(data)
        last_send = time.time()
        current_stream = len(data)
        while data != '':
            print("In loop")
            if rate:
                if curr_send_rate(BLOCK_SIZE, last_send - time.time()) > rate:
                    continue
                else:
                    break
            output.write(data)
            last_send = time.time()
            current_stream += len(data)
            data = request_file.read(BLOCK_SIZE)
        now = time.time()
        output.flush()
    print('Served %d bytes of file: %s in %f seconds' % (
        current_stream, request, now - start_time) )
    return now - start_time


def curr_send_rate(data_size, time_to_send_data):
    """ Method to calculate the current rate at which the data
        is being sent. Data_size in byes
        The return value is in kbps
    """
    rate = None
    while True:
        try:
            rate = data_size * 8 / time_to_send_data / 1000
            break
        except ZeroDivisionError:
            continue
    return rate


def start_server():
    """ Module to start the server"""
    http_server = BaseHTTPServer.HTTPServer((HOSTNAME, PORT),
                                            MyHTTPRequestHandler)
    print( " ".join(("Listening on ", HOSTNAME, " at Port ",
                    str(PORT), " - press ctrl-c to stop")) )
    # Use this Version of HTTP Protocol
    http_server.protocol_version = HTTP_VERSION
    http_server.serve_forever()


def create_arguments(parser):
    """ Adding arguments to the parser"""
    parser.add_argument('-p', '--PORT', type=int,
                        help=("Port Number to run the server. Default = %d" % DEFAULT_PORT), default=DEFAULT_PORT)
    parser.add_argument('-s', '--HOSTNAME', help=("Hostname of the server. Default = %s"
                                                  % DEFAULT_HOSTNAME), default=DEFAULT_HOSTNAME)
    parser.add_argument('-d', '--SLOW_RATE', type=float, help=(
        "Delay value for the server in msec. Default = %f" % DEFAULT_SLOW_RATE),
                        default=DEFAULT_SLOW_RATE)


def update_config(args):
    """ Module to update the config values with the a
    arguments """
    globals().update(vars(args))
    return


def main():
    """Program wrapper"""
    parser = ArgumentParser(description='Process server parameters')
    create_arguments(parser)
    args = parser.parse_args()
    update_config(args)
    configure_log_file(log_file=None)
    start_server()


if __name__ == "__main__":
    config_dash.LOG_LEVEL = logging.INFO
    sys.exit(main())
