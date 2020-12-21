#!/usr/bin/python
from __future__ import absolute_import, division, print_function, unicode_literals
''' RaspiInfotainment: Infotainment display for the Raspberry Pi. 
It combines an advanced digital picture frame, a weather forecast and a surveillance camera viewer.  
'''
import os
import logging
import time
import datetime
import random
import math
import pi3d

from pi3d.Texture import MAX_SIZE
from PIL import Image, ImageFilter # these are needed for getting exif data from images
import config
import weather
import GPSlookup

logging.basicConfig( level=logging.INFO, format="[%(levelname)s] %(message)s" )

if config.USE_MQTT:
  try:
    import paho.mqtt.client as mqtt
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

#####################################################
def tex_load(pic_num, iFiles, size=None):
  if type(pic_num) is int:
    fname = iFiles[pic_num][0]
    orientation = iFiles[pic_num][1]
  else: # allow file name to be passed to this function ie for missing file image
    fname = pic_num
    orientation = 1
  try:
    ext = os.path.splitext(fname)[1].lower()
    dt = None
    if ext in ('.heif','.heic'):
      im = convert_heif(fname)
    else:
      im = Image.open(fname)
    if config.DELAY_EXIF and type(pic_num) is int: # don't do this if passed a file name
      if iFiles[pic_num][3] is None: # dt set to None before exif read
        (orientation, dt, exif_info) = get_exif_info(fname, im)
        iFiles[pic_num][1] = orientation
        iFiles[pic_num][3] = dt
        iFiles[pic_num][4] = exif_info
    (w, h) = im.size
    max_dimension = MAX_SIZE # TODO changing MAX_SIZE causes serious crash on linux laptop!
    if not config.AUTO_RESIZE: # turned off for 4K display - will cause issues on RPi before v4
        max_dimension = 3840 # TODO check if mipmapping should be turned off with this setting.
    if w > max_dimension:
        im = im.resize((max_dimension, int(h * max_dimension / w)), resample=Image.BICUBIC)
    elif h > max_dimension:
        im = im.resize((int(w * max_dimension / h), max_dimension), resample=Image.BICUBIC)
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
        im_b = im_b.resize(size, resample=Image.BICUBIC)
        im_b.putalpha(round(255 * config.EDGE_ALPHA))  # to apply the same EDGE_ALPHA as the no blur method.
        im = im.resize((int(x * sc_f) for x in im.size), resample=Image.BICUBIC)
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

def item2str(item):
  if item == None:
    val = '-' 
  elif isinstance(item, tuple):
    val = int(item[0]) / int(item[1])
    if val > 1:
      if val == int(val):
        val = str(int(val)) # display as integer 
      else:
        val = str(val)  # display as decimal number
    else:
      val = '1/' + str(int(item[1] / item[0])) # display as fracture    
  else:
    val = str(item)  
  return val      

def clean_string(fmt_str):
  fmt_str = ''.join([c for c in fmt_str if c in config.CODEPOINTS]) # clean string 
  fmt_str = fmt_str[:99]  # limit length to 99 characters
  return fmt_str

