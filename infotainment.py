#!/usr/bin/python
from __future__ import absolute_import, division, print_function, unicode_literals
''' RaspiInfotainment: Infotainment display for the Raspberry Pi. 
It combines an advanced digital picture frame, a weather forecast and a surveillance camera viewer.  
This project heavily inherited from PictureFrame2020.py, which is part of https://github.com/pi3d/pi3d_demos
'''
import os
import platform
import sys
import logging
import time
import datetime
import random
import math
import subprocess
import pi3d
from pi3d.Texture import MAX_SIZE
from PIL import Image, ImageFilter # these are needed for getting exif data from images

import config
import dircache
import weather
import display

try:
  import paho.mqtt.client as mqttcl
  import paho.mqtt.publish as mqttpub
except Exception as e:
  logging.warning("Couldn't initialize MQTT: {}".format(e))

try:
  import vlc 
except Exception as e:
  logging.warning("Couldn't initialize VLC: {}".format(e))

#####################################################
# global variables 
date_from = None
date_to = None
quit = False
paused = False 
nexttm = 0.0
next_pic_num = 0
iFiles = []
nFi = 0
show_camera = False
camera_end_tm = 0.0
monitor_status = "ON"
pcache = None  
start_date = None

#####################################################
def tex_load(pic_num, iFiles, size=None):
  if type(pic_num) is int:
    fname =       iFiles[pic_num][0]
    orientation = iFiles[pic_num][1]
    dt =          iFiles[pic_num][3]
    exif_info =   iFiles[pic_num][4] 
  else: # allow file name to be passed to this function ie for missing file image
    fname = pic_num
    orientation = 1
  try:
    ext = os.path.splitext(fname)[1].lower()
    if ext in ('.heif','.heic'):
      im = convert_heif(fname)
    else:
      im = Image.open(fname)      
    if config.DELAY_EXIF and type(pic_num) is int: # don't do this if passed a file name
      if dt is None: # exif info ot yet available
        (orientation, dt, exif_info) = get_exif_info(fname, im)
        iFiles[pic_num][1] = orientation
        iFiles[pic_num][3] = dt
        iFiles[pic_num][4] = exif_info
    (w, h) = im.size
    max_dimension = MAX_SIZE # TODO changing MAX_SIZE causes serious crash on linux laptop!
    if not config.AUTO_RESIZE: # turned off for 4K display - will cause issues on RPi before v4
        max_dimension = 3840 # TODO check if mipmapping should be turned off with this setting.
    if w > max_dimension:
        im = im.resize((max_dimension, int(h * max_dimension / w)), resample=Image.LANCZOS)
    elif h > max_dimension:
        im = im.resize((int(w * max_dimension / h), max_dimension), resample=Image.LANCZOS)
    if orientation == 2:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    elif orientation == 3:
        im = im.transpose(Image.ROTATE_180) # rotations are clockwise
    elif orientation == 4:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    elif orientation == 5:
        im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
    elif orientation == 6:
        im = im.transpose(Image.ROTATE_270)
    elif orientation == 7:
        im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
    elif orientation == 8:
        im = im.transpose(Image.ROTATE_90)
    if config.BLUR_EDGES and size is not None:
      wh_rat = (size[0] * im.size[1]) / (size[1] * im.size[0])
      if abs(wh_rat - 1.0) > 0.01: # make a blurred background
        (sc_b, sc_f) = (size[1] / im.size[1], size[0] / im.size[0])
        if wh_rat > 1.0:
          (sc_b, sc_f) = (sc_f, sc_b) # swap round
        (w, h) =  (round(size[0] / sc_b / config.BLUR_ZOOM), round(size[1] / sc_b / config.BLUR_ZOOM))
        (x, y) = (round(0.5 * (im.size[0] - w)), round(0.5 * (im.size[1] - h)))
        box = (x, y, x + w, y + h)
        blr_sz = (int(x * 512 / size[0]) for x in size)
        im_b = im.resize(size, resample=0, box=box).resize(blr_sz)
        im_b = im_b.filter(ImageFilter.GaussianBlur(config.BLUR_AMOUNT))
        im_b = im_b.resize(size, resample=Image.LANCZOS)
        im_b.putalpha(round(255 * config.EDGE_ALPHA))  # to apply the same EDGE_ALPHA as the no blur method.
        im = im.resize((int(x * sc_f) for x in im.size), resample=Image.LANCZOS)
        """resize can use Image.LANCZOS (alias for Image.ANTIALIAS) for resampling
        for better rendering of high-contranst diagonal lines. NB downscaled large
        images are rescaled near the start of this try block if w or h > max_dimension
        so those lines might need changing too.
        """
        im_b.paste(im, box=(round(0.5 * (im_b.size[0] - im.size[0])),
                            round(0.5 * (im_b.size[1] - im.size[1]))))
        im = im_b # have to do this as paste applies in place
    tex = pi3d.Texture(im, blend=True, m_repeat=True, automatic_resize=config.AUTO_RESIZE,
                        free_after_load=True)
    #tex = pi3d.Texture(im, blend=True, m_repeat=True, automatic_resize=config.AUTO_RESIZE,
    #                    mipmap=config.AUTO_RESIZE, free_after_load=True) # poss try this if still some artifacts with full resolution
  except Exception as e:
    logging.error('''Couldn't load file {} giving error: {}'''.format(fname, e))
    tex = None
  return tex

