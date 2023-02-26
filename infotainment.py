#!/usr/bin/python
from __future__ import absolute_import, division, print_function, unicode_literals
''' RaspiInfotainment: Infotainment display for the Raspberry Pi. 
It combines an advanced digital picture frame, a weather forecast and a surveillance camera viewer.  
This project heavily inherited from PictureFrame2020.py, which is part of https://github.com/pi3d/pi3d_demos

(c) by Christian Rödel, https://github.com/croedel/PiInfotainment
'''
import os
import platform
import sys
import logging
import time
import datetime
import math
import subprocess
import pi3d
from pi3d.Texture import MAX_SIZE
from PIL import Image, ImageFilter # these are needed for getting exif data from images

from config import cfg
import dircache
import weatherscreen
import PVscreen
import displaymsg

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
shutdown = False
nexttm = 0.0
next_pic_num = 0
iFiles = []
nFi = 0
show_camera = False
camera_end_tm = 0.0
monitor_status = "ON"
pcache = None  
start_date = None
info_show_now = False

#####################################################
def tex_load(pic_num, iFiles, size=None):
  global pcache
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
    if cfg['DELAY_EXIF'] and type(pic_num) is int: # don't do this if passed a file name
      if dt is None: # exif info ot yet available
        (orientation, dt, exif_info) = pcache.read_exif_info(fname, im)
        iFiles[pic_num][1] = orientation
        iFiles[pic_num][3] = dt
        iFiles[pic_num][4] = exif_info
    (w, h) = im.size
    max_dimension = MAX_SIZE # TODO changing MAX_SIZE causes serious crash on linux laptop!
    if not cfg['AUTO_RESIZE']: # turned off for 4K display - will cause issues on RPi before v4
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
    if cfg['BLUR_EDGES'] and size is not None:
      wh_rat = (size[0] * im.size[1]) / (size[1] * im.size[0])
      if abs(wh_rat - 1.0) > 0.01: # make a blurred background
        (sc_b, sc_f) = (size[1] / im.size[1], size[0] / im.size[0])
        if wh_rat > 1.0:
          (sc_b, sc_f) = (sc_f, sc_b) # swap round
        (w, h) =  (round(size[0] / sc_b / cfg['BLUR_ZOOM']), round(size[1] / sc_b / cfg['BLUR_ZOOM']))
        (x, y) = (round(0.5 * (im.size[0] - w)), round(0.5 * (im.size[1] - h)))
        box = (x, y, x + w, y + h)
        blr_sz = (int(x * 512 / size[0]) for x in size)
        im_b = im.resize(size, resample=0, box=box).resize(blr_sz)
        im_b = im_b.filter(ImageFilter.GaussianBlur(cfg['BLUR_AMOUNT']))
        im_b = im_b.resize(size, resample=Image.LANCZOS)
        im_b.putalpha(round(255 * cfg['EDGE_ALPHA']))  # to apply the same EDGE_ALPHA as the no blur method.
        im = im.resize((int(x * sc_f) for x in im.size), resample=Image.LANCZOS)
        """resize can use Image.LANCZOS (alias for Image.ANTIALIAS) for resampling
        for better rendering of high-contranst diagonal lines. NB downscaled large
        images are rescaled near the start of this try block if w or h > max_dimension
        so those lines might need changing too.
        """
        im_b.paste(im, box=(round(0.5 * (im_b.size[0] - im.size[0])),
                            round(0.5 * (im_b.size[1] - im.size[1]))))
        im = im_b # have to do this as paste applies in place
    tex = pi3d.Texture(im, blend=True, m_repeat=True, automatic_resize=cfg['AUTO_RESIZE'],
                        free_after_load=True)
    #tex = pi3d.Texture(im, blend=True, m_repeat=True, automatic_resize=cfg['AUTO_RESIZE'],
    #                    mipmap=cfg['AUTO_RESIZE, free_after_load=True) # poss try this if still some artifacts with full resolution
  except Exception as e:
    logging.error('''Couldn't load file {} giving error: {}'''.format(fname, e))
    tex = None
  return tex

def get_files(dt_from=None, dt_to=None, refresh=True):
  global pcache
  mqtt_publish_status( fields=["status","pic_dir_refresh"], status="updating file_list" )
  file_list = pcache.get_file_list( dt_from, dt_to, refresh=refresh )
  mqtt_publish_status( fields="status", status="running" )
  logging.info('File list refreshed: {} images found'.format(len(file_list)) )
  return file_list, len(file_list) # tuple of file list, number of pictures


def convert_heif(fname):
  try:
    import pyheif
    from PIL import Image
    heif_file = pyheif.read(fname)
    image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw", heif_file.mode, heif_file.stride)
    return image
  except:
    logging.warning("Could't convert HEIF. Have you installed pyheif?")

def set_text_overlay(iFiles, pic_num, textlines):
  texts = displaymsg.format_text(iFiles, pic_num)
  i=0
  for item in textlines:
    item.set_text(text_format=texts[i])
    i += 1    

# start the picture frame
def start_picframe():
  global date_from, date_to, quit, paused, nexttm, next_pic_num, iFiles, nFi, monitor_status, pcache, info_show_now
  if cfg['KENBURNS']:
    kb_up = True
    cfg['FIT'] = False
    cfg['BLUR_EDGES'] = False
  if cfg['BLUR_ZOOM'] < 1.0:
    cfg['BLUR_ZOOM'] = 1.0

  sfg = None # slide for background
  sbg = None # slide for foreground
  delta_alpha = 1.0 / (cfg['FPS'] * cfg['FADE_TIME']) # delta alpha

  # Initialize pi3d system
  DISPLAY = pi3d.Display.create(x=0, y=0, frames_per_second=cfg['FPS'], display_config=pi3d.DISPLAY_CONFIG_HIDE_CURSOR, background=cfg['BACKGROUND'])
  CAMERA = pi3d.Camera(is_3d=False)

  shader = pi3d.Shader(cfg['SHADER'])
  slide = pi3d.Sprite(camera=CAMERA, w=DISPLAY.width, h=DISPLAY.height, z=5.0)
  slide.set_shader(shader)
  slide.unif[47] = cfg['EDGE_ALPHA']
  slide.unif[54] = cfg['BLEND_TYPE']

  if cfg['KEYBOARD']:
    kbd = pi3d.Keyboard()

  # PointText and TextBlock. If INFO_TXT_TIME <= 0 then this is just used for no images message
  grid_size = math.ceil(len(cfg['CODEPOINTS']) ** 0.5)
  font = pi3d.Font(cfg['FONT_FILE'], codepoints=cfg['CODEPOINTS'], grid_size=grid_size, shadow_radius=5.0, shadow=(0,0,0,128))
  text = pi3d.PointText(font, CAMERA, max_chars=1000, point_size=cfg['TEXT_POINT_SIZE'])
  textlines = []
  textlines.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 50, y=DISPLAY.height * 0.45,
                      text_format=" ", z=0.1, rot=0.0, char_count=100, size=0.8, spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0)) )
  textlines.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 50, y=DISPLAY.height * 0.45 - 40,
                      text_format=" ", z=0.1, rot=0.0, char_count=100, size=0.8, spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0)) )
  textlines.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 50, y=-DISPLAY.height * 0.4,
                      text_format=" ", z=0.1, rot=0.0, char_count=100, size=0.99, spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0)) )
  textlines.append( pi3d.TextBlock(x=-DISPLAY.width * 0.5 + 50, y=-DISPLAY.height * 0.4 - 50,
                      text_format=" ", z=0.1, rot=0.0, char_count=100, size=0.99, spacing="F", space=0.0, colour=(1.0, 1.0, 1.0, 1.0)) )
  for item in textlines:
    text.add_text_block(item)

  # prepare to display info screens (0) weather, (1) PVinfo
  info_interstitial = 'OFF'
  next_info_tm = 0.0
  info_index = 0 # defines which info screen to show (0)weather, (1)PVinfo
  # (0) weather screen
  weatherinfo = pi3d.PointText(font, CAMERA, max_chars=2000, point_size=cfg['W_POINT_SIZE'])
  weatherobj =  weatherscreen.obj_create(DISPLAY.width, DISPLAY.height)
  for _, obj in weatherobj['current'].items():
    weatherinfo.add_text_block( obj )
  for item in weatherobj['forecast']:
    for key, obj in item.items():
      if key != 'icon':
        weatherinfo.add_text_block( obj )
  weatherscreen.set_alpha(weatherobj=weatherobj, alpha=0)

  # (1) PV info screen
  PVinfo = pi3d.PointText(font, CAMERA, max_chars=2000, point_size=cfg['PV_POINT_SIZE'])
  PVobj =  PVscreen.obj_create(DISPLAY.width, DISPLAY.height)
  for key, obj in PVobj['data'].items():
    PVinfo.add_text_block( obj )
  PVscreen.set_alpha(pvobj=PVobj, alpha=0)

  next_check_tm = time.time() + cfg['CHECK_DIR_TM'] # check for new files or directory in image dir every n seconds
  next_monitor_check_tm = 0.0
  num_run_through = 0
  
  
  # here comes the main loop
  while DISPLAY.loop_running():
    tm = time.time()
    if (tm > nexttm and not paused) or (tm - nexttm) >= 86400.0: 
      if nFi > 0:
        nexttm = tm + cfg['TIME_DELAY']
        sbg = sfg
        sfg = None

        if (info_show_now or (cfg['INFO_SKIP_CNT'] > 0 and next_pic_num > 0 and (next_pic_num % cfg['INFO_SKIP_CNT'] == 0))) and info_interstitial == 'OFF':  
          # show infoscreen interstitial
          info_interstitial = 'ON'
          if info_index == 0:
            sfg = tex_load(cfg['W_BACK_IMG'], 1, (DISPLAY.width, DISPLAY.height))
          else:
            sfg = tex_load(cfg['PV_BACK_IMG'], 1, (DISPLAY.width, DISPLAY.height))
          if info_show_now:
            info_show_now = False
            for item in textlines:
              item.colouring.set_colour(alpha=0)
        else: 
          # continue with next picture
          if info_interstitial == 'ON':
            info_interstitial = 'FADE'
          
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
          if cfg['INFO_TXT_TIME'] > 0.0:
            set_text_overlay(iFiles, pic_num, textlines)
          else: # could have a NO IMAGES selected and being drawn
            for item in textlines:
              item.colouring.set_colour(alpha=0.0)
          mqtt_publish_status( status="running", pic_num=pic_num )

      if sfg is None:
        sfg = tex_load(cfg['NO_FILES_IMG'], 1, (DISPLAY.width, DISPLAY.height))
        sbg = sfg
        mqtt_publish_status( status="no pictures found" )

      a = 0.0 # alpha - proportion front image to back
      name_tm = tm + cfg['INFO_TXT_TIME']
      if sbg is None: # first time through
        sbg = sfg
      slide.set_textures([sfg, sbg])
      slide.unif[45:47] = slide.unif[42:44] # transfer front width and height factors to back
      slide.unif[51:53] = slide.unif[48:50] # transfer front width and height offsets
      wh_rat = (DISPLAY.width * sfg.iy) / (DISPLAY.height * sfg.ix)
      if (wh_rat > 1.0 and cfg['FIT']) or (wh_rat <= 1.0 and not cfg['FIT']):
        sz1, sz2, os1, os2 = 42, 43, 48, 49
      else:
        sz1, sz2, os1, os2 = 43, 42, 49, 48
        wh_rat = 1.0 / wh_rat
      slide.unif[sz1] = wh_rat
      slide.unif[sz2] = 1.0
      slide.unif[os1] = (wh_rat - 1.0) * 0.5
      slide.unif[os2] = 0.0
      if cfg['KENBURNS']:
        xstep, ystep = (slide.unif[i] * 2.0 / cfg['TIME_DELAY'] for i in (48, 49))
        slide.unif[48] = 0.0
        slide.unif[49] = 0.0
        kb_up = not kb_up

    if cfg['KENBURNS']:
      t_factor = nexttm - tm
      if kb_up:
        t_factor = cfg['TIME_DELAY'] - t_factor
      slide.unif[48] = xstep * t_factor
      slide.unif[49] = ystep * t_factor

    transition_happening = False
    if monitor_status.startswith("ON"):
      if a < 1.0: # image transition is happening
        transition_happening = True
        a += delta_alpha
        if a > 1.0:
          a = 1.0
        slide.unif[44] = a * a * (3.0 - 2.0 * a)
        if info_interstitial == 'ON': # fade in infoscreen
          if info_index == 0:
            weatherscreen.set_alpha(weatherobj=weatherobj, alpha=a)
          else:
            PVscreen.set_alpha(pvobj=PVobj, alpha=a)
        else: # fade in picture -> fade in text
          for item in textlines:
            item.colouring.set_colour(alpha=a)
          if info_interstitial == 'FADE': # fade out infoscreen
            if info_index == 0:
              weatherscreen.set_alpha(weatherobj=weatherobj, alpha=1-a)
            else:
              PVscreen.set_alpha(pvobj=PVobj, alpha=1-a)
            if a==1:
              info_interstitial = 'OFF'
              if info_index == 0 and cfg['PV_INFO_ENABLE']:
                info_index = 1 # PV info next
              elif info_index == 1:
                info_index = 0 # Weather info next

      if nFi <= 0:
        textlines[0].set_text("NO IMAGES SELECTED")
        textlines[0].colouring.set_colour(alpha=1.0)
        next_check_tm = tm + 10.0
        text.regen()
      elif tm > name_tm and tm < name_tm + 2.0 and info_interstitial != 'ON':  # fade out text
        alpha = 1- (tm - name_tm)/2.0
        for item in textlines:
          item.colouring.set_colour(alpha=alpha)
        transition_happening = True
        text.regen()
  
      slide.draw()
      text.draw()

      if info_interstitial != 'OFF':
        if info_index == 0:
          for item in weatherobj['forecast']:
            item['icon'].draw()
          for _, obj in weatherobj['static'].items():  
            obj.draw()
          weatherinfo.regen()
          weatherinfo.draw()
        else:
          for _, obj in PVobj['icon'].items():
            obj.draw()
          PVinfo.regen()
          PVinfo.draw()

    else: # monitor OFF -> minimize system activity to reduce power consumption
      time.sleep(10)

    if not transition_happening: # no transition effect safe to reshuffle etc
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
          if pcache.refresh_cache() or (cfg['SHUFFLE'] and num_run_through >= cfg['RESHUFFLE_NUM']): # refresh file list required
            if cfg['RECENT_DAYS'] > 0 and not cfg['DATE_FROM']: # reset data_from to reflect that time is proceeding
              date_from = datetime.datetime.now() - datetime.timedelta(cfg['RECENT_DAYS'])
              date_from = (date_from.year, date_from.month, date_from.day)
            iFiles, nFi = get_files(date_from, date_to)
            num_run_through = 0
            next_pic_num = 0
          next_check_tm = tm + cfg['CHECK_DIR_TM'] # next check
        if tm > next_info_tm: # refresh info screen data
          weatherscreen.refresh( weatherobj )
          PVscreen.refresh( PVobj )
          next_info_tm = tm + cfg['INFO_REFRESH_DELAY'] # next check

    if cfg['KEYBOARD']:
      k = kbd.read()
      if k != -1:
        nexttm = time.time()
      if k==27: #ESC
        break
      if k==ord(' '):
        paused = not paused
      if k==ord('b'): # go back a picture
        next_pic_num -= 2
        if next_pic_num < -1:
          next_pic_num = -1      
    if quit or show_camera: # set by MQTT
      break

  if cfg['KEYBOARD']:
    kbd.close()
  DISPLAY.destroy()

# MQTT functionality - see https://www.thedigitalpictureframe.com/
def on_mqtt_connect(mqttclient, userdata, flags, rc):
  logging.info("Connected to MQTT broker")

def on_mqtt_message(mqttclient, userdata, message):
  try:
    # TODO not ideal to have global but probably only reasonable way to do it
    global next_pic_num, iFiles, nFi, date_from, date_to, info_show_now 
    global quit, shutdown, paused, nexttm, show_camera, camera_end_tm, monitor_status
    msg = message.payload.decode("utf-8")
    reselect = False
    logging.info( 'MQTT: {} -> {}'.format(message.topic, msg))
    if message.topic.endswith("/date_from"): # NB entered as mqtt string "2016:12:25"
      try:
        msg = msg.replace(".",":").replace("/",":").replace("-",":")
        df = msg.split(":")
        date_from = tuple(int(i) for i in df)
        if len(date_from) != 3:
          raise Exception("invalid date format")
      except:
        date_from = None
      reselect = True
    elif message.topic.endswith("/date_to"):
      try:
        msg = msg.replace(".",":").replace("/",":").replace("-",":")
        df = msg.split(":")
        date_to = tuple(int(i) for i in df)
        if len(date_to) != 3:
          raise Exception("invalid date format")
      except:
        date_to = None
      reselect = True
    elif message.topic.endswith("/recent_days"):
      cfg['RECENT_DAYS'] = int(msg)  
      if cfg['RECENT_DAYS'] > 0:
        date_from = datetime.datetime.now() - datetime.timedelta(cfg['RECENT_DAYS'])  
        date_from = (date_from.year, date_from.month, date_from.day)
        date_to = None
        reselect = True
    elif message.topic.endswith("/time_delay"):
      cfg['TIME_DELAY'] = float(msg)
    elif message.topic.endswith("/quit"):
      quit = True
    elif message.topic.endswith("/shutdown"):
      quit = True
      shutdown = True
    elif message.topic.endswith("/pause"):
      paused = not paused # toggle from previous value
    elif message.topic.endswith("/back"):
      next_pic_num -= 2
      if next_pic_num < -1:
        next_pic_num = -1
      nexttm = time.time() 
    elif message.topic.endswith("/next"):
      nexttm = time.time() 
    elif message.topic.endswith("/info_skip_count"):
      cfg['INFO_SKIP_CNT'] = int(msg)
    elif message.topic.endswith("/subdirectory"):
      cfg['SUBDIRECTORY'] = msg
      date_from = date_to = None
      reselect = True
    elif message.topic.endswith("/camera"):
      show_camera = True
      camera_end_tm = time.time() + cfg['CAMERA_THRESHOLD']
      if monitor_status.startswith('OFF'): 
        monitor_status = "ON"
        switch_HDMI(monitor_status)
    elif message.topic.endswith("/info_show_now"):
      info_show_now = True
      nexttm = time.time() 
    elif message.topic.endswith("/monitor"):
      if msg == "ON":
        monitor_status = "ON-MANUAL"
        paused = False
      elif msg == "OFF":
        monitor_status = "OFF-MANUAL"
        paused = True
      else:
        monitor_status = "ON"
        paused = False
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
    client.username_pw_set(cfg['MQTT_LOGIN'], cfg['MQTT_PASSWORD']) 
    client.connect(cfg['MQTT_SERVER'], cfg['MQTT_PORT'], 60) 
    client.subscribe(cfg['MQTT_TOPIC'] + "/cmd/+", qos=0)
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    client.loop_start()
    logging.info('MQTT client started. topic={}'.format(cfg['MQTT_TOPIC']))
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
  current_pic = iFiles[pic_num][0][len(cfg['PIC_DIR'])+1:] if pic_num>=0 else "None"
  cpu_temp = subprocess.check_output( ["vcgencmd", "measure_temp"] ) if os.name == 'posix' else "-"
  fcache_t = pcache.get_cache_check_date()
  fcache_t = fcache_t.strftime("%d.%m.%Y %H:%M:%S") if fcache_t != None else "-"  
  info_data = {
    "status": status,
    "start_date": start_date.strftime("%d.%m.%Y %H:%M:%S"),
    "subdirectory": cfg['SUBDIRECTORY'],
    "date_from": dfrom,
    "date_to": dto,
    "recent_days": cfg['RECENT_DAYS'],
    "paused": str(paused), 
    "pic_num": str(pic_num+1) + " / " + str(nFi),
    "info_skip_count": cfg['INFO_SKIP_CNT'],
    "monitor_status": monitor_status,
    "status_date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
    "current_pic": current_pic,
    "cpu_temp": cpu_temp,
    "pic_dir_refresh": fcache_t 
  }
  if hasattr(os, "getloadavg"):
    info_data["load"] = str(os.getloadavg())

  messages = []
  for key, val in info_data.items():
    if len(fields)==0 or key in fields:
      topic = cfg['MQTT_TOPIC'] + "/stat/" + key
      messages.append( { "topic": topic, "payload": val } )  
  auth = { "username": cfg['MQTT_LOGIN'], "password": cfg['MQTT_PASSWORD'] }
  try:
    mqttpub.multiple( messages, client_id="infotainment-server", hostname=cfg['MQTT_SERVER'], port=cfg['MQTT_PORT'], auth=auth)
  except Exception as e:
    logging.warning("Error while sending MQTT status: {}".format(e))

#-------------------------------------------
def cam_viewer_start():
  logging.info("CamViewer started")
  vlc_instance = vlc.Instance('--no-xlib')
  player = vlc_instance.media_player_new() 
  player.set_fullscreen(True)
  media = vlc.Media(cfg['CAMERA_URL']) 
  player.set_media(media) 
  player.video_set_scale(cfg['CAMERA_ZOOM'])
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
    time.sleep(3) # wake up regularly to check if camera_end_tm changed async via MQTT   
  cam_viewer_stop(player)
  if monitor_status.startswith("OFF"):
    switch_HDMI("OFF") # switch monitor OFF again 

def check_monitor_status( tm=time.time() ):
  if len(cfg['MONITOR_SCHEDULE']) == 0:
    return "ON" # No schedule defined: Always ON
  tm_now = datetime.datetime.fromtimestamp(tm)
  schedules = cfg['MONITOR_SCHEDULE'].get(tm_now.weekday())
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
  else:
    logging.info( "Switching HDMI to: OFF" )    
    cmd = ["vcgencmd", "display_power", "0"]
  subprocess.call(cmd)

def system_shutdown():
  logging.warning( "!!! Initiating system shutdown !!!" )    
  cmd = ["shutdown", "now"]
  subprocess.call(cmd)

#-------------------------------------------
def main():
  ret = 0
  global nexttm, date_from, date_to, iFiles, nFi, quit, show_camera, pcache, start_date, shutdown
  logging.info('Starting infotainment system...')
  start_date = datetime.datetime.now()
  pcache = dircache.DirCache()
  mqttclient = mqtt_start()
  mqtt_publish_status( status="initializing" )

  date_from = None
  date_to = None  
  if cfg['DATE_FROM'] and len(cfg['DATE_FROM']) == 3:
    date_from = tuple(cfg['DATE_FROM'])
    cfg['RECENT_DAYS'] = None # hard start date overwrites RECENT_DAYS setting
  if cfg['DATE_TO'] and len(cfg['DATE_TO']) == 3:
    date_to = tuple(cfg['DATE_TO'])
  if cfg['RECENT_DAYS'] > 0:
    dfrom = datetime.datetime.now() - datetime.timedelta(cfg['RECENT_DAYS'])  
    date_from = (dfrom.year, dfrom.month, dfrom.day)

  logging.info('Initial scan of image directory...')
  iFiles, nFi = get_files(date_from, date_to, refresh=False)
    
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
  if shutdown:
    system_shutdown()
  sys.exit(ret)

#############################################################################
if __name__ == "__main__":
  main()