def format_text(iFiles, pic_num):
  try:
    filename = os.path.basename(iFiles[pic_num][0])
    pathname = os.path.dirname(os.path.relpath(iFiles[pic_num][0], config.PIC_DIR))
    dt = datetime.datetime.fromtimestamp(iFiles[pic_num][3])
    exif_info = iFiles[pic_num][4] 
    if config.RESOLVE_GPS: # GPS reverse lookup is quite expensive - so we check if it is required, before executing
      gps_str = GPSlookup.lookup( exif_info.get('GPSInfo') )
    else:
      gps_str = '' 

    rep = { 
      '<file>':   filename[:40],    # filename of image
      '<path>':   pathname[:40],    # pathname of image
      '<date>':   dt.strftime("%d.%m.%Y"),  # image creation date (dd.mm.yyyy)
      '<num>':    str(pic_num+1),        # number of current picuture in current file list
      '<total>':  str(len(iFiles)),      # total number of picutures in current file list  
      '<rating>': '*' * int(exif_info.get('Rating', 0)),
      '<make>':   exif_info.get('Make', ''),
      '<model>':  exif_info.get('Model', ''),
      '<artist>': exif_info.get('Artist', ''),
      '<copy>':   exif_info.get('Copyright', ''),
      '<desc>':   exif_info.get('ImageDescription', ''),
      '<exp>':    item2str(exif_info.get('ExposureTime')) + 's',
      '<fnum>':   'f/' + item2str(exif_info.get('FNumber')),
      '<iso>':    'ISO ' + item2str(exif_info.get('ISOSpeedRatings')),
      '<flen>':   item2str(exif_info.get('FocalLength')) + 'mm',
      '<flen35>': item2str(exif_info.get('FocalLengthIn35mmFilm')) + 'mm',
      '<res>':    item2str(exif_info.get('ExifImageWidth')) + 'x' + item2str(exif_info.get('ExifImageHeight')),
      '<gps>':    gps_str 
    }

    txt1 = config.TEXT1_FORMAT
    txt2 = config.TEXT2_FORMAT
    txt3 = config.TEXT3_FORMAT
    txt4 = config.TEXT4_FORMAT

    for i, j in rep.items():
      txt1 = txt1.replace(i, j)
      txt2 = txt2.replace(i, j)
      txt3 = txt3.replace(i, j)
      txt4 = txt4.replace(i, j)

    txt1 = clean_string(txt1)
    txt2 = clean_string(txt2)
    txt3 = clean_string(txt3)
    txt4 = clean_string(txt4)
  except Exception as e: # something went wrong when formatting
    txt1 = txt2 = txt3 = txt4 = ' '
    logging.warning('Exception in format_text: ', e)
  return (txt1, txt2, txt3, txt4)

def check_picdir_changed():
  last_change = 0.0
  for root, subdirs, filenames in os.walk(config.PIC_DIR, topdown=True):
    subdirs[:] = [d for d in subdirs if d not in config.IGNORE_DIRS] # prune irrelevant subdirs
    mod_tm = os.stat(root).st_mtime
    if mod_tm > last_change:
      last_change = mod_tm
  return last_change

def get_files(dt_from=None, dt_to=None):
  logging.info('Refreshing file list')
  # dt_from and dt_to are either None or tuples (2016,12,25)
  if dt_from is None:
    dt_from = 0.0
  else:  
    dt_from = time.mktime(dt_from + (0, 0, 0, 0, 0, 0))
  if dt_to is None:
    dt_to = float(pow(2,32))
  else:  
    dt_to = time.mktime(dt_to + (0, 0, 0, 0, 0, 0))

  file_list = []
  extensions = ['.png','.jpg','.jpeg','.heif','.heic'] # can add to these
  picture_dir = os.path.join(config.PIC_DIR, config.SUBDIRECTORY)
  for root, subdirs, filenames in os.walk(picture_dir, topdown=True):
    subdirs[:] = [d for d in subdirs if d not in config.IGNORE_DIRS] # prune irrelevant subdirs
    mod_tm = os.stat(root).st_mtime # directory modification time
    create_tm = os.stat(root).st_ctime # directory creation time
    if (mod_tm < dt_from or create_tm > dt_to) and random.randint(1,config.OUTDATED_DIR_PROP) != 1:
      logging.info(' - {}: Ignored - Time restriction'.format(root))  
      continue
    if ".INFOTAINMENT_IGNORE.txt" in filenames:
      logging.info(' - {}: Ignored - ".INFOTAINMENT_IGNORE.txt" found '.format(root))  
      continue
    logging.info(' - {}: Reading files'.format(root) )  
    for filename in filenames:
      ext = os.path.splitext(filename)[1].lower()
      if ext in extensions and not filename.startswith('.'):
        file_path_name = os.path.join(root, filename)
        include_flag = True
        orientation = 1 # this is default - unrotated
        dt = None # if exif data not read - used for checking in tex_load
        exif_info = {}
        mtime = os.path.getmtime(file_path_name)
        if config.DELAY_EXIF:
          if dt_from is not None and mtime < dt_from and random.randint(1,config.OUTDATED_FILE_PROP) != 1:
            include_flag = False # file is older then dt_from --> ignore
        else:    
          (orientation, dt, exif_info) = get_exif_info(file_path_name)
          if (dt_from is not None and dt < dt_from) or (dt_to is not None and dt > dt_to):
            include_flag = False
        if include_flag:
          # append [file_name, orientation, file_changed_date, exif_date, exif_info] 
          file_list.append([file_path_name, orientation, mtime, dt, exif_info])
  if config.SHUFFLE:
    file_list.sort(key=lambda x: x[2]) # will be later files last
    temp_list_first = file_list[-config.RECENT_N:]
    temp_list_last = file_list[:-config.RECENT_N]
    random.shuffle(temp_list_first)
    random.shuffle(temp_list_last)
    file_list = temp_list_first + temp_list_last
  else:
    file_list.sort() # if not config.SHUFFLEd; sort by name
  logging.info('File list refreshed: {} images found'.format(len(file_list)) )
  return file_list, len(file_list) # tuple of file list, number of pictures

