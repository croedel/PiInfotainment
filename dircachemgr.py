#!/usr/bin/python
''' Cache for picture directory tree 
'''  
import argparse
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
  dirstat = cache.get_dirstat()
  for path, count in dirstat.items():
    print( "- {:s}: {:d} files".format(path, count) )

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
  refresh:    Refreshes the directory cache.
  clear_exif: Clears the cached EXIF info.
  """
  parser = argparse.ArgumentParser(description='PI Infotainment dircache manager utility', epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('--file', '-f', default=config.DIR_CACHE_FILE, help='cache file')
  parser.add_argument('command', choices=["summary", "list", "refresh", "clear_exif"] )
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

#-------------------------------
if __name__ == '__main__':
  main()