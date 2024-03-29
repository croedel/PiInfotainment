""" Fetches weather data from openweathermap.org and returns the result as formatted strings 
"""
import requests
import time
import datetime
import locale
import math
from config import cfg
import logging

last_refresh = 0.0

def _uvi2str( uvi, lang ):
  if uvi < 3:
    ret = 'niedrig' if lang=="de" else 'low'
  elif uvi < 6:
    ret = 'mittel' if lang=="de" else 'medium'
  elif uvi < 8:
    ret = 'hoch' if lang=="de" else 'high'
  elif uvi < 11:
    ret = 'sehr hoch' if lang=="de" else 'very high'
  else:
    ret = 'extrem' if lang=="de" else 'extreme'
  return ret

def _degree2str( degree ):
  wind_rose = ('N','NO','O','SO','S','SW','W','NW','N')
  idx = int((degree + 22.5) / 45)
  return wind_rose[idx]

def _request_openweathermap( lat, lon, units, lang, appid ):  # get weather info from OpenWeatherMap API
  ret="ERROR"
  global last_refresh
  tm = time.time()
  if tm > last_refresh + 120:  # limit to max. 30 requests per hour to prevent API abuse
    last_refresh = tm
    url = 'https://api.openweathermap.org/data/2.5/onecall'
    payload = { 'lat': lat, 'lon': lon, 'units': units, 'lang': lang, 'appid': appid }
    try:
      response = requests.get( url, payload, timeout=3 )
    except requests.exceptions.RequestException as err:
      logging.error( "Couldn't request openweathermap API: Exception {:s}".format(str(err)) )
    else:
      if response.status_code == 200:
        ret = response.json()
      else:
        logging.error( "Error while requesting openweathermap API: {:s} -> {:d} {:s}".format( str(payload), response.status_code, response.reason) )
  else:
    logging.info( "Weather data refresh aborted: abuse prevention triggered" )
    ret = "ABUSE"
  return ret  
  
# normalize weather info
def _normalize_weather(weather_info, lang):
  if lang == 'de':
    txt_now = "Aktuell"
    daytime = {
      7: 'Morgens', 
      10: 'Vormittags',
      13: 'Mittags',
      16: 'Nachmittags', 
      19: 'Abends', 
      0: 'Nachts'
    }
  else:
    txt_now = "Now"
    daytime = {
      7: 'morning',
      10: 'forenoon', 
      13: 'noon',
      16: 'afternoon', 
      19: 'evening', 
      0: 'night'
    } 
  w_dict = {}

  try:
    # current weather
    w_dict['current'] = {}
    w_dict['forecast'] = []
    w_current = weather_info.get('current')
    if w_current:
      dt = datetime.datetime.fromtimestamp(w_current.get('dt'))
      dt_rise = datetime.datetime.fromtimestamp(w_current.get('sunrise'))
      dt_set = datetime.datetime.fromtimestamp(w_current.get('sunset'))
      uvi_str = _uvi2str(w_current.get('uvi', '-'), lang=lang)
      wind_str = _degree2str(w_current.get('wind_deg', '-'))
      w_dict['current']['dt'] = dt.strftime('%a %d.%m.%Y %H:%M')
      w_dict['current']['sunrise'] = dt_rise.strftime('%H:%M')
      w_dict['current']['sunset'] = dt_set.strftime('%H:%M')
      w_dict['current']['uvi'] = '{:s} ({:.0f})'.format(uvi_str, w_current.get('uvi', '-'))

      data = {}
      data['date'] = txt_now
      data['daytime'] = " "
      data['temp'] = '{:.1f}°C'.format(w_current.get('temp', '-'))
      data['feels_like'] = '{:.1f}°C'.format(w_current.get('feels_like', '-'))
      data['pressure'] = '{:.0f}hPa'.format(w_current.get('pressure', '-'))
      data['humidity'] = '{:.0f}%'.format(w_current.get('humidity', '-'))
      data['wind'] = '{:s} {:.0f}km/h'.format(wind_str, w_current.get('wind_speed', 0) * 3.6)
      data['clouds'] = '{:0.0f}/8'.format(w_current.get('clouds', '-') * 8/100)
      minutely = weather_info.get('minutely')
      if minutely and len(minutely)>0: 
        data['pop'] = '{:.0f}%'.format(weather_info['minutely'][0].get('precipitation', 0) *100)

      w_current_weather = w_current.get('weather')
      if w_current_weather and w_current_weather[0]:
        data['wid'] = w_current_weather[0].get('id', '-')
        data['main'] = w_current_weather[0].get('main', '-')
        data['description'] = w_current_weather[0].get('description', '-')
        data['icon'] = w_current_weather[0].get('icon', '-') + '.png'
      w_dict['forecast'].append( data )

    # read hourly forecast data
    dt_now = datetime.datetime.now()
    w_hourly = weather_info.get('hourly')
    if w_hourly:
      last_date = "-"
      for item in w_hourly:
        dt = datetime.datetime.fromtimestamp(item.get('dt'))
        if dt < dt_now or dt.hour not in (7,10,13,16,19,0):
          continue
        if dt.hour == 0:
          dt += datetime.timedelta(days=-1) # let this belong to the previous day
        wind_str = _degree2str(w_current.get('wind_deg', '-'))
        data = {}
        data['date'] = dt.strftime('%a %d.%m.')
        if data['date'] == last_date:
          data['date'] = " "
        else:
          last_date = data['date']
        data['daytime'] = daytime[dt.hour]
        data['temp'] = '{:.1f}°C'.format(item.get('temp', '-'))
        data['feels_like'] = '{:.1f}°C'.format(item.get('feels_like', '-'))
        data['pressure'] = '{:.0f}hPa'.format(item.get('pressure', '-'))
        data['humidity'] = '{:.0f}%'.format(item.get('humidity', '-'))
        data['wind'] = '{:s} {:.0f}km/h'.format(wind_str, w_current.get('wind_speed', '-') * 3.6)
        data['clouds'] = '{:0.0f}/8'.format(item.get('clouds', '-') * 8/100)
        data['pop'] = '{:.0f}%'.format(item.get('pop', '-') *100)

        w_hourly_weather = item.get('weather')
        if w_hourly_weather and w_hourly_weather[0]:
          data['wid'] = w_hourly_weather[0].get('id', '-')
          data['main'] = w_hourly_weather[0].get('main', '-')
          data['description'] = w_hourly_weather[0].get('description', '-')
          data['icon'] = w_hourly_weather[0].get('icon', '-') + '.png'

        w_dict['forecast'].append( data )
  except Exception as e:
    logging.error( "Error while normalizing weather data: Exception {:s}".format(str(e)) )
  return w_dict
  
#------------------------------------------------------------------    
# this is the main function to get the weather info
def get_weather_info( lat, lon, units, lang, appid ): 
  logging.info('Refreshing weather info')
  w_dict = {}
  if lang == 'de':
    locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")  
  raw_data = _request_openweathermap( lat, lon, units, lang, appid )
  if isinstance(raw_data, dict):
    w_dict = _normalize_weather(raw_data, lang)
  return w_dict

#############################################################################
if __name__ == "__main__":
  logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )
  weather_info = get_weather_info( 48.1355979, 11.3627159, 'metric', 'de', cfg['W_API_KEY'] )

  current = weather_info.get('current')
  print( "Current")
  if current:
    for tag, val in current.items():
      print( " - " + tag + ": " + str(val) )
  print()

  forecast = weather_info.get('forecast')
  print( "Forecast")
  if forecast:
    for item in weather_info['forecast']:
      for tag, val in item.items():
        print( " - " + tag + ": " + str(val) )
      print()  