def get_files(dt_from=None, dt_to=None):
  global pcache
  mqtt_publish_status( fields="status", status="updating file_list" )
  file_list = pcache.get_file_list( dt_from, dt_to )
  mqtt_publish_status( fields="status", status="running" )
  logging.info('File list refreshed: {} images found'.format(len(file_list)) )
  return file_list, len(file_list) # tuple of file list, number of pictures


def get_exif_info(file_path_name, im=None):
  global pcache
  exif_info = {}
  dt = None
  orientation = None
  try:
    if im is None:
      im = Image.open(file_path_name) # lazy operation so shouldn't load (better test though)
    exif_data = im._getexif() # TODO check if/when this becomes proper function
    dt = time.mktime(
        time.strptime(exif_data[config.EXIF_DICT['DateTimeOriginal']], '%Y:%m:%d %H:%M:%S'))
    orientation = int(exif_data[config.EXIF_DICT['Orientation']])
    # assemble exif_info
    for tag, val in config.EXIF_DICT.items():
      data = exif_data.get(val)
      if data:
        exif_info[tag] = data
    pcache.set_exif_info( file_path_name, orientation, dt, exif_info ) # write back to cache
  except Exception as e: # NB should really check error here but it's almost certainly due to lack of exif data
    logging.debug('Exception while trying to read EXIF: ', e)
    if dt == None:
      dt = os.path.getmtime(file_path_name) # so use file last modified date
    if orientation == None:
      orientation = 1
  return (orientation, dt, exif_info)

def convert_heif(fname):
  try:
    import pyheif
    from PIL import Image
    heif_file = pyheif.read(fname)
    image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw", heif_file.mode, heif_file.stride)
    return image
  except:
    logging.warning("Could't convert HEIF. Have you installed pyheif?")


# start the picture frame
def start_picframe():
  global date_from, date_to, quit, paused, nexttm, next_pic_num, iFiles, nFi, monitor_status, pcache
  if config.KENBURNS:
    kb_up = True
    config.FIT = False
    config.BLUR_EDGES = False
  if config.BLUR_ZOOM < 1.0:
    config.BLUR_ZOOM = 1.0

  sfg = None # slide for background
  sbg = None # slide for foreground
  next_check_tm = time.time() + config.CHECK_DIR_TM # check if new file or directory every n seconds
  delta_alpha = 1.0 / (config.FPS * config.FADE_TIME) # delta alpha

  # Initialize pi3d system
  DISPLAY = pi3d.Display.create(x=0, y=0, frames_per_second=config.FPS,
                display_config=pi3d.DISPLAY_CONFIG_HIDE_CURSOR, background=config.BACKGROUND)
  CAMERA = pi3d.Camera(is_3d=False)

  shader = pi3d.Shader(config.SHADER)
  slide = pi3d.Sprite(camera=CAMERA, w=DISPLAY.width, h=DISPLAY.height, z=5.0)
  slide.set_shader(shader)
  slide.unif[47] = config.EDGE_ALPHA
  slide.unif[54] = config.BLEND_TYPE

  if config.KEYBOARD:
    kbd = pi3d.Keyboard()

  # PointText and TextBlock. If INFO_TXT_TIME <= 0 then this is just used for no images message
  grid_size = math.ceil(len(config.CODEPOINTS) ** 0.5)
  font = pi3d.Font(config.FONT_FILE, codepoints=config.CODEPOINTS, grid_size=grid_size, shadow_radius=5.0,
                  shadow=(0,0,0,128))
  text = pi3d.PointText(font, CAMERA, max_chars=400, point_size=config.TEXT_POINT_SIZE)
  textlines = []
  textlines.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 50, y=-DISPLAY.height * 0.4,
                            text_format="{:s}".format(" "), z=0.1, rot=0.0, char_count=75, size=0.99, 
                            spacing="F", space=0.02, colour=(1.0, 1.0, 1.0, 1.0)) )
  textlines.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 50, y=-DISPLAY.height * 0.4 - 50,
                            text_format="{:s}".format(" "), z=0.1, rot=0.0, char_count=75, size=0.99, 
                            spacing="F", space=0.02, colour=(1.0, 1.0, 1.0, 1.0)) )
  textlines.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 50, y=DISPLAY.height * 0.45,
                            text_format="{:s}".format(" "), z=0.1, rot=0.0, char_count=49, size=0.8, 
                            spacing="F", space=0.02, colour=(1.0, 1.0, 1.0, 1.0)) )
  textlines.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 50, y=DISPLAY.height * 0.45 - 40,
                            text_format="{:s}".format(" "), z=0.1, rot=0.0, char_count=49, size=0.8, 
                            spacing="F", space=0.02, colour=(1.0, 1.0, 1.0, 1.0)) )
  for item in textlines:
    text.add_text_block(item)

  # prepare to display weather info
  w_point_size = config.W_POINT_SIZE
  w_padding = w_point_size
  weatherinfo = pi3d.PointText(font, CAMERA, max_chars=3000, point_size=w_point_size)
  icon_shader = pi3d.Shader("uv_flat")
  weathertexts = []
  weathericons = []
  w_item_cnt = int(DISPLAY.height * 0.9 / (2*w_point_size + w_padding))
  for i in range(w_item_cnt):
    weathertexts.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 200, y=DISPLAY.height *0.45-70 - i*(2*w_point_size + w_padding),
                            text_format="{:s}".format(" "), z=0.1, rot=0.0, char_count=100, size=0.99, 
                            spacing="F", space=0.02, colour=(1.0, 1.0, 1.0, 1.0)) )
    weathertexts.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 250, y=DISPLAY.height *0.45-70 - i*(2*w_point_size + w_padding) - w_point_size,
                            text_format="{:s}".format(" "), z=0.1, rot=0.0, char_count=100, size=0.99, 
                            spacing="F", space=0.02, colour=(1.0, 1.0, 1.0, 1.0)))
    weathericons.append( pi3d.ImageSprite(config.W_ICON_DIR + '01d.png', icon_shader, w=200, h=200, 
                            x=-DISPLAY.width * 0.5 + 100, y=DISPLAY.height *0.45-70 - i*(2*w_point_size + w_padding) - 20, z=1.0) )

  for item in weathertexts:
    weatherinfo.add_text_block( item )
  for item in weathericons:
    item.set_alpha(0.0)
  
  weather_interstitial_active = True
  next_weather_tm = 0.0
  next_monitor_check_tm = 0.0
  num_run_through = 0
  
  # here comes the main loop
  while DISPLAY.loop_running():
    tm = time.time()
    if (tm > nexttm and not paused) or (tm - nexttm) >= 86400.0: # this must run first iteration of loop
      if nFi > 0:
        nexttm = tm + config.TIME_DELAY
        sbg = sfg
        sfg = None

        if (config.W_SKIP_CNT > 0) and (next_pic_num % config.W_SKIP_CNT == 0) and not weather_interstitial_active: 
          # show weather interstitial
          weather_interstitial_active = True
          sfg = tex_load(config.W_BACK_IMG, 1, (DISPLAY.width, DISPLAY.height))
          for item in textlines:
            item.colouring.set_colour(alpha=0.0)
          for item in weathertexts:
            item.colouring.set_colour(alpha=1.0)
          for item in weathericons:
            item.set_alpha(1.0)
        else: 
          # continue with next picture
          if weather_interstitial_active: # deactivate weather info
            for item in weathertexts:
              item.colouring.set_colour(alpha=0.0)
            for item in weathericons:
              item.set_alpha(0.0)
            weather_interstitial_active = False
          
          start_pic_num = next_pic_num
          while sfg is None: # keep going through until a usable picture is found  
            pic_num = next_pic_num
            sfg = tex_load(pic_num, iFiles, (DISPLAY.width, DISPLAY.height))
            next_pic_num += 1
            if next_pic_num >= nFi:
              num_run_through += 1
              next_pic_num = 0
            if next_pic_num == start_pic_num:
              nFi = 0
              break
          # set description
          if config.INFO_TXT_TIME > 0.0:
            texts = display.format_text(iFiles, pic_num)
            i=0
            for item in textlines:
              item.set_text(text_format=texts[i])
              i += 1    
          else: # could have a NO IMAGES selected and being drawn
            for item in textlines:
              item.colouring.set_colour(alpha=0.0)
          mqtt_publish_status( status="running", pic_num=pic_num )

      if sfg is None:
        sfg = tex_load(config.NO_FILES_IMG, 1, (DISPLAY.width, DISPLAY.height))
        sbg = sfg
        mqtt_publish_status( status="no pictures found" )

      a = 0.0 # alpha - proportion front image to back
      name_tm = time.time() + config.INFO_TXT_TIME
      if sbg is None: # first time through
        sbg = sfg
      slide.set_textures([sfg, sbg])
      slide.unif[45:47] = slide.unif[42:44] # transfer front width and height factors to back
      slide.unif[51:53] = slide.unif[48:50] # transfer front width and height offsets
      wh_rat = (DISPLAY.width * sfg.iy) / (DISPLAY.height * sfg.ix)
      if (wh_rat > 1.0 and config.FIT) or (wh_rat <= 1.0 and not config.FIT):
        sz1, sz2, os1, os2 = 42, 43, 48, 49
      else:
        sz1, sz2, os1, os2 = 43, 42, 49, 48
        wh_rat = 1.0 / wh_rat
      slide.unif[sz1] = wh_rat
      slide.unif[sz2] = 1.0
      slide.unif[os1] = (wh_rat - 1.0) * 0.5
      slide.unif[os2] = 0.0
      if config.KENBURNS:
        xstep, ystep = (slide.unif[i] * 2.0 / config.TIME_DELAY for i in (48, 49))
        slide.unif[48] = 0.0
        slide.unif[49] = 0.0
        kb_up = not kb_up

    if config.KENBURNS:
      t_factor = nexttm - tm
      if kb_up:
        t_factor = config.TIME_DELAY - t_factor
      slide.unif[48] = xstep * t_factor
      slide.unif[49] = ystep * t_factor

    if a < 1.0: # transition is happening
      a += delta_alpha
      if a > 1.0:
        a = 1.0
      slide.unif[44] = a * a * (3.0 - 2.0 * a)
    else: # no transition effect safe to reshuffle etc
      if tm > next_monitor_check_tm: # Check if it's time to switch monitor status
        scheduled_status = check_monitor_status(tm)
        if monitor_status != scheduled_status and not monitor_status.endswith("-MANUAL"):
          switch_HDMI(scheduled_status)
          paused = True if scheduled_status.startswith("OFF") else False
          monitor_status = scheduled_status
          mqtt_publish_status( fields="monitor_status" )
        next_monitor_check_tm = tm + 60 # check every minute
      if monitor_status.startswith("ON"):
        if tm > next_check_tm: # time to check picture directory
          if pcache.refresh_cache() or (config.SHUFFLE and num_run_through >= config.RESHUFFLE_NUM): # refresh file list required
            if config.RECENT_DAYS > 0: # reset data_from to reflect time is proceeding
              date_from = datetime.datetime.now() - datetime.timedelta(config.RECENT_DAYS)
              date_from = (date_from.year, date_from.month, date_from.day)
            iFiles, nFi = get_files(date_from, date_to)
            num_run_through = 0
            next_pic_num = 0
          next_check_tm = tm + config.CHECK_DIR_TM # next check
        if tm > next_weather_tm: # refresh weather info
          weather_info = weather.get_weather_info( config.W_LATITUDE, config.W_LONGITUDE, config.W_UNIT, config.W_LANGUAGE, config.W_API_KEY )
          for i in range( min(len(weather_info), w_item_cnt) ):
            weathertexts[i*2].set_text(text_format=weather_info[i]['title'])
            weathertexts[i*2+1].set_text(text_format=weather_info[i]['txt'])   
            w_tex = pi3d.Texture(config.W_ICON_DIR + weather_info[i]['icon'], blend=True, automatic_resize=True, free_after_load=True)
            weathericons[i].set_textures( [w_tex] )
          next_weather_tm = tm + config.W_REFRESH_DELAY # next check

    slide.draw()

    if nFi <= 0:
      textlines[0].set_text("NO IMAGES SELECTED")
      textlines[0].colouring.set_colour(alpha=1.0)
      next_check_tm = tm + 5.0
    elif tm < name_tm and weather_interstitial_active == False:
      # this sets alpha for the TextBlock from 0 to 1 then back to 0
      dt = (config.INFO_TXT_TIME - name_tm + tm + 0.1) / config.INFO_TXT_TIME
      alpha = max(0.0, min(1.0, 3.0 - abs(3.0 - 6.0 * dt)))
      for item in textlines:
        item.colouring.set_colour(alpha=alpha)

    text.regen()
    text.draw()
    weatherinfo.regen()
    weatherinfo.draw()
    for item in weathericons:
      item.draw()

    if config.KEYBOARD:
      k = kbd.read()
      if k != -1:
        nexttm = time.time() - 86400.0
      if k==27: #ESC
        break
      if k==ord(' '):
        paused = not paused
      if k==ord('s'): # go back a picture
        next_pic_num -= 2
        if next_pic_num < -1:
          next_pic_num = -1      
    if quit or show_camera: # set by MQTT
      break

  if config.KEYBOARD:
    kbd.close()
  DISPLAY.destroy()

