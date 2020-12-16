""" Fetches weather data from openweathermap.org and returns the result as formatted strings 
"""
import requests
import datetime
import locale
import config
import logging

def request_openweathermap( lat, lon, units, lang, appid ):  # get weather info from OpenWeatherMap API
  url = 'https://api.openweathermap.org/data/2.5/onecall'
  payload = { 'lat': lat, 'lon': lon, 'units': units, 'lang': lang, 'appid': appid }
  ret="ERROR"
  try:
    response = requests.get( url, payload )
  except requests.exceptions.RequestException as err:
    logging.error( "Couldn't request openweathermap API: Exception {:s}".format(err) )
  else:
    if response.status_code == 200:
      ret = response.json()
    else:
      logging.error( "Error while requesting openweathermap API: {:s} -> {:d} {:s}".format( str(payload), response.status_code, response.reason) )
  return ret  
  
# normalize weather info
def normalize_weather(weather_info, lang):
  if lang == 'de':
    t_prec_start = 'Niederschlag ab' 
    t_prec_stop = 'Niederschlag bis'
    t_prec_none = 'kein Niederschlag'
    t_prec_cont = 'anhaltender Niederschlag'
    daytime = {
      6: 'Morgens', 
      12: 'Mittags', 
      18: 'Abends', 
      0: 'Nachts'
    }
  else:
    t_prec_start = 'precipitation starts' 
    t_prec_stop = 'precipitation ends'
    t_prec_none = 'no precipitation'
    t_prec_cont = 'continous precipitation'
    daytime = {
      6: 'morning', 
      12: 'noon', 
      18: 'evening', 
      0: 'night'
    } 
  w_dict = {}

  try:
    # current weather
    w_current = weather_info.get('current')
    if w_current:
      dt = datetime.datetime.fromtimestamp(w_current.get('dt'))
      dt_rise = datetime.datetime.fromtimestamp(w_current.get('sunrise'))
      dt_set = datetime.datetime.fromtimestamp(w_current.get('sunset'))
      w_dict['dt'] = dt.strftime('%a %d.%m. %H:%M')
      w_dict['sunrise'] = dt_rise.strftime('%H:%M')
      w_dict['sunset'] = dt_set.strftime('%H:%M')
      w_dict['temp'] = w_current.get('temp', '-')
      w_dict['feels_like'] = w_current.get('feels_like', '-')
      w_dict['pressure'] = w_current.get('pressure', '-')
      w_dict['humidity'] = w_current.get('humidity', '-')
      w_dict['uvi'] = w_current.get('uvi', '-')
      w_dict['clouds'] = w_current.get('clouds', '-')
      w_dict['wind_speed'] = w_current.get('wind_speed', '-')
      w_dict['wind_deg'] = w_current.get('wind_deg', '-')

      w_current_weather = w_current.get('weather')
      if w_current_weather and w_current_weather[0]:
        w_dict['wid'] = w_current_weather[0].get('id', '-')
        w_dict['main'] = w_current_weather[0].get('main', '-')
        w_dict['description'] = w_current_weather[0].get('description', '-')
        w_dict['icon'] = w_current_weather[0].get('icon', '-')

    # read minutely forecast data
    w_minutely = weather_info.get('minutely')
    w_dict['precipitation'] = ''
    if w_minutely:
      prec_now = None 
      for item in w_minutely:
        prec = float( item.get('precipitation', '0.0') )
        if prec < 0.3:
          prec = 0 # very low amount -> set to 0 
        if prec_now == None:
          prec_now = prec
        else:
          dt = datetime.datetime.fromtimestamp(item.get('dt'))
          if prec_now == 0 and prec > 0:
            w_dict['precipitation'] = '{:s} {:s}'.format( t_prec_start, dt.strftime('%H:%M') )
            break 
          elif prec_now > 0 and prec == 0:
            w_dict['precipitation'] = '{:s} {:s}'.format( t_prec_stop, dt.strftime('%H:%M') )
            break 
        if prec == 0:
          w_dict['precipitation'] = t_prec_none
        else:
          w_dict['precipitation'] = t_prec_cont

    # read hourly forecast data
    w_dict['forecast'] = []
    w_hourly = weather_info.get('hourly')
    if w_hourly:
      for item in w_hourly:
        dt = datetime.datetime.fromtimestamp(item.get('dt'))
        if dt.hour not in (6,12,18,0):
          continue
        if dt.hour == 0:
          dt += datetime.timedelta(days=-1) # let this belong to the previous day
        data = {}
        data['date'] = dt.strftime('%a %d.%m.')
        data['daytime'] = daytime[dt.hour]
        data['temp'] = item.get('temp', '-')
        data['feels_like'] = item.get('feels_like', '-')
        data['pressure'] = item.get('pressure', '-')
        data['humidity'] = item.get('humidity', '-')
        data['wind_speed'] = item.get('wind_speed', '-')
        data['wind_deg'] = item.get('wind_deg', '-')
        data['clouds'] = item.get('clouds', '-')
        data['pop'] = item.get('pop', '-')      

        w_hourly_weather = item.get('weather')
        if w_hourly_weather and w_hourly_weather[0]:
          data['wid'] = w_hourly_weather[0].get('id', '-')
          data['main'] = w_hourly_weather[0].get('main', '-')
          data['description'] = w_hourly_weather[0].get('description', '-')
          data['icon'] = w_hourly_weather[0].get('icon', '-')

        w_dict['forecast'].append( data )

    # read alerts (if present)
    w_dict['alerts'] = []
    w_alerts = weather_info.get('alerts')
    if w_alerts:
      for item in w_alerts:
        data = {}
        dt_start = datetime.datetime.fromtimestamp(item.get('start'))
        dt_end = datetime.datetime.fromtimestamp(item.get('end'))
        data['start'] = dt_start.strftime('%a %d.%m. %H:%M')
        data['end'] = dt_end.strftime('%a %d.%m. %H:%M')
        data['event'] = item.get('event', '-')
        data['description'] = item.get('description', '-')

        w_dict['alerts'].append( data ) 
  except Exception as e:
    logging.error( "Error while normalizing weather data: Exception {:s}".format(e) )
  return w_dict

def uvi2str( uvi, lang ):
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

def degree2str( degree ):
  wind_rose = ('N','NO','O','SO','S','SW','W','NW','N')
  idx = int((degree + 22.5) / 45)
  return wind_rose[idx]
  
def format_weather( obj, wtype, lang ):
  if wtype == 'now':
    rep = { 
      '<date>':     obj['dt'], 
      '<sunrise>':  obj['sunrise'], 
      '<sunset>':   obj['sunset'],
      '<temp>':     '{:.1f}°C'.format(obj['temp']), 
      '<ftemp>':    '{:.1f}°C'.format(obj['feels_like']), 
      '<desc>':     obj['description'], 
      '<prec>':     obj['precipitation'], 
      '<pressure>': '{:.0f}hPa'.format(obj['pressure']),
      '<humidity>': '{:.0f}%'.format(obj['humidity']),
      '<clouds>':   '{:0.0f}/8'.format(obj['clouds'] * 8/100),
      '<wind>':     '{:.0f}km/h'.format(obj['wind_speed'] * 3.6), 
      '<winddeg>':  degree2str(obj['wind_deg']),
      '<uvi>':      '{:.0f}'.format(obj['uvi']), 
      '<uvtxt>':    uvi2str(obj['uvi'], lang)  
    }
    title = config.W_NOW_TITLE
    txt = config.W_NOW_TXT
  elif wtype == 'alert':
    rep = { 
      '<start>':   obj['start'], 
      '<end>':     obj['end'], 
      '<event>':   obj['event'], 
      '<desc>':    obj['description'] 
    }
    title = config.W_ALERT_TITLE
    txt = config.W_ALERT_TXT
  else:
    rep = { 
      '<date>':     obj['date'], 
      '<daytime>':  obj['daytime'], 
      '<temp>':     '{:.1f}°C'.format(obj['temp']), 
      '<ftemp>':    '{:.1f}°C'.format(obj['feels_like']), 
      '<wind>':     '{:.0f}km/h'.format(obj['wind_speed'] * 3.6), 
      '<winddeg>':  degree2str(obj['wind_deg']),
      '<pressure>': '{:.0f}hPa'.format(obj['pressure']),
      '<humidity>': '{:.0f}%'.format(obj['humidity']),
      '<clouds>':   '{:0.0f}/8'.format(obj['clouds'] * 8/100),
      '<pop>':      '{:.0f}%'.format(obj['pop'] * 100) 
    }
    if wtype == 'forecast-short':
      rep['<date>'] = '    '
    title = config.W_FORECAST_TITE
    txt = config.W_FORECAST_TXT 

  for i, j in rep.items():
    title = title.replace(i, j)
    txt = txt.replace(i, j)
  return (title, txt)
    
# this is the main function to get the weather info
def get_weather_info( lat, lon, units, lang, appid ): 
  logging.info('Refreshing weather info')
  if lang == 'de':
    locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")  

  weather_info = []
  raw_data = request_openweathermap( lat, lon, units, lang, appid )
  if raw_data != "ERROR":
    w_dict = normalize_weather(raw_data, lang)
    if len(w_dict) > 0:
      item = {}
      (item['title'], item['txt']) = format_weather( w_dict, 'now', lang )
      item['icon'] = w_dict['icon'] + '.png'  
      weather_info.append(item)

      for obj in w_dict['alerts']:
        item = {}
        (item['title'], item['txt']) = format_weather( obj, 'alert', lang )
        item['icon'] = 'alert.png'  
        weather_info.append(item)

      last_date = ""
      for obj in w_dict['forecast']:
        item = {}
        if obj['date'] != last_date:
          (item['title'], item['txt']) = format_weather( obj, 'forecast', lang )
          last_date = obj['date']
        else:
          (item['title'], item['txt']) = format_weather( obj, 'forecast-short', lang )
        item['icon'] = obj['icon'] + '.png'
        weather_info.append(item)
    else: 
      item = {}
      item['title'] = 'Weather data error'
      item['txt'] = ''
      item['icon'] = 'alert.png'  
      weather_info.append(item)
  else: 
    item = {}
    item['title'] = 'Weather info unavailable'
    item['txt'] = ''
    item['icon'] = 'alert.png'  
    weather_info.append(item)

  return weather_info

#############################################################################
if __name__ == "__main__":
  logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )
  weather_info = get_weather_info( 48.1355979, 11.3627159, 'metric', 'de', '6ebd6acb5966433fad4c667062d4c18e' )

  for item in weather_info:
    print( item['title'] )
    print( ' '*5 + item['txt'] )
    print()
