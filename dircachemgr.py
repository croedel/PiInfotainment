#!/usr/bin/python
''' Cache for picture directory tree 
'''  
import argparse
import datetime
import logging
import config
import dircache

#-----------------------------
def do_summary(cache, args): 
  filecount = cache.get_filecount()
  exifcount = cache.get_exifcount() 
  exifrate = exifcount / filecount if filecount>0 else 0 
  print( "Cache file:       {:s}".format( args.file ))
  print( "Created:          {:s}".format( str(cache.get_cache_refresh_date())) )
  print( "#Directories:     {:d}".format( cache.get_dircount()) )
  print( "#Files:           {:d}".format( filecount ) )
  print( "#Files with EXIF: {:d} ({:.1f}%)".format( exifcount, exifrate)  )

def do_list(cache, args): 
  do_summary(cache, args)
  dirlist = cache.get_dirlist()
  for dir_item in dirlist:
    print( "{:s}: {:d} files".format(dir_item[0], dir_item[1]) )

def do_list_full(cache, args):
  path_trunc = len(config.PIC_DIR) + 1
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
  print("Clearing EXIF info...")
  cache.clear_exif()
  do_summary(cache, args)

#-----------------------------
def parse_options():
  epilog = """commands:
  summary:    List a short summary of the cache.
  list:       Lists all directories plus the no. of files. 
  list_full:  Lists all directories and all files. 
  refresh:    Refreshes the directory cache.
  clear_exif: Clears the cached EXIF info.
  """
  parser = argparse.ArgumentParser(description='PI Infotainment dircache manager utility', epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('--file', '-f', default=config.DIR_CACHE_FILE, help='cache file')
  parser.add_argument('command', choices=["summary", "list", "list_full", "refresh", "clear_exif"] )
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
  elif args.command == "list": 
    do_list(cache, args)
  elif args.command == "list_full": 
    do_list_full(cache, args)

#-------------------------------
if __name__ == '__main__':
  main()