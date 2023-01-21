#!/usr/bin/python
''' Manages PI3D objects for PVinfo sceen 
'''
import logging
import os
import pi3d
from config import cfg
import rctpower

def obj_create( width, height ):
  icon_shader = pi3d.Shader("uv_flat")
  pvobj = {}

  # This screen is optimized for a display size of FullHD 1920 x 1080
  # So the ranges are ==> x +/-960 ; y +/-540
  # You might need to adjust for other display dimensions
  y_top = height*0.5 - cfg['W_MARGIN_TOP']
  x_left = -width*0.5 + cfg['W_MARGIN_LEFT']

  pvobj['dt'] = pi3d.TextBlock(x=x_left, y=y_top, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['current_string_a'] = pi3d.TextBlock(x=x_left+60, y=-20, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['current_string_b'] = pi3d.TextBlock(x=x_left+150, y=40, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['current_battery_power'] = pi3d.TextBlock(x=-200, y=-height*0.5+200, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['current_battery_soc'] = pi3d.TextBlock(x=0, y=-height*0.5+100, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['current_house_ext_power'] = pi3d.TextBlock(x=200, y=300, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['current_grid_power'] = pi3d.TextBlock(x=400, y=30, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['day_energy'] = pi3d.TextBlock(x=x_left+100, y=400, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['total_energy'] = pi3d.TextBlock(x=x_left+100, y=200, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))                    
  pvobj['day_house_usage'] = pi3d.TextBlock(x=300, y=-250, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['day_autarky_rate'] = pi3d.TextBlock(x=width*0.3, y=-height*0.5+400, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['day_balance_rate'] = pi3d.TextBlock(x=width*0.3, y=-height*0.5+200, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['day_balance'] = pi3d.TextBlock(x=width*0.3, y=-height*0.5+100, text_format=" ", z=0.0, rot=0.0, char_count=20, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))

  pvobj['battery_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'battery_5.png'), icon_shader, w=width/7, h=height/5, 
                x=0, y=-height*0.5+50, z=1.0) 
  pvobj['island_mode_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'grid_on.png'), icon_shader, w=width/7, h=height/5, 
                x=200, y=-30, z=1.0)
  return pvobj

def set_battery_soc(pv_info, pvobj):
  try:
    soc_val = int(pv_info['current_battery_soc']['value'])
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
  pvobj['battery_icon'].set_textures( [tex] )

def set_island_mode(pv_info, pvobj):
  try:
    val = int(pv_info['current_island_mode']['value'])
    if val == 1:
      icon = "grid_off.png"
    else:
      icon = "grid_on.png"
  except:
      icon = "grid_on.png"
  tex = pi3d.Texture(os.path.join(cfg['PV_ICON_DIR'], icon), blend=True, automatic_resize=True, free_after_load=True)
  pvobj['island_mode_icon'].set_textures( [tex] )


def refresh(pvobj):
  pv_info = rctpower.get_PV_device_data()
  try:
    for key, data in pv_info.items():
      if data["title"] in pvobj:
        text = data["format"].format(data["value"])
        pvobj[key].set_text(text_format=text)
    set_battery_soc(pv_info, pvobj)    
    set_island_mode(pv_info, pvobj)    
  except Exception as e:
    logging.error("Couldn't update PV object. error: {}".format(str(e)))

def set_alpha(pvobj, alpha):
  try:
    for key, obj in pvobj.items():
      if key == 'battery_icon':
        obj.set_alpha(alpha)
      else:
        obj.colouring.set_colour(alpha=alpha)  
  except Exception as e:
    logging.error("Couldn't set alpha for PV object. error: {}".format(str(e)))
