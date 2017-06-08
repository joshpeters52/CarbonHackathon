import pyrebase
from math import radians, sin, cos, atan2, sqrt

def calc_dist(lat1, lon1, lat2, lon2):
	dlon = radians(lon2 - lon1)
	dlat = radians(lat2 - lat1)

	lat1 = radians(lat1)
	lat2 = radians(lat2)	

	a = (sin(dlat/2))**2 + cos(lat1) * cos(lat2) * (sin(dlon/2))**2 
	c = 2 * atan2( sqrt(a), sqrt(1-a) )
	return c * 3961 * 5280	

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

id = user['idToken']

u1 = { "lat": 51.5033640, "lon": -0.1276250, "name": "Derek" }
u2 = { "lat": 51.5034640, "lon": -0.1276250, "name": "Joe" }
u3 = { "lat": 51.504, "lon": -0.1276250, "name": "Bob" }

# db.child("users").child("Derek").set(u1, id)
# db.child("users").child("Joe").set(u2, id)
# db.child("users").child("Bob").set(u3, id)
 
user1 = db.child("users").child("Jeff").get(id).val()
user2 = db.child("users").child("Derek").get(id).val()

print user1 is None
print user2 is None

# users = db.child("users").get(id).val()


# for i in users:
# 	u = users[i]
# 	n = u["name"]
# 	lat = u["lat"]
# 	lon = u["lon"]

# 	for j in users:
# 		if users[j]["name"] is n:
# 			continue
# 		nxt_lat = users[j]["lat"]
# 		nxt_lon = users[j]["lon"]
# 		d = calc_dist(lat, lon,  nxt_lat, nxt_lon)
# 		print d