def get_exif_info(file_path_name, im=None):
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
  global date_from, date_to, quit, paused, nexttm, next_pic_num, iFiles, nFi
 
  if config.KENBURNS:
    kb_up = True
    config.FIT = False
    config.BLUR_EDGES = False
  if config.BLUR_ZOOM < 1.0:
    config.BLUR_ZOOM = 1.0

  last_file_change = check_picdir_changed()
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

  # PointText and TextBlock. If SHOW_NAMES_TM <= 0 then this is just used for no images message
  grid_size = math.ceil(len(config.CODEPOINTS) ** 0.5)
  font = pi3d.Font(config.FONT_FILE, codepoints=config.CODEPOINTS, grid_size=grid_size, shadow_radius=4.0,
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
    weathericons.append( pi3d.ImageSprite('weather_icons/01d.png', icon_shader, w=200, h=200, 
                            x=-DISPLAY.width * 0.5 + 100, y=DISPLAY.height *0.45-70 - i*(2*w_point_size + w_padding) - 20, z=1.0) )

  for item in weathertexts:
    weatherinfo.add_text_block( item )
  
  weather_interstitial_active = True
  next_weather_tm = 0.0
  num_run_through = 0

  # here comes the main loop
  while DISPLAY.loop_running():
    tm = time.time()
    if (tm > nexttm and not paused) or (tm - nexttm) >= 86400.0: # this must run first iteration of loop
      if nFi > 0:
        nexttm = tm + config.TIME_DELAY
        sbg = sfg
        sfg = None

        if (config.W_SKIP_CNT > 0) and (next_pic_num % config.W_SKIP_CNT == 1) and not weather_interstitial_active: 
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
              if config.SHUFFLE and num_run_through >= config.RESHUFFLE_NUM:
                num_run_through = 0
                last_file_change = 0.0
#                random.shuffle(iFiles)
              next_pic_num = 0
            if next_pic_num == start_pic_num:
              nFi = 0
              break
          # set description
          if config.SHOW_NAMES_TM > 0.0:
            texts = format_text(iFiles, pic_num)
            i=0
            for item in textlines:
              item.set_text(text_format=texts[i])
              i += 1    
          else: # could have a NO IMAGES selected and being drawn
            for item in textlines:
              item.colouring.set_colour(alpha=0.0)

      if sfg is None:
        sfg = tex_load(config.NO_FILES_IMG, 1, (DISPLAY.width, DISPLAY.height))
        sbg = sfg

      a = 0.0 # alpha - proportion front image to back
      name_tm = time.time() + config.SHOW_NAMES_TM
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
      if tm > next_check_tm:
        mtime = check_picdir_changed()
        if mtime > last_file_change:
          if config.RECENT_DAYS > 0: # reset data_from to reflect time is proceeding
            date_from = datetime.datetime.now() - datetime.timedelta(config.RECENT_DAYS)
            date_from = (date_from.year, date_from.month, date_from.day)
          iFiles, nFi = get_files(date_from, date_to)
          num_run_through = 0
          next_pic_num = 0
          last_file_change = mtime
        next_check_tm = tm + config.CHECK_DIR_TM # create new file list at this time
      if tm > next_weather_tm and not paused: # refresh weather info
        weather_info = weather.get_weather_info( config.W_LATITUDE, config.W_LONGITUDE, config.W_UNIT, config.W_LANGUAGE, config.W_API_KEY )
        for i in range( min(len(weather_info), w_item_cnt) ):
          weathertexts[i*2].set_text(text_format=weather_info[i]['title'])
          weathertexts[i*2+1].set_text(text_format=weather_info[i]['txt'])   
          w_tex = pi3d.Texture('weather_icons/' + weather_info[i]['icon'], blend=True, automatic_resize=True, free_after_load=True)
          weathericons[i].set_textures( [w_tex] )
        next_weather_tm = tm + config.W_REFRESH_DELAY

    slide.draw()

    if nFi <= 0:
      textlines[0].set_text("NO IMAGES SELECTED")
      textlines[0].colouring.set_colour(alpha=1.0)
      next_check_tm = tm + 5.0
    elif tm < name_tm and weather_interstitial_active == False:
      # this sets alpha for the TextBlock from 0 to 1 then back to 0
      dt = (config.SHOW_NAMES_TM - name_tm + tm + 0.1) / config.SHOW_NAMES_TM
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
    global quit, paused, nexttm, show_camera, camera_end_tm
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
        date_from = None
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
    elif message.topic == "screen/shuffle":
      config.SHUFFLE = True if msg == "True" else False
      reselect = True
    elif message.topic == "screen/quit":
      quit = True
    elif message.topic == "screen/pause":
      paused = not paused # toggle from previous value
    elif message.topic == "screen/back":
      next_pic_num -= 2
      if next_pic_num < -1:
        next_pic_num = -1
      nexttm = time.time() - 86400.0
    elif message.topic == "screen/subdirectory":
      config.SUBDIRECTORY = msg
      reselect = True
    elif message.topic == "screen/camera":
      show_camera = True
      camera_end_tm = time.time() + config.CAMERA_THRESHOLD
    else:
      logging.info('Unknown MQTT topic: {}'.format(message.topic))

    if reselect:
      iFiles, nFi = get_files(date_from, date_to)
      next_pic_num = 0
  except Exception as e:
    logging.warning("Error while handling MQTT message: {}".format(e))

#-------------------------------------------
def mqtt_start(): 
  try: 
    client = mqtt.Client()
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

def cam_start():
  global camera_end_tm
  player = cam_viewer_start()
  while camera_end_tm > time.time():
    time.sleep(5) # wake up regularly to check if camera_end_tm changed async via MQTT   
  cam_viewer_stop(player)

#-------------------------------------------
def main():
  global nexttm, date_from, date_to, iFiles, nFi, quit, show_camera
  logging.info('Starting infotainment system...')
  if config.USE_MQTT:
    mqttclient = mqtt_start()
  if config.RECENT_DAYS > 0:
    dfrom = datetime.datetime.now() - datetime.timedelta(config.RECENT_DAYS)  
    date_from = (dfrom.year, dfrom.month, dfrom.day)
 
  logging.info('Initial scan of image directory...')
  iFiles, nFi = get_files(date_from, date_to)
    
  while not quit:
    logging.info('Starting picture frame')
    nexttm = 0.0
    start_picframe()
    if show_camera:
      logging.info('Starting camera viewer')
      cam_start()
      show_camera = False
      quit = True # TODO just as workaround!
    
  if config.USE_MQTT:
    mqtt_stop(mqttclient)
  logging.info('Infotainment system stopped')

#############################################################################
if __name__ == "__main__":
  main()