# MQTT functionality - see https://www.thedigitalpictureframe.com/
def on_mqtt_connect(mqttclient, userdata, flags, rc):
  logging.info("Connected to MQTT broker")

def on_mqtt_message(mqttclient, userdata, message):
  try:
    # TODO not ideal to have global but probably only reasonable way to do it
    global next_pic_num, iFiles, nFi, date_from, date_to 
    global quit, paused, nexttm, show_camera, camera_end_tm, monitor_status
    msg = message.payload.decode("utf-8")
    reselect = False
    logging.info( 'MQTT: {} -> {}'.format(message.topic, msg))
    if message.topic == "screen/date_from": # NB entered as mqtt string "2016:12:25"
      try:
        msg = msg.replace(".",":").replace("/",":").replace("-",":")
        df = msg.split(":")
        date_from = tuple(int(i) for i in df)
        if len(date_from) != 3:
          raise Exception("invalid date format")
      except:
        date_from = None
      reselect = True
    elif message.topic == "screen/date_to":
      try:
        msg = msg.replace(".",":").replace("/",":").replace("-",":")
        df = msg.split(":")
        date_to = tuple(int(i) for i in df)
        if len(date_to) != 3:
          raise Exception("invalid date format")
      except:
        date_to = None
      reselect = True
    elif message.topic == "screen/recent_days":
      config.RECENT_DAYS = int(msg)  
      if config.RECENT_DAYS > 0:
        date_from = datetime.datetime.now() - datetime.timedelta(config.RECENT_DAYS)  
        date_from = (date_from.year, date_from.month, date_from.day)
        date_to = None
        reselect = True
    elif message.topic == "screen/time_delay":
      config.TIME_DELAY = float(msg)
    elif message.topic == "screen/quit":
      quit = True
    elif message.topic == "screen/pause":
      paused = not paused # toggle from previous value
    elif message.topic == "screen/back":
      next_pic_num -= 2
      if next_pic_num < -1:
        next_pic_num = -1
      nexttm = time.time() - 86400.0
    elif message.topic == "screen/w_skip_count":
      config.W_SKIP_CNT = int(msg)
    elif message.topic == "screen/subdirectory":
      config.SUBDIRECTORY = msg
      date_from = date_to = None
      reselect = True
    elif message.topic == "screen/camera":
      show_camera = True
      camera_end_tm = time.time() + config.CAMERA_THRESHOLD
    elif message.topic == "screen/monitor":
      if msg == "ON":
        monitor_status = "ON-MANUAL"
        paused = False
        switch_HDMI( monitor_status )
      elif msg == "OFF":
        monitor_status = "OFF-MANUAL"
        paused = True
        switch_HDMI( monitor_status )
      else:
        monitor_status = "ON"
        switch_HDMI( monitor_status )
    else:
      logging.info('Unknown MQTT topic: {}'.format(message.topic))

    mqtt_publish_status( status="MQTT command received: {} -> {}".format(message.topic, msg) )
    if reselect:
      iFiles, nFi = get_files(date_from, date_to)
      next_pic_num = 0
  except Exception as e:
    logging.warning("Error while handling MQTT message: {}".format(e))

#-------------------------------------------
def mqtt_start(): 
  try: 
    client = mqttcl.Client()
    client.username_pw_set(config.MQTT_LOGIN, config.MQTT_PASSWORD) 
    client.connect(config.MQTT_SERVER, config.MQTT_PORT, 60) 
    client.subscribe("screen/+", qos=0)
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    client.loop_start()
    logging.info('MQTT client started')
    return client
  except Exception as e:
    logging.warning("Couldn't start MQTT: {}".format(e))

def mqtt_stop(client):
  try: 
    client.loop_stop()
    logging.info('MQTT client stopped')
  except Exception as e:
    logging.warning("Couldn't stop MQTT: {}".format(e))

def mqtt_publish_status( fields=[], status="-", pic_num=-1 ):
  if isinstance( fields, str):
    fields = [fields]  
  global iFiles, nFi, date_from, date_to, paused, monitor_status, start_date, pcache
  dfrom = datetime.datetime(*date_from).strftime("%d.%m.%Y %H:%M:%S") if date_from != None else "None" 
  dto = datetime.datetime(*date_to).strftime("%d.%m.%Y %H:%M:%S") if date_to != None else "None"
  current_pic = iFiles[pic_num][0] if pic_num>=0 else "None"
  cpu_temp = subprocess.check_output( ["vcgencmd", "measure_temp"] )
  info_data = {
    "status": status,
    "start_date": start_date.strftime("%d.%m.%Y %H:%M:%S"),
    "subdirectory": config.SUBDIRECTORY,
    "date_from": dfrom,
    "date_to": dto,
    "recent_days": config.RECENT_DAYS,
    "paused": str(paused), 
    "pic_num": str(pic_num+1) + " / " + str(nFi),
    "w_skip_count": config.W_SKIP_CNT,
    "monitor_status": monitor_status,
    "status_date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
    "current_pic": current_pic,
    "cpu_temp": cpu_temp,
    "pic_dir_refresh": pcache.get_cache_refresh_date().strftime("%d.%m.%Y %H:%M:%S") 
  }
  if hasattr(os, "getloadavg"):
    info_data["load"] = str(os.getloadavg())

  messages = []
  for key, val in info_data.items():
    if len(fields)==0 or key in fields:
      messages.append( { "topic": "screenstat/" + key, "payload": val } )  
  auth = { "username": config.MQTT_LOGIN, "password": config.MQTT_PASSWORD }
  try:
    mqttpub.multiple( messages, client_id="infotainment-server", hostname=config.MQTT_SERVER, port=config.MQTT_PORT, auth=auth)
  except Exception as e:
    logging.warning("Error while sending MQTT status: {}".format(e))

