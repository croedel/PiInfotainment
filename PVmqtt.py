#!/usr/bin/env python3
"""
Read PV data from MQTT broker
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import time
from config import cfg

try:
  import paho.mqtt.client as mqttcl
  import paho.mqtt.publish as publish
except Exception as e:
  logging.error("MQTT not set up because of: {}".format(e))

# =====================================
# MQTT client functionality
def on_mqtt_connect(mqttclient, userdata, flags, rc):
  logging.info("Connected to MQTT broker")

#----------------------  
def on_mqtt_message(mqttclient, userdata, message):
  global srvstat, pic_history
  try:
    msg = message.payload.decode("utf-8")
    topic = message.topic.split("/")
    parameter = topic[2] + "_" + topic[3]
    userdata[parameter] = msg # store received data in userdata
    logging.debug("MQTT data received: {} = {}".format(parameter, msg))

  except Exception as e:
    logging.warning("Error while handling MQTT message: {}".format(str(e)))

#----------------------  
def mqtt_start(server, port, login, password, topic, pvdata): 
  try:  
    client = mqttcl.Client()
    client.user_data_set(pvdata) # allow to store received data
    client.username_pw_set(login, password) 
    client.connect(server, port, 60) 
    client.subscribe(topic + "/#", qos=0)
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    client.loop_start()
    logging.info('MQTT client started')
    return client
  except Exception as e:
    logging.error("Couldn't start MQTT: {}".format(str(e)))
    return None

#----------------------  
def mqtt_stop(client):
  try: 
    client.loop_stop()
    logging.info('MQTT client stopped')
  except Exception as e:
    logging.warning("Couldn't stop MQTT: {}".format(str(e)))


#====================================================
# Main class which enables to connect to mqtt broker and retrieve inverter data
class PVmqtt:
  #----------------------  
  def __init__(self):
    self.mqttclient = None
    self.pvdata = {}

  #----------------------  
  def __del__(self):
    if self.mqttclient:
      mqtt_stop(self.mqttclient)

  #----------------------  
  def connect(self, server, port, login, password, topic):  
    self.mqttclient = mqtt_start(server=server, port=port, login=login, password=password, 
                                 topic=topic, pvdata=self.pvdata)
    if self.mqttclient:
      return True
    else:
      return False

  #----------------------  
  def _format_data(self, key, unit):
    value = self.pvdata.get(key, 0)
    direction = None

    if unit in ("W", "kWh", '%'):   
      value = float(value)
    if unit in ("W", '%'):
      value = int(round(value, 0))
    if unit in ("W", "kWh"):
      if value == 0:
        direction = 3
      elif value > 0:
        direction = 1
      else:    
        direction = 2
        value = -value  

    if direction:
      return { "value": value, "unit": unit, "direction": direction }
    else:
      return { "value": value, "unit": unit }
  
  #----------------------  
  # get mqtt data as nicely formatted dictionary, containing "value", "unit" and - if applicable - "direction"
  def get_data(self):
    data = {}
    try:
        data["dt"] = self._format_data("current_api_date", "")                        # Timestamp
        data["current_PV"] = self._format_data("current_PV", "W")                     # Current power flow from PV
        data["current_grid"] = self._format_data("current_grid", "W")                 # Current power flow from/to grid
        data["current_battery"] = self._format_data("current_battery", "W" )          # Current power flow from/to battery
        data["current_battery_SOC"] = self._format_data("current_battery_SOC", "%" )  # Current battery SOC
        data["current_load"] = self._format_data("current_consumption", "W" )         # Current consumed power
        data["grid_interrupt"] = self._format_data("current_inverter_status", "" )    # Grid status
        if data["grid_interrupt"]["value"] == "5":
          data["grid_interrupt"]["value"] = True  # Grid interrupted
        else:
          data["grid_interrupt"]["value"] = False  
        data["day_grid_load"] = self._format_data("day_grid_load", "kWh")             # Today's energy loaded from grid
        data["day_grid_feed"] = self._format_data("day_grid_feed", "kWh")             # Today's energy fed into grid
        data["day_usage"] = self._format_data("day_usage", "kWh")                     # Today's total energy consumption
        data["day_usage_self"] = self._format_data("day_usage_self", "kWh")           # Today's energy consumption originating from own PV or battery (i.e. not grid)
        data["day_total"] = self._format_data("day_total", "kWh")                     # Today's total energy production (PV + battery discharge)
        data["day_autarky_rate"] = self._format_data("day_autarky_rate", "%")             # Today's independance rate from grid power
        data["day_self_usage_rate"] = self._format_data("day_own_consumption_rate", "%")  # Ratio of self used energy (vs. fed into grid)
        data["day_production"] = self._format_data("day_PV", "kWh")                   # Energy produced by the PV today
        data["month_production"] = self._format_data(0, "kWh")                        # Energy produced by the PV this month
        data["year_production"] = self._format_data(0, "kWh")                         # Energy produced by the PV this year
        data["total_production"] = self._format_data("total_PV", "kWh")               # Energy produced by the PV in total
    except Exception as e:
        logging.error( "Error while retrieving PV data: {}".format(e) )

    return data

#==================================
# Test only
def main():
  if cfg['VERBOSE'] == True:
    logging.getLogger().setLevel(logging.DEBUG)
  
  pvmqtt = PVmqtt()
  pvmqtt.connect( server=cfg['MQTT_PV_SERVER'], port=cfg['MQTT_PV_PORT'], 
                  login=cfg['MQTT_PV_LOGIN'], password=cfg['MQTT_PV_PASSWORD'], 
                  topic=cfg['MQTT_PV_TOPIC'] )

  time.sleep(20)
  data = pvmqtt.get_data()

  logging.info("---------------------------------")
  logging.info("Formatted PV data:")
  for param, data in data.items():
    logging.info( "{}: {} {} {}".format(param, data.get("value"), data.get("unit"), data.get("direction")) )

#----------------------
if __name__ == '__main__':
  main()
  