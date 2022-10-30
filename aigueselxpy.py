#!/usr/bin/python3 

import requests
import time
import json
import os
import getopt
from datetime import datetime
import sys

s = requests.Session()

class ResponseException(Exception):
	pass
	
class LoginException(Exception):
	pass

class DataOnServerException(Exception):
	pass


def extract_token(text):
	temp = str(text).split('p_auth=',1)
	return temp[1][:8]

def do_login(user, passwd):
	global s
	base_url = "https://www.aigueselx.com/login"
	login_url = "https://www.aigueselx.com/login?p_p_id=CustomLoginPortlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&_CustomLoginPortlet_javax.portlet.action=%2Flogin%2Flogin&_CustomLoginPortlet_mvcRenderCommandName=%2Flogin%2Flogin"
	headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0'}
	values = {	
			'_CustomLoginPortlet_formDate': '',
			'_CustomLoginPortlet_saveLastPath': 'false',
			'_CustomLoginPortlet_redirect': '',
			'_CustomLoginPortlet_doActionAfterLogin': 'false',
			'_CustomLoginPortlet_login': user,
			'_CustomLoginPortlet_password': passwd,
			'_CustomLoginPortlet_lastContract': '',
			'p_auth': ''}
	
	try:
		step =  "1"
		r = s.get(base_url, headers=headers, timeout=20)
		if r.status_code != 200:
			raise ResponseException("Response error on login stage(" + step + "/2), code: {}".format(r.status_code))
			s = None
		values['_CustomLoginPortlet_formDate'] = str(int(time.time()) )
		values["p_auth"] = extract_token(r.content)
		step =  "2"
		r = s.post(login_url, headers=headers, data=values, timeout = 20)
		if r.status_code != 200:
			raise ResponseException("Response error on login stage("+ step + "/2), code: {}".format(r.status_code))
			s = None
		if "Su usuario o contrase\\xc3\\xb1a no es correcto" in str(r.content):
			raise LoginException("Login error, bad login")
			s = None
	except requests.exceptions.Timeout:
		print("No response from aigueselx.es (login step " + step + ")")
		sys.exit(1)
	except LoginException as e:
		print(e)
		sys.exit(1)
	except ResponseException as e:
		print(e)
		sys.exit(1)
	
def get_consumption(date_from, date_to):
	global s
	pre_consumption_url = "https://www.aigueselx.com/group/aguas-de-elche/mis-consumos"
	consumption_url = "https://www.aigueselx.com/group/aguas-de-elche/mis-consumos?p_p_id=MisConsumos&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_cacheability=cacheLevelPage&p_auth={0}&_MisConsumos_op=buscarConsumosHoraria&_MisConsumos_fechaInicio={1}&_MisConsumos_fechaFin={2}&_MisConsumos_inicio=0&_MisConsumos_fin=500"
	headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0'}

	try:
		step = "1"
		r = s.get(pre_consumption_url, headers=headers, timeout=20)
		if r.status_code != 200:
			raise ResponseException("Response error on grab consumption stage (" + step + "/2), code: {}".format(r.status_code))
			s = None
		step = "2"
		r = s.get(consumption_url.format(extract_token(r.content),date_from,date_to), headers=headers, timeout=20)
		if r.status_code != 200:
			raise ResponseException("Response error on grab consumption stage (" + step + "/2), code: {}".format(r.status_code))
			s = None
		if len(r.json()["consumos"]) == 0:
			raise DataOnServerException("No data available on server")
	except requests.exceptions.Timeout:
		print("No response from aigueselx.es (get consumption step " + step + " )")
		sys.exit(1)
	except ResponseException as e:
		print(e)
		sys.exit(1)
	except DataOnServerException as e:
		print(e)
		sys.exit(1)
	return rejson(r.json())