#-------------------------------------------
def cam_viewer_start():
  logging.info("CamViewer started")
  player = vlc.MediaPlayer(config.CAMERA_URL) 
  player.video_set_scale(config.CAMERA_ZOOM)
  player.play()
  return player

def cam_viewer_stop(player):
  logging.info("CamViewer stopped")
  player.stop()
  player.release()

def cam_show():
  global camera_end_tm, monitor_status
  if monitor_status.startswith("OFF"):
    switch_HDMI("ON") # switch monitor temporarily ON
  player = cam_viewer_start()
  while camera_end_tm > time.time():
    time.sleep(5) # wake up regularly to check if camera_end_tm changed async via MQTT   
  cam_viewer_stop(player)
  if monitor_status.startswith("OFF"):
    switch_HDMI("OFF") # switch monitor OFF again 

def check_monitor_status( tm=time.time() ):
  if len(config.MONITOR_SCHEDULE) == 0:
    return "ON" # No schedule defined: Always ON
  tm_now = datetime.datetime.fromtimestamp(tm)
  schedules = config.MONITOR_SCHEDULE.get(tm_now.weekday())
  if schedules == None:
    return "OFF" # No schedule for this weekday: OFF for the whole day
  status = "OFF" 
  for item in schedules:
    start_t = datetime.time( item[0][0], item[0][1] )
    stop_t = datetime.time( item[1][0], item[1][1] )
    tm_start = datetime.datetime.combine( tm_now.date(), start_t )
    tm_stop = datetime.datetime.combine( tm_now.date(), stop_t )
    if tm_now >= tm_start and tm_now <= tm_stop:
      status = "ON"
      break
  return status

