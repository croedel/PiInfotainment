#!/usr/bin/python
''' Retrieve RKI Corona data 
'''

import requests
import csv
from config import cfg
import logging

def _request_rki_data( id ):  # get data from RKI API
  ret="ERROR"
  url = 'https://services7.arcgis.com/mOBPykOjAyBO2ZKk/arcgis/rest/services/RKI_Landkreisdaten/FeatureServer/0/query'
  payload = { 'where':'AGS='+id, 'outFields':'*', 'outSR':'4326', 'f':'json' }
  try:
    response = requests.get( url, payload, timeout=3 )
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

#----------------
def _request_hospitalization( region ):  # get data from github
  ret="-1"
  url = 'https://raw.githubusercontent.com/robert-koch-institut/COVID-19-Hospitalisierungen_in_Deutschland/master/Aktuell_Deutschland_COVID-19-Hospitalisierungen.csv'
  try:
    response = requests.get( url, timeout=3 )
  except requests.exceptions.RequestException as err:
    logging.error( "Couldn't request hospitalization from github: Exception {:s}".format(str(err)) )
  else:
    if response.status_code == 200:
      data = response.text
      csvdata = csv.DictReader( data.splitlines() )
      for row in csvdata:
        r_date = row.get('Datum')
        r_region = row.get('Bundesland')
        r_age = row.get('Altersgruppe')
        r_hospitalization = row.get('7T_Hospitalisierung_Inzidenz')
        if( r_region == region and r_age == '00+' ):
          ret = r_hospitalization    
          #print( row )  
          break
    else:
      logging.error( "Error while requesting hospitalization from github: {:s} -> {:d} {:s}".format( str(id), response.status_code, response.reason) )

  return ret  

#------------------------------------------------------------------    
# this is the main function to get the weather info
def get_covid_info( id, region ): 
  logging.info('Refreshing COVID info')
  raw_data = _request_rki_data( id )
  covid_data = _normalize_rki_data(raw_data)
  covid_data['region'] = region
  covid_data['hospitalization'] = _request_hospitalization( region )
  return covid_data

#############################################################################
if __name__ == "__main__":
  logging.basicConfig( level=logging.INFO, format="%(asctime)s : %(levelname)s : %(message)s" )
  covid_data = get_covid_info( cfg['RKI_ID'], cfg['RKI_REGION'] )
  print( str(covid_data) )  