def pretty_data(rejson_data):
	print("\n\n\t\t\t\t\t CONSUMOS [00h > 11h | 12h > 23h] (litros)")
	print("{: <13} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3}|{: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3}".format("","0h","1h","2h","3h","4h","5h","6h","7h","8h","9h","10h","11h","12h","13h","14h","15h","16h","17h","18h","19h","20h","21h","22h","23h"))
	rejson_data = json.loads(rejson_data)
	for i in rejson_data.keys():
		print("{: <13} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3}|{: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3} {: <3}".format(i+ ":",rejson_data[i][0],rejson_data[i][1],rejson_data[i][2],rejson_data[i][3],rejson_data[i][4],rejson_data[i][5],rejson_data[i][6],rejson_data[i][7],rejson_data[i][8],rejson_data[i][9],rejson_data[i][10],rejson_data[i][11],rejson_data[i][12],rejson_data[i][13],rejson_data[i][14],rejson_data[i][15],rejson_data[i][16],rejson_data[i][17],rejson_data[i][18],rejson_data[i][19],rejson_data[i][20],rejson_data[i][21],rejson_data[i][22],rejson_data[i][23]))

def rejson(orig_json_data):
#Rebuild json structure
#Fix missing dates in json responses. Set -1 value for still not read. Set fixed 24 sized output per day. Change date format
	months = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
	day_consumptions = []
	dates = []
	for i in range(len(orig_json_data["consumos"])):
		if orig_json_data["consumos"][i]["fechaConsumo"][:11] not in dates:
			dates.append(orig_json_data["consumos"][i]["fechaConsumo"][:11])

		if i == 0:
			while int(orig_json_data["consumos"][0]["fechaConsumo"][12:14]) != (23 - len(day_consumptions)): #fill still not measured with -1
				day_consumptions.append("-1")
		else:
			while int(orig_json_data["consumos"][i]["fechaConsumo"][12:14]) != (23 - (len(day_consumptions) % 24)): #fix missing hours
				day_consumptions.append("0")
		day_consumptions.append(str(int(1000*float(orig_json_data["consumos"][i]["consumo"].replace(",",".")))))
	
	out_dict = dict()
	for i in range(len(dates)):
		day_piece = day_consumptions[24*i:24*(i+1)]
		day_piece = day_piece[::-1]
		current_date = dates[i][:2] + "/" + str((1+months.index(dates[i][3:][:3]))).zfill(2) + "/" + dates[i][7:][:4]
		out_dict.update({current_date:day_piece})
	return str(out_dict).replace("\'","\"")

def main(argv):
	username = ''
	passwd = ''	
	from_date = ''
	to_date = ''
	out = ''

	try:
		opts, args = getopt.getopt(argv,"hju:f:t:",["help","credentials=","from=", "to=", "json="])
	except getopt.GetoptError:
		show_usage()
	for opt, arg in opts:
		if opt in ('-h','--help'):
			show_usage()
		elif opt in ("-u", "--credentials") and ':' in arg:
			username = arg.split(':')[0]
			passwd = arg.split(':')[1]
		elif opt in ("-f", "--from"):
			from_date = arg.replace("-","/")
		elif opt in ("-j", "--json"):
			out = "json"
		elif opt in ("-t", "--to"):
			to_date = arg.replace("-","/")
	if len(username)>0 and len(passwd)>0 and len(from_date)==10 and len(to_date)==10:
		do_login(username, passwd)
		json_consumption = get_consumption(from_date, to_date)
		if out == 'json':
			print(json_consumption)
		else:
			pretty_data(json_consumption)
	else:
		show_usage()

def show_usage():
	print('\n\naigueselxpy.py -u user:password -f <dd-mm-yyyy> -t <dd-mm-yyyy> v1.0')
	print('Get hour water consumptions between dates')
	print('\n\t-u or --credentials: provide user credentials from aigueselx.es')
	print('\n\t-f or --from: from date (also valid with \'/\' instead of \'-\'')
	print('\n\t-t or --to: to date (also valid with \'/\' instead of \'-\'')
	print('\n\t-j or --json: print json output (table presentation is the default output)')
	print('\n\t-h or --help: show this help')
	sys.exit(2)

if __name__ == "__main__":
   main(sys.argv[1:])
   
