from dotenv import load_dotenv
import os
import base64
import requests
from flask import Flask, request, render_template, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import re
from datetime import date, datetime
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_principal import Permission, RoleNeed, identity_loaded, UserNeed

from envc import ADMIN_USERNAME, ADMIN_PASSWORD,ADMIN_EMAIL, DATABASE_URI, SECRET_KEY, User

from flask import Flask, render_template, flash, redirect, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView



app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLAlchemy_TRACK_MODIFICATION'] = False
db = SQLAlchemy(app)
admin = Admin()

# app.config['SECRET_KEY'] = 'your_generated_secret_key_here'  # For development
# OR for production, more securely:
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'fallback_secret_key')

migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

load_dotenv()  # This loads the environment variables from .env file




print("Database:", DATABASE_URI)



# Create admin page

# @login_required 
@app.route('/admin')
def admin():
    # id = current_user.id
    # if id == 1:
    users = db.session.execute(db.select(User)).scalars()
    print(users)
    return render_template('admin/admin_panel.html', users=users)
    # else:
    #     flash('sorry you must be the admin to access the admin page...')
    #     return redirect(url_for('dashboard'))

@app.route('/add_user_from_admin')
def add_user():
    return render_template('admin/add_user.html')



@app.route('/admin/edit_user')
def edit_user():

    return render_template('admin_panel.html')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:
        return f'{self.id} - {self.username}'    

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        # Here you could also add logic to check if the user's account is disabled
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
   

    


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    contact_name = db.Column(db.String)
    address = db.Column(db.String)
    phone = db.Column(db.String)
    email = db.Column(db.String)
    balance = db.Column(db.String)


class BillingEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_company_id = db.Column(db.Integer, db.ForeignKey('company.id'))    
    client_company = db.relationship('Company', backref='billing_entries')
    contact_name = db.Column(db.String)
#     client_company_name = db.Column(db.String)
    hours = db.Column(db.String)
    amount = db.Column(db.String)
    description = db.Column(db.String)
    entry_date = db.Column(db.String)
    payment_status = db.Column(db.String)
    follow_up_date = db.Column(db.String)


    
# Create the tables in the database (usually in a separate script)
with app.app_context():
    db.create_all()
    

admin_permission = Permission(RoleNeed('admin'))



@app.route('/print_columns')
def print_columns():
    column_names = [column.name for column in BillingEntry.__table__.columns]
    return ', '.join(column_names)

    
def get_line(lines, index, default=''):
    if index < len(lines):
        parts = lines[index].split(': ')
        if len(parts) > 1:
            return parts[1]
    return default

@app.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        # Render the HTML file for the user interface
        print(current_user.is_authenticated)
        return render_template('index.html')
    else:
        # Redirect to login page if not authenticated
        return redirect(url_for('login'))


@app.route('/upload', methods=['POST'])
@login_required
def upload_image():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        # Convert the image to base64
        base64_image = base64.b64encode(file.read()).decode('utf-8')
        
        # OpenAI API Key
        api_key = SECRET_KEY  

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": "gpt-4-vision-preview",  # Replace with the actual model name
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
#                             "text": "Read the text in this image."
                            "text": "What does each line say? Only list the content. Do not include 'Bill to'."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

       
        
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        extracted_text = response.json()['choices'][0]['message']['content']

#         # Split the text by lines and organize it into a dictionary
        lines = extracted_text.splitlines()



        entry_data = {
            'contact_name': get_line(lines, 0),
            'client_company_name': get_line(lines, 1),
            'address': get_line(lines, 2),
            'phone': get_line(lines, 3),
            'email': get_line(lines, 4),
            'hours': get_line(lines, 5),  # Default to '0' if not present
            'description': get_line(lines, 6),
            'entry_date': get_line(lines, 7),  # Date parsing will be handled later
            'payment_status': get_line(lines, 8),
            'follow_up_date':get_line(lines, 9)
        }
        
        companies = Company.query.all()
    
        return render_template('edit_extracted_text.html', entry_data=entry_data, companies=companies)




@app.route('/submit_entry', methods=['POST'])
@login_required
def submit_entry():
    new_company_name = request.form.get('new_company')
    existing_company_id = request.form.get('existing_company')

    if new_company_name:
        # Create a new Company with additional fields
        new_company = Company(
            name=new_company_name,
            address=request.form.get('address'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
        )
        db.session.add(new_company)
        db.session.commit()
        company_id = new_company.id
    elif existing_company_id:
        # Use the existing company ID
        company_id = existing_company_id
    else:
        # Handle the case where no company is provided
        return "No company selected", 400

    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Create a new BillingEntry
    new_entry = BillingEntry(
        contact_name=request.form['contact_name'],
        client_company_id=company_id,
        hours=request.form['hours'],
        description=request.form['description'],
#         entry_date=request.form.get('entry_date'),  # Ensure proper date format or handling
        entry_date = current_date,
        payment_status=request.form.get('payment_status'),  # Ensure this field exists in the form
        follow_up_date=request.form.get('follow_up_date')  # Ensure this is formatted correctly

    )
    db.session.add(new_entry)
    db.session.commit()

    return redirect(url_for('view_entries'))

  

@app.route('/edit_extracted_text', methods=['GET', 'POST'])
@login_required
def edit_extracted_text():
    if request.method == 'GET':
        extracted_text = request.args.get('extracted_text', '')
        return render_template('edit_extracted_text.html', extracted_text=extracted_text)
    elif request.method == 'POST':
        edited_text = request.form['edited_text']
        new_entry = BillingEntry(text=edited_text)
        db.session.add(new_entry)
        db.session.commit()
        return redirect(url_for('view_entries'))


@app.route('/save_text', methods=['POST'])
@login_required
def save_text():
    edited_text = request.form['text']
    new_entry = BillingEntry(text=edited_text)
    db.session.add(new_entry)
    db.session.commit()
    return redirect(url_for('view_entries'))


@app.route('/view_entries')
@login_required
def view_entries():
    all_entries = BillingEntry.query.all()  # Query all entries from the database
    return render_template('view_entries.html', entries=all_entries)



@app.route('/delete_entry/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    entry = BillingEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('view_entries'))

@app.route('/companies')
@login_required
def list_companies():
    companies = Company.query.order_by(Company.name).all()

    for company in companies:
        company.all_payments_yes = all(entry.payment_status == 'Yes' for entry in company.billing_entries)

        for entry in company.billing_entries:
            # Convert and format the entry_date
            if entry.entry_date:
                entry.formatted_entry_date = datetime.strptime(entry.entry_date, '%Y-%m-%d').strftime('%B %d, %Y')
            else:
                entry.formatted_entry_date = None

            # Convert and format the follow_up_date
            if entry.follow_up_date:
                entry.formatted_follow_up_date = datetime.strptime(entry.follow_up_date, '%Y-%m-%d').strftime('%B %d, %Y')
            else:
                entry.formatted_follow_up_date = None

    return render_template('companies.html', companies=companies)

@app.route('/calendar')
@login_required
def calendar():

    entries = BillingEntry.query.all()  # Assuming you want all entries
    events = []
    
    for entry in entries:
        formatted_follow_up_date = datetime.strptime(entry.follow_up_date, '%Y-%m-%d').strftime('%b %d, %Y')
        formatted_entry_date = datetime.strptime(entry.entry_date, '%Y-%m-%d').strftime('%b %d, %Y')

    for entry in entries:
        if entry.follow_up_date:
            events.append({
                    'title': entry.client_company.name,
                    'start': entry.follow_up_date,  # Ensure this is in YYYY-MM-DD format
                    'extendedProps': {
                    'contactName': entry.contact_name,
                    'entryDate': formatted_entry_date,
                    'hours': entry.hours,
                    'description': entry.description,
                    'paymentStatus': entry.payment_status,
                }
            })
    return render_template('calendar.html', events=events)

@app.route('/edit_billing_entry/<int:entry_id>', methods=['GET'])
@login_required
def edit_entry(entry_id):
    entry = BillingEntry.query.get_or_404(entry_id)  # Fetch the entry or return 404
    return render_template('edit_billing_entry.html', entry=entry)

@app.route('/update_entry/<int:entry_id>', methods=['POST'])
@login_required
def update_entry_by_id(entry_id):
    entry = BillingEntry.query.get_or_404(entry_id)
    entry.contact_name = request.form['contact_name']
    entry.hours = request.form['hours']
    entry.description = request.form['description']
    entry.entry_date = request.form['entry_date']
    entry.payment_status = request.form['payment_status']
    entry.follow_up_date = request.form['follow_up_date']
    db.session.commit()
    return redirect(url_for('view_entries')) 

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))  # Redirect to the main page after login

        # Handle login failure
        return "Invalid username or password", 401

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == "POST":
        _id = request.form.get('_id')
        username=request.form.get('username')
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.get(_id)
        user.username=username
        user.email=email
        
        user.set_password(password)
        db.session.commit()
    return render_template('profile.html')


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)  # Forbidden
    return render_template('admin/dashboard.html')

    
    
@app.route('/admin/manage-users')
@login_required
@admin_permission.require(http_exception=403)
def manage_users():
    print('create manage users')
    
    
@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user
    identity.user = current_user

    # Add the UserNeed to the identity
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))

    # Assuming `is_admin` is a boolean flag in your user model
    if current_user.is_admin:
        identity.provides.add(RoleNeed('admin'))




def create_admin_user():
    with app.app_context():
        admin_user = User.query.filter_by(username=ADMIN_USERNAME).first()
        if not admin_user:
            hashed_password = generate_password_hash(ADMIN_PASSWORD)
            new_admin = User(username=ADMIN_USERNAME, email=ADMIN_EMAIL, password_hash=hashed_password, is_admin=True)
            db.session.add(new_admin)
            db.session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")


def total_users_count():
    with app.app_context():
        total_users = User.query.count()
        print(f"Total number of users: {total_users}")
        
def list_users():
    with app.app_context():
        users = User.query.all()
        for user in users:
            print(f"Username: {user.username}, Email: {user.email}")



if __name__ == '__main__':
#     create_admin_user()
#     list_users()
#     total_users_count()
    app.run(debug=True, port=5000)