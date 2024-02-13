from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
from fuzzywuzzy import fuzz
from common import *

app = Flask(__name__)
DB_NAME = "database.db"
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
app.config['SECRET_KEY'] = "secret key"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)
# Create an instance of Migrate
migrate = Migrate(app, db)

UPLOAD_FOLDER = '/home/ishafayshahid/iLost_n_Found/static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def remove_old_image(filename):
    if filename != "no_file":
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route('/delete_image/<string:item_type>/<int:id>')
def delete_image(item_type, id):
    if item_type == 'found':
        item = FoundItem.query.get_or_404(id)
    elif item_type == 'lost':
        item = LostItem.query.get_or_404(id)
    else:
        return redirect(url_for('update_item', item_status=item_type, id=str(id)))

    try:
        remove_old_image(item.ipic)
        item.ipic = "no_file"
        db.session.commit()
        flash('Image removed successfully!', 'success')
        return redirect(url_for('update_item', item_status=item_type, id=str(id)))
    except IntegrityError:
        flash("There was a problem deleting that image.", "error")
        db.session.rollback()


class User(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(20), nullable=False)
    lname = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    addr = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(20), nullable=False)
    state = db.Column(db.String(20), nullable=False)
    zip = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    fb_link = db.Column(db.String(120), nullable=False)
    ig_link = db.Column(db.String(120), nullable=False)
    tw_link = db.Column(db.String(120), nullable=False)


class LostItem(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    iname = db.Column(db.String(50), nullable=False)
    ipic = db.Column(db.String(200), nullable=False)
    idesc = db.Column(db.Text, nullable=False)
    iloc = db.Column(db.String(120), nullable=False)
    uploader_email = db.Column(db.String(120), nullable=False)
    item_status = db.Column(db.String(10), nullable=False, default='lost')
    date_created = db.Column(db.DateTime, default=datetime.utcnow)


class FoundItem(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    iname = db.Column(db.String(50), nullable=False)
    ipic = db.Column(db.String(200), nullable=False)
    idesc = db.Column(db.Text, nullable=False)
    iloc = db.Column(db.String(120), nullable=False)
    uploader_email = db.Column(db.String(120), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)


class ClaimItem(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    claimant_email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    item_id = db.Column(db.Integer, primary_key=False)
    item_type = db.Column(db.String(10), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)


@app.route("/")
def home():
    t_lost_items = LostItem.query.count()
    t_found_items = FoundItem.query.count()
    t_users = User.query.count()
    return render_template("pages/home.html", t_lost_items=t_lost_items, t_found_items=t_found_items, t_users=t_users)


@app.route("/about")
def about():
    return render_template("pages/about.html")


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)
        addr = request.form.get('addr')
        city = request.form.get('city')
        state = request.form.get('state')
        zip = request.form.get('zip')
        fb_link = request.form.get('fb_link')
        ig_link = request.form.get('ig_link')
        tw_link = request.form.get('tw_link')
        user = User(fname=fname, lname=lname, email=email, password=hashed_password, addr=addr, city=city, state=state,
                    zip=zip, fb_link=fb_link, ig_link=ig_link, tw_link=tw_link)
        check_user = User.query.filter_by(email=email).first()
        if check_user:
            flash("Email already exists.", "error")
            return redirect(url_for("signup"))
        else:
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully! Please log in to your account.', 'success')
            return redirect(url_for("login"))
    return render_template("account/signup.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    message = request.args.get('message')
    if message:
        flash(message)
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user:
            if check_password_hash(user.password, password):
                session['email'] = email  # Set session only if password is correct
                flash("You have been logged in successfully!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("You have entered the wrong password!", "error")
        else:
            flash("You're not registered with us. Please create an account.", "error")
    return render_template("account/login.html")


@app.route('/dashboard')
def dashboard():
    if "email" in session:
        email = session['email']
        user = User.query.filter_by(email=email).first()
        lost_items = LostItem.query.all()
        found_items = FoundItem.query.all()
        someone_claim = ClaimItem.query.all()

        lostitems_count = 0
        for item in lost_items:
            if item.uploader_email == email:
                lostitems_count = lostitems_count + 1

        founditems_count = 0
        for item in found_items:
            if item.uploader_email == email:
                founditems_count = founditems_count + 1

        sf_l_item_count = 0
        for l_item in lost_items:
            if l_item.uploader_email == email:
                for s_claim in someone_claim:
                    if s_claim.item_type == 'lost' and s_claim.item_id == l_item.sno:
                        sf_l_item_count = sf_l_item_count + 1

        sf_f_item_count = 0
        for f_item in found_items:
            if f_item.uploader_email == email:
                for s_claim in someone_claim:
                    if s_claim.item_type == 'found' and s_claim.item_id == f_item.sno:
                        sf_f_item_count = sf_f_item_count + 1


        return render_template("account/dashboard.html",
                               email=email,
                               user=user,
                               lostitems=lost_items,
                               founditems=found_items,
                               someone_claim=someone_claim,
                               lostitems_count=lostitems_count,
                               founditems_count=founditems_count,
                               sf_l_item_count=sf_l_item_count,
                               sf_f_item_count=sf_f_item_count
                               )
    else:
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop("email", None)
    flash("You have been logged out successfully!", "success")
    return redirect(url_for("login"))


@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        option = request.form.get('options')

        if "1" == option:
            iname = request.form.get('iname')
            idesc = request.form.get('idesc')
            iloc = request.form.get('iloc')
            uploader_email = session['email']

            task_pic = None  # Set a default value for pic if the condition is not met

            if 'ipic' in request.files:
                task_pic = request.files['ipic']
                if task_pic.filename != '':
                    if task_pic.filename and allowed_file(task_pic.filename):
                        current_time = datetime.now().strftime("%Y%m%d%H%M%S")
                        filename = secure_filename(task_pic.filename)
                        filename_with_time = current_time + "_" + filename
                        task_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_with_time))
                        task_pic = filename_with_time
                    else:
                        error_message = "Invalid file type. Allowed file types are: png, jpg, jpeg, gif"
                        query_params = urlencode({'error': error_message})
                        return redirect(f"{request.url}?{query_params}")
                else:
                    task_pic = "no_file"

            item = LostItem(iname=iname, idesc=idesc, iloc=iloc, uploader_email=uploader_email, ipic=task_pic)
            db.session.add(item)
            db.session.commit()
            flash("Your lost item has been added successfully!", "success")
            return redirect(url_for("dashboard"))

        if option == "2":
            iname = request.form.get('iname')
            idesc = request.form.get('idesc')
            iloc = request.form.get('iloc')
            uploader_email = session['email']

            task_pic = None  # Set a default value for pic if the condition is not met

            if 'ipic' in request.files:
                task_pic = request.files['ipic']
                if task_pic.filename != '':
                    if task_pic.filename and allowed_file(task_pic.filename):
                        current_time = datetime.now().strftime("%Y%m%d%H%M%S")
                        filename = secure_filename(task_pic.filename)
                        filename_with_time = current_time + "_" + filename
                        task_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_with_time))
                        task_pic = filename_with_time
                    else:
                        error_message = "Invalid file type. Allowed file types are: png, jpg, jpeg, gif"
                        query_params = urlencode({'error': error_message})
                        return redirect(f"{request.url}?{query_params}")
                else:
                    task_pic = "no_file"

            item = FoundItem(iname=iname, idesc=idesc, iloc=iloc, uploader_email=uploader_email, ipic=task_pic)
            db.session.add(item)
            db.session.commit()
            flash("Found item has been added successfully!", "success")
            return redirect(url_for("dashboard"))

    return render_template("items/add_item.html")


@app.route('/lost')
def lost():
    items = LostItem.query.order_by(LostItem.date_created.desc()).all()
    return render_template("items/lost_item.html", items=items)


@app.route('/found')
def found():
    items = FoundItem.query.order_by(FoundItem.date_created.desc()).all()
    return render_template("items/found_item.html", items=items)


@app.route('/view_<string:item_type>/<int:id>')
def view_lost_n_found_item(item_type, id):
    if item_type == 'found':
        item = FoundItem.query.get(id)
    elif item_type == 'lost':
        item = LostItem.query.get(id)
    else:
        return redirect(url_for('dashboard'))

    if item:
        email = item.uploader_email
        # Fetch user details associated with the item uploader_email
        user = User.query.filter_by(email=email).first()

        t_lost_items = LostItem.query.count()
        t_found_items = FoundItem.query.count()
        return render_template("items/view_lost_n_found_item.html", item=item, item_type=item_type,
                               t_lost_items=t_lost_items, t_found_items=t_found_items, user=user)
    else:
        return redirect(url_for('dashboard'))


@app.route('/update_item_status/<string:item_status>/<int:id>')
def update_item_status(item_status, id):
    item = LostItem.query.filter_by(sno=id).first()
    item.item_status = item_status

    try:
        db.session.commit()
        flash("Item status updated successfully!", "success")
        return redirect(url_for('dashboard'))
    except IntegrityError:
        flash("Error: Failed to change item status.", "error")
        db.session.rollback()


@app.route('/update_item/<string:item_status>/<int:id>', methods=['GET', 'POST'])
def update_item(item_status, id):
    if item_status == 'lost':
        item = LostItem.query.get_or_404(id)
    elif item_status == 'found':
        item = FoundItem.query.get_or_404(id)
    else:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        item.iname = request.form.get('iname')
        item.idesc = request.form.get('idesc')
        item.iloc = request.form.get('iloc')

        if 'ipic' in request.files:
            task_pic = request.files['ipic']
            if task_pic.filename != '':
                # File was uploaded
                if task_pic.filename and allowed_file(task_pic.filename):
                    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
                    filename = secure_filename(task_pic.filename)
                    filename_with_time = current_time + "_" + filename

                    filename = secure_filename(task_pic.filename)
                    # Remove old image
                    remove_old_image(item.ipic)
                    # Save new image
                    task_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_with_time))
                    item.ipic = filename_with_time
                else:
                    error_message = "Invalid file type. Allowed file types are: png, jpg, jpeg, gif"
                    query_params = urlencode({'error': error_message})
                    return redirect(f"{request.url}?{query_params}")
            else:
                item.ipic = "no_file"

        try:
            db.session.commit()
            flash("Item updated successfully!", "success")
            return redirect(url_for('dashboard'))
        except IntegrityError:
            flash("Error: Failed to update item.", "error")
            db.session.rollback()

    else:
        return render_template('items/edit_item.html', item=item, item_status=item_status)


