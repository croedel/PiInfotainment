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
  
class DirCache:
  dir_cache = {}

  def __init__(self):
    self._read_dir_cache()

  def _update_dir_cache(self):
    tm = datetime.datetime.now()
    if len(self.dir_cache) < 2: # invalid - create new one
      logging.info('Refreshing directory cache. No valid pickle file found - creating new one')
      self.dir_cache.clear()
      self.dir_cache['dir'] = {}
      self.dir_cache['statistics'] = {}
      self.dir_cache['statistics']['created'] = tm
    elif tm < self.dir_cache['statistics']['last_check'] + datetime.timedelta(seconds=config.CHECK_DIR_TM):  
      logging.info('Refresh of directory cache not necessary: Last update: {}'.format(str(self.dir_cache['statistics']['created'])))
      return False
    else:
      logging.info('Refreshing directory cache. Last update: {}'.format(str(self.dir_cache['statistics']['created'])))

    # mark all directories in cache
    for dir_item, val in self.dir_cache['dir'].items():
      val['meta'][2] = False    

    updated = False
    picture_dir = os.path.normpath( config.PIC_DIR )
    for root, subdirs, filenames in os.walk(picture_dir, topdown=True):
      subdirs[:] = [d for d in subdirs if d not in config.IGNORE_DIRS] # prune irrelevant subdirs
      mtime = os.stat(root).st_mtime 
      ctime = os.stat(root).st_ctime
      if ".INFOTAINMENT_IGNORE.txt" in filenames:
        logging.info(' - {}: skipped - ".INFOTAINMENT_IGNORE.txt" found '.format(root))  
        continue
      if root in self.dir_cache['dir']: # directory is already known
        self.dir_cache['dir'][root]['meta'][2] = True # mark directory as existing  
        if self.dir_cache['dir'][root]['meta'][1] == mtime:     # check if directory changed since last scan
          logging.info(' - {}: unchanged'.format(root) )
          continue
        else: # dir changed
          logging.info(' - {}: directory changed ({} - {})'.format(root, self.dir_cache['dir'][root]['meta'][1], mtime ) )  
          self.dir_cache['dir'][root]['meta'] = [ ctime, mtime, True ]   
          self.dir_cache['dir'][root]['files'].clear()
      else: 
        self.dir_cache['dir'][root] = {}
        self.dir_cache['dir'][root]['meta'] = [ ctime, mtime, True ]   
        self.dir_cache['dir'][root]['files'] = {} 

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
          self.dir_cache['dir'][root]['files'][filename] = [orientation, mtime, dt, exif_info] 

    for dir_item, val in self.dir_cache['dir'].items():
      if val['meta'][2] == False and len(val['files']) > 0: # directory was deleted     
        val['files'].clear()
        updated = True

    if updated:
      logging.info('Directory cache refreshed: {} directories'.format( len(self.dir_cache['dir'] )))
      self.dir_cache['statistics']['created'] = tm
      updated = True
    else:
      logging.info('Directory cache: no changes' )
      updated = False
    self.dir_cache['statistics']['last_check'] = tm 
    return updated

  def _save_dir_cache(self):
    logging.info('Saving directory cache to pickle file')
    with open('.dir_cache.p', 'wb') as myfile:
      pickle.dump(self.dir_cache, myfile)

  def _read_dir_cache(self):
    logging.info('Reading directory cache from pickle file')
    try:
      with open('.dir_cache.p', 'rb') as myfile:
        self.dir_cache = pickle.load( myfile )
        self.dir_cache['statistics']['last_check'] = self.dir_cache['statistics']['created']
    except OSError as err:
      logging.info("Couldn't directory cache from pickle file")
      self.dir_cache = {}
      pass

  # update cache: set exif data for given file
  def set_exif_info( self, file_path_name, orientation, dt, exif_info ):
    file_path_name = os.path.normpath( file_path_name )
    path, fname = os.path.split( file_path_name )
    try:
      self.dir_cache['dir'][path]['files'][fname][0] = orientation
      self.dir_cache['dir'][path]['files'][fname][2] = dt
      self.dir_cache['dir'][path]['files'][fname][3] = exif_info
      logging.info("EXIF info set for: {} - {}, {}, {}".format(file_path_name, orientation, dt, str(exif_info) ))
    except Exception as err:
      logging.error("Couldn't update EXIF info for: {} - {}".format(file_path_name, str(err)))

  # refreshes the cache, if needed
  def refresh_cache(self):
    updated = self._update_dir_cache()
    if updated:
      self._save_dir_cache()
    return updated

  # create a filtered file list
  def get_file_list( self, dt_from=None, dt_to=None ):
    updated = self.refresh_cache()
    # dt_from and dt_to are either None or tuples (2016,12,25)
    if isinstance(dt_from, tuple):  
      dt_from = time.mktime(dt_from + (0, 0, 0, 0, 0, 0))
    if isinstance(dt_to, tuple):  
      dt_to = time.mktime(dt_to + (0, 0, 0, 0, 0, 0))
    path_restrict = False  
    if config.SUBDIRECTORY and config.SUBDIRECTORY != "": 
      path_restrict = os.path.normpath( os.path.join( config.PIC_DIR, config.SUBDIRECTORY ) )
 
    # create file_list
    file_list=[]
    for path, val in self.dir_cache['dir'].items():
      if not path_restrict or path.startswith( path_restrict ): # if either no restriction or path matches restriction 
        for item, attr in val['files'].items():
          ftime = attr[2] if attr[2] != None else attr[1] # preferably use EXIF date, fallback is mdate 
          distance_from = max(0, dt_from-ftime) if dt_from is not None else 0
          distance_to = max(0, ftime-dt_to) if dt_to is not None else 0
          distance = max(distance_from, distance_to) / (3600*24) # days 
          propability = 1 - (distance * 1/config.RECENT_DAYS)   
          propability = max( config.OUTDATED_FILE_PROP, propability ) # set minimum to config value 
          if random.random() <= propability:
            fpath = os.path.join(path, item)
            file_list.append( [ fpath, attr[0], attr[1], attr[2], attr[3] ] ) 
    return file_list

if __name__ == '__main__':
  # some test / demo code
  pcache = DirCache()  
  file_list = pcache.get_file_list()
  logging.info("File list: {} items".format(len(file_list)))

  dfrom = datetime.datetime.now() - datetime.timedelta(30)
  date_from = (dfrom.year, dfrom.month, dfrom.day) 
  file_list = pcache.get_file_list(dt_from=date_from)
  logging.info("File list: {} items".format(len(file_list)))

  pcache.set_exif_info( "//SYNOLOGYDS216/photo/2020\\DCR_9547.JPG", 1, 1583668078.1234, {} )     
  pcache.set_exif_info( "//SYNOLOGYDS216/photo/not_existing.jpg", 1, 1583668078.1234, {} )     

