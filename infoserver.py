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
  import paho.mqtt.client as mqttcl
  import paho.mqtt.publish as publish
except Exception as e:
  logging.warning("MQTT not set up because of: {}".format(e))

srvstat = {}

# --------- MQTT -------------
def on_mqtt_connect(mqttclient, userdata, flags, rc):
  logging.info("Connected to MQTT broker")

def on_mqtt_message(mqttclient, userdata, message):
  global srvstat
  try:
    msg = message.payload.decode("utf-8")
    logging.info( 'MQTT: {} -> {}'.format(message.topic, msg))
    topic = message.topic.split("/")
    srvstat[topic[1]] = msg
  except Exception as e:
    logging.warning("Error while handling MQTT message: {}".format(e))

def mqtt_start(): 
  try: 
    client = mqttcl.Client()
    client.username_pw_set(config.MQTT_LOGIN, config.MQTT_PASSWORD) 
    client.connect(config.MQTT_SERVER, config.MQTT_PORT, 60) 
    client.subscribe("screenstat/+", qos=0)
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    client.loop_start()
    logging.info('MQTT client started')
    return client
  except Exception as e:
    logging.warning("Couldn't start MQTT: {}".format(e))

def mqtt_stop(client):
  try: 
    client.loop_stop()
    logging.info('MQTT client stopped')
  except Exception as e:
    logging.warning("Couldn't stop MQTT: {}".format(e))

def mqtt_publish( topic, payload ):  
  auth = {
    'username': config.MQTT_LOGIN,
    'password': config.MQTT_PASSWORD 
  }  
  logging.info("Publish MQTT command {}: {} {}".format(topic, payload, str(auth)))
  try:
    publish.single(topic, payload=payload, hostname=config.MQTT_SERVER, port=config.MQTT_PORT, keepalive=10, auth=auth)
  except Exception as e:
    logging.warning("Could't send MQTT command: {}".format(e))

# actual webserver -------------------------------------------

class Handler(BaseHTTPRequestHandler):
  def _set_header(self, status=200):
    if status == 200:
      self.send_response(200)
      self.send_header('Content-type', 'text/html')
      self.send_header('Cache-Control', 'no-cache')
    else:
      self.send_error(status)
    self.end_headers()

  def _publishMQTT( self, params ):
    # publish command to MQTT
    if 'topic' in params:
      topic = 'screen/' + params['topic'][0]   
      if 'data' in params:
        data = params['data'][0]
      else:
        data = ''
      mqtt_publish( topic, data )

  def _getSrvStatus(self):
    global srvstat
    status_info = { 
      "Status date": srvstat.get("status_date", "-"),
      "Status": srvstat.get("status", "-"),
      "Picture directory": srvstat.get("pic_dir", "-"),
      "Subdirectory": srvstat.get("subdirectory", "-"),
      "Show pictures of last N days": srvstat.get("recent_days", "-"),
      "Start Date": srvstat.get("date_from", "-"),
      "End Date": srvstat.get("date_to", "-"),
      "Paused": srvstat.get("paused", "-"), 
      "Current Picture": srvstat.get("pic_num", "-"),
      "Total no. of pictures": srvstat.get("nFi", "-"),
      "Monitor status": srvstat.get("monitor_status", "-"),
      "pid": srvstat.get("pid", "-"),
      "System info": srvstat.get("uname", "-"),
      "System load": srvstat.get("load", "-")
    }

    status_table = ""
    for i, j in status_info.items():
      status_table += "<tr>\n"
      status_table += "  <td>\n"
      status_table += "    " + i + "\n"
      status_table += "  </td>\n"
      status_table += "  <td>\n"
      status_table += "    " + j + "\n"
      status_table += "  </td>\n"
      status_table += "</tr>\n"
    return status_table

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
    
    if path == "index.html":
      self._publishMQTT( params )
      status_table = self._getSrvStatus()
    try:
      with open(fname, 'rb') as file:
        if path == "index.html":
          content = file.read().decode("utf-8")
          content = content.replace( "%server_status%", status_table )
          self._set_header(200)
          self.wfile.write(content.encode("utf-8")) # Read the file and send the contents 
        else:
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

#----------------------

def run(server_class=HTTPServer, handler_class=Handler, addr='localhost', port=8080):
  mqttclient = mqtt_start()
  server_address = (addr, port)
  httpd = server_class(server_address, handler_class)
  logging.info('Starting httpd on {}:{}'.format(addr, port))
  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    pass
  httpd.server_close()
  mqtt_stop(mqttclient)
  logging.info('httpd stopped')


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Infotainment HTTP server")
  parser.add_argument( "-a", "--address", default="localhost", help="Specify the IP address on which the server listens" )
  parser.add_argument( "-p", "--port", type=int, default=8080, help="Specify the port on which the server listens" )
  args = parser.parse_args()
  run( addr=args.address, port=args.port )
 