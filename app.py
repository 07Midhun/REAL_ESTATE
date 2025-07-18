from flask import Flask, render_template, request, redirect, url_for, flash,session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
 

app = Flask(__name__)
app.secret_key = 'your_secret_key'  
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

client = MongoClient('mongodb://localhost:27017/realestate_db')
db = client['realestate_db'] 
users_collection = db['users']  
listings_collection = db['listings']  


def get_user_by_username(username):
    user = db.users.find_one({"username": username})
    return user

def get_user_by_email(email):
    user = db.users.find_one({"email": email})
    return user



def add_user(username, email, password):
    user_data = {
        "username": username,
        "email": email,
        "password": password  
    }
    db.users.insert_one(user_data)


@app.route('/')
def index():
    return redirect(url_for('signup')) 


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)  

        if user and user['password'] == password:
            session['username'] = user['username']  
            return redirect(url_for('dashboard'))  
        else:
            flash('Invalid credentials. Please try again.')  
    return render_template('login.html')  


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        add_user(username, email, password) 
        session['username'] = username  
        return redirect(url_for('dashboard'))  
    return render_template('signup.html')  


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = users_collection.find_one({'email': email})

        if user:
            flash('Password reset instructions sent to your email.')
        else:
            flash('Email not found.')

    return render_template('forgot_password.html') 


@app.route('/profile')
def profile():
    if 'username' in session:  
        user = get_user_by_username(session['username'])
        
        user_listings = listings_collection.find({'username': session['username']})

        return render_template('index.html', user=user, listings=user_listings)
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'username' in session: 
        user = get_user_by_username(session['username'])  
        return render_template('index.html', user=user) 
    return redirect(url_for('login'))    

    return render_template3669('index.html', user=user) 

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if 'username' not in session:  
        flash('Please log in to create a listing.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        location = request.form.get('location')
        property_type = request.form.get('property_type')

        
        image = request.files.get('image')
        image_url = None  

        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"/{app.config['UPLOAD_FOLDER']}{filename}"

        if not title or not description or not price or not location or not property_type:
            flash('All fields are required!')
            return redirect(url_for('sell'))

        listings_collection.insert_one({
            'title': title,
            'description': description,
            'price': float(price),  
            'location': location,
            'property_type': property_type,
            'image_url': image_url,
            'username': session['username']  
        })

        flash('Listing added successfully!')
        return redirect(url_for('dashboard'))

    return render_template('add_listing.html')  

@app.route('/listings')
def view_listings():
    listings = [
        {
            "title": "Sample Land",
            "description": "Beautiful land available.",
            "price": "$100,000",
            "location": "City Center",
            "image_url": "static/images/land.jpg" 
        },
    ]
    
    return render_template('view_listing.html', listings=listings)


@app.route('/buy')
def buy():
    try:
        listings = list(listings_collection.find())  
        print("Retrieved listings:", listings)  
        return render_template('view_listing.html', listings=listings) 
    except Exception as e:
        print(f"Error retrieving listings: {e}")
        flash('An error occurred while retrieving listings.')
        return redirect(url_for('dashboard')) 
@app.route('/land')
def land():
    return render_template('buy_sell.html', property_type="Land")

@app.route('/house')
def house():
    return render_template('buy_sell.html', property_type="House")

@app.route('/flat')
def flat():
    return render_template('buy_sell.html', property_type="Flat")
@app.route('/buy_land')
def buy_land():
    try:
        
        listings = list(listings_collection.find({'property_type': 'Land'}))
        return render_template('view_listing.html', listings=listings)
    except Exception as e:
        print(f"Error retrieving land listings: {e}")
        flash('An error occurred while retrieving land listings.')
        return redirect(url_for('dashboard'))


@app.route('/buy_house')
def buy_house():
    try:
        listings = list(listings_collection.find({'property_type': 'House'}))
        return render_template('view_listing.html', listings=listings)
    except Exception as e:
        print(f"Error retrieving house listings: {e}")
        flash('An error occurred while retrieving house listings.')
        return redirect(url_for('dashboard'))

@app.route('/buy_flat')
def buy_flat():
    try:
        listings = list(listings_collection.find({'property_type': 'Flat'}))
        return render_template('view_listing.html', listings=listings)
    except Exception as e:
        print(f"Error retrieving flat listings: {e}")
        flash('An error occurred while retrieving flat listings.')
        return redirect(url_for('dashboard'))
    
@app.route('/delete_land', methods=['GET', 'POST'])
def delete_land():
    try:
        # Show all land listings with a delete button
        listings = list(listings_collection.find({'property_type': 'Land'}))
        
        if request.method == 'POST':
            
            listing_id = request.form.get('listing_id')
            if listing_id:
                listings_collection.delete_one({'_id': ObjectId(listing_id)})
                flash('Land listing deleted successfully.')
                return redirect(url_for('delete_land'))

        return render_template('delete_listing.html', listings=listings)
    except Exception as e:
        print(f"Error retrieving land listings for deletion: {e}")
        flash('An error occurred while retrieving land listings for deletion.')
        return redirect(url_for('dashboard'))


@app.route('/delete_house', methods=['GET', 'POST'])
def delete_house():
    try:
        listings = list(listings_collection.find({'property_type': 'House'}))
        
        if request.method == 'POST':
            listing_id = request.form.get('listing_id')
            if listing_id:
                listings_collection.delete_one({'_id': ObjectId(listing_id)})
                flash('House listing deleted successfully.')
                return redirect(url_for('delete_house'))

        return render_template('delete_listing.html', listings=listings, property_type="House")
    except Exception as e:
        print(f"Error retrieving house listings for deletion: {e}")
        flash('An error occurred while retrieving house listings for deletion.')
        return redirect(url_for('dashboard'))

@app.route('/delete_flat', methods=['GET', 'POST'])
def delete_flat():
    try:
        listings = list(listings_collection.find({'property_type': 'Flat'}))
        
        if request.method == 'POST':
            listing_id = request.form.get('listing_id')
            if listing_id:
                listings_collection.delete_one({'_id': ObjectId(listing_id)})
                flash('Flat listing deleted successfully.')
                return redirect(url_for('delete_flat'))

        return render_template('delete_listing.html', listings=listings, property_type="Flat")
    except Exception as e:
        print(f"Error retrieving flat listings for deletion: {e}")
        flash('An error occurred while retrieving flat listings for deletion.')
        return redirect(url_for('dashboard'))


if __name__ == "__main__":
    app.run(debug=True)