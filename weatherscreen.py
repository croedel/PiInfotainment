#!/usr/bin/python
''' Manages PI3D objects for weather sceen 
'''
import logging
import os
import pi3d
import config
import weather

def weather_obj_create( width, height ):
  icon_shader = pi3d.Shader("uv_flat")
  weatherobj = {}
  # Assumed display size: 1920 x 1080 ==> +/-960 ; +/-540

  w_static_size = 75  # size of static images
  w_icon_size = 180   # size of weather icons
  w_margin_left = 30
  w_margin_top = 100
  y_top = height*0.5 - w_margin_top
  weatherobj['static'] = {}
  weatherobj['static']['sunrise'] = pi3d.ImageSprite(os.path.join(config.W_ICON_DIR, 'sunrise.png'), icon_shader, w=w_static_size, h=w_static_size, 
                          x=-160, y=y_top, z=1.0) 
  weatherobj['static']['sunset'] = pi3d.ImageSprite(os.path.join(config.W_ICON_DIR, 'sunset.png'), icon_shader, w=w_static_size, h=w_static_size, 
                          x=60, y=y_top, z=1.0) 
  weatherobj['static']['uvidx'] = pi3d.ImageSprite(os.path.join(config.W_ICON_DIR, 'uvidx.png'), icon_shader, w=w_static_size, h=w_static_size, 
                          x=400, y=y_top, z=1.0) 

  x = -width*0.5 + w_margin_left + w_static_size*0.5
  weatherobj['static']['temp'] = pi3d.ImageSprite(os.path.join(config.W_ICON_DIR, 'temp.png'), icon_shader, w=w_static_size*1.5, h=w_static_size*1.5, 
                          x=x, y=-10, z=1.0) 
  weatherobj['static']['pop'] = pi3d.ImageSprite(os.path.join(config.W_ICON_DIR, 'rainprop.png'), icon_shader, w=w_static_size, h=w_static_size, 
                          x=x, y=-150, z=1.0) 
  weatherobj['static']['wind'] = pi3d.ImageSprite(os.path.join(config.W_ICON_DIR, 'wind.png'), icon_shader, w=w_static_size, h=w_static_size, 
                          x=x, y=-250, z=1.0) 
  weatherobj['static']['humidity'] = pi3d.ImageSprite(os.path.join(config.W_ICON_DIR, 'humidity.png'), icon_shader, w=w_static_size, h=w_static_size, 
                          x=x, y=-350, z=1.0) 
  weatherobj['static']['pressure'] = pi3d.ImageSprite(os.path.join(config.W_ICON_DIR, 'pressure.png'), icon_shader, w=w_static_size, h=w_static_size, 
                          x=x, y=-450, z=1.0) 

  weatherobj['current'] = {}
  weatherobj['current']['dt'] = pi3d.TextBlock(x=-900, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  weatherobj['current']['sunrise'] = pi3d.TextBlock(x=-105, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=10, size=0.6, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  weatherobj['current']['sunset'] = pi3d.TextBlock(x=120, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=10, size=0.6, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  weatherobj['current']['uvi'] = pi3d.TextBlock(x=460, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.6, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))

  w_margin_left = w_margin_left + 2*w_static_size
  w_spacing = int(w_icon_size / 1.8)
  w_item_cnt = int( (width-w_margin_left) / (w_icon_size + w_spacing))
  weatherobj['forecast'] = []
  for i in range(w_item_cnt):
    item = {}
    x = -width*0.5 + w_margin_left + i*(w_icon_size + w_spacing)
    item['date'] = pi3d.TextBlock(x=x, y=320, text_format=" ", z=0.1, rot=0.0, char_count=20, size=0.8, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['daytime'] = pi3d.TextBlock(x=x, y=270, text_format=" ", z=0.1, rot=0.0, char_count=15, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['temp'] = pi3d.TextBlock(x=x, y=20, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.99, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['feels_like'] = pi3d.TextBlock(x=x, y=-40, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['pop'] = pi3d.TextBlock(x=x, y=-150, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['wind'] = pi3d.TextBlock(x=x, y=-250, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['humidity'] = pi3d.TextBlock(x=x, y=-350, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
    item['pressure'] = pi3d.TextBlock(x=x, y=-450, text_format=" ", z=0.1, rot=0.0, char_count=10, size=0.6, 
                            spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))

    item['icon'] = pi3d.ImageSprite(os.path.join(config.W_ICON_DIR, '01d.png'), icon_shader, w=w_icon_size, h=w_icon_size, 
                x=x+90, y=150, z=1.0) 
    weatherobj['forecast'].append( item )
  return weatherobj

def weather_refresh(weatherobj):
  weather_info = weather.get_weather_info( config.W_LATITUDE, config.W_LONGITUDE, config.W_UNIT, config.W_LANGUAGE, config.W_API_KEY )
  try:
    for key, val in weather_info['current'].items():
      if key in weatherobj['current']:
        weatherobj['current'][key].set_text(text_format=val)
    for i in range( min(len(weather_info['forecast']), len(weatherobj['forecast'])) ):
      for key, val in weather_info['forecast'][i].items():
        if key in weatherobj['forecast'][i]:
          if key == 'icon':
            w_tex = pi3d.Texture(os.path.join(config.W_ICON_DIR, weather_info['forecast'][i]['icon']), 
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

