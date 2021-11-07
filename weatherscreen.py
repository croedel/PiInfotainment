#!/usr/bin/python
''' Manages PI3D objects for weather sceen 
'''
import logging
import os
import pi3d
from config import cfg
import weather

def weather_obj_create( width, height ):
  icon_shader = pi3d.Shader("uv_flat")
  weatherobj = {}

  # This screen is optimized for a display size of FullHD 1920 x 1080
  # So the ranges are ==> x +/-960 ; y +/-540
  # You might need to adjust for other display dimensions
  y_top = height*0.5 - cfg['W_MARGIN_TOP']
  x_sunrise = -width*0.5 + cfg['W_POINT_SIZE']*10
  x_sunset = x_sunrise + cfg['W_STATIC_SIZE']*3
  x_uvi = x_sunset + cfg['W_STATIC_SIZE']*4  
  x_cases7 = x_uvi + cfg['W_STATIC_SIZE']*5 
  weatherobj['static'] = {}
  weatherobj['static']['sunrise'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], 'sunrise.png'), icon_shader, w=cfg['W_STATIC_SIZE'], h=cfg['W_STATIC_SIZE'], 
                          x=x_sunrise, y=y_top, z=1.0) 
  weatherobj['static']['sunset'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], 'sunset.png'), icon_shader, w=cfg['W_STATIC_SIZE'], h=cfg['W_STATIC_SIZE'], 
                          x=x_sunset, y=y_top, z=1.0) 
  weatherobj['static']['uvidx'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], 'uvidx.png'), icon_shader, w=cfg['W_STATIC_SIZE'], h=cfg['W_STATIC_SIZE'], 
                          x=x_uvi, y=y_top, z=1.0) 
  weatherobj['static']['corona'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], 'corona_g.png'), icon_shader, w=cfg['W_STATIC_SIZE'], h=cfg['W_STATIC_SIZE'], 
                          x=x_cases7, y=y_top, z=1.0) 

  x = -width*0.5 + cfg['W_MARGIN_LEFT'] + cfg['W_STATIC_SIZE']*0.5
  x_dt = -width*0.5 + cfg['W_MARGIN_LEFT']
  y_date = y_top - cfg['W_STATIC_SIZE']*1.5
  y_icon = y_date - cfg['W_ICON_SIZE']*0.9
  y_temp = 0
  y_pop = y_temp - cfg['W_STATIC_SIZE']*1.5
  y_wind = y_pop - cfg['W_STATIC_SIZE']*1.5
  y_humidity = y_wind - cfg['W_STATIC_SIZE']*1.5
  y_pressure = y_humidity - cfg['W_STATIC_SIZE']*1.5

  weatherobj['static']['temp'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], 'temp.png'), icon_shader, w=cfg['W_STATIC_SIZE']*1.5, h=cfg['W_STATIC_SIZE']*1.5, 
                          x=x, y=y_temp, z=1.0) 
  weatherobj['static']['pop'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], 'rainprop.png'), icon_shader, w=cfg['W_STATIC_SIZE'], h=cfg['W_STATIC_SIZE'], 
                          x=x, y=y_pop, z=1.0) 
  weatherobj['static']['wind'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], 'wind.png'), icon_shader, w=cfg['W_STATIC_SIZE'], h=cfg['W_STATIC_SIZE'], 
                          x=x, y=y_wind, z=1.0) 
  weatherobj['static']['humidity'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], 'humidity.png'), icon_shader, w=cfg['W_STATIC_SIZE'], h=cfg['W_STATIC_SIZE'], 
                          x=x, y=y_humidity, z=1.0) 
  weatherobj['static']['pressure'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], 'pressure.png'), icon_shader, w=cfg['W_STATIC_SIZE'], h=cfg['W_STATIC_SIZE'], 
                          x=x, y=y_pressure, z=1.0) 

  weatherobj['current'] = {}
  weatherobj['current']['dt'] = pi3d.TextBlock(x=x_dt, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  weatherobj['current']['sunrise'] = pi3d.TextBlock(x=x_sunrise+cfg['W_STATIC_SIZE']*0.7, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=10, size=0.6, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  weatherobj['current']['sunset'] = pi3d.TextBlock(x=x_sunset+cfg['W_STATIC_SIZE']*0.7, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=10, size=0.6, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  weatherobj['current']['uvi'] = pi3d.TextBlock(x=x_uvi+cfg['W_STATIC_SIZE']*0.7, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.6, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  weatherobj['current']['cases7_per_100k'] = pi3d.TextBlock(x=x_cases7+cfg['W_STATIC_SIZE']*0.7, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))

  w_item_cnt = int( (width-cfg['W_MARGIN_LEFT']) / (cfg['W_ICON_SIZE'] + cfg['W_SPACING']))
  weatherobj['forecast'] = []
  for i in range(w_item_cnt):
    item = {}
    x = -width*0.5 + cfg['W_MARGIN_LEFT'] + 2*cfg['W_STATIC_SIZE'] + i*(cfg['W_ICON_SIZE'] + cfg['W_SPACING'])
    item['date'] = pi3d.TextBlock(x=x, y=y_date, text_format=" ", z=0.1, rot=0.0, char_count=20, size=0.8, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['daytime'] = pi3d.TextBlock(x=x, y=y_date-cfg['W_STATIC_SIZE']*0.7, text_format=" ", z=0.1, rot=0.0, char_count=15, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['temp'] = pi3d.TextBlock(x=x, y=y_temp+cfg['W_STATIC_SIZE']*0.4, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.99, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['feels_like'] = pi3d.TextBlock(x=x, y=y_temp-cfg['W_STATIC_SIZE']*0.4, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['pop'] = pi3d.TextBlock(x=x, y=y_pop, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['wind'] = pi3d.TextBlock(x=x, y=y_wind, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['humidity'] = pi3d.TextBlock(x=x, y=y_humidity, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['pressure'] = pi3d.TextBlock(x=x, y=y_pressure, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))

    item['icon'] = pi3d.ImageSprite(os.path.join(cfg['W_ICON_DIR'], '01d.png'), icon_shader, w=cfg['W_ICON_SIZE'], h=cfg['W_ICON_SIZE'], 
                x=x+cfg['W_ICON_SIZE']*0.5, y=y_icon, z=1.0) 
    weatherobj['forecast'].append( item )
  return weatherobj

def set_corona_colour(weather_info, weatherobj):
  try:
    cases7 = int(weather_info['current']['cases7_per_100k'])
    if cases7 < 20:
      colour = (0.0, 0.7, 0.0, 1.0) 
      icon = "corona_g.png"
    elif cases7 < 35:
      colour = (1.0, 1.0, 0.2, 1.0) 
      icon = "corona_l.png"
    elif cases7 < 50:
      colour = (1.0, 0.6, 0.1, 1.0) 
      icon = "corona_y.png"
    elif cases7 < 100:
      colour = (1.0, 0.1, 0.0, 1.0) 
      icon = "corona_p.png"
    elif cases7 < 150:
      colour = (1.0, 0.0, 1.0, 1.0)
      icon = "corona_v.png"
    else:
      colour = (0.8, 0.3, 1.0, 1.0)
      icon = "corona_x.png"
  except:
    colour = (1.0, 1.0, 1.0, 1.0)       
  weatherobj['current']['cases7_per_100k'].colouring.set_colour( colour=colour )         
  tex = pi3d.Texture(os.path.join(cfg['W_ICON_DIR'], icon), blend=True, automatic_resize=True, free_after_load=True)
  weatherobj['static']['corona'].set_textures( [tex] )

def weather_refresh(weatherobj):
  weather_info = weather.get_weather_info( cfg['W_LATITUDE'], cfg['W_LONGITUDE'], cfg['W_UNIT'], cfg['W_LANGUAGE'], cfg['W_API_KEY'] )
  try:
    for key, val in weather_info['current'].items():
      if key in weatherobj['current']:
        weatherobj['current'][key].set_text(text_format=val)
    set_corona_colour(weather_info, weatherobj)    
    for i in range( min(len(weather_info['forecast']), len(weatherobj['forecast'])) ):
      for key, val in weather_info['forecast'][i].items():
        if key in weatherobj['forecast'][i]:
          if key == 'icon':
            w_tex = pi3d.Texture(os.path.join(cfg['W_ICON_DIR'], weather_info['forecast'][i]['icon']), 
                  blend=True, automatic_resize=True, free_after_load=True)
            weatherobj['forecast'][i][key].set_textures( [w_tex] )
          else:  
            weatherobj['forecast'][i][key].set_text(text_format=val)
  except Exception as e:
    logging.error("Couldn't update weather object. error: {}".format(str(e)))

def weather_set_alpha(weatherobj, alpha):
  try:
    for _, obj in weatherobj['static'].items():
      obj.set_alpha(alpha)
    for _, obj in weatherobj['current'].items():
      obj.colouring.set_colour(alpha=alpha)
    for item in weatherobj['forecast']:
      for key, obj in item.items():
        if key == 'icon':
          obj.set_alpha(alpha)
        else:
          obj.colouring.set_colour(alpha=alpha)  
  except Exception as e:
    logging.error("Couldn't set alpha for weather object. error: {}".format(str(e)))

