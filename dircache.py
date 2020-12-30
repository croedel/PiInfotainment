#!/usr/bin/python
''' Cache for picture directory tree 
'''  

import os
import datetime
import time
import random
import logging
import pickle  
import config
  
logging.basicConfig( level=logging.INFO, format="[%(levelname)s] %(message)s" )

# global
dir_cache = {}

#----------- internal helper functions -----------
def update_dir_cache( dir_cache ):
  tm = datetime.datetime.now()
  if len(dir_cache) < 2: # invalid - create new one
    logging.info('Refreshing directory cache. No valid pickle file found - creating new one')
    dir_cache.clear()
    dir_cache['dir'] = {}
    dir_cache['statistics'] = {}
    dir_cache['statistics']['created'] = tm
  elif tm < dir_cache['statistics']['last_check'] + datetime.timedelta(seconds=config.CHECK_DIR_TM):  
    logging.info('Refresh of directory cache not necessary: Last update: {}'.format(str(dir_cache['statistics']['created'])))
    return (dir_cache, False)
  else:
    logging.info('Refreshing directory cache. Last update: {}'.format(str(dir_cache['statistics']['created'])))

  # mark all directories in cache
  for dir_item, val in dir_cache['dir'].items():
    val['meta'][2] = False    

  updated = False
  picture_dir = os.path.normpath( os.path.join(config.PIC_DIR, config.SUBDIRECTORY) )
  for root, subdirs, filenames in os.walk(picture_dir, topdown=True):
    subdirs[:] = [d for d in subdirs if d not in config.IGNORE_DIRS] # prune irrelevant subdirs
    mtime = os.stat(root).st_mtime 
    ctime = os.stat(root).st_ctime
    if ".INFOTAINMENT_IGNORE.txt" in filenames:
      logging.info(' - {}: skipped - ".INFOTAINMENT_IGNORE.txt" found '.format(root))  
      continue
    if root in dir_cache['dir']: # directory is already known
      dir_cache['dir'][root]['meta'][2] = True # mark directory as existing  
      if dir_cache['dir'][root]['meta'][1] == mtime:     # check if directory changed since last scan
        logging.info(' - {}: unchanged'.format(root) )
        continue
      else: # dir changed
        dir_cache['dir'][root]['files'].clear()  
    else: 
      dir_cache['dir'][root] = {}
      dir_cache['dir'][root]['meta'] = [ ctime, mtime, True ]   
      dir_cache['dir'][root]['files'] = {} 

    logging.info(' - {}: Scanning files'.format(root) )
    updated = True
    for filename in filenames:
      ext = os.path.splitext(filename)[1].lower()
      if ext in config.PIC_EXT and not filename.startswith('.'):
        file_path_name = os.path.join(root, filename)
        mtime = os.path.getmtime(file_path_name)        
        orientation = 1 # this is default - unrotated
        dt = None # EXIF create date  - used for checking in tex_load
        exif_info = {}
        # [orientation, file_changed_date, exif_date, exif_info] 
        dir_cache['dir'][root]['files'][filename] = [orientation, mtime, dt, exif_info] 

  for dir_item, val in dir_cache['dir'].items():
    if val['meta'][2] == False and len(val['files']) > 0: # directory was deleted     
      val['files'].clear()
      updated = True

  if updated:
    logging.info('Directory cache refreshed: {} directories'.format( len(dir_cache['dir'] )))
    dir_cache['statistics']['created'] = tm
    updated = True
  else:
    logging.info('Directory cache: no changes' )
    updated = False
  dir_cache['statistics']['last_check'] = tm 
  return dir_cache, updated


def save_dir_cache( dir_cache ):
  logging.info('Saving directory cache to pickle file')
  with open('.dir_cache.p', 'wb') as myfile:
    pickle.dump(dir_cache, myfile)

def read_dir_cache():
  logging.info('Reading directory cache from pickle file')
  dir_cache = {}
  try:
    with open('.dir_cache.p', 'rb') as myfile:
      dir_cache = pickle.load( myfile )
      dir_cache['statistics']['last_check'] = dir_cache['statistics']['created']
  except OSError as err:
    logging.info("Couldn't directory cache from pickle file")
    pass
  return dir_cache

#----------- following functions can be used externally -----------

# update cache: set exif data for given file
def set_exif_info( file_path_name, orientation, dt, exif_info ):
  global dir_cache
  file_path_name = os.path.normpath( file_path_name )
  path, fname = os.path.split( file_path_name )
  try:
    dir_cache['dir'][path]['files'][fname][0] = orientation
    dir_cache['dir'][path]['files'][fname][2] = dt
    dir_cache['dir'][path]['files'][fname][3] = exif_info
  except Exception as err:
    logging.warning("Couldn't update EXIF info for: {}".format(file_path_name))

# refreshes the cache, if needed
def refresh_cache():
  global dir_cache
  if len(dir_cache) < 2: # cache not yet initialized
    dir_cache = read_dir_cache()
  (dir_cache, updated) = update_dir_cache(dir_cache)
  if updated:
    save_dir_cache( dir_cache )
  return updated

# create a filtered file list
def get_file_list( dt_from=None, dt_to=None ):
  updated = refresh_cache()
  # dt_from and dt_to are either None or tuples (2016,12,25)
  dt_from = 0.0 if dt_from is None else time.mktime(dt_from + (0, 0, 0, 0, 0, 0))
  dt_to = float(pow(2,32)) if dt_to is None else time.mktime(dt_to + (0, 0, 0, 0, 0, 0))
  global dir_cache
  # create file_list
  file_list=[]
  for path, val in dir_cache['dir'].items():
    for item, attr in val['files'].items():
      add_to_filelist = False 
      ftime = attr[2] if attr[2] != None else attr[1] # preferably use EXIF date, fallback is mdate 
      if ftime > dt_from and ftime < dt_to:
        add_to_filelist = True 
      if random.randint(0,config.OUTDATED_FILE_PROP) == 1:
        add_to_filelist = True   
      if add_to_filelist:
        fpath = os.path.join(path, item)
        file_list.append( [ fpath, attr[0], attr[1], attr[2], attr[3] ] ) 
  return file_list

if __name__ == '__main__':
  file_list = get_file_list()
  logging.info("File list: {} items".format(len(file_list)))
  file_list = get_file_list()
  logging.info("File list: {} items".format(len(file_list)))

  set_exif_info( "//SYNOLOGYDS216/photo/2020\\DCR_9547.JPG", 1, 1583668078.1234, {} )     
  set_exif_info( "//SYNOLOGYDS216/photo/not_existing.jpg", 1, 1583668078.1234, {} )     

