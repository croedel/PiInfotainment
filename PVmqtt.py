#!/usr/bin/env python3
"""
Read PV data from MQTT broker
"""
import logging
import time
from config import cfg

try:
  import paho.mqtt.client as mqttcl
except Exception as e:
  logging.error("MQTT not set up because of: {}".format(e))

# =====================================
# MQTT client functionality
def on_pv_mqtt_connect(mqttclient, userdata, flags, rc):
  logging.info("Connected to MQTT broker; rc={}".format(rc))

def on_pv_mqtt_disconnect(client, userdata, rc):
  logging.warning("MQTT broker disconnected: {}".format(rc))

def on_pv_mqtt_subscribe(client, userdata, mid, granted_qos):
  logging.info("MQTT broker subscribed to mid {}".format(mid))

#----------------------  
def on_pv_mqtt_message(mqttclient, userdata, message):
  try:
    msg = message.payload.decode("utf-8")
    topic = message.topic.split("/")
    parameter = topic[2] + "/" + topic[3]
    userdata[parameter] = msg # store received data in userdata
    if parameter == "now-base/api_date":
      logging.info("MQTT data received: {} = {}".format(parameter, msg))
    logging.debug("MQTT data received: {} = {}".format(parameter, msg))

  except Exception as e:
    logging.warning("Error while handling MQTT message: {}".format(str(e)))

#----------------------  
def pv_mqtt_start(server, port, login, password, topic, pvdata): 
  try:  
    client = mqttcl.Client( clean_session=True )
    client.user_data_set(pvdata) # allow to store received data
    client.username_pw_set(login, password) 
    client.on_connect = on_pv_mqtt_connect
    client.on_disconnect = on_pv_mqtt_disconnect
    client.on_message = on_pv_mqtt_message
    client.on_subscribe = on_pv_mqtt_subscribe
    client.connect(server, port, 60)
    topics = [ 
      (topic + "/now-base/#", 0),
      (topic + "/day/#", 0),
      (topic + "/total/#", 0) 
    ]
    client.subscribe(topics)
    client.loop_start()
    logging.info('MQTT client started')
    return client
  except Exception as e:
    logging.error("Couldn't start MQTT: {}".format(str(e)))
    return None

#----------------------  
def pv_mqtt_stop(client):
  try: 
    client.loop_stop()
    logging.info('MQTT client stopped')
  except Exception as e:
    logging.warning("Couldn't stop MQTT: {}".format(str(e)))


#====================================================
# Main class which enables to connect to mqtt broker and retrieve inverter data
class PVmqtt:
  #----------------------  
  PV_map = [
    # Name                    MQTT parameter                Unit
    [ "dt",                   "now-base/api_date",          ""    ],  # Timestamp
    [ "current_PV",           "now-base/pv",                "W"   ],  # Current power flow from PV
    [ "current_grid",         "now-base/grid_power",        "W"   ],  # Current power flow from/to grid
    [ "current_battery",      "now-base/battery",           "W"   ],  # Current power flow from/to battery
    [ "current_battery_SOC",  "now-base/battery_soc",       "%"   ],  # Current battery SOC
    [ "current_load",         "now-base/consumption",       "W"   ],  # Current consumed power
    [ "current_backup",       "now-base/backup",            "W"   ],  # Current backup power
    [ "grid_interrupt",       "now-base/inverter_status",   ""    ],  # Grid status
    [ "day_grid_load",        "day/grid_purchase_day",      "kWh" ],  # Today's energy loaded from grid
    [ "day_grid_feed",        "day/grid_feed_day",          "kWh" ],  # Today's energy fed into grid
    [ "day_usage",            "day/consumption_day",        "kWh" ],  # Today's total energy consumption
    [ "day_autarky_rate",     "day/autarky_rate_day",       "%"   ],  # Today's independance rate from grid power
    [ "day_self_usage_rate",  "day/own_consumption_day",    "%"   ],  # Ratio of self used energy (vs. fed into grid)
    [ "day_production",       "day/pv_day",                 "kWh" ],  # Energy produced by the PV today
    [ "total_production",     "total/pv_total",             "kWh" ],  # Energy produced by the PV in total
  ]

  #----------------------  
  def __init__(self, server, port, login, password, topic):
    self.server = server
    self.port = port
    self.login = login
    self.password = password 
    self.topic = topic
    self.mqttclient = None
    self.pvdata = {}

  #----------------------  
  def __del__(self):
    if self.mqttclient:
      pv_mqtt_stop(self.mqttclient)

  #----------------------  
  def connect(self):  
    retry = 0
    while not self.mqttclient and retry < 5:
      self.mqttclient = pv_mqtt_start(server=self.server, port=self.port, login=self.login, password=self.password, 
                                   topic=self.topic, pvdata=self.pvdata)
      if not self.mqttclient:
        retry += 1
        logging.warning( "Couldn't connect to MQTT server. retry={}/5".format(retry) )
        time.sleep(10)

    if self.mqttclient:
      return True
    else:
      logging.error( "Couldn't connect to MQTT server.".format(retry) )
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
        direction = 3   # =0
      elif value > 0:
        direction = 1   # positive
      else:    
        direction = 2   # negative
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
        for item in self.PV_map:
          data[item[0]] = self._format_data(item[1], item[2])
        if data["grid_interrupt"]["value"] == "5":
          data["grid_interrupt"]["value"] = True  # Grid interrupted
        else:
          data["grid_interrupt"]["value"] = False  
    except Exception as e:
        logging.error( "Error while retrieving PV data: {}".format(e) )
    return data

#==================================
# Test only
def main():
  if cfg['VERBOSE'] == True:
    logging.getLogger().setLevel(logging.DEBUG)
  
  pvmqtt = PVmqtt( server=cfg['MQTT_PV_SERVER'], port=cfg['MQTT_PV_PORT'], 
                   login=cfg['MQTT_PV_LOGIN'], password=cfg['MQTT_PV_PASSWORD'], 
                   topic=cfg['MQTT_PV_TOPIC'] )
  pvmqtt.connect()

  time.sleep(20)
  data = pvmqtt.get_data()

  logging.info("---------------------------------")
  logging.info("Formatted PV data:")
  for param, data in data.items():
    logging.info( "{}: {} {} {}".format(param, data.get("value"), data.get("unit"), data.get("direction")) )

#----------------------
if __name__ == '__main__':
  main()
