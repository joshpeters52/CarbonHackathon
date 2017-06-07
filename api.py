from flask import Flask, jsonify, abort, make_response, request
from twilio.rest import Client
from pyshorteners import Shortener

import tinys3
import os
import time
import json
import requests

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = "+15715703304"

AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.environ.get("S3_BUCKET_NAME")

app = Flask(__name__, static_url_path="")

@app.route("/api/send-group", methods=['POST'])
def send_group():
	req_data = request.get_json()

	if "group" not in req_data:
		return req_err("No 'group' field in request data")
	elif "mms" not in req_data:
		return req_err("No 'mms' field in request data")

	# mms enabled?
	# hellellelejlej;lw
	# q;ljlkefjlkwejf
	# klwefjlkwejlkfjwe
	mms_enabled = req_data["mms"]

	vcard_filenames = []

	for person in req_data["group"]:

		if "fname" not in person:
			return req_err("No 'fname' field in a group member")
		elif "lname" not in person:
			return req_err("No 'lname' field in a group member (fname: '" + person["fname"] + "')")
		elif "numbers" not in person:
			return req_err("No 'numbers' field in a group member (fname: '" + person["fname"] + "', lname: '" + person["lname"] + "')")
		elif len(person["numbers"]) <= 0:
			return req_err("At least one number required for a group member (fname: '" + person["fname"] + "', lname: '" + person["lname"] + "')")

		for number in person["numbers"]:

			if len(number["num"]) != 10:
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
			body="Quircl's magic is brewing... Your contacts will be here shortly!")

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
				contact_text += "\nvCard: " + url_shortener("https://s3.amazonaws.com/carbonhackathon-quircl/" + filename) + "\n\n"

		if not mms_enabled:
			twilio_client.messages.create(
				to="+1" + mobile,
				from_=TWILIO_FROM_NUMBER,
				body=contact_text + "Thanks for using Quircl!")



	# client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

	# myfile = open("/tmp/file3.vcf", "w")
	# myfile.write("BEGIN:VCARD\nVERSION:3.0\nN:Doe;Jane;;;\nFN:Jane Doe\nORG:Example.com Inc.;\nTEL;type=WORK;type=pref:+1 617 555 1212\nEND:VCARD")
	# myfile.close()

	# myfile = open("/tmp/file3.vcf", "rb")
	# pool = tinys3.Pool(AWS_ACCESS_KEY, AWS_SECRET_KEY, tls=True)

	# r = pool.upload("file3.vcf", myfile, AWS_S3_BUCKET)
	# r.result()

	# message = client.messages.create(
	#     to="+14109033502", 
	#     from_="+14123243487",
	#     body="This is John Doe!",
	#     media_url="https://s3.amazonaws.com/carbonhackathon-quircl/file3.vcf")

	return jsonify({'test': "hello"}), 200


def req_err(message):
	response = jsonify({ "success": False, "data": message })
	response.status_code = 400
	return response

def create_vcard_str(fname, lname, numbers):
	result = "BEGIN:VCARD\nN:" + lname + ";" + fname + ";;;\n"
	for number in numbers:
		result += "TEL;" + number["type"].upper() + ":+1" + number["num"] + "\n"
	return result + "END:VCARD"

def convert_phone_number(number):
	result = ""
	for i in range(10):
		result += number[i]
		if i == 2 or i == 5:
			result += "-"
	return result

def url_shortener(url):
	shortener = Shortener("Isgd")
	return shortener.short(url)


if __name__ == '__main__':
	app.run(debug=True)