@app.route('/delete_item/<string:item_status>/<int:id>')
def delete_item(item_status, id):
    if item_status == 'lost':
        task_to_delete = LostItem.query.get_or_404(id)
    elif item_status == 'found':
        task_to_delete = FoundItem.query.get_or_404(id)
    else:
        return redirect(url_for('dashboard'))

    try:
        # Remove the image file from the server if it exists
        if task_to_delete.ipic != "no_file":
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], task_to_delete.ipic)
            if os.path.exists(file_path):
                os.remove(file_path)
        db.session.delete(task_to_delete)
        db.session.commit()
        flash("Item deleted successfully!", "success")
        return redirect(url_for('dashboard'))
    except IntegrityError:
        flash("There was a problem deleting that item.", "error")
        return redirect(url_for('dashboard'))


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if "email" in session:
        email = session['email']
        if request.method == 'POST':
            old_password = request.form.get('old-pass')
            new_password = request.form.get('new-pass')
            confirm_password = request.form.get('confirm-pass')

            user = User.query.filter_by(email=email).first()

            if user and check_password_hash(user.password, old_password):
                if new_password == confirm_password:
                    user.password = generate_password_hash(new_password)
                    try:
                        db.session.commit()
                        flash("Password changed successfully! Please login again.", "success")
                        return redirect(url_for('login'))
                    except IntegrityError:
                        flash("Error: Failed to change password.", "error")
                        db.session.rollback()
                else:
                    flash("Error: New password and confirm password do not match.", "error")
            else:
                flash("Error: Invalid old password. Please try again.", "error")
                return redirect(url_for('update_password'))
        return render_template('account/change_password.html')
    else:
        return redirect(url_for('login'))


@app.route('/my_account', methods=['GET', 'POST'])
def my_account():
    if "email" in session:
        email = session['email']
        user = User.query.filter_by(email=email).first()

        if request.method == 'POST':
            user.fname = request.form.get('fname')
            user.lname = request.form.get('lname')
            user.addr = request.form.get('addr')
            user.city = request.form.get('city')
            user.state = request.form.get('state')
            user.zip = request.form.get('zip')
            user.fb_link = request.form.get('fb_link')
            user.ig_link = request.form.get('ig_link')
            user.tw_link = request.form.get('tw_link')

            try:
                flash("Account details updated successfully!", "success")
                db.session.commit()
            except IntegrityError:
                flash("Failed to update account details.", "error")
                db.session.rollback()

        return render_template('account/my_account.html', user=user)
    else:
        return redirect(url_for('login'))


@app.route("/search", methods=['POST', 'GET'])
def search():
    l_matched = []
    f_matched = []
    if request.method == 'POST':
        s = request.form['search']
        lost_items = LostItem.query.all()
        found_items = FoundItem.query.all()

        for i in lost_items:
            if fuzz.partial_ratio(s, i.iname.lower()) >= 70:
                l_matched.append(i)
        for i in found_items:
            if fuzz.partial_ratio(s, i.iname.lower()) >= 70:
                f_matched.append(i)
        return render_template('common/search.html', keyword=s, lost_items=l_matched, found_items=f_matched)


@app.route('/claim_item/<string:item_type>/<int:id>', methods=['GET', 'POST'])
def claim_item(item_type, id):
    if item_type == 'found':
        item = FoundItem.query.get_or_404(id)
    elif item_type == 'lost':
        item = LostItem.query.get_or_404(id)
    else:
        return redirect(url_for(item_type))

    if request.method == 'POST':
        if item:
            name = request.form.get('name')
            claimant_email = request.form.get('email')
            message = request.form.get('message')
            item_id = id
            item_type = item_type

            claim_items = ClaimItem(name=name,
                            claimant_email=claimant_email,
                            message=message,
                            item_id=item_id,
                            item_type=item_type)
            db.session.add(claim_items)
            db.session.commit()
            flash("Thank you. A confirmation email has been sent successfully. You will be kept informed by email about your claim.", "success")

            return redirect(url_for('view_lost_n_found_item', item_type=item_type, id=id))
        else:
            return redirect(url_for('/'))
    return render_template("items/claim_item.html", item=item, item_type=item_type)


@app.context_processor
def inject_common_functions():
    return {
        'ftitle': ftitle
    }


if __name__ == '__main__':
    app.run(debug=True)
