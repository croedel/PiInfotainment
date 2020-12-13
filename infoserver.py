#!/usr/bin/env python3
"""
Infotainment HTTP Server
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import argparse
import urllib
import os
import config
logging.basicConfig( level=logging.INFO, format="[%(levelname)s] %(message)s" )

try:
  import paho.mqtt.publish as publish
except Exception as e:
  logging.warning("MQTT not set up because of: {}".format(e))

def mqtt_publish( topic, payload ):  
  auth = {}
  auth['username'] = config.MQTT_LOGIN
  auth['password'] = config.MQTT_PASSWORD 
  logging.info("Publish MQTT command {}: {} {}".format(topic, payload, str(auth)))
  try:
    publish.single(topic, payload=payload, hostname=config.MQTT_SERVER, port=config.MQTT_PORT, keepalive=10, auth=auth)
  except Exception as e:
    logging.warning("Could't send MQTT command: {}".format(e))

class Handler(BaseHTTPRequestHandler):
  def _set_header(self, status=200):
    if status == 200:
      self.send_response(200)
      self.send_header('Content-type', 'text/html')
      self.send_header('Cache-Control', 'no-cache')
    else:
      self.send_error(status)
    self.end_headers()

  def do_GET(self):
    parts = self.path.strip('/').split('?')
    path = parts[0]
    if path == '':
      path = "index.html"  
    if len(parts) > 1:
      params = urllib.parse.parse_qs(parts[1])
    else:
      params = ''
    fname = os.path.join(os.path.dirname(__file__), path)
    logging.info("GET request, Path: {}, fname: {}, Params: {}".format(path, fname, str(params)) )
    
    # publish command to MQTT
    if 'topic' in params:
      topic = 'frame/' + params['topic'][0]   
      if 'data' in params:
        data = params['data'][0]
      else:
        data = ''
      mqtt_publish( topic, data )
    
    try:
      with open(fname, 'rb') as file: 
        self._set_header(200)
        self.wfile.write(file.read()) # Read the file and send the contents 
    except IOError as e:
      logging.warning("Couldn't open {}".format(e))
      self._set_header(404)

  def do_POST(self):
    content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
    post_data = self.rfile.read(content_length) # <--- Gets the data itself
    logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
            str(self.path), str(self.headers), post_data.decode('utf-8'))
    self._set_header()
    self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))

#########################
def run(server_class=HTTPServer, handler_class=Handler, addr='localhost', port=8080):
  server_address = (addr, port)
  httpd = server_class(server_address, handler_class)
  logging.info('Starting httpd on {}:{}'.format(addr, port))
  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    pass
  httpd.server_close()
  logging.info('Stopping httpd...')


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Infotainment HTTP server")
  parser.add_argument( "-a", "--address", default="localhost", help="Specify the IP address on which the server listens" )
  parser.add_argument( "-p", "--port", type=int, default=8080, help="Specify the port on which the server listens" )
  args = parser.parse_args()
  run( addr=args.address, port=args.port )
 