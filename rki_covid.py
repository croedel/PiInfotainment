#!/usr/bin/python
''' Retrieve RKI Corona data 
'''

import requests
from config import cfg
import logging

def _request_rki_data( id ):  # get data from RKI API
  ret="ERROR"
  url = 'https://services7.arcgis.com/mOBPykOjAyBO2ZKk/arcgis/rest/services/RKI_Landkreisdaten/FeatureServer/0/query'
  payload = { 'where':'AGS='+id, 'outFields':'*', 'outSR':'4326', 'f':'json' }
  try:
    response = requests.get( url, payload )
  except requests.exceptions.RequestException as err:
    logging.error( "Couldn't request RKI API: Exception {:s}".format(str(err)) )
  else:
    if response.status_code == 200:
      ret = response.json()
    else:
      logging.error( "Error while requesting RKI API: {:s} -> {:d} {:s}".format( str(payload), response.status_code, response.reason) )
  return ret  

#----------------

def _normalize_rki_data( raw_data ):
  covid_data = {}
  covid_data['cases7_per_100k'] = -1
  try:
    covid_data['name'] = raw_data['features'][0]['attributes']['BEZ'] + ' ' + raw_data['features'][0]['attributes']['GEN']
    covid_data['cases7_per_100k'] = raw_data['features'][0]['attributes']['cases7_per_100k']
  except Exception as e:
    logging.error( "Error while normalizing RKI data: Exception {:s}".format(str(e)) ) 
  return covid_data

#------------------------------------------------------------------    
# this is the main function to get the weather info
def get_covid_info( id ): 
  logging.info('Refreshing COVID info')
  raw_data = _request_rki_data( id )
  covid_data = _normalize_rki_data(raw_data)
  return covid_data

#############################################################################
if __name__ == "__main__":
  logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )
  covid_data = get_covid_info( cfg['RKI_ID'] )
  print( str(covid_data) )  
