""" GPS info transformation + reverse Geo lookup 
"""
import requests

def reverse_lookup(lat, lon):
  url = 'https://nominatim.openstreetmap.org/reverse'
  payload = { 'format': 'jsonv2', 'lat': lat, 'lon': lon, 'zoom': 10, 'addressdetails': 1 }
  headers = { 'User-Agent': 'pi3d PictureFrame' }
  ret='ERROR'
  try:
    response = requests.get( url, payload, headers=headers )
  except requests.exceptions.RequestException as err:
    print( "Couldn't request openstreetmap API: Exception {:s}".format(err) )
  else:
    if response.status_code == 200:
      ret = response.json()
    else:
      print( "Error while requesting openstreetmap API: {:s} -> {:d} {:s}".format( str(payload), response.status_code, response.reason) )

  return ret

def latlon2dec(direction, degrees, minutes, seconds):
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
  gps_info = {
    1: 'E', 
    2: (48,18,2),
    3: 'N', 
    4: (11,22,0) 
  }  
  print( lookup(gps_info) )
