﻿import sqlite3
import datetime
import sys, getopt
import json
import requests

expect = 2018
verbose = False
duration = False
lastFmToken = ""

def flags():
	opts, args = getopt.getopt(sys.argv[2:], "d:v", ["duration="])
	for o, token in opts:
		if o == "-v":
			global verbose
			verbose = True
		elif o in ("-d", "--duration"):
			global duration
			duration = True
			global lastFmToken
			lastFmToken = token

def shouldNotIgnore(title, year, expect):
	splitted = title[:8]
	if (splitted.encode("utf-8") == "A écouté"):
		if (year[:4].encode("utf-8") == "2018"):
			return True
		else:
			False
	else:
		return False

def open_file():
	if (sys.argv[1].endswith('.json')):
		try:
			file = open(sys.argv[1], "r")
			return file
		except:
			print "Could not open your history file"
			sys.exit()
	else:
		print "Your history file should be an html file"
		sys.exit()

def parse_json(file, cursor):
	json_object = json.load(file)
	for obj in json_object:
		if (shouldNotIgnore(obj['title'], obj['time'], expect) and 'description' in obj):
			cursor.execute("""INSERT INTO songs(title, artist, year) VALUES(?, ?, ?)""", (obj['title'][9:], obj['description'], obj['time']))

def print_db(cursor):
	#Test results from DB
	print ("####################Full List#####################")
	cursor.execute("""SELECT id, artist, title, year FROM songs""")
	rows = cursor.fetchall()
	for row in rows:
		datetime.datetime.now()
		print('{0} : {1} - {2} - {3}'.format(row[0], row[1].encode("utf-8"), row[2].encode("utf-8"), row[3]))

def prepare_clean_db(cursor):
	#Artist top
	cursor.execute("""SELECT artist, COUNT(*) FROM songs GROUP BY artist""")
	result = cursor.fetchall()
	for res in result:
		cursor.execute("""INSERT INTO artist_count(artist, occurence) VALUES(?, ?)""", (res[0], res[1]))

	#Song Top
	cursor.execute("""SELECT title, COUNT(*) FROM songs GROUP BY title""")
	result_song = cursor.fetchall()
	for res_song in result_song:
		cursor.execute("""INSERT INTO songs_count(title, occurence) VALUES(?, ?)""", (res_song[0], res_song[1]))

def delete_duplicate(cursor):
	#Doublon Deletor
	cursor.execute("""SELECT title, COUNT(*), artist FROM songs GROUP BY title""")
	result_doublon = cursor.fetchall()
	for res_doublon in result_doublon:
		cursor.execute("""INSERT INTO report(title, artist, occurence) VALUES(?, ?, ?)""", (res_doublon[0], res_doublon[2], res_doublon[1]))

def print_full_tops(cursor):
	print ("####################Top Artists#####################")
	cursor.execute("""SELECT artist, occurence FROM artist_count ORDER by occurence DESC""")
	rows = cursor.fetchall()
	for row in rows:
		datetime.datetime.now()
		print('{0} - {1}'.format(row[0].encode("utf-8"), row[1]))

	print ("####################Top Songs#####################")
	cursor.execute("""SELECT title, occurence FROM songs_count ORDER by occurence DESC""")
	rows = cursor.fetchall()
	for row in rows:
		datetime.datetime.now()
		print('{0} - {1}'.format(row[0].encode("utf-8"), row[1]))

def get_duration(cursor):
	#Count duration
	cursor.execute("""SELECT id, artist, title FROM report""")
	rows = cursor.fetchall()
	for row in rows:
		datetime.datetime.now()
		parameters = {"method": "track.getInfo", "api_key": lastFmToken, "artist": row[1].encode("utf-8"), "track": row[2].encode("utf-8"), "format": "json"}
		response = requests.get("http://ws.audioscrobbler.com//2.0/", params=parameters)
		if (response.status_code == 200):
			json_parsed = response.json()
			if ('error' in json_parsed):
				print "error found"
				cursor.execute("""UPDATE report SET duration = ? WHERE id = ?""", (0, row[0]))
				continue
			else:
				duration = json_parsed['track']['duration']
				cursor.execute("""UPDATE report SET duration = ? WHERE id = ?""", (duration, row[0]))

	#Calcul total duration
	if verbose:
		print ("####################Full List WITHOUT DOUBLON AND DURATION#####################")
	total_duration = 0
	error_rate = 0
	cursor.execute("""SELECT id, artist, title, duration, occurence FROM report""")
	rows = cursor.fetchall()
	for row in rows:
		datetime.datetime.now()
		song_count = row[0]
		if verbose:
			print('{0} : {1} - {2}- {3} - occurence : {4}'.format(row[0], row[1].encode("utf-8"), row[2].encode("utf-8"), row[3], row[4]))
		total_duration += row[3] * row[4]
		if row[3] == 0:
			error_rate = error_rate + 1
	return (total_duration, error_rate, song_count)

def gen_report(cursor, data):
	#Top 10 Report
	sys.stdout = open('report.dat', 'w')
	print ("#################### Top Artists #####################")
	cursor.execute("""SELECT artist, occurence FROM artist_count ORDER by occurence DESC LIMIT 10""")
	rows = cursor.fetchall()
	for row in rows:
		datetime.datetime.now()
		print('{0} - {1}'.format(row[0].encode("utf-8"), row[1]))

	print ("#################### Top Songs #####################")
	cursor.execute("""SELECT title, occurence FROM songs_count ORDER by occurence DESC LIMIT 10""")
	rows = cursor.fetchall()
	for row in rows:
		datetime.datetime.now()
		print('{0} - {1}'.format(row[0].encode("utf-8"), row[1]))

	if duration:
		print ("\n#################### Duration #####################")
		print ('Total duration : {0}', data[0])
		print ('Total song count : ', data[2])
		print ('Error count : ', data[1])
		print ('Error rate : {0}%'.format((float(data[1])/data[2])*100))
	sys.stdout.close()

def main():
	flags()
	#Config
	conn = sqlite3.connect('gmusic.db')
	cursor = conn.cursor()
	with open('schema.sql') as fp:
		cursor.executescript(fp.read())
	data = ""

	file = open_file()

	print ("Welcome on GMusic Year Wrapper.")
	print ("We are now processing your file. Note that this process can be long (generally between 1 and 4 hours)")
	print ("No more informations will be displayed during this process. You can check log.dat at any time to check progression.")

	#Start log in log file
	if verbose:
		sys.stdout = open('log.dat', 'w')

	parse_json(file, cursor)
	if verbose:
		print_db(cursor)
	prepare_clean_db(cursor)
	if verbose:
		print_full_tops(cursor)
	delete_duplicate(cursor)
	if duration:
		data = get_duration(cursor)
	if verbose:
		sys.stdout.close()
	gen_report(cursor, data)

main()