#!/usr/bin/env python3
"""
Infotainment HTTP Server
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import argparse
import urllib
import html
import datetime
import os
import config

try:
  import paho.mqtt.client as mqttcl
  import paho.mqtt.publish as publish
except Exception as e:
  logging.warning("MQTT not set up because of: {}".format(e))

srvstat = {}
server_address = ()
pic_history = []

# --------- MQTT -------------
def on_mqtt_connect(mqttclient, userdata, flags, rc):
  logging.info("Connected to MQTT broker")

def on_mqtt_message(mqttclient, userdata, message):
  global srvstat, pic_history
  try:
    msg = message.payload.decode("utf-8")
    topic = message.topic.split("/")
    srvstat[topic[1]] = msg
    if topic[1] == "current_pic" and msg != "None":
      tm = datetime.datetime.now()
      pic_history.append([tm, msg])
      pic_history.sort(key=lambda x: x[0], reverse=True)
      if len(pic_history) > config.PIC_HISTORY:
        pic_history.pop(len(pic_history)-1)
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
    logging.error("Could't send MQTT command: {}".format(e))

# actual webserver -------------------------------------------

class Handler(BaseHTTPRequestHandler):
  def _set_header(self, status=200, type="html"):
    if status == 200:
      self.send_response(200)
      self.send_header('Content-type', 'text/'+type)
      self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
      self.send_header('Pragma', 'no-cache')
      self.send_header('Expires', '0')
    else:
      self.send_error(status)
    self.end_headers()

  def _publish_MQTT( self, params ):
    # publish command to MQTT
    if 'topic' in params:
      topic = 'screen/' + params['topic'][0]   
      if 'data' in params:
        data = params['data'][0]
      else:
        data = ''
      mqtt_publish( topic, data )

  def _get_srv_status_info(self):
    global srvstat
    status_info = { 
      "Status date": srvstat.get("status_date", "-"),
      "Status": srvstat.get("status", "-"),
      "Subdirectory": srvstat.get("subdirectory", "-"),
      "Show pictures of last N days": srvstat.get("recent_days", "-"),
      "Start Date": srvstat.get("date_from", "-"),
      "End Date": srvstat.get("date_to", "-"),
      "Paused": srvstat.get("paused", "-"), 
      "Picture": srvstat.get("pic_num", "-"),
      "Current picture": srvstat.get("current_pic", "-"),
      "Picture dir refreshed": srvstat.get("pic_dir_refresh", "-"),
      "Weather skip count": srvstat.get("w_skip_count", "-"),
      "Monitor status": srvstat.get("monitor_status", "-"),
      "Infotainment system started": srvstat.get("start_date", "-"),
      "System load": srvstat.get("load", "-"),
      "CPU temperature": srvstat.get("cpu_temp", "-")
    }

    status_table = ""
    for key, val in status_info.items():
      status_table += "<tr>\n"
      status_table += "  <td> " + html.escape(key) + " </td>\n"
      status_table += "  <td> " + html.escape(val) + " </td>\n"
      status_table += "</tr>\n"
    return status_table

  def _get_pic_history(self):
    global pic_history
    history_table = ""
    for item in pic_history:
      history_table += "<tr>\n"
      history_table += "  <td> " + item[0].strftime("%d.%m.%Y %H:%M:%S") + " </td>\n"
      history_table += "  <td> " + html.escape(item[1]) + " </td>\n"
      history_table += "</tr>\n"
    return history_table

  def _get_dynamic_content( self, content ):
    global server_address
    content = content.decode("utf-8")
    parts = self.path.strip('/').split('?')
    if len(parts) > 1: # URL with parameters -> redirect
      destination = "http://" + server_address[0]
      if server_address[1] != 80:
        destination += ":" + str(server_address[1])
      destination += "/index.html"
      content = content.replace( "%redirect%", '<meta http-equiv="refresh" content="0; url=' + destination + '" />' )
    else:
      content = content.replace( "%redirect%", "")  
    # replace dynamic content  
    content = content.replace( "%server_status%", self._get_srv_status_info() )    
    content = content.replace( "%picture_history%", self._get_pic_history() )
    return content.encode("utf-8")

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
      self._publish_MQTT( params )
    try:
      with open(fname, 'rb') as file:
        content = file.read()
        if path == "index.html":
          content = self._get_dynamic_content(content)
        if fname.endswith(".css"):
          self._set_header(200, type="css")
        else:
          self._set_header(200, type="html")
        self.wfile.write(content)  
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
  global server_address
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
  parser.add_argument( "-a", "--address", default="localhost", help="Host name or IP address on which the server listens" )
  parser.add_argument( "-p", "--port", type=int, default=8080, help="Specify the port on which the server listens" )
  args = parser.parse_args()
  run( addr=args.address, port=args.port )
 