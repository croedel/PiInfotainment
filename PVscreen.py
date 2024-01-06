#!/usr/bin/python
''' Manages PI3D objects for PVinfo sceen 
'''
import logging
import os
import pi3d
from config import cfg
import PVmqtt

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
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['data']['current_PV'] = pi3d.TextBlock(x=-400, y=25, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['data']['current_battery'] = pi3d.TextBlock(x=50, y=-230, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['data']['current_battery_SOC'] = pi3d.TextBlock(x=-60, y=-400, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['data']['current_load'] = pi3d.TextBlock(x=50, y=180, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['data']['current_grid'] = pi3d.TextBlock(x=300, y=25, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))

  pvobj['data']['day_production'] = pi3d.TextBlock(x=x_left+200, y=-160, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['data']['total_production'] = pi3d.TextBlock(x=x_left+200, y=-270, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.7, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))

  pvobj['data']['day_usage'] = pi3d.TextBlock(x=450, y=440, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['data']['day_autarky_rate'] = pi3d.TextBlock(x=450, y=330, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.99, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))

  pvobj['data']['day_grid_load'] = pi3d.TextBlock(x=580, y=-260, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.7, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))
  pvobj['data']['day_grid_feed'] = pi3d.TextBlock(x=580, y=-350, text_format=" ", z=0.0, rot=0.0, char_count=12, size=0.7, 
                        spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0))

  pvobj['icon'] = {}
  pvobj['icon']['battery_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'battery_1.png'), icon_shader, w=280, h=140, 
                x=5, y=-400, z=1.0) 
  pvobj['icon']['grid_interrupt_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'grid_interrupt.png'), icon_shader, w=100, h=100, 
                x=640, y=0, z=1.0)
  
  pvobj['icon']['grid_flow_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'arrow.png'), icon_shader, w=100, h=40, 
                x=380, y=-90, z=1.0)
  pvobj['icon']['battery_flow_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'arrow.png'), icon_shader, w=100, h=40, 
                x=-50, y=-230, z=1.0)
  pvobj['icon']['PV_flow_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'arrow.png'), icon_shader, w=100, h=40, 
                x=-300, y=-90, z=1.0)
  pvobj['icon']['load_flow_icon'] = pi3d.ImageSprite(os.path.join(cfg['PV_ICON_DIR'], 'arrow.png'), icon_shader, w=100, h=40, 
                x=-50, y=170, z=1.0)
  return pvobj

#---------------------------------------------
def set_battery_soc(pvdata, pvobj):
  icon = ""
  try:
    soc = float(pvdata['current_battery_SOC']['value'])
    if soc <= 20:
      icon = "battery_1.png"
    elif soc <= 40:
      icon = "battery_2.png"
    elif soc <= 60:
      icon = "battery_3.png"
    elif soc <= 80:
      icon = "battery_4.png"
    else:
      icon = "battery_5.png"
  except Exception as e:
    logging.error("Couldn't set battery icon. error: {}".format(str(e)))
    icon = "battery_1.png"

  tex = pi3d.Texture(os.path.join(cfg['PV_ICON_DIR'], icon), blend=True, automatic_resize=True, free_after_load=True)
  pvobj['icon']['battery_icon'].set_textures( [tex] )

#---------------------------------------------
def set_island_mode(pvdata, pvobj):
  alpha = 0
  try:
    if pvdata['grid_interrupt']['value']:
      alpha = 1
  except:
    alpha = 0
  pvobj['icon']['grid_interrupt_icon'].set_alpha(alpha)

#---------------------------------------------
def set_flow_arrows(pvdata, pvobj):
  try:
    if pvdata['current_grid']['direction'] == 2:
      pvobj['icon']['grid_flow_icon'].rotateToZ(180) 
      pvobj['icon']['grid_flow_icon'].set_alpha(1)
    elif pvdata['current_grid']['direction'] == 1:
      pvobj['icon']['grid_flow_icon'].rotateToZ(0) 
      pvobj['icon']['grid_flow_icon'].set_alpha(1)
    else:
      pvobj['icon']['grid_flow_icon'].set_alpha(0)

    if pvdata['current_battery']['direction'] == 1:
      pvobj['icon']['battery_flow_icon'].rotateToZ(90) 
      pvobj['icon']['battery_flow_icon'].set_alpha(1)
    elif pvdata['current_battery']['direction'] == 2:
      pvobj['icon']['battery_flow_icon'].rotateToZ(270)
      pvobj['icon']['battery_flow_icon'].set_alpha(1)
    else:
      pvobj['icon']['battery_flow_icon'].set_alpha(0)
    
    if pvdata['current_PV']['direction'] == 1:
      pvobj['icon']['PV_flow_icon'].rotateToZ(0) 
      pvobj['icon']['PV_flow_icon'].set_alpha(1)
    else:
      pvobj['icon']['PV_flow_icon'].set_alpha(0)
    
    if pvdata['current_load']['direction'] == 1:
      pvobj['icon']['load_flow_icon'].rotateToZ(90) 
      pvobj['icon']['load_flow_icon'].set_alpha(1)
    else:
      pvobj['icon']['load_flow_icon'].set_alpha(0)
  except Exception as e:
    logging.error("Couldn't set flow arrow icons. error: {}".format(str(e)))

#---------------------------------------------
def set_data_colours(pvdata, pvobj):
  # colour codes
  c_green = (0.0, 0.7, 0.0, 1.0)
  c_yellow = (1.0, 0.6, 0.1, 1.0)
  c_red = (1.0, 0.0, 0.0, 1.0)

  try:
    # set text colours
    if float(pvdata['day_autarky_rate']["value"]) >= 80:
      pvobj['data']['day_autarky_rate'].colouring.set_colour(c_green)
    elif float(pvdata['day_autarky_rate']["value"]) >= 50:
      pvobj['data']['day_autarky_rate'].colouring.set_colour(c_yellow)
    else:
      pvobj['data']['day_autarky_rate'].colouring.set_colour(c_red)
  except Exception as e:
    logging.error("Couldn't set PV text colors. error: {}".format(str(e)))

#---------------------------------------------
def refresh(pvobj, pvmqtt):
  logging.info("Refreshing PV info")
  pvdata = pvmqtt.get_data()
  try:
    for param, data in pvdata.items():
      if param in pvobj['data']:
        text = "{}{}".format( data["value"], data["unit"] )
        pvobj['data'][param].set_text(text_format=text)
    set_battery_soc(pvdata, pvobj)    
    set_island_mode(pvdata, pvobj)
    set_data_colours(pvdata, pvobj)   
    set_flow_arrows(pvdata, pvobj) 
  except Exception as e:
    logging.error("Couldn't update PV object. error: {}".format(str(e)))

#---------------------------------------------
def set_alpha(pvobj, alpha):
  try:
    for _, obj in pvobj['data'].items():
      obj.colouring.set_colour(alpha=alpha) 
    for _, obj in pvobj['icon'].items():
      if alpha > 0 and obj.alpha() > 0: 
        obj.set_alpha(alpha=alpha)
  except Exception as e:
    logging.error("Couldn't set alpha for PV objects. error: {}".format(str(e)))
