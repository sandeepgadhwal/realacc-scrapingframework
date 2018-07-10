from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings

# Import Libraries
import time
import datetime
import pandas as pd
import json
import requests
import urllib
#import MySQLdb

# Create your views here.
from django.http import HttpResponse

def index(request):
    query_params = dict(request.GET)
    for key, value in query_params.items():
        query_params[key] = value[0].lower()
    if not query_params['resourcetype']:
        query_params['resourcetype'] = 'list'
    elif not (query_params['resourcetype'] == 'list' or query_params['resourcetype'] == 'gis'):
        return HttpResponse("Wrong Resource Type", status=500)
    if query_params['apns']:
        query_params['apns'] = query_params['apns'].split(",")
        query_params['apns'] = [x.strip() for x in query_params['apns']]
        if query_params['querytype'] == 'ondemand':
            data = ondemand(query_params)
            if not data:
                data = {
                'error': 'No data returned for your request'
                }
            return JsonResponse(data, status=200, safe=False)
        elif query_params['querytype'] == 'bulk':
            bulk(query_params)
            message = "Your Request has been accepted to scrape " + len(query_params['apns']) + " APN numbers."
            return HttpResponse(message, status=201)
        else:
            return HttpResponse("Wrong Query Type", status=500)
    else:
        return HttpResponse("No APNS supplied", status=500)

def scraper(query_params):
    if query_params['countyid'] == '48201' or query_params['countyid'] == 'harris':
        data = []
        if query_params['resourcetype'] == 'list':
            #Configurables
            protocol = "https://"
            server = "public.hcad.org/records/recorddetails.asp"
            url = protocol + server
            params = {
                'url_encryp': 'hideacct',
                'tab': "",
                'bld': 1,
                'card': 1,
                'taxyear': 2018,
                'acct': ""
            }
            #Playing with headers
            my_referer = 'http://hcad.org/property-search/real-property/real-property-search-by-account-number/'
            UserAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
            mod_headers = {'referer': my_referer, 'User-Agent':UserAgent}
            # Start Scrpaing
            for apn in query_params['apns']:
                params['acct'] = apn
                #hit Server
                response = requests.get(url, params=params, headers=mod_headers)#, verify=False)
                print(url+"?"+urllib.parse.urlencode(params))
                if response.ok:
                    row = {}
                    try:
                        #Try to Save Response
                        row['HCad No'] = apn
                        response = response.text
                        row['OWNER NAME'] = response.split("<!-- ---------- OWNER NAME ---------- -->\r\n")[1].split("<br />")[0].strip()
                        row['Mail Street Adress'] = response.split("<!-- ---------- MAILING ADDRESS (ADDR1 AND ADDR2) ---------- -->\r\n ")[1].split("<br />")[0].strip()
                        addrs2 = response.split("<!-- ---------- MAILING ADDRESS (CITY-STATE-ZIP OR COUNTRY)---------- -->\r\n ")[1].split("<br />")[0].strip()
                        row['Mail City'] = addrs2.split('&nbsp;')[0]
                        row['Mail State'] = addrs2.split('&nbsp;')[1]
                        row['Mail Zip Code'] = addrs2.split('&nbsp;')[2]
                    except Exception as e:
                        row['Error'] = 'No Data Found for this APN'
                        print(e)
                        pass
                    data.append(row)
        elif query_params['resourcetype'] == 'gis':
            #Configurables
            protocol = "https://"
            server = "arcweb.hcad.org/server/rest/services/public/public_query/MapServer/0/query"
            url = protocol + server
            params = {
                'f': 'json',
                'returnGeometry': 'false',
                'spatialRel': 'esriSpatialRelIntersects',
                'outFields': '*'
            }
            #Playing with headers
            my_referer = 'http://hcad.org/property-search/real-property/real-property-search-by-account-number/'
            UserAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
            mod_headers = {'referer': my_referer, 'User-Agent':UserAgent}
            # Start Scrpaing
            params['where'] = "HCAD_NUM IN ('" + "','".join(query_params['apns']) + "')"
            response = requests.get(url, params=params, headers=mod_headers)#, verify=False)
            print(url+"?"+urllib.parse.urlencode(params))
            if response.ok:
                features = response.json()['features']
                response = {}
                for feature in features:
                    attributes = feature['attributes']
                    response[attributes['HCAD_NUM']] = attributes
                for apn in query_params['apns']:
                    #hit Server
                    row = {}
                    try:
                        #Try to Save Response
                        row['HCad No'] = apn
                        row['OWNER NAME'] = response[apn]['owner']
                        row['Mail Street Adress'] = response[apn]['address']
                        row['Mail City'] = response[apn]['city']
                        row['Mail State'] = 'TX'
                        row['Mail Zip Code'] = response[apn]['zip']
                    except Exception as e:
                        row['Error'] = 'No Data Found for this APN'
                        print(e)
                        pass
                    data.append(row)
        return data
def ondemand(query_params):
    data = scraper(query_params)
    return data
async def bulk(query_params):
    data = scraper(query_params)
