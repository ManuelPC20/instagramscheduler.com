from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = '123fdf3rf42f2f13f1f2f2f2'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database_insta.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'C:/Users/manuel/Desktop'  # Specify the folder where you want to save the uploaded photos
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}  # Specify the allowed file extensions


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    instagram_id = db.Column(db.String)
    instagram_token = db.Column(db.String)
    posts = db.relationship('Post', backref='user', lazy=True)

    def __repr__(self):
        return f"<User(name='{self.name}', email='{self.email}')>"

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post = db.Column(db.String)
    post_time = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Post(user_id='{self.user_id}', post='{self.post}', post_time='{self.post_time}')>"


def get_logged_in_user():
    if 'user' in session:
        user_id = session['user']['id']
        return User.query.get(user_id)

    return None


def get_previous_posts():
    user = get_logged_in_user()  # Get the logged-in user
    if user:
        previous_posts = Post.query.filter_by(user_id=user.id).all()
        return previous_posts
    return []



@app.route('/')
@app.route('/home')
def home():
    user = get_logged_in_user()  # Get the logged-in user
    user_authenticated = True if user else False
    if user:
        previous_posts = get_previous_posts()  # Get previous posts for the user
        return render_template('home.html', user=user, previous_posts=previous_posts)
    else:
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if authenticate(email, password):
            user = User.query.filter_by(email=email).first()
            session['user'] = {
                'id': user.id,
                'name': user.name,
                'email': user.email
            }
            return redirect('/home')
        return 'Invalid credentials. Please try again.'
    user_authenticated = True if 'user' in session else False  # Check if the user is authenticated
    return render_template('login.html', user_authenticated=user_authenticated)


@app.route('/logout')
def logout():
    if 'user' in session:
        session.pop('user', None)
    return redirect('/login')

def save_user(user_data):
    user = User(**user_data)
    db.session.add(user)
    db.session.commit()


def authenticate(email, password):
    user = User.query.filter_by(email=email).first()
    if user:
        return user.password == password
    return False


def schedule_post(user_id, post, post_time, instagram_token):
    user = User.query.get(user_id)
    if user is None:
        return 'User not found.'

    post = Post(user=user, post=post, post_time=post_time)
    db.session.add(post)
    db.session.commit()
    print(f"Post scheduled for User ID: {user_id}")
    print(f"Post: {post}")
    print(f"Scheduled Time: {post_time}")
    print(f"Instagram Token: {instagram_token}")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        instagram_id = request.form['instagram_id']
        instagram_token = request.form['instagram_token']
        user_data = {
            'name': name,
            'email': email,
            'password': password,
            'instagram_id': instagram_id,
            'instagram_token': instagram_token
        }
        save_user(user_data)
        return 'User registered successfully!'
    return render_template('register.html')


@app.route('/register_post', methods=['GET', 'POST'])
@login_required
def register_post():
    user = get_logged_in_user()  # Get the logged-in user

    if request.method == 'POST':
        user_id = request.form['user_id']
        post = request.form['post']
        post_time = datetime.strptime(request.form['post_time'], '%Y-%m-%dT%H:%M')

        # Retrieve the user's data
        user = User.query.get(user_id)
        if user is None:
            return 'User not found.'

        # Retrieve the Instagram token from the user's data
        instagram_token = user.instagram_token
        if instagram_token is None:
            return 'Instagram token not found.'

        # Handle file upload
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                photo.save(filepath)
                post.photo_url = filepath  # Save the file path in the post model

        schedule_post(user_id, post, post_time, instagram_token)

        # Redirect back to the home page with a success message
        return redirect(url_for('home', success=True))

    return render_template('register_post.html', user=user)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    # Retrieve the post from the database
    post = Post.query.get(post_id)

    # Check if the post exists
    if post is None:
        return 'Post not found.'

    # Check if the post belongs to the logged-in user
    if post.user_id != session['user']['id']:
        return 'Unauthorized access.'

    # Delete the post from the database
    db.session.delete(post)
    db.session.commit()

    return redirect(url_for('home'))



if __name__ == '__main__':
    app.app_context().push()
    db.create_all()
    app.run(debug=True)
