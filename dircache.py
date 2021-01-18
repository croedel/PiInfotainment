#!/usr/bin/python
''' Cache for picture directory tree 
'''  

import os
import fnmatch
import datetime
import time
import random
import logging
import pickle  
import yaml
import config
  
class DirCache:
  dir_cache = {}
  fname = ""

  # ------- private core functionalities -----------------
  def __init__(self, fname=config.DIR_CACHE_FILE):
    self.fname = fname
    self._read_dir_cache()

  def _parse_yaml_file(self, filepath):
    try:
      with open(filepath, 'r', encoding='utf-8') as myfile:
        cfg = yaml.safe_load(myfile)
        return cfg
    except yaml.YAMLError as err:
      logging.error("Couldn't read .INFOTAINMENT yaml file: {} - {}".format(filepath, err) )
      return None

  def _yaml_permits(self, yaml_cfg, filename):
    permitted = True 
    if yaml_cfg:
      exclude = yaml_cfg.get("exclude")
      include = yaml_cfg.get("include")
      if exclude:
        for ex_pattern in exclude:
          if fnmatch.fnmatch( filename, ex_pattern ):
            permitted = False 
            if include:
              for in_pattern in include:
                if fnmatch.fnmatch( filename, in_pattern ):
                  permitted = True    
                  break
            break
    return permitted

  def _update_dir_cache(self):
    tm = datetime.datetime.now()
    if len(self.dir_cache) < 2: # invalid - create new one
      logging.info('Refreshing directory cache. No valid pickle file found - creating new one')
      self.dir_cache.clear()
      self.dir_cache['dir'] = {}
      self.dir_cache['statistics'] = {}
      self.dir_cache['statistics']['created'] = tm
    elif tm < self.dir_cache['statistics']['created'] + datetime.timedelta(seconds=config.CHECK_DIR_TM):  
      logging.info('Refresh of directory cache not necessary: Last update: {}'.format(str(self.dir_cache['statistics']['created'])))
      return False
    else:
      logging.info('Refreshing directory cache. Last update: {}'.format(str(self.dir_cache['statistics']['created'])))

    # mark all directories in cache
    for dir_item, val in self.dir_cache['dir'].items():
      val['meta'][3] = False    

    picture_dir = os.path.normpath( config.PIC_DIR )
    for root, subdirs, filenames in os.walk(picture_dir, topdown=True):
      subdirs[:] = [d for d in subdirs if d not in config.IGNORE_DIRS] # prune irrelevant subdirs
      mtime = os.stat(root).st_mtime 
      ctime = os.stat(root).st_ctime
      yaml_fname = os.path.join(root, ".INFOTAINMENT.yaml")
      ytime = 0.0
      if os.path.isfile( yaml_fname ):
        ytime = os.stat(yaml_fname).st_mtime           
      if root in self.dir_cache['dir']: # directory is already known
        self.dir_cache['dir'][root]['meta'][3] = True # mark directory as existing  
        if self.dir_cache['dir'][root]['meta'][1] == mtime and self.dir_cache['dir'][root]['meta'][2] == ytime: # check if directory changed since last scan
          logging.debug(' - {}: unchanged'.format(root) )
          continue
        else: # dir changed
          logging.info(' - {}: directory changed ({} - {})'.format(root, self.dir_cache['dir'][root]['meta'][1], mtime ) )  
          self.dir_cache['dir'][root]['meta'] = [ ctime, mtime, ytime, True ]   
          self.dir_cache['dir'][root]['files'].clear()
      else: 
        self.dir_cache['dir'][root] = {}
        # [file_create_date, file_changed_date, yuml_date, exif_info] 
        self.dir_cache['dir'][root]['meta'] = [ ctime, mtime, ytime, True ]   
        self.dir_cache['dir'][root]['files'] = {} 

      logging.info(' - {}: Scanning files'.format(root) )
      yaml_cfg = None
      if ytime > 0:
        yaml_cfg = self._parse_yaml_file( os.path.join(root, yaml_fname) )
      for filename in filenames:
        ext = os.path.splitext(filename)[1].lower()
        if ext in config.PIC_EXT and not filename.startswith('.') and self._yaml_permits(yaml_cfg, filename):
          file_path_name = os.path.join(root, filename)
          mtime = os.path.getmtime(file_path_name)        
          orientation = 1 # this is default - unrotated
          dt = None # EXIF create date  - used for checking in tex_load
          exif_info = {}
          # [orientation, file_changed_date, exif_date, exif_info] 
          self.dir_cache['dir'][root]['files'][filename] = [orientation, mtime, dt, exif_info] 

    # cleanup cache
    delete_list = []
    for dir_item, val in self.dir_cache['dir'].items():
      if val['meta'][3] == False: # directory not existing any more     
        delete_list.append(dir_item)    
    if len(delete_list) > 0:
      for i in delete_list:
        del self.dir_cache['dir'][i]
        logging.info('Deleting dir from cache: {}'.format(i) )

    self.dir_cache['statistics']['created'] = tm
    logging.info('Directory cache refreshed: {} directories'.format( len(self.dir_cache['dir'] )))
    return True

  def _save_dir_cache(self):
    try:
      with open(self.fname+".tmp", 'wb') as myfile:
        pickle.dump(self.dir_cache, myfile)
      os.replace(self.fname+".tmp", self.fname)  
      logging.info('Saved directory cache to pickle file {}'.format(self.fname))
    except OSError as err:
      logging.info("Couldn't write directory cache to pickle file: {}".format(str(err)))

  def _read_dir_cache(self):
    logging.info('Reading directory cache from pickle file {}'.format(self.fname))
    try:
      with open(self.fname, 'rb') as myfile:
        self.dir_cache = pickle.load( myfile )
    except OSError as err:
      logging.info("Couldn't read directory cache from pickle file: {}".format(str(err)))
      self.dir_cache = {}
  
  # ----------- public functions --------------------
  # update cache: set exif data for given file
  def set_exif_info( self, file_path_name, orientation, dt, exif_info ):
    file_path_name = os.path.normpath( file_path_name )
    path, fname = os.path.split( file_path_name )
    try:
      self.dir_cache['dir'][path]['files'][fname][0] = orientation
      self.dir_cache['dir'][path]['files'][fname][2] = dt
      self.dir_cache['dir'][path]['files'][fname][3] = exif_info
    except Exception as err:
      logging.error("Couldn't update EXIF info for: {} - {}".format(file_path_name, str(err)))

  def get_exif_info(self, file_path_name):
    exif_data = {}
    file_path_name = os.path.normpath( file_path_name )
    if not file_path_name.startswith(config.PIC_DIR):
      file_path_name = os.path.join(config.PIC_DIR, file_path_name)
    path, fname = os.path.split( file_path_name )
    exif_data['path'] = path
    exif_data['file'] = fname
    try:
      exif_data['orientation'] = self.dir_cache['dir'][path]['files'][fname][0]
      exif_data['dt'] = self.dir_cache['dir'][path]['files'][fname][2]
      exif_data['exif_info'] = self.dir_cache['dir'][path]['files'][fname][3]
    except Exception as err:
      logging.warning("Couldn't get EXIF info for: {} - {}".format(file_path_name, str(err)))
    return exif_data  

  # refreshes the cache, if needed
  def refresh_cache(self):
    updated = self._update_dir_cache()
    if updated:
      self._save_dir_cache()
    return updated

  # create a filtered file list
  def get_file_list( self, dt_from=None, dt_to=None, refresh=True ):
    if refresh:  
      self.refresh_cache()
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
          propability = 1 - (distance * 1/config.PROP_SLOPE)   
          propability = max( config.OUTDATED_FILE_PROP, propability ) # set minimum to config value 
          if random.random() <= propability:
            fpath = os.path.join(path, item)
            # [file_path, orientation, file_changed_date, exif_date, exif_info]
            file_list.append( [ fpath, attr[0], attr[1], attr[2], attr[3] ] ) 

    if config.SHUFFLE:
      if config.RECENT_N == 0:
        random.shuffle(file_list)
      else:
        file_list.sort(key=lambda x: x[2]) # will be later files last
        temp_list_first = file_list[-config.RECENT_N:]
        temp_list_last = file_list[:-config.RECENT_N]
        random.shuffle(temp_list_first)
        random.shuffle(temp_list_last)
        file_list = temp_list_first + temp_list_last
    else:
      file_list.sort() # if not config.SHUFFLEd; sort by name
        
    logging.info("New file list created: {} images".format(len(file_list)))
    return file_list

  # ------- maintenance functionalities -----------------
  def get_cache_refresh_date(self):
    date=None
    if len(self.dir_cache) > 0:
      date = self.dir_cache['statistics']['created']
    return date  

  def get_dircount(self):
    count=0
    if len(self.dir_cache) > 0:
      count = len(self.dir_cache['dir'])
    return count

  def get_dirlist(self):
    dirlist = []
    if len(self.dir_cache) > 0:
      for path, val in self.dir_cache['dir'].items():
        dirlist.append( [path, len(val['files'])] ) 
    return dirlist

  def get_dirlist_full(self):
    dirlist = []
    if len(self.dir_cache) > 0:
      for path, val in self.dir_cache['dir'].items():
        ctime = self.dir_cache['dir'][path]['meta'][0]
        mtime = self.dir_cache['dir'][path]['meta'][1]
        ytime = self.dir_cache['dir'][path]['meta'][2]
        # Directory: ["d", dir_name, ctime, mtime, ytime]
        dirlist.append( ["d", path, ctime, mtime, ytime ] ) 
        for item, attr in val['files'].items():
          # File: ["f", filename, orientation, file_changed_date, exif_date, exif_info]
          dirlist.append( ["f", item, attr[0], attr[1], attr[2], attr[3] ] ) 
    return dirlist

  def get_filecount(self):
    count=0
    if len(self.dir_cache) > 0:
      for path, val in self.dir_cache['dir'].items():
        count += len(val['files'])
    return count

  def get_exifcount(self):
    count=0
    if len(self.dir_cache) > 0:
      for path, val in self.dir_cache['dir'].items():
        for item, attr in val['files'].items():
          if attr[2] != None:
            count += 1 
    return count

  def clear_exif(self):
    count=0
    if len(self.dir_cache) > 0:
      for path, val in self.dir_cache['dir'].items():
        for item, attr in val['files'].items():
          if attr[2] != None:
            attr[2] = None
            attr[3] = {}
            count += 1 
    return count

#-----------------------------------------
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

