#!/usr/bin/python
''' Cache for picture directory tree 
'''  

import os
import sys
import datetime
import random
import logging
import pickle  
import config
  
logging.basicConfig( level=logging.INFO, format="[%(levelname)s] %(message)s" )

# global
dir_cache = {}

def update_dir_cache( dir_cache ):
  latest_change = 0.0
  if len(dir_cache) < 2: # invalid - create new one
    logging.info('Refreshing directory tree. No valid pickle file found - creating new one')
    dir_cache.clear()
    dir_cache['dir'] = {}
    dir_cache['statistics'] = {}
    dir_cache['statistics']['created'] = datetime.datetime.now()
    dir_cache['statistics']['latest_change'] = 0.0
  else:  
    logging.info('Refreshing directory tree. Last update: {}'.format(str(dir_cache['statistics']['created'])))

  picture_dir = os.path.join(config.PIC_DIR, config.SUBDIRECTORY)
  for root, subdirs, filenames in os.walk(picture_dir, topdown=True):
    subdirs[:] = [d for d in subdirs if d not in config.IGNORE_DIRS] # prune irrelevant subdirs
    mtime = os.stat(root).st_mtime 
    ctime = os.stat(root).st_ctime 
    if mtime > latest_change:
      latest_change = mtime
    if ".INFOTAINMENT_IGNORE.txt" in filenames:
      logging.info(' - {}: skipped - ".INFOTAINMENT_IGNORE.txt" found '.format(root))  
      continue
    if root in dir_cache['dir']: # directory is already known
      if dir_cache['dir'][root]['meta'][1] == mtime:     # check if directory changed since last scan
        logging.info(' - {}: unchanged'.format(root) )
        continue
      else: # dir changed
        dir_cache['dir'][root]['files'].clear()  
    else: 
      dir_cache['dir'][root] = {}
      dir_cache['dir'][root]['meta'] = [ ctime, mtime ]   
      dir_cache['dir'][root]['files'] = [] 

    logging.info(' - {}: Scanning files'.format(root) )
    for filename in filenames:
      ext = os.path.splitext(filename)[1].lower()
      if ext in config.PIC_EXT and not filename.startswith('.'):
        file_path_name = os.path.join(root, filename)
        mtime = os.path.getmtime(file_path_name)        
        orientation = 1 # this is default - unrotated
        dt = None # EXIF create date  - used for checking in tex_load
        exif_info = {}
        # append [orientation, file_changed_date, exif_date, exif_info] 
        dir_cache['dir'][root]['files'].append( [file_path_name, orientation, mtime, dt, exif_info] )

  if dir_cache['statistics']['latest_change'] < latest_change:
    logging.info('File list refreshed: {} directories'.format( len(dir_cache['dir']) ) )
    dir_cache['statistics']['latest_change'] = latest_change
    dir_cache['statistics']['created'] = datetime.datetime.now()
    updated = True
  else:
    logging.info('File list: no changes' )
    updated = False
  return (dir_cache, updated)

def save_dir_cache( dir_cache ):
  logging.info('Saving file list to pickle file')
  with open('.dir_cache.p', 'wb') as myfile:
    pickle.dump(dir_cache, myfile)

def read_dir_cache():
  logging.info('Reading file list from pickle file')
  dir_cache = {}
  try:
    with open('.dir_cache.p', 'rb') as myfile:
      dir_cache = pickle.load( myfile )
  except OSError as err:
    logging.info("Couldn't read file list from pickle file")
    pass
  return dir_cache

#--------- this is the main function
def get_file_list():
  global dir_cache
  if len(dir_cache) < 2: # cache not yet initialized
    dir_cache = read_dir_cache()
  (dir_cache, updated) = update_dir_cache(dir_cache)
  if updated:
    save_dir_cache( dir_cache )

  file_list=[]
  for path, val in dir_cache['dir'].items():
    file_list.extend( val['files'] )
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

if __name__ == '__main__':
  file_list, length = get_file_list()

