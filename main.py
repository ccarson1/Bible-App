from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import PyPDF2
import re
import os
from flask_migrate import Migrate
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

secret_key = os.urandom(24)
print(secret_key)

app.secret_key = secret_key

# Configure the SQLite database, relative to the app instance folder
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}


# Initialize the database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define a model (table) for the database
class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(80), nullable=False)
    book_id = db.Column(db.Integer,db.ForeignKey('books.id'), nullable=False)
    data = db.Column(db.String(500), nullable=False)
    owner = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f'<Note {self.title}>'

class Books(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    notes = db.relationship('Notes', backref='book', lazy=True)

    def __repr__(self):
        return f'<Book {self.name}>'

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_image = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    bookmark = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'




# Create the database tables
with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']



def get_book_text(book_name):

    #pdf_file = 'D:\Library/bible\KJVBible\kjvbible\pdfs/'+ book_name +'.pdf'
    pdf_file = 'pdfs/'+ book_name +'.pdf'


    file = open(pdf_file, 'rb')
    pdfreader = PyPDF2.PdfReader(file)

    numbered_books = r"Page\s\d+\s\d+\s[a-sA-Z]+\s"
    #passages = r"\s{\d:\d}\s"

    x = pdfreader.pages

    passages=[]
    for p in range(len(x)):
        passage = x[p].extract_text().replace('www.holybooks.com', '').replace("\n", " ")
        passage = re.sub(r'\s+', ' ', passage).strip()

        sub_pass = re.split(r"(\s{\d+:\d+}\s)", passage)
        passages.append(sub_pass)



    return passages

def create_html_text(passages):
    # Initialize the HTML with the heading
    head = passages[0].pop(0)  # Assuming the first element in passages contains the header
    page_text = "<h4 class='text-center'>" + head + " <small id='header-page' style='margin-left: 50%;'></small></h4><hr>"
    counter = 0
    for page_count, g in enumerate(passages):
        spans = ''

        for count, i in enumerate(g):
            # Split the text by spaces and process each word
            words = i.split()

            for j in words:
                if j.strip():  # Check if the word is not just whitespace
                    if re.search(r"{\d+:\d+}", j):
                        counter = counter +1
                        spans += '<span class="passage p' + str(counter) + '">' + j + '</span>'
                    else:
                        spans += '<span class="word w' + str(counter) + ' p'+ str(page_count) +'">' + j + '</span>'

        # Append the constructed spans to the page_text
        page_text += '<div class="read_cols">' + spans + '</div>'

    return page_text


@app.route('/submit-data', methods=['POST'])
def submit_data():
    # Get the JSON data from the request
    data = request.get_json()
    name = data.get('name')
    book = data.get('book')
    book_id = data.get('book_id')
    print("The book id for this selection is " + str(book_id))
    print(f"Received name: {name}, book: {book}")
    passages=create_html_text(get_book_text(book))

    user = session.get('username')
    print(f"The datatype for the user is {(user)}")

    all_notes = Notes.query.filter_by(book_id=book_id).all()
    notes_list = []
    for note in all_notes:
        print(type(note.owner))
        print(type(user))
        if str(note.owner).rstrip() == str(user).rstrip():
            print("This passed")
            notes_list.append({"id": note.id, "title": note.title, "book": note.book_id, "data": note.data} )
    #notes_list = [{"id": note.id, "title": note.title, "book": note.book_id, "data": note.data} for note in all_notes]
    print(notes_list)
    # Process the data or save it to the database
    # Return a response
    return jsonify({'book': book, 'passage': passages, 'notes': notes_list}), 200

@app.route('/save-bookmark', methods=['POST'])
def save_bookmark():
    data = request.get_json()

    book = data.get('book')
    page = data.get('page')
    username = data.get('username')
    book_id = data.get('book_id')

    bookmark_string = f'{{"book": "{book}", "page": "{page}", "username": "{username}", "book_id": "{book_id}"}}'

    print(bookmark_string)

    try:
        user = Users.query.filter_by(username=username).first()

        print(f"The User's bookmark is {user.bookmark}")

        if user:
            user.bookmark = bookmark_string
            db.session.commit()

            return jsonify({'book': book, 'page': page, 'username': username, 'book_id': book_id}), 200
        else:
            return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        print(f'Error saving bookmark: {e}')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/load-bookmark', methods=['POST'])
def load_bookmark():
    data = request.get_json()

    username = data.get('username')

    try:
        user = Users.query.filter_by(username=username).first()
        if user:
            bookmark = json.loads(user.bookmark)

            print(bookmark)
            print(type(bookmark))
            print(bookmark['book'])

            book = bookmark['book']
            book_id = bookmark['book_id']
            page = bookmark['page']


            print(bookmark)
            passages=create_html_text(get_book_text(book))
            all_notes = Notes.query.filter_by(book_id=book_id, owner=user.username).all()
            notes_list = [{"id": note.id, "title": note.title, "book": note.book_id, "data": note.data} for note in all_notes]

            return jsonify({'book': book, 'book_id': book_id, 'page': page, 'passage': passages, 'notes': notes_list}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        print(f'Error loading bookmark: {e}')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/save-notes', methods=['POST'])
def save_notes():
    data = request.get_json()

    username = data.get('username')
    notes = data.get('notes')

    # Debugging print statements to check data
    print("Received data:", data)
    print("Current user is: ", username)

    if not isinstance(notes, list):
        return jsonify({'error': 'Invalid data format: Expected a list'}), 400

    # Process each note in the list
    errors = []
    saved_notes = []
    for note in notes:
        if not isinstance(note, dict):
            errors.append('Invalid item format: Expected a dictionary')
            continue

        title = note.get('title', '').strip()
        book_id = note.get('book', '')
        note_data = note.get('data', '').strip()

        # Check if required fields are present
        if not all([title, book_id, note_data]):
            errors.append('Missing required fields in note')
            continue

        try:
            # Check if the note already exists
            existing_note = Notes.query.filter_by(title=title, book_id=book_id).first()

            if existing_note:
                # Update the existing note
                existing_note.data = note_data
                db.session.commit()
                saved_notes.append({"id": existing_note.id, 'title': title, 'book': book_id, 'data': note_data})
            else:
                # Add new note
                new_note = Notes(title=title, book_id=book_id, data=note_data, owner=username)
                db.session.add(new_note)
                db.session.commit()
                saved_notes.append({"id": new_note.id, 'title': title, 'book': book_id, 'data': note_data, 'owner': username})

            # Fetch all notes from the database
            all_notes = Notes.query.filter_by(book_id=book_id).all()
            notes_list = [{"id": note.id, "title": note.title, "book": note.book_id, "data": note.data, 'owner': note.owner} for note in all_notes]
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            print(f'Error saving note: {e}')
            errors.append('Failed to save note')

    if errors:
        return jsonify({'errors': errors}), 400

    return jsonify({'saved': True, 'notes': notes_list})

@app.route('/delete-note', methods=['POST'])
def delete_note():
    data = request.get_json()
    note_id = data.get('note_id')
    book_id = data.get('book_id')

    print("Note id:" + str(note_id))
    print("Bood id:" + str(book_id))

    note = Notes.query.get(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404

    try:
        db.session.delete(note)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    # Fetch all notes from the database
    all_notes = Notes.query.filter_by(book_id=book_id).all()
    notes_list = [{"id": note.id, "title": note.title, "book": note.book_id, "data": note.data} for note in all_notes]
    print(notes_list)

    db.session.commit()
    return jsonify({'deleted': True, 'notes': notes_list}), 200

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username-input')
        password = request.form.get('input-pass')

        print(username)
        print(password)

        try:
            valid_user = Users.query.filter_by(username=username).first()

            if(valid_user and valid_user.password == password):
                print(valid_user.user_image)
                session['username'] = username
                session['profile-image'] = valid_user.user_image
                session['email'] = valid_user.email
                session['password'] = valid_user.password

                return redirect(url_for('bible'))

        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            print(f'Error saving user: {e}')




    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username-input')
        email = request.form.get('email-input')
        password = request.form.get('input-pass')
        password_retype = request.form.get('input-pass-retype')

        # Here you can add your logic to handle the form data
        # For example, you might want to check if the passwords match,
        # validate the email, save the user to the database, etc.

        print(username)
        print(email)
        print(password)

        try:
            user_exists = Users.query.filter_by(username=username).first()

            if user_exists:
                print("User already exists")
            else:
                new_user = Users(username=username, password=password, email=email)
                db.session.add(new_user)
                db.session.commit()

                # If everything is fine, you can redirect to another page
                return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            print(f'Error saving user: {e}')



        if password != password_retype:
            # Handle the error - e.g., render the signup page again with an error message
            return render_template('signup.html', error="Passwords do not match")



    # Render the signup page for GET requests
    return render_template('signup.html')

@app.route('/bible')
def bible():
    username = session.get('username')
    userimage = session.get('profile-image')
    print(userimage)
    return render_template('bible.html', username=username, userimage=userimage)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    username = session.get('username')
    userimage = session.get('profile-image')  # Stored user image in session
    useremail = session.get('email')
    userpass = session.get('password')

    if request.method == 'POST':
        username = request.form.get('username-input')
        email = request.form.get('email-input')
        password = request.form.get('input-pass')
        update = request.form.get('change-input')
        change_image = request.form.get('change-image')
        profile_image = request.files.get('profile-image')  # Get uploaded file

        if update == 'on':
            user = Users.query.filter_by(username=username).first()

            if user:
                # Handle profile image upload
                if change_image == 'on' and profile_image and allowed_file(profile_image.filename):
                    filename = secure_filename(profile_image.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    profile_image.save(filepath)  # Save file to static/images

                    new_image_path = f'images/{filename}'  # Save relative path
                    user.user_image = new_image_path  
                    
                    # 🔹 Update session with the new image path
                    session['profile-image'] = new_image_path

                # Update user info
                user.email = email
                user.password = password

                try:
                    db.session.commit()
                    flash('Profile updated successfully', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error updating profile: {e}', 'danger')
            else:
                flash('User not found', 'danger')

    # 🔹 Fetch updated session data before rendering
    return render_template(
        'profile.html', 
        username=session.get('username'), 
        userimage=session.get('profile-image'), 
        useremail=session.get('email'), 
        userpass=session.get('password')
    )


if __name__ == '__main__':
    app.run(debug=True)