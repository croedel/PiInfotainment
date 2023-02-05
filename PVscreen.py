#!/usr/bin/python
''' Manages PI3D objects for PVinfo sceen 
'''
import logging
import os
import pi3d
from config import cfg
import PVinverter

#---------------------------------------------
def obj_create( width, height ):
  icon_shader = pi3d.Shader("uv_flat")
  pvobj = {}

  # This screen is optimized for a display size of FullHD 1920 x 1080
  # So the ranges are ==> x +/-960 ; y +/-540
  # You might need to adjust for other display dimensions
  y_top = height*0.5 - cfg['W_MARGIN_TOP']
  x_left = -width*0.5 + cfg['W_MARGIN_LEFT']
  pvobj['data'] = {}
  pvobj['data']['dt'] = pi3d.TextBlock(x=x_left, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['current_string_a'] = pi3d.TextBlock(x=x_left+60, y=-20, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['current_string_b'] = pi3d.TextBlock(x=x_left+150, y=40, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['current_battery_power'] = pi3d.TextBlock(x=-200, y=-height*0.5+200, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['current_battery_soc'] = pi3d.TextBlock(x=0, y=-height*0.5+100, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['current_house_ext_power'] = pi3d.TextBlock(x=200, y=300, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['current_grid_power'] = pi3d.TextBlock(x=400, y=30, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['day_energy'] = pi3d.TextBlock(x=x_left+100, y=400, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['total_energy'] = pi3d.TextBlock(x=x_left+100, y=200, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)                    
  pvobj['data']['day_house_usage'] = pi3d.TextBlock(x=300, y=-250, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['day_autarky_rate'] = pi3d.TextBlock(x=width*0.3, y=-height*0.5+400, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['day_balance_rate'] = pi3d.TextBlock(x=width*0.3, y=-height*0.5+200, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)
  pvobj['data']['day_balance'] = pi3d.TextBlock(x=width*0.3, y=-height*0.5+100, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0), justify=1.0)

  pvobj['icon'] = {}
  pvobj['icon']['battery_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'battery_5.png'), icon_shader, w=width/7, h=height/5, 
                x=0, y=-height*0.5+50, z=1.0) 
  pvobj['icon']['island_mode_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'grid_on.png'), icon_shader, w=width/7, h=height/5, 
                x=200, y=-30, z=1.0)
  return pvobj

#---------------------------------------------
def set_battery_soc(pvdata, pvobj):
  try:
    soc = int(pvdata['current_battery_soc']['value'])
    if soc < 20:
      icon = "battery_1.png"
    elif soc < 40:
      icon = "battery_2.png"
    elif soc < 60:
      icon = "battery_3.png"
    elif soc < 80:
      icon = "battery_4.png"
    else:
      icon = "battery_5.png"
  except:
      icon = "battery_5.png"
  tex = pi3d.Texture(os.path.join(cfg['PV_ICON_DIR'], icon), blend=True, automatic_resize=True, free_after_load=True)
  pvobj['icon']['battery_icon'].set_textures( [tex] )

#---------------------------------------------
def set_island_mode(pvdata, pvobj):
  try:
    val = int(pvdata['current_island_mode']['value'])
    if val == 1:
      icon = "grid_off.png"
    else:
      icon = "grid_on.png"
  except:
      icon = "grid_on.png"
  tex = pi3d.Texture(os.path.join(cfg['PV_ICON_DIR'], icon), blend=True, automatic_resize=True, free_after_load=True)
  pvobj['icon']['island_mode_icon'].set_textures( [tex] )

#---------------------------------------------
def set_data_colours(pvdata, pvobj):
  # colour codes
  c_green = (0.0, 0.7, 0.0, 1.0)
  c_yellow = (1.0, 0.6, 0.1, 1.0)
  c_red = (1.0, 0.0, 0.0, 1.0)

  # set text colours
  if pvdata['current_battery_power']["value"] > 0:
    pvobj['data']['current_battery_power'].colouring.set_colour(c_red)
  else:
    pvobj['data']['current_battery_power'].colouring.set_colour(c_green)

  if pvdata['current_grid_power']["value"] > 0:
    pvobj['data']['current_grid_power'].colouring.set_colour(c_red)
  else:
    pvobj['data']['current_grid_power'].colouring.set_colour(c_green)

  if pvdata['day_autarky_rate']["value"] > 80:
    pvobj['data']['day_autarky_rate'].colouring.set_colour(c_green)
  elif pvdata['day_autarky_rate']["value"] > 50:
    pvobj['data']['day_autarky_rate'].colouring.set_colour(c_yellow)
  else:
    pvobj['data']['day_autarky_rate'].colouring.set_colour(c_red)

  if pvdata['day_balance_rate']["value"] > 0:
    pvobj['data']['day_balance_rate'].colouring.set_colour(c_green)
  else:
    pvobj['data']['day_balance_rate'].colouring.set_colour(c_red)

  if pvdata['day_balance']["value"] > 0:
    pvobj['data']['day_balance'].colouring.set_colour(c_green)
  else:
    pvobj['data']['day_balance'].colouring.set_colour(c_red)

#---------------------------------------------
def refresh(pvobj):
  pvdata = PVinverter.get_PV_device_data()
  try:
    for param, data in pvdata.items():
      if param in pvobj['data']:
        text = data["format"].format(data["value"])
        pvobj['data'][param].set_text(text_format=text)
    set_battery_soc(pvdata, pvobj)    
    set_island_mode(pvdata, pvobj)
    set_data_colours(pvdata, pvobj)    
  except Exception as e:
    logging.error("Couldn't update PV object. error: {}".format(str(e)))

#---------------------------------------------
def set_alpha(pvobj, alpha):
  try:
    for _, obj in pvobj['icon'].items():
        obj.set_alpha(alpha)
    for _, obj in pvobj['data'].items():
        obj.colouring.set_colour(alpha=alpha)  
  except Exception as e:
    logging.error("Couldn't set alpha for PV object. error: {}".format(str(e)))
