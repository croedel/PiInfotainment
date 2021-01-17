""" GPS info transformation + reverse Geo lookup 
"""
import requests
import logging

def reverse_lookup(lat, lon):
  url = 'https://nominatim.openstreetmap.org/reverse'
  payload = { 'format': 'jsonv2', 'lat': lat, 'lon': lon, 'zoom': 10, 'addressdetails': 1 }
  headers = { 'User-Agent': 'pi3d RaspiPicFrame' }
  ret='ERROR'
  try:
    response = requests.get( url, payload, headers=headers )
  except requests.exceptions.RequestException as err:
    logging.error( "Couldn't request openstreetmap API: Exception {:s}".format(err) )
  else:
    if response.status_code == 200:
      ret = response.json()
    else:
      logging.error( "Error while requesting openstreetmap API: {:s} -> {:d} {:s}".format( str(payload), response.status_code, response.reason) )

  return ret

def latlon2dec(direction, degrees, minutes, seconds):
  # GPS info can be decimal or tuples
  if isinstance(degrees, tuple): 
    degrees = degrees[0] / degrees[1]
  if isinstance(minutes, tuple): 
    minutes = minutes[0] / minutes[1]
  if isinstance(seconds, tuple): 
    seconds = seconds[0] / seconds[1]
  dec = float(degrees) + float(minutes)/60 + float(seconds)/(60*60)
  if direction == 'S' or direction == 'W':
    dec *= -1
  return dec  

def lookup( gps_info ):
  try:
    lat = latlon2dec( gps_info[1], gps_info[2][0], gps_info[2][1], gps_info[2][2] )
    lon = latlon2dec( gps_info[3], gps_info[4][0], gps_info[4][1], gps_info[4][2] )  

    json = reverse_lookup(lat, lon)  
    if json != 'ERROR':
      addr = json.get('address')
      if addr:
        ret = addr.get('country_code','??').upper() + '-' 
        if addr.get('postcode'):
          ret += addr.get('postcode') + ' '
        if json.get('name'):
          ret += json.get('name')
  except:
    ret = ''
  return ret

#############################################################################
if __name__ == "__main__":
  logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )

  gps_info =  { 1: 'N', 2: ((48, 1), (7, 1), (3162, 100)), 3: 'E', 4: ((11, 1), (21, 1), (5236, 100)), 
    5: b'\x00', 6: (691071, 1286), 12: 'K', 13: (0, 1), 16: 'T', 17: (171448, 1293), 23: 'T', 24: (171448, 1293), 31: (65, 1)}
  print( lookup(gps_info) )

  gps_info = { 1: 'N', 2: (48, 7, 1, 3.162), 3: 'E', 4: (11, 21, 5.236 ) } 
  print( lookup(gps_info) )