def switch_HDMI( status ):
  if status.startswith("ON"):
    logging.info( "Switching HDMI to: ON" )    
    cmd = ["vcgencmd", "display_power", "1"]
  elif status.startswith("OFF"):
    logging.info( "Switching HDMI to: OFF" )    
    cmd = ["vcgencmd", "display_power", "0"]
  subprocess.call(cmd)

#-------------------------------------------
def main():
  ret = 0
  global nexttm, date_from, date_to, iFiles, nFi, quit, show_camera, pcache, start_date
  logging.info('Starting infotainment system...')
  start_date = datetime.datetime.now()
  pcache = dircache.DirCache()
  mqttclient = mqtt_start()
  mqtt_publish_status( status="initializing" )

  date_from = None
  date_to = None  
  if config.DATE_FROM and len(config.DATE_FROM) == 3:
    date_from = config.DATE_FROM
  if config.DATE_TO and len(config.DATE_TO) == 3:
    date_to = config.DATE_TO
  if config.RECENT_DAYS > 0:
    dfrom = datetime.datetime.now() - datetime.timedelta(config.RECENT_DAYS)  
    date_from = (dfrom.year, dfrom.month, dfrom.day)

  logging.info('Initial scan of image directory...')
  iFiles, nFi = get_files(date_from, date_to)
    
  while not quit:
    mqtt_publish_status( fields="status", status="started" )
    logging.info('Starting picture frame')
    nexttm = 0.0
    start_picframe()
    if show_camera:
      mqtt_publish_status( fields="status", status="camera view started" )
      logging.info('Starting camera viewer')
      cam_show()
      show_camera = False
      quit = True # TODO just as workaround since PI3D can't be re-initialized
      ret = 10 # Tell surrounding shell script to restart
    
  mqtt_stop(mqttclient)
  if ret==10:
    mqtt_publish_status( fields="status", status="stopped - awaiting restart" )
  else:  
    mqtt_publish_status( fields="status", status="stopped" )
  logging.info('Infotainment system stopped')
  sys.exit(ret)

#############################################################################
if __name__ == "__main__":
  main()
