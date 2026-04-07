from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

client = MongoClient('mongodb://localhost:27017/')
db = client['realestate_db']
users_collection = db['users']
listings_collection = db['listings']
reviews_collection = db['reviews']

# --- Helper Functions ---
def get_user_by_username(username):
    return users_collection.find_one({"username": username})

def get_user_by_email(email):
    return users_collection.find_one({"email": email})

def add_user(username, email, password, phone=None, address=None):
    if get_user_by_username(username):
        return "Username already exists."
    if get_user_by_email(email):
        return "Email already exists."
    users_collection.insert_one({
        "username": username,
        "email": email,
        "password": password,
        "phone": phone,
        "address": address,
        "is_admin": False
    })
    return "Success"

# --- Routes ---
@app.route('/')
def index():
    return redirect(url_for('signup'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)
        if user and user['password'] == password:
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        result = add_user(username, email, password, phone, address)
        if result != "Success":
            flash(result)
            return redirect(url_for('signup'))
        session['username'] = username
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        if get_user_by_email(email):
            flash('Password reset link sent to your email.')
        else:
            flash('Email not found.')
    return render_template('forgot_password.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = get_user_by_username(session['username'])
    listings = list(listings_collection.find({'username': user['username']}))

    return render_template('index.html', user=user, listings=listings,
                           total=listings_collection.count_documents({}),
                           land_count=listings_collection.count_documents({'property_type': 'Land'}),
                           house_count=listings_collection.count_documents({'property_type': 'House'}),
                           flat_count=listings_collection.count_documents({'property_type': 'Flat'}))

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        location = request.form['location']
        property_type = request.form['property_type']
        contact_phone = request.form.get('contact_phone', '')
        contact_email = request.form.get('contact_email', '')
        contact_address = request.form.get('contact_address', '')
        image = request.files.get('image')

        if not all([title, description, price, location, property_type]):
            flash("All fields are required!")
            return redirect(url_for('sell'))

        image_url = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(path)
            image_url = f"/{path}"

        listings_collection.insert_one({
            'title': title,
            'description': description,
            'price': float(price),
            'location': location,
            'property_type': property_type.capitalize(),
            'image_url': image_url,
            'username': session['username'],
            'contact_phone': contact_phone,
            'contact_email': contact_email,
            'contact_address': contact_address,
            'created_at': datetime.now()
        })

        flash("Listing added successfully!")
        return redirect(url_for('dashboard'))

    return render_template('add_listing.html')

@app.route('/buy_<property>')
def buy_property(property):
    try:
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        location = request.args.get('location')
        sort_order = request.args.get('sort', 'asc')

        query = {'property_type': property.capitalize()}
        if min_price is not None:
            query['price'] = {'$gte': min_price}
        if max_price is not None:
            query.setdefault('price', {})['$lte'] = max_price
        if location:
            query['location'] = location

        sort = [('price', 1)] if sort_order == 'asc' else [('price', -1)]
        listings = list(listings_collection.find(query).sort(sort))

        locations = listings_collection.distinct('location')

        return render_template('view_listing.html', listings=listings,
                               locations=locations,
                               selected_location=location,
                               property_type=property.capitalize())
    except Exception as e:
        flash(f"Error loading {property} listings: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/listing/<listing_id>', methods=['GET', 'POST'])
def view_listing_details(listing_id):
    listing = listings_collection.find_one({'_id': ObjectId(listing_id)})
    if not listing:
        flash("Listing not found.")
        return redirect(url_for('dashboard'))

    user = get_user_by_username(session['username']) if 'username' in session else None

    if request.method == 'POST':
        if not user:
            flash("Login to post a review.")
            return redirect(url_for('login'))

        rating = int(request.form['rating'])
        comment = request.form['comment']

        reviews_collection.insert_one({
            'listing_id': listing_id,
            'username': user['username'],
            'rating': rating,
            'comment': comment,
            'timestamp': datetime.now()
        })
        flash("Review submitted.")

    reviews = list(reviews_collection.find({'listing_id': listing_id}))
    return render_template('listing_details.html', listing=listing, reviews=reviews, user=user)

@app.route('/listing/<listing_id>/contact')
def contact_owner(listing_id):
    listing = listings_collection.find_one({'_id': ObjectId(listing_id)})
    if not listing:
        flash("Listing not found.")
        return redirect(url_for('dashboard'))
    
    return render_template('contact_owner.html', listing=listing)

@app.route('/delete_<property>', methods=['GET', 'POST'])
def delete_property(property):
    try:
        listings = list(listings_collection.find({'property_type': property.capitalize()}))
        if request.method == 'POST':
            listing_id = request.form.get('listing_id')
            if listing_id:
                listings_collection.delete_one({'_id': ObjectId(listing_id)})
                flash(f"{property.capitalize()} listing deleted.")
                return redirect(url_for('delete_property', property=property))
        return render_template('delete_listing.html', listings=listings, property_type=property.capitalize())
    except Exception as e:
        flash(f"Error deleting {property} listings: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/property/<property_type>')
def property_page(property_type):
    if 'username' not in session:
        return redirect(url_for('login'))
    user = get_user_by_username(session['username'])
    return render_template('buy_sell.html', property_type=property_type.capitalize(), user=user)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = get_user_by_username(session['username'])
    if not user.get('is_admin', False):
        flash("Unauthorized access.")
        return redirect(url_for('dashboard'))

    users = list(users_collection.find())
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/user/<username>/listings')
def view_user_listings(username):
    if 'username' not in session:
        return redirect(url_for('login'))
    current_user = get_user_by_username(session['username'])
    if not current_user.get('is_admin', False):
        flash("Unauthorized access.")
        return redirect(url_for('dashboard'))

    user = get_user_by_username(username)
    if not user:
        flash("User not found.")
        return redirect(url_for('admin_dashboard'))

    listings = list(listings_collection.find({'username': username}))
    return render_template('view_user_listings.html', user=user, listings=listings)

@app.route('/admin/browse_properties')
def admin_browse_properties():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_username(session['username'])
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    property_type = request.args.get('property_type', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    location = request.args.get('location', '')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Build query
    query = {}
    if property_type:
        query['property_type'] = property_type
    if min_price is not None:
        query['price'] = {'$gte': min_price}
    if max_price is not None:
        if 'price' in query:
            query['price']['$lte'] = max_price
        else:
            query['price'] = {'$lte': max_price}
    if location:
        query['location'] = {'$regex': location, '$options': 'i'}
    
    # Sort options
    sort_direction = -1 if sort_order == 'desc' else 1
    sort_criteria = [(sort_by, sort_direction)]
    
    # Get all listings with filters
    listings = list(listings_collection.find(query).sort(sort_criteria))
    
    # Get unique values for filters
    property_types = listings_collection.distinct('property_type')
    locations = listings_collection.distinct('location')
    
    # Calculate statistics
    total_listings = len(listings)
    total_value = sum(listing.get('price', 0) for listing in listings)
    avg_price = total_value / total_listings if total_listings > 0 else 0
    
    return render_template('admin_browse_properties.html', 
                         listings=listings,
                         property_types=property_types,
                         locations=locations,
                         filters={
                             'property_type': property_type,
                             'min_price': min_price,
                             'max_price': max_price,
                             'location': location,
                             'sort_by': sort_by,
                             'sort_order': sort_order
                         },
                         stats={
                             'total_listings': total_listings,
                             'total_value': total_value,
                             'avg_price': avg_price
                         })

@app.route('/promote/<username>', methods=['POST'])
def promote_user(username):
    users_collection.update_one({'username': username}, {'$set': {'is_admin': True}})
    flash(f"{username} promoted to admin.")
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_user/<username>', methods=['POST'])
def delete_user(username):
    users_collection.delete_one({'username': username})
    flash(f"User {username} deleted.")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_username(session['username'])
    if not user:
        flash("User not found.")
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', user.get('email', ''))
        phone = request.form.get('phone', user.get('phone', ''))
        address = request.form.get('address', user.get('address', ''))
        
        # Update user information
        users_collection.update_one(
            {'username': user['username']},
            {
                '$set': {
                    'email': email,
                    'phone': phone,
                    'address': address
                }
            }
        )
        
        flash("Profile updated successfully!")
        return redirect(url_for('dashboard'))
    
    return render_template('edit_profile.html', user=user)

@app.route('/buy_property_payment/<listing_id>')
def buy_property_payment(listing_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    listing = listings_collection.find_one({'_id': ObjectId(listing_id)})
    if not listing:
        flash("Property not found.")
        return redirect(url_for('dashboard'))
    
    user = get_user_by_username(session['username'])
    return render_template('buy_payment.html', listing=listing, user=user)

@app.route('/process_payment/<listing_id>', methods=['POST'])
def process_payment(listing_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    listing = listings_collection.find_one({'_id': ObjectId(listing_id)})
    if not listing:
        flash("Property not found.")
        return redirect(url_for('dashboard'))
    
    payment_method = request.form.get('payment_method')
    amount = request.form.get('amount')
    
    # Here you would integrate with actual payment gateways
    # For now, we'll simulate a successful payment
    payment_successful = True
    
    if payment_successful:
        # Create a payment record
        payment_data = {
            'listing_id': listing_id,
            'buyer_username': session['username'],
            'seller_username': listing['username'],
            'amount': float(amount),
            'payment_method': payment_method,
            'status': 'completed',
            'timestamp': datetime.now()
        }
        
        # You can create a payments collection to store payment records
        # db['payments'].insert_one(payment_data)
        
        flash(f"Payment successful! You have purchased {listing['title']}")
        return redirect(url_for('dashboard'))
    else:
        flash("Payment failed. Please try again.")
        return redirect(url_for('buy_property_payment', listing_id=listing_id))

if __name__ == '__main__':
    app.run(debug=True)
