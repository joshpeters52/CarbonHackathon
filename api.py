from flask import Flask, jsonify, abort, make_response, request
from twilio.rest import Client
from pyshorteners import Shortener
from math import radians, sin, cos, atan2, sqrt

import tinys3
import os
import time
import json
import random
import requests
import pyrebase

NEARBY_THRESHOLD_IN_FEET = 200

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = "+15715703304"

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.environ.get("S3_BUCKET_NAME")

config = {
    "apiKey": "AIzaSyBBVOdkBnlh8tiE7FqAp8X5pa1zPTqMH_Q",
    "authDomain": "quircl-12e1f.firebaseapp.com",
    "databaseURL": "https://quircl-12e1f.firebaseio.com",
    "projectId": "quircl-12e1f",
    "storageBucket": "quircl-12e1f.appspot.com"
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
user = auth.sign_in_with_email_and_password("plautzdn@gmail.com", "adminpassword")
db = firebase.database()

id_token = user['idToken']

app = Flask(__name__, static_url_path="")

@app.route("/api/get-nearby", methods=['POST'])
def get_nearby():
	req_data = request.get_json()

	if "lat" not in req_data:
		return req_err("No 'lat' field in request data")
	elif "lon" not in req_data:
		return req_err("No 'lon' field in request data")
	elif "name" not in req_data or len(req_data["name"]) <= 0:
		return req_err("No 'fname' field in request data")
	elif "number" not in req_data or len(req_data["number"]) != 10:
		return req_err("No 'number' field in request data")

	name = req_data["name"]
	number = req_data["number"]
	lat = req_data["lat"]
	lon = req_data["lon"]

	user_id = name.replace(" ", "") + number

	user_json = { "name": name, "number": number, "lat": lat, "lon": lon }
	user_exists = db.child("users").child(name + number).get(id_token).val() is not None

	if user_exists:
		db.child("users").child(user_id).update(user_json, id_token)
	else:
		db.child("users").child(user_id).set(user_json, id_token)

	users = db.child("users").get(id_token).val()

	nearby_users = []
	for i in users:
		if i != user_id:
			nxt_lat = users[i]["lat"]
			nxt_lon = users[i]["lon"]
			
			if calc_dist(lat, lon,  nxt_lat, nxt_lon):
				nearby_users.append(users[i])

	return jsonify({ "success": True, "data": nearby_users }), 200

@app.route("/api/remove-from-nearby/<user_id>", methods=['DELETE'])
def remove_from_nearby(user_id):
	if user_id is None or len(user_id) <= 10:
		return req_err("No URL parameter for user id (first name + last name + number)")

	db.child("users").child(user_id).remove(id_token)		
	
	return jsonify({ "success": True, "data": "Successfully removed '" + user_id + "' from nearby database"})


@app.route("/api/send-group", methods=['POST'])
def send_group():
	req_data = request.get_json()

	if "group" not in req_data:
		return req_err("No 'group' field in request data")
	elif "mms" not in req_data:
		return req_err("No 'mms' field in request data")

	mms_enabled = req_data["mms"]

	vcard_filenames = []

	for person in req_data["group"]:

		if "fname" not in person or len(person["fname"]) <= 0 or " " in person["fname"]:
			return req_err("No 'fname' field in a group member")
		elif "lname" not in person or len(person["lname"]) <= 0 or " " in person["lname"]:
			return req_err("No 'lname' field in a group member (fname: '" + person["fname"] + "')")
		elif "numbers" not in person:
			return req_err("No 'numbers' field in a group member (fname: '" + person["fname"] + "', lname: '" + person["lname"] + "')")
		elif len(person["numbers"]) <= 0:
			return req_err("At least one number required for a group member (fname: '" + person["fname"] + "', lname: '" + person["lname"] + "')")

		for number in person["numbers"]:

			if "type" not in number:
				return req_err("No 'type' field in a number (fname: '" + person["fname"] + "', lname: '" + person["lname"] + "')")
			elif "num" not in number:
				return req_err("No 'num' field in a number (fname: '" + person["fname"] + "', lname: '" + person["lname"] + "', type: '" + number["type"] + "')")
			elif len(number["num"]) != 10:
				return req_err("Number must be exactly 10 concatenated digits (fname: '" + person["fname"] + "', lname: '" + person["lname"] + "', number: '" + number["num"] + "')")

			try:
				int(number["num"])
			except:
				return req_err("Number not valid (fname: '" + person["fname"] + "', lname: '" + person["lname"] + "', number: '" + number["num"] + "')")

		fname = person["fname"]
		lname = person["lname"]
		numbers = person["numbers"]
		mobile = numbers[0]["num"]

		vcard_filename = fname + "." + lname + "." + mobile + ".vcf"
		vcard_filenames.append(vcard_filename)

		if mms_enabled:
			vcard_str = create_vcard_str(fname, lname, numbers)
			vcard_file = open("/tmp/" + vcard_filename, "w")
			vcard_file.write(vcard_str)
			vcard_file.close()

	if mms_enabled:
		s3_pool = tinys3.Pool(AWS_ACCESS_KEY, AWS_SECRET_KEY, tls=True, size=len(req_data["group"]))

		uploads = []
		for i in range(len(req_data["group"])):
			vcard_file = open("/tmp/" + vcard_filenames[i], "rb")
			uploads.append(s3_pool.upload(vcard_filenames[i], vcard_file, AWS_S3_BUCKET))

		s3_pool.all_completed(uploads)

	twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

	for person in req_data["group"]:
		fname = person["fname"]
		lname = person["lname"]
		mobile = person["numbers"][0]["num"]

		message = twilio_client.messages.create(
			to="+1" + mobile,
			from_=TWILIO_FROM_NUMBER,
			body=generate_quircl() + "\n\nYour social circle will be ready shortly!")

		time.sleep(1)

		contact_text = ""

		for filename in vcard_filenames:
			split = filename.split(".")
			next_fname = split[0]
			next_lname = split[1]
			next_mobile = split[2]

			if next_fname == fname and next_lname == lname and next_mobile == mobile:
				continue

			if mms_enabled:
				time.sleep(1)
				message = twilio_client.messages.create(
					to="+1" + mobile,
					from_=TWILIO_FROM_NUMBER,
					media_url="https://s3.amazonaws.com/carbonhackathon-quircl/" + filename)
			else:
				contact_text += next_fname + " " + next_lname + "\n" + convert_phone_number(next_mobile)
				contact_text += "\nContact: " + url_shortener("https://s3.amazonaws.com/carbonhackathon-quircl/" + filename) + "\n\n"

		if not mms_enabled:
			twilio_client.messages.create(
				to="+1" + mobile,
				from_=TWILIO_FROM_NUMBER,
				body=contact_text + "Thanks for using Quircl!")

	return jsonify({ "success": True, "data": "Contacts successfully transmitted" }), 200


def req_err(message):
	response = jsonify({ "success": False, "data": message })
	response.status_code = 400
	print("Error!! MESSAGE: " + message)
	return response

def create_vcard_str(fname, lname, numbers):
	result = "BEGIN:VCARD\nN:" + lname + ";" + fname + ";;;\n"
	for number in numbers:
		result += "TEL;" + number["type"].upper() + ":+1" + number["num"] + "\n"
	return result + "END:VCARD"

def convert_phone_number(number):
	result = "("
	for i in range(10):
		result += number[i]
		if i == 2:
			result += ") "
		elif i == 5:
			result += "-"
	return result

def url_shortener(url):
	shortener = Shortener("Tinyurl")
	return shortener.short(url)[7:]

def generate_quircl():
	quircls = [ 
		"Quircl's magic is brewing...",
		"Quircl says, \"Hang tight earthling!\"",
		"1,238 Quircls are hard at work!",
		"Quircl is making the jump to hyperspace...",
		"\"Houston we have NO problems,\" Quircl explains.",
		"Quircl is readying the ignition...",
		"\"'Patience you must have.' -Yoda\" -Quircl",
		"How many Quircls does it take to get your contacts?",
		"The platypus is a distant relative of the Quircl.",
		"A group of Quircls is a Quircl Circle.",
		"To Quircl or not to Quircl? That is the question.",
		"Quircls like long walks on the beach...",
		"For just 20 cents a day, you can feed a family of Quircls",
		"Scientists hate him! Wait to find out what this Quircl did to social circles everywhere!!",
		"Contrary to popular belief... Quircls actually have 7 arms, not 6.",
		"Quircls don't care who you voted for.",
		"Squirtle and Quircl walk into a bar...",
		"If you or a loved one have been diagnosed with Quircl-syndrome... That's awesome."
		]

	return quircls[random.randint(0, len(quircls) - 1)]

def calc_dist(lat1, lon1, lat2, lon2):
	dlon = radians(lon2 - lon1)
	dlat = radians(lat2 - lat1)

	lat1 = radians(lat1)
	lat2 = radians(lat2)	

	a = (sin(dlat/2))**2 + cos(lat1) * cos(lat2) * (sin(dlon/2))**2 
	c = 2 * atan2( sqrt(a), sqrt(1-a) )
	return c * 3961 * 5280 <= NEARBY_THRESHOLD_IN_FEET		

if __name__ == '__main__':
	app.run(debug=True)
