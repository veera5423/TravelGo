from flask import jsonify

from datetime import datetime
from flask import Flask,render_template, request, redirect, url_for, flash,session
from pymongo import MongoClient, errors,ASCENDING
from bson import ObjectId
import json
from dotenv import load_dotenv
import os
 

load_dotenv()  # Load variables from .env

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
mongo_uri = os.getenv("MONGO_URI")  # Needed for flash messages

# Connect to MongoDB

try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)  
    
    client.admin.command('ping')
    print("MongoDB connection successful!")
except errors.ServerSelectionTimeoutError as err:
    print("MongoDB connection failed:", err)
db = client['TravelGo']  # Db name
users_collection = db['users']  
reviews_collection = db['reviews']
trips_collection = db['trips'] 
hotels_collection=db['hotels']
bookings=db['bookings']


@app.route("/")
def home():
  return render_template('home.html')
# @app.route("/dashboard")
# def dashboard():
#    return render_template('dashboard.html')
@app.route("/dashboard")
def dashboard():
    reviews = list(reviews_collection.find().sort("_id", -1).limit(5))
    user = None
    if 'username' in session:
        user = users_collection.find_one({'username': session['username']})
    return render_template('dashboard.html', reviews=reviews, user=user)
        
#Forgot password
@app.route("/forgotpassword")    
def forgotpassword():
    return render_template("forgotpassword.html")    
        

# todo chage validation 
@app.route("/sign-in",methods=["GET","POST"])
def signin():
   if request.method == "POST":
      username=request.form.get("username")
      password=request.form.get("password")
      
      #Find user in dbuser
      user=users_collection.find_one({"username":username})

      if user and user["password"]==password:
         session['username']=username
         flash("Login Successfull!","sucess")
         return redirect(url_for("dashboard"))
      else:
         flash("Invalid Credentials.","error")
         return redirect(url_for("signin"))
   return render_template('login.html')

@app.route("/sign-up", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        # You should hash the password in production!
        if users_collection.find_one({"email":email}):
            flash("Email already exits ")
            return redirect(url_for("signup"))

        # Insert into MongoDB
        users_collection.insert_one({
            "username": username,
            "email": email,
            "phone": phone,
            "password": password
        })
        flash("Registration successful!", "success")
        return redirect(url_for("signin"))
    return render_template('register.html')
@app.route("/about")
def about():
   return render_template('about.html')


@app.route("/submit_review", methods=["POST"])
def submit_review():
    if 'username' not in session:
        flash("You must be logged in to submit a review.", "error")
        return redirect(url_for("signin"))

    name = session['username']
    rating = int(request.form.get('rating', 0))
    comment = request.form.get('comment', '').strip()

    if rating < 1 or rating > 5 or not comment:
        flash("Please provide valid rating and comment.", "error")
        return redirect(url_for("dashboard"))

    review_doc = {
        "name": name,
        "rating": rating,
        "comment": comment,
        "timestamp": datetime.utcnow()
    }
    reviews_collection.insert_one(review_doc)
    flash("Review submitted successfully!", "success")
    return redirect(url_for("dashboard"))


# Booking Routes
@app.route("/book-train")
def book_train():
    return render_template("book_train.html")  

@app.route("/book-cab")
def book_cab():
    return render_template("book_cabtest.html")  

@app.route("/book-bus")
def book_bus():
    # return render_template("book_bus.html") 
    return render_template("book_bustest.html") 


@app.route("/book-flight")
def book_flight():
    return render_template("book_flight.html")

@app.route("/book-hotel",methods=["GET"])
def book_hotel():
    return render_template("book_hoteltest.html")  
@app.route("/booking-history")
def bookingHistory():
    return render_template("booking_history.html")



import re

@app.route('/search-trips', methods=['POST','GET'])
def search_trips():
    from_location = request.form.get("from", "").strip()
    to_location = request.form.get("to", "").strip()
    date = request.form.get("date", "")
    # cab_type = request.form.get("cab_type", "").strip()
    class_type = request.form.get("classType", "").strip()
    sort_by = request.form.get('sortBy').strip()
    time = request.form.get("time", "").strip()
    # passengers = request.form.get("passengers", "").strip()  # Optional

    # Convert date to match stored format if needed
    try:
        search_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify([])

    query = {
        "from": {"$regex": f"^{re.escape(from_location)}$", "$options": "i"},
        "to": {"$regex": f"^{re.escape(to_location)}$", "$options": "i"},
        "date": date
    }
    if class_type:
        query["class_type"] = {"$regex": f"^{re.escape(class_type)}$", "$options": "i"}
    if time:
        query["time"] = time
    # if passengers:
    #     query["passengers"] = int(passengers)

    trips = list(trips_collection.find(query, {"_id": 0}))

    return jsonify(trips)


#search cabs
@app.route('/search-cabs', methods=['POST'])
def search_cabs():
    from_location = request.form.get("from", "").strip()
    to_location = request.form.get("to", "").strip()
    date = request.form.get("date", "").strip()
    time = request.form.get("time", "").strip()
    passengers = request.form.get("passengers", "").strip()
    

    try:
        search_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify([])

    query = {
        "type": "cab",
        "from": {"$regex": f"^{re.escape(from_location)}$", "$options": "i"},
        "to": {"$regex": f"^{re.escape(to_location)}$", "$options": "i"},
        "date": date
    }

    if time:
        query["time"] = time
    if passengers:
        try:
            query["available_seats"] = {"$gte": int(passengers)}
        except ValueError:
            pass  # ignore invalid input

    trips = list(trips_collection.find(query, {"_id": 0}))
    for trip in trips:
        trip["passengerscount"] = int(passengers) if passengers.isdigit() else 1
    return jsonify(trips)




#Search trains


@app.route('/search-trains', methods=['POST'])
def search_trains():
    from_location = request.form.get("from", "").strip()
    to_location = request.form.get("to", "").strip()
    date = request.form.get("date", "").strip()
    train_class = request.form.get("class", "").strip()

    # Validate and format date
    try:
        datetime.strptime(date, "%Y-%m-%d")  # Validates format
    except ValueError:
        return jsonify([])  # Return empty if date is invalid

    # Query construction
    query = {
        "from": {"$regex": f"^{re.escape(from_location)}$", "$options": "i"},
        "to": {"$regex": f"^{re.escape(to_location)}$", "$options": "i"},
        "date": date
    }

    if train_class:
        query["class"] = {"$regex": f"^{re.escape(train_class)}$", "$options": "i"}

    # Fetch results
    trains = list(trips_collection.find(query, {"_id": 0}))

    return jsonify(trains)


# Search hotels
@app.route("/get-hotels",methods=['POST'])
def gethotels():
    city=request.form.get("city","").strip()
    checkin=request.form.get("checkin")
    checkout=request.form.get("checkout")
    room_type=request.form.get("room_type")
    guests=request.form.get("guests")
    # query = {
    #     "city": {"$regex": f"^{re.escape(city)}$", "$options": "i"},
    #     "available_from": {"$lte": checkin},
    #     "available_to": {"$gte": checkout},
    #     "room_type":{"$regex":f"^{re.escape(room_type)}$","$options":"i"},
    #     "guests":guests,
    # }
    query = {
    "city": {"$regex": f"^{re.escape(city)}$", "$options": "i"},
    "room_type": {"$regex": f"^{re.escape(room_type)}$", "$options": "i"},
    "available_from": {"$lte": checkin},
    "available_to": {"$gte": checkout}
    }
    try:
        guests = int(guests)
        query["max_guests"] = {"$gte": guests}
    except ValueError:
        pass  # Ignore if guests not a number


    hotels=list(hotels_collection.find(query,{"_id":0}))
    return jsonify(hotels)
  
  
  #Search Flights


@app.route('/search-flights', methods=['POST'])
def search_flights():
    from_location = request.form.get("from", "").strip()
    to_location = request.form.get("to", "").strip()
    date = request.form.get("date", "").strip()
    flight_class = request.form.get("class", "").strip()

    # Validate date
    try:
        search_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify([])

    # Build query
    query = {
        "from": {"$regex": f"^{re.escape(from_location)}$", "$options": "i"},
        "to": {"$regex": f"^{re.escape(to_location)}$", "$options": "i"},
        "date": date
    }

    if flight_class:
        query["class"] = {"$regex": f"^{re.escape(flight_class)}$", "$options": "i"}

    # Fetch matching flights
    flights = list(trips_collection.find(query, {"_id": 0}))

    return jsonify(flights)


# Paste the JSON array here



# # submitbooking
# @app.route('/submit-booking', methods=['POST'])
# def submit_booking():
#     if 'username' not in session:
#         return jsonify({"error": "User not logged in"}), 401

#     data = request.get_json()
#     if (data.get("type")!="hotel"):
#         name = data.get('bus_name')
#         from_location = data.get('from')
#         to_location = data.get('to')
#         date = data.get('date')
#         departure = data.get('departure')
#         arrival = data.get('arrival')
#         price = data.get('price')
#         selected_seats_or_rooms = data.get('selected_seats')
#         gender = data.get('gender')
#     else:
#         name=data.get("name")
#         from_location = ""
#         to_location = ""
#         departure = data.get('departure')
#         arrival = data.get('arrival')
#         price = data.get('price')
#         selected_seats_or_rooms = data.get('selected_seats-or-rooms')
#         gender = data.get('gender')
#         date = data.get('date')


#     # if not all([name, from_location, to_location, date, departure, arrival, price, selected_seats, gender]):
#     #     return jsonify({"error": "Missing booking information"}), 400

#     booking_doc = {
#         "username": session['username'],
#         "name": name,
#         "from": from_location,
#         "to": to_location,
#         "date": date,
#         "departure": departure,
#         "arrival": arrival,
#         "price": price,
#         "selected_seats_or_rooms": selected_seats_or_rooms,
#         "gender": gender,
#         "booking_time": datetime.utcnow()
#     }
#     booking_doc1 = {
#         "username": session['username'],
#         "name": name,
#         "from": from_location,
#         "to": to_location,
#         "date": date,
#         "departure": departure,
#         "arrival": arrival,
#         "price": price,
#         "selected_seats_or_rooms": selected_seats_or_rooms,
#         "gender": gender,
#         # "booking_time": datetime.utcnow()
#     }
    

#     booking_data = booking_doc1.copy()
#     date_value = booking_data["date"]
#     if isinstance(date_value, datetime):
#         booking_data["date"] = date_value.strftime("%Y-%m-%d")

#     try:
#         # db.bookings.insert_one(booking_doc)
#         session['pending_booking'] = json.dumps(booking_data)
#         return redirect(url_for('payment'))
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/all-trips', methods=['GET'])
# def all_trips():
#     trips = list(trips_collection.find({}, {"_id": 0}))

#     return jsonify(trips)






@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('signin'))

@app.route('/user-bookings', methods=['GET'])
def user_bookings():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    username = session['username']
    today = datetime.utcnow().date()
    bookings = list(db.bookings.find({'username': username}))
   
    current = []
    previous = []
    for b in bookings:
        try:
            trip_date = datetime.strptime(b['date'], '%Y-%m-%d').date()
        except Exception:
            trip_date = today
        b['_id'] = str(b['_id'])
        if trip_date >= today:
            current.append(b)
        else:
            previous.append(b)
        
    return jsonify({'current': current, 'previous': previous})

@app.route('/cancel-booking', methods=['POST'])
def cancel_booking():
    if 'username' not in session:
        return jsonify({'error': 'User not logged in'}), 401
    data = request.get_json()
    booking_id = data.get('booking_id')
    if not booking_id:
        return jsonify({'error': 'Missing booking_id'}), 400
    booking = db.bookings.find_one({'_id': ObjectId(booking_id), 'username': session['username']})
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    db.bookings.delete_one({'_id': ObjectId(booking_id)})
    return jsonify({'message': 'Booking cancelled successfully'})

@app.route('/prepayment', methods=['POST'])
def prepayment():
    if 'username' not in session:
        return jsonify({'error': 'You must be logged in to book.'}), 401

    if not request.is_json:
        return jsonify({'error': 'Expected JSON data.'}), 400

    booking = request.get_json()
    # Validate necessary fields
    # required = ['name', 'arrival', 'departure', 'price', 'selected_seats_or_rooms']
    # if not all(k in booking for k in required):
    #     return jsonify({'error': 'Missing booking data.'}), 400
    if not booking:
        return jsonify({'error': 'Invalid booking data'}), 400
    print(booking)

    # Store booking in session temporarily
    # print(booking)
    # print("json booking:",booking)

    session['pending_booking'] = json.dumps(booking)
    return jsonify({'redirect': url_for('payment')})



@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'username' not in session:
        flash('You must be logged in to make a payment.', 'error')
        return redirect(url_for('signin'))

    if request.method == 'GET':
        # Get pending booking from session
        booking_data = session.get('pending_booking')
        if not booking_data:
            flash('No booking found to process.', 'error')
            return redirect(url_for('dashboard'))

        try:
            booking = json.loads(booking_data)
        except:
            flash('Invalid booking data.', 'error')
            return redirect(url_for('dashboard'))

        return render_template('payment.html', booking_data=booking)

    # POST: Process payment form
    card_number = request.form.get('card_number')
    expiry = request.form.get('expiry')
    cvv = request.form.get('cvv')

    if not (card_number and expiry and cvv):
        flash('Please fill in all payment fields.', 'error')
        return redirect(url_for('payment'))

    try:
        booking_data = session.get('pending_booking')
        booking = json.loads(booking_data)
    except:
        flash('Booking data error.', 'error')
        return redirect(url_for('dashboard'))

    # Add payment + user info
    booking['username'] = session['username']
    booking['booking_time'] = datetime.utcnow()
    booking['payment'] = {
        'card_number': f'**** **** **** {card_number[-4:]}',
        'expiry': expiry
    }

    try:
        db.bookings.insert_one(booking)
        session.pop('pending_booking', None)
        flash('Payment successful! Booking confirmed.', 'success')
        return redirect(url_for('bookingHistory'))
    except Exception as e:
        flash('Error saving booking: ' + str(e), 'error')
        return redirect(url_for('dashboard'))



# @app.route('/payment', methods=['GET', 'POST'])
# def payment():
#     if 'username' not in session:
#         flash('You must be logged in to make a payment.', 'error')
#         return redirect(url_for('signin'))

#     if request.method == 'GET':
#         # Booking data should be passed as query param or session
#         booking_data = request.args.get('booking_data')
#         if not booking_data:
#             booking_data = session.get('pending_booking')
#         else:
#             session['pending_booking'] = booking_data

#         # If booking_data is a string, parse it to dict
#         booking_dict = {}
#         if booking_data:
#             try:
#                 booking_dict = json.loads(booking_data)
#             except Exception:
#                 booking_dict = {}
#         # return render_template('payment.html', booking_data=booking_dict)
#         return jsonify({'status': 'success', 'redirect': url_for('bookingHistory')})


#     # POST: process payment and booking
#     card_number = request.form.get('card_number')
#     expiry = request.form.get('expiry')
#     cvv = request.form.get('cvv')
#     booking_data = request.form.get('booking_data')
#     if not (card_number and expiry and cvv and booking_data):
#         flash('Missing payment or booking information.', 'error')
#         return redirect(url_for('payment'))

#     # Here you would integrate with a payment gateway. We'll mock success.
#     # try:
#     #     booking = booking_data if isinstance(booking_data, dict) else json.loads(booking_data)
#     # except Exception:
#     #     flash('Invalid booking data.', 'error')
#     #     return redirect(url_for('dashboard'))

#     # Add username and booking time
#     # booking = booking_data if isinstance
#     try:
#         booking = json.loads(booking_data)
#     except Exception:
#         flash('Invalid booking data.', 'error')
#         return redirect(url_for('payment'))

#     booking=booking_data
#     booking['username'] = session['username']
#     booking['booking_time'] = datetime.utcnow()
#     try:
#         db.bookings.insert_one(booking)
#         session.pop('pending_booking', None)
#         flash('Payment successful! Booking confirmed.', 'success')
#         return redirect(url_for('bookingHistory'))
#     except Exception as e:
#         flash('Booking failed: ' + str(e), 'error')
#         return redirect(url_for('dashboard'))
    

if __name__ == '__main__':
    app.run(debug=True)
