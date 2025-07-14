from flask import Flask, render_template, request, session, flash, url_for
from werkzeug.utils import redirect
from pymongo import MongoClient
import random
from config import configurations
import secrets
from flask_mail import Mail, Message
from datetime import datetime
from bson import ObjectId

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
app.db = client.Microblog
app.secret_key = secrets.token_hex(16)
app.config['MAIL_SERVER'] = configurations['MAIL_SERVER']
app.config['MAIL_PORT'] = configurations['MAIL_PORT']
app.config['MAIL_USE_TLS'] = configurations['MAIL_USE_TLS']
app.config['MAIL_USE_SSL'] =   configurations['MAIL_USE_SSL']
app.config['MAIL_USERNAME'] =  configurations['MAIL_USERNAME']
app.config['MAIL_PASSWORD'] =  configurations['MAIL_PASSWORD']
app.config['MAIL_DEFAULT_SENDER'] = configurations['MAIL_DEFAULT_SENDER']
mail = Mail(app)



def otp_genrator():
    return random.randint(111111,999999)

def send_email(email, subject, body, msg):
    message = Message(subject, recipients=[email], body=body)
    try:
        mail.send(message)
        print(f'{msg} has been sent successfully to {email}')
    except Exception as e:
        print(f'Erron on sending email: {str(e)}')

def get_unique_username(user):
    flag = True
    for item in app.db.Credentials.find({}):
        if user == item.get('username'):
            flag = False
            break
    return flag

def get_user_details(username):
    user_details = app.db.credentials.find_one({'username':username})
    return user_details

def notify_followers(username, title):
    followers = app.db.followers.find_one({username: {'$exists': True}})[username]
    user_details = get_user_details(username)
    user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
    deactivated_username = app.db.deactivate.find_one({'Accounts': {'$exists': True}})
    if followers and deactivated_username:
        followers = [f for f in followers if f not in deactivated_username['Accounts']]
    if followers:
        for follower in followers:
            email = get_user_details(follower)['email']
            subject = f'🚀 New Blog Alert: {user} just dropped a Must-Read Post!'
            body = f'''
            Hi There, 
            🎉 Great News! {user} just published a brand-new blog titled "{title}" and it is packed with insights that you'll love.

            Don't miss out to read it now and join the conversation!

            stay tunded for more amazing updates,

            Microblog Team
            '''
            send_email(email, subject, body, msg='msg to followers')

@app.route('/')
def home():
    user = ''
    if 'username' in session:
        username = session['username']
        user_details = get_user_details(username)
        user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
    entries = [
        (
            entry['title'],
            entry['content'],
            entry['created_at'],
            entry['author'],
            entry['_id']
        ) for entry in app.db.entries.find({})
    ]

    return render_template('home.html', user=user, entries=entries)

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        for user in app.db.credentials.find({}):
            if username == user['username'] and password == user['password']:
                session['username'] = username
                app.db.deactivate.update_one({'Accounts':{'$exists': True}},{'$pull': {'Accounts':username}})
                return redirect('/')
    
    return render_template('login.html')

@app.route('/signup', methods = ['GET', 'POST'])
def signup():
    if request.method == 'POST':
        print(request.form)
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        if get_unique_username(username):
            session['username'] = username
        else:
            flash('Username already exist. Please choose different username,', 'error')
            return render_template('signup.html')
        email = request.form['email']
        otp = otp_genrator()
        subject = 'Microblog - OTP Validation'
        body = f'Your OTP for Microblog Sign Up is: {otp}'
        send_email(email, subject, body, msg='OTP')
        session['otp'] = otp
        session['first_name']= first_name
        session['last_name'] = last_name
        session['email'] = email
        session['password'] = request.form['password']
        return render_template('otp.html', email=email  )
    return render_template('signup.html')

@app.route('/verify_otp', methods = ['POST'])
def verify_otp():
    user_otp = request.form.get('otp')
    saved_otp = session.get('otp')
    print(session)
    if user_otp and saved_otp and user_otp == str(saved_otp):
        app.db.credentials.insert_one(
            {
                'first_name': session['first_name'],
                'last_name': session['last_name'],
                'username': session['username'],
                'password': session['password'],
                'email': session['email']
            }
        )

        subject = 'Welcome to Microblog!'
        body = f'Dear {session["first_name"].capitalize()}, \n\tThank you for choosing Mircoblog! Your account has been create successfully. Dive into our platform and discover a world of possiblities. If you have any queries or suggestions, our team is there to help you out.\n\n Best Regards, \nMicroblog Team'
        send_email(session['email'], subject, body, msg='Onboarding mail')
        return redirect('/')
    else:
        return redirect('/signup')

@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username')
    return redirect('/')


@app.route('/about')
def about():
    user = ''
    if 'username' in session:
        username = session['username']
        user_details = get_user_details(username)
        user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
    return render_template('about.html', user=user)


@app.route('/user_page', methods =['GET', 'POST'])
def user_page():
    if 'username' not in session:
        return redirect('/')
    else:
        username = session['username']
        user_details = get_user_details(username)
        user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
        entries = [
        (
            entry['title'],
            entry['content'],
            entry['created_at'],
            entry['author'],
            entry['_id']
        ) for entry in app.db.entries.find({}) if entry['username'] == session['username']
    ]
    
    return render_template('user_page.html',user=user, entries=entries)


@app.route('/newblog', methods = ['GET', 'POST'])
def newblog():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
    if request.method == 'POST':
        blog_title = request.form.get('title')
        blog_content = request.form.get('content')
        formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        app.db.entries.insert_one({
            'username': username,
            'author': user,
            'title': blog_title,
            'content': blog_content,
            'created_at': formatted_date
        })

        subject ='🚀 Your blog post is live!'
        body = f'Dear {user}, \n\tExciting news! Your new blog post, {blog_title}, is now live on Microblog!. 🎉 Thank you for sharing you insights! Your contribution make our coummunity thrive. Looking forward to more from you! \n\n Best Regards,\nMicroblog Team.'
        send_email(user_details['email'], subject, body, msg='New Blog')
        notify_followers(username, blog_title)
        return redirect('/user_page')
    
    return render_template('new_blog.html', user=user)


@app.route('/view/<string:entry_id>', methods = ['GET'])
def view(entry_id):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
    if request.method == 'GET':
        entry = app.db.entries.find_one({'_id':(ObjectId(entry_id))})
        return render_template('view.html', entry = entry, user=user)

@app.route('/update_blog/<string:entry_id>', methods=['GET', 'POST'])
def update_blog(entry_id):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
    if request.method == 'GET':
        entry = app.db.entries.find_one({'_id':(ObjectId(entry_id))})
        return render_template('update_blog.html', entry = entry, user=user)
    elif request.method == 'POST':
        updated_title = request.form.get('updated_title')
        updated_contnet = request.form.get('updated_content')
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
        result = app.db.entries.update_one(
            {'_id':ObjectId(entry_id)},
            {'$set':{'title': updated_title, 'content':updated_contnet, 'created_at': updated_at}}
        )

        if result.modified_count >0:
            print('Blog entry updated successfully...')

        return redirect('/user_page')
    
@app.route('/delete_blog/<string:entry_id>', methods = ['GET', 'POST'])
def delete_blog(entry_id):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
    if request.method == 'GET':
        entry = app.db.entries.find_one({'_id':ObjectId(entry_id)})
        return render_template('delete_blog.html', entry=entry, user=user)
    elif request.method == 'POST':
        result = app.db.entries.delete_one(
            {'_id': ObjectId(entry_id)}
        )
        print('Blog has been deleted successfully...')

        return redirect('/user_page')
    
@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
    contribution = [
        (
            entry['author'],
            entry['title'],
            entry['content'],
            entry['created_at'],
            entry['_id']
        ) for entry in app.db.entries.find({}) if entry['username'] == session['username']
    ]
    followers = app.db.followers.find_one({username:{'$exists':True}})
    if followers:
        follower_count = len(followers[username])
    else:
        follower_count = 0
    return render_template('profile.html', is_own_profile = True, follower_count = follower_count, contribution = contribution, user=user,profile_user =user, username = username , email = user_details    ['email'])


@app.route('/user_profile/<string:username>')
def user_profile(username):
    if 'username' not in session:
        return redirect('/')
    session_username = session['username']
    session_userdata = get_user_details(session_username)
    session_user = f'{session_userdata["first_name"].capitalize()} {session_userdata["last_name"].capitalize()}'
    profile_user_userdata = get_user_details(username)
    profile_user = f'{profile_user_userdata["first_name"].capitalize()} {profile_user_userdata["last_name"].capitalize()}'
    contribution = [
        (
            entry['author'],
            entry['title'],
            entry['content'],
            entry['created_at'],
            entry['_id']
        ) for entry in app.db.entries.find({}) if entry['username'] == username
    ]

    is_own_profile = True if session_username == username else False
    followers = app.db.followers.find_one({username:{'$exists':True}})
    print(followers)
    if followers:
        follower_count = len(followers[username])
        is_following = True if session_username in followers[username] else False
    else:
        follower_count = 0
        is_following = False

    return render_template('profile.html', is_own_profile = is_own_profile, follower_count = follower_count, is_following = is_following, contribution = contribution, user=session_user,profile_user =profile_user, username = username , email = profile_user_userdata['email'])

@app.route('/follow/<string:username>', methods = ['POST'])
def follow(username):
    if 'username' not in session:
        return redirect('/')
    session_username = session['username']
    if not app.db.followers.find_one({username: {'$exists': True}}):
        app.db.followers.insert_one({username: [session_username]})
    else:
        app.db.followers.update_one(
            {username:{'$exists': True}},
            {'$push': {username:session_username}}
        )

    return redirect(url_for('user_profile', username = username))

@app.route('/unfollow/<string:username>', methods = ['POST'])
def unfollow(username):
    if 'username' not in session:
        return redirect('/')
    session_username = session['username']
    app.db.followers.update_one(
        {username:{'$exists': True}},
        {'$pull': {username:session_username}}
    )

    return redirect(url_for('user_profile', username = username))


@app.route('/delete_account', methods = ['GET', 'POST'])
def delete_account():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    user = f'{user_details["first_name"].capitalize()} {user_details["last_name"].capitalize()}'
    if request.method == 'POST':
        delte_option = request.form.get('delete_option')
        if delte_option == 'deactivate':
            if not app.db.deactivate.find_one({'Accounts': {'$exists': True}}):
                app.db.deactivate.insert_one({'Accounts': [username]})
            else:
                app.db.deactivate.update_one(
                    {'Accounts':{'$exists': True}},
                    {'$push': {'Accounts':username}}
            )
            return redirect('/logout')
        elif delte_option == 'all_data':
            app.db.credentials.delete_one({'username': session['username']})
            app.db.entries.delete_many({'username': session['username']})
            return redirect('/logout')
    return render_template('delete_user.html', user=user)
        























if __name__ == '__main__':
    app.run(port=8000, host='0.0.0.0', debug=True)

