import pyrebase

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

db.child("users").push(u1, id)
db.child("users").push(u2, id)
db.child("users").push(u3, id)
 
