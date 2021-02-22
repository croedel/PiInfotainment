#!/usr/bin/python
''' Cache for picture directory tree 
'''  
import argparse
import datetime
import logging
import os
import dircache
import GPSlookup
import displaymsg
from config import cfg

#-----------------------------
def do_summary(cache, args): 
  filecount = cache.get_filecount()
  exifcount = cache.get_exifcount() 
  exifrate = exifcount / filecount * 100 if filecount>0 else 0 
  print( "Cache file:       {:s}".format( args.file ))
  print( "Image path:       {:s}".format( str(cache.get_cache_path())) )
  print( "Created:          {:s}".format( str(cache.get_cache_create_date())) )
  print( "Last check:       {:s}".format( str(cache.get_cache_check_date())) )
  print( "#Directories:     {:d}".format( cache.get_dircount()) )
  print( "#Files:           {:d}".format( filecount ) )
  print( "#Files with EXIF: {:d} ({:.1f}%)".format( exifcount, exifrate)  )

def do_list(cache, args): 
  do_summary(cache, args)
  dirlist = cache.get_dirlist()
  for dir_item in dirlist:
    print( "{:s}: {:d} files".format(dir_item[0], dir_item[1]) )

def do_list_long(cache, args):
  path_trunc = len(cfg['PIC_DIR']) + 1
  do_summary(cache, args)
  dirlist = cache.get_dirlist_full()
  for dir_item in dirlist:
    if dir_item[0] == "d": # directory
      path = dir_item[1][path_trunc:]    
      ctime = datetime.datetime.fromtimestamp(dir_item[2]).strftime("%y/%m/%d-%H:%M")
      mtime = "-"  
      ytime = "-"  
      if dir_item[3]:
        mtime = datetime.datetime.fromtimestamp(dir_item[3]).strftime("%y/%m/%d-%H:%M")
      if dir_item[4]:
        ytime = datetime.datetime.fromtimestamp(dir_item[4]).strftime("%y/%m/%d-%H:%M")
      print( "-"*60 )
      print( "D c:{:14s} m:{:14s} y:{:14s} {:s}".format(ctime, mtime, ytime, path) )
    else:
      ftime = "-"
      exif_time = "-"
      if dir_item[3]:
        ftime = datetime.datetime.fromtimestamp(dir_item[3]).strftime("%y/%m/%d-%H:%M")
      if dir_item[4]:
        exif_time = datetime.datetime.fromtimestamp(dir_item[4]).strftime("%y/%m/%d-%H:%M")
      print( "  f:{:14s} x:{:14s} {:s}".format(ftime, exif_time, dir_item[1]) )

def do_refresh(cache, args):
  print("Refreshing cache...")
  cache.refresh_cache()
  do_summary(cache, args)

def do_clear_exif(cache, args):
  yn = input("Do you really want to clear all cached EXIF info from cache? (y/N)")
  if yn == "y" or yn == "Y": 
    print("Clearing EXIF info...")
    cache.clear_exif()
    cache._save_dir_cache()
    do_summary(cache, args)
  else:
    print("aborted")  

def do_get_exif(cache, args):
  print( "File: {:s}".format(args.param) )
  print( "EXIF:" ) 
  exif = cache.get_exif_info(args.param)
  exif_data = exif.get('exif_info')
  if exif_data:
    for key, val in exif_data.items():
      if key == 'GPSInfo': 
        val = GPSlookup.lookup(val)
      else:
        val = displaymsg.item2str(val)  
      print( "  {:25s}: {:s}".format( key, str(val) ) )

def do_refresh_exif(cache, args):
  do_refresh(cache, args)
  print("Refreshing cached EXIF info...")
  filecount = cache.get_filecount()
  curfile = 0
  dirname = None
  dirlist = cache.get_dirlist_full()
  for dir_item in dirlist:
    if dir_item[0] == "d": # file
      dirname = dir_item[1]
      print( "{:3.0f}% - scanning files in directory: {:s}".format( curfile/filecount*100, dirname) )  
    else:
      fname = os.path.join(dirname, dir_item[1])
      cache.read_exif_info(fname)
      curfile += 1
  do_summary(cache, args)

#-----------------------------
def parse_options():
  epilog = """commands:
  summary:              List a short summary of the cache.
  list:                 List all directories plus the no. of files. 
  list_long:            List all directories and all files. 
  refresh:              Refreshe the directory cache.
  refresh_exif:         Refresh EXIF infos. 
  get_exif <filepath>:  Show cached EXIF info for given <filepath>.
  clear_exif:           Clear all cached EXIF infos(!) from cache. 
  """
  parser = argparse.ArgumentParser(description='PI Infotainment dircache manager utility', epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('--file', '-f', default=cfg['DIR_CACHE_FILE'], help='cache file')
  parser.add_argument('command', choices=["summary", "list", "list_long", "refresh", "clear_exif", "get_exif", "refresh_exif"], nargs='?', default="summary" )
  parser.add_argument('param', nargs='?', help="parameter" )
  return parser.parse_args()

def main():
  args = parse_options()
  cache = dircache.DirCache(args.file)
  if args.command == "summary": 
    do_summary(cache, args)
  elif args.command == "refresh": 
    do_refresh(cache, args)
  elif args.command == "clear_exif": 
    do_clear_exif(cache, args)
  elif args.command == "get_exif": 
    do_get_exif(cache, args)
  elif args.command == "list": 
    do_list(cache, args)
  elif args.command == "list_long": 
    do_list_long(cache, args)
  elif args.command == "refresh_exif": 
    do_refresh_exif(cache, args)

#-------------------------------
if __name__ == '__main__':
  main()