########## Imports ##########

from flask import Flask, render_template, request, redirect, session, url_for
from flask_oauthlib.client import OAuth
from flask_session import Session
from flask_mail import *
from random import *
from bson.objectid import ObjectId
from base64 import b64encode
import pymongo
from datetime import datetime
import bcrypt
import string
import random
from bson.binary import Binary
from jinja2 import Environment
from threading import Timer
import gridfs


def chr_filter(value):
    return chr(value)

########## Clear Session ##############


def clear_session():
    session.pop('msg', None)

########## Getting Current Date ##########


current_date_time = datetime.now()

########## Flask App Configuration ##########

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = True
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


########## Google OAuth Configuration ##########

oauth = OAuth(app)
google = oauth.remote_app(
    'google',
    consumer_key='551512512972-sva6sd52q4u89lj5ippl60ts9v00lcok.apps.googleusercontent.com',
    consumer_secret='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',
    request_token_params={
        'scope': 'email profile',
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)


# Add the custom filter to the Jinja2 environment
app.jinja_env.filters['chr'] = chr_filter

########## Database Connection ##########
client = pymongo.MongoClient('mongodb://localhost:27017/classroom')
database = client['classroom']
classes = database['classes']  # classes
users = database['users']  # users
enrolled = database['enrolled_classes']  # enrolled_classes
topic = database['topics']  # topics
test = database['test']  # test
assignment = database['assignment']  # assignments
assignment_score = database['assignment_score']  # assignment scorecard
notifications = database['notifications']  # notifications
announcement = database['announcement']  # announcement
test_result = database['test_result']  # test result

if not client.is_mongos:
    print("Connection To MongoDB : Successful")
else:
    print("Connection To MongoDB : Failed")

########## Mail Verification ##########
mail = Mail(app)
app.config["MAIL_SERVER"] = 'smtp.gmail.com'
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = 'mc222437@zealeducation.com'
app.config['MAIL_PASSWORD'] = 'Ad1301@anjajylmbt'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

########### OTP CODE Generator #############

#### OTP MAP ####
otpMap = {}


def otpCode():
    return randint(0000, 9999)


########## Class Code Generator ##########

def classCode():
    alphanumeric = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanumeric) for _ in range(6))

########## Topic Code Generator ##########


def topicCode():
    alphanumeric = string.ascii_letters + string.digits
    return ''.join(random.choice(alphanumeric) for _ in range(6))

########## Class Color Code Generator ##########


def colorCode():
    code = randint(1, 18)
    return "cover" + str(code)


########## Notification Sender ##########

def notification(notifyType, title, status, email):
    notifications.insert_one({
        'email': email,
        'posted': current_date_time.strftime("%d-%m-%Y %I:%M:%S %p"),
        'type': notifyType,
        'title': title,
        'status': status
    })

# Function to insert image into MongoDB


def insert_image(image_data, collection_name):
    fs = gridfs.GridFS(database, collection=collection_name)
    fs.put(image_data, filename="uploaded_image")


########## Routing To Templates ##########

########## Dashboard ##########


@app.route('/')
def index():
    if session.get('user'):
        email = session.get('user')
        user = users.find_one({'email': email})
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html')

########## Login ##########


@app.route('/login')
def login():
    if session.get('user'):
        return redirect(url_for('dashboard'))
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/login/authorized')
def authorized():
    response = google.authorized_response()
    if response is None or response.get('access_token') is None:
        return 'Access denied: reason={} error={}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )

    session['google_token'] = (response['access_token'], '')
    user_info = google.get('userinfo')

    # Extract user information
    email = user_info.data.get('email')
    fname = user_info.data.get('given_name')
    lname = user_info.data.get('family_name')
    image = user_info.data.get('picture')
    session['user'] = email
    user = users.find_one({'email': email})
    if user:
        return redirect(url_for('dashboard'))
    return render_template('chooserole.html', email=email, fname=fname, lname=lname, image=image)


@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')

########## Register User ##########


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        role = request.form['role']
        image = request.form['image']
        user = users.find_one({'email': email})
        if user:
            return redirect(url_for('dashboard'))
        users.insert_one({
            'fname': fname,
            'lname': lname,
            'email': email,
            'role': role,
            'profile': image
        })
        return redirect(url_for('dashboard'))


########## Register ##########


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    if user['role'] == 'teacher':
        classesData = classes.find({'teacher': email})
        classesCount = classes.count_documents({'teacher': email})
        notifycount = notifications.count_documents(
            {'email': email, 'status': 'unread'})
        notifydata = list(notifications.find(
            {'email': email, 'status': 'unread'}))
        session['notifydata'] = notifydata
        session['notifycount'] = notifycount
        session['userdata'] = user
        return render_template('dashboard.html', classesData=classesData, classesCount=classesCount, notifycount=notifycount, notifydata=notifydata)
    else:
        data = enrolled.find({'email': email})
        classesCount = enrolled.count_documents({'email': email})
        notifycount = notifications.count_documents(
            {'email': email, 'status': 'unread'})
        notifydata = notifications.find({'email': email, 'status': 'unread'})
        classesData = []
        for i in data:
            query = classes.find_one({'code': i['code']})
            classesData.append(query)
        session['userdata'] = user
        notifycount = notifications.count_documents(
            {'email': email, 'status': 'unread'})
        notifydata = list(notifications.find(
            {'email': email, 'status': 'unread'}))
        session['notifydata'] = notifydata
        session['notifycount'] = notifycount
        return render_template('dashboard.html', classesData=classesData, classesCount=classesCount, notifycount=notifycount, notifydata=notifydata)

########## Create Class Form ##########


@app.route('/createclass', methods=['GET', 'POST'])
def createClassForm():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""

    # Sessions Data Extraction
    email = session.get('user')
    user = users.find_one({'email': email})
    if request.method == 'POST':
        className = request.form['className']
        subject = request.form['subject']
        code = classCode()
        bg = colorCode()
        query = classes.insert_one({
            'className': className,
            'subject': subject,
            'code': code,
            'bg': bg,
            'teacher': email,
            'created': datetime.now().strftime("%d-%m-%Y")
        })
        if query:
            notification('Class Created', className +
                         " class created successfully", 'unread', email)
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('createClassForm'))
    return render_template('createclass.html', user=user)


############ Invite ################

@app.route('/invite', methods=['POST'])
def invite():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    invite = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    if request.method == 'POST':
        classDetails = session['classDetails']
        teacher = users.find_one({'email': classDetails['teacher']})
        teacherName = teacher['fname'] + " " + teacher['lname']
        inviteEmail = request.form['invite']
        code = classDetails['code']
        html_content = f"""
        <html>
        <head>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Rock+Salt&display=swap" rel="stylesheet">
        <link
            href="https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap"
            rel="stylesheet">
        </head>
        <body>
        <div style="text-align: center;">
            <a href=""
            style="font-size:2em;color: #00466a;text-decoration:none;font-weight:600;font-family: Rock Salt, cursive;">Rainbow
            Classroom</a>
        </div>
        <div style="text-align: center; font-family: Poppins; line-height: 2px;">
            <img style="border-radius: 50%; margin-top: 3%;" src="{teacher['profile']}">
            <h3>{teacherName}</h3>
            <p style="color: grey; text-decoration: none">{teacher['email']}</p>
            <div style="margin-top: 5%;">
            <p style="font-weight: 300; font-size: 1.3em;">Invited you to join {classDetails['className']}</p>
            </div>
            <div style="margin-top: 3%;">
            <p style="font-weight: 300; font-size: 1.3em; color: grey;">Class Code</p>
            <h1 style="letter-spacing: 10px; margin-top: 3%;">{code}</h1>
            </div>
        </div>
        </body>
        </html>
            """

        msg = Message('Class invitation: ' +
                      classDetails['className'], sender=email, recipients=[inviteEmail])
        msg.html = html_content
        try:
            mail.send(msg)
            invite = "success"
            return render_template('students.html', invite=invite)
        except smtplib.SMTPException as e:
            invite = "fail"
            return render_template('student.html', invite=invite)
    return render_template('students.html')

########## Join Class Form ##########


@app.route('/joinclass', methods=['GET', 'POST'])
def joinClassFrom():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    if request.method == 'POST':
        code = request.form['code']
        exist = enrolled.find_one({'email': email})
        if exist:
            msg = 'exist'
            return render_template('joinclass.html', msg=msg, user=user)
        query = classes.find_one({'code': code})
        if query:
            enrolled.insert_one({
                'email': user['email'],
                'code': code
            })
            notification('New Student', user['fname'] + " " + user['lname'] + ' joined the class ' +
                         query['className'], 'unread', query['teacher'])
            notification('Class Enrolled', 'You enrolled classs ' +
                         query['className'], 'unread', email)
            return redirect(url_for('dashboard'))
        else:
            msg = 'error'
    return render_template('joinclass.html', msg=msg, user=user)

########## Class Details ##########


@app.route('/classdetails', methods=['GET', 'POST'])
def classDetails():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    if request.method == 'POST':
        code = request.form['code']
        classDetails = classes.find_one({'code': code})
        topics = list(topic.find({'code': code}))
        stdCount = enrolled.count_documents({'code': code})
        faculty = users.find_one({'email': classDetails['teacher']})
        stdemails = enrolled.find({'code': code})
        stddata = []
        for data in stdemails:
            query = users.find_one({'email': data['email']})
            details = {
                'name': query['fname'] + " " + query['lname'],
                'profile': query['profile'],
                'email': query['email']
            }
            stddata.append(details)

        announcementData = []
        announcementData = list(announcement.find({'code': code}))
        if announcementData:
            ancmtcount = announcement.count_documents({'code': code})
            session['announcement'] = announcementData
            session['ancmntcount'] = ancmtcount
        else:
            session['announcement'] = ""
            session['ancmntcount'] = 0
        session['stddata'] = stddata
        session['classDetails'] = classDetails
        session['stdCount'] = stdCount
        session['topics'] = topics
        session['faculty'] = faculty
        session['stddata'] = stddata
        return render_template('classdetails.html', user=user, classDetails=classDetails, stdCount=stdCount, faculty=faculty, topics=topics)
    return render_template('classdetails.html', user=user)

########## Class Topic Form ##########


@app.route('/addtopic', methods=['GET', 'POST'])
def addTopic():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    code = request.form['code']
    if request.method == 'POST' and request.form['addtopic'] == 'true':
        code = request.form['code']
        classdata = classes.find_one({'code': code})
        name = request.form['topic']
        query = topic.insert_one(
            {'topic_name': name,
             'topic_code': topicCode(),
             'code': code,
             'material': [],
             'created': datetime.now().strftime("%d-%m-%Y")
             }
        )

        if query:
            topics = list(topic.find({'code': code}))
            session['topics'] = topics
            msg = 'success'
            notification('New Topic', 'Topic added to the class ' +
                         classdata['className'], 'unread', email)
            stdEmails = enrolled.find({'code': code})
            for data in stdEmails:
                notification('New Topic', 'Topic added to the class ' +
                             classdata['className'], 'unread', data['email'])
            return redirect(url_for('classDetails'))
        else:
            msg = 'error'
            return render_template('material.html', user=user, msg=msg)
    return render_template('addtopic.html', user=user, code=code)


############# Students ##############

@app.route('/students', methods=['POST'])
def students():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    return render_template('students.html')


@app.route('/profile')
def profile():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    profile = users.find_one({'email': email})
    session['profile'] = profile
    return render_template('profile.html')


########## Material ##########


@app.route('/material', methods=['GET', 'POST'])
def material():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    if request.method == 'POST':
        id = request.form['id']
        query = topic.find_one({'topic_code': id})
        materials = query['material']
        return render_template('material.html', user=user, query=query, materials=materials)
    return render_template('material.html', user=user)


@app.route('/viewnote', methods=['GET', 'POST'])
def viewNote():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    if request.method == 'POST':
        name = request.form['file']
        print(name)
        query = topic.find_one({'material': {'$elemMatch': {'name': name}}})
        print(query)
        note = ""
        for data in query['material']:
            x = data['name']
            if name == x:
                encoded_content = b64encode(data['file']).decode('utf-8')
                break
        return render_template('viewnote.html', user=user, encoded_content=encoded_content)
    return render_template('viewnote.html', user=user)


@app.route('/addmaterial', methods=['GET', 'POST'])
def addMaterial():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    id = request.form['id']
    data = topic.find_one({'topic_code': id})

    if request.method == 'POST' and request.form['lock'] == 'no':
        id = request.form['id']
        file = request.files['file']
        fileData = file.stream.read()
        fileName = file.filename
        classdata = classes.find_one({'code': data['code']})
        print(id)
        query = topic.update_one(
            {'topic_code': id}, {"$push": {"material": {"name": fileName, "file": fileData}}})
        if query:
            msg = 'success'
            notification('New Material', 'Material added to the class ' +
                         classdata['className'], 'unread', classdata['teacher'])
            stdEmails = enrolled.find({'code': data['code']})
            for data in stdEmails:
                notification('New Material', 'You have new material in the class ' +
                             classdata['className'], 'unread', data['email'])
            return render_template('addmaterial.html', user=user, msg=msg, data=data)
        else:
            msg = "error"
    return render_template('addmaterial.html', user=user, msg=msg, data=data)

########## Create Test ##########


@app.route('/createtest', methods=['GET', 'POST'])
def createTest():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    code = request.form['code']
    testdata = list(test.find({'code': code}))
    if testdata:
        session['testdata'] = testdata
    return render_template('createtest.html', user=user, code=code)

########## Submit Test ##########


@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    data = request.json
    code = request.json['code']
    query = classes.find_one({'code': code})
    test.insert_one(data)
    notification('Test Created', 'Test created for the class ' +
                 query['className'], 'unread', email)
    return redirect(url_for('createTest'))


########## View Test ##########
@app.route('/viewtest', methods=['GET', 'POST'])
def viewTest():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    classdata = session['classDetails']
    code = classdata['code']
    classDetails = classes.find_one({'code': code})
    tests = test.find({'code': code})
    ids = list(test_result.find({'email': email}))
    resultids = []
    for i in ids:
        resultids.append(i['tid'])
    session['resultids'] = resultids
    if request.method == 'POST' and user['role'] == 'teacher' and request.form['result'] == 'yes':
        id = ObjectId(request.form['id'])
        testdata = test.find_one({'_id': id})
        session['test'] = testdata
        resultData = list(test_result.find({'tid': id}))
        session['result'] = resultData
        return render_template('viewtestresult.html', resultData=resultData)

    elif request.method == 'POST' and request.form['test'] == 'true':
        id = ObjectId(request.form['id'])
        tests = test.find_one({'_id': id})
        code = request.form['code']
        classDetails = classes.find_one({'code': code})
        session['testtotalscore'] = len(tests['questions'])
        stdresult = test_result.find_one({'tid': id})
        return render_template('viewtestdata.html', tests=tests, user=user, classDetails=classDetails)

    elif request.method == 'POST' and request.form['test'] == 'false' and request.form['post'] == 'yes':
        id = ObjectId(request.form['id'])
        tests = test.find_one({'_id': id})
        test.update_one(
            {'_id': id}, {'$set': {'response': False, 'post': True}})

    elif request.method == 'POST' and request.form['test'] == 'false' and request.form['post'] == 'no' and request.form['response'] == 'yes':
        id = ObjectId(request.form['id'])
        tests = test.find_one({'_id': id})
        responseType = not (tests['response'])
        test.update_one({'_id': id}, {'$set': {'response': responseType}})
    elif request.method == 'POST' and request.form['test'] == 'result':
        id = ObjectId(request.form['id'])
        tests = test.find_one({'_id': id})
        stdresult = test_result.find_one({'email': email,'tid': id})
        merged_result = {}
        merged_result.update(tests)
        merged_result.update(stdresult)
        noque = len(tests['questions'])
        return render_template('viewteststdresult.html', merged_result=merged_result, stdresult=stdresult, noque=noque)

    if user['role'] == 'student':
        tests = test.find({'code': code, 'post': True})
        result = list(test_result.find({'email': email}))
        session['result'] = result
    else:
        tests = test.find({'code': code})
    return render_template('viewtest.html', tests=tests, user=user, classDetails=classDetails)


########### Student Test #############

@app.route('/onlinetest', methods=['POST'])
def onlineTest():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    classData = session['classDetails']
    if request.method == 'POST' and request.form['test'] == 'view':
        id = ObjectId(request.form['id'])
        testdata = test.find_one({'_id': id})
        session['test'] = testdata
        return render_template('studenttest.html')

    elif request.method == 'POST' and request.form['test'] == 'submit':
        id = ObjectId(request.form['id'])
        testdata = test.find_one({'_id': id})
        if testdata['response'] == True:
            noque = len(testdata['questions'])
            anskey = []
            for data in testdata['questions']:
                anskey.append(data['ans'])
            answers = []
            for i in range(1, noque + 1):
                radio = 'ans' + str(i)
                ans = request.form[radio]
                answers.append(int(ans))

            score = 0
            for i in range(0, noque):
                if anskey[i] == answers[i]:
                    score += 1

            test_result.insert_one({
                'tid': id,
                'name': user['fname'] + ' ' + user['lname'],
                'email': email,
                'answers': answers,
                'myscore': score,
                'submission': datetime.now()
            })
            result = test_result.find_one({'tid': id, 'email': email})
            resultids = list(test_result.find({'email': email}))
            session['resultids'] = resultids
            return redirect(url_for('viewTest'))
        else:
            msg = "error"
            return render_template('testresult.html', msg == msg)
    return render_template('studenttest.html')


########## Post Assignments ##########


@app.route('/assignments', methods=['POST'])
def assignments():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    code = request.form['code']
    classDetails = classes.find_one({'code': code})
    query = assignment.find({'code': code})
    data = query
    show = ""
    if query:
        count = assignment.count_documents({'code': code})
        msg = 'yes' if count > 0 else 'no'
        show = 'yes'
    else:
        msg = 'no'

    if request.method == 'POST' and request.form['lock'] == 'true':
        code = request.form['code']
        name = request.form['name']
        ddline = datetime.strptime(request.form['ddline'], "%Y-%m-%d")
        score = request.form['score']
        file = request.files['file']
        fileData = file.stream.read()
        content = file.content_type
        query = assignment.insert_one({
            'code': code,
            'name': name,
            'post': datetime.now().strftime("%d-%m-%Y"),
            'ddline': ddline,
            'score': score,
            'file': fileData,
            'content': content,
        })
        msg = 'success' if query else 'error'
        show = 'yes'
        data = assignment.find({'code': code})
        notification('New Assignment', 'Assignment added to the class ' +
                     classDetails['className'], 'unread', classDetails['teacher'])
        stdEmails = enrolled.find({'code': code})
        for data in stdEmails:
            notification('New Assignment', 'You have new assignment in the class ' +
                         classDetails['className'], 'unread', data['email'])
        data = assignment.find({'code': code})
        return render_template('assignments.html', user=user, classDetails=classDetails, msg=msg, show=show, data=data)
    return render_template('assignments.html', user=user, classDetails=classDetails, msg=msg, show=show, data=data)


########## View Assignment ScoreCard ##########


@app.route('/viewassignment', methods=['GET', 'POST'])
def viewassignment():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    classdata = session['classDetails']
    code = classdata['code']
    classDetails = classes.find_one({'code': code})
    data = ""
    student = ""
    if request.method == 'POST':
        id = ObjectId(request.form['id'])
        data = assignment.find_one({'_id': id})
        submission = list(assignment_score.find({'aid': id}))
        session['submission'] = submission
        session['assgnmtdata'] = data
    return render_template('viewassignment.html', user=user, classDetails=classDetails, data=data)


@app.route('/submitassignment', methods=['POST'])
def submitAssignment():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    user = session['userdata']
    if request.method == 'POST':
        id = ObjectId(request.form['mainid'])
        if user['role'] == 'student':
            file = request.files['assignment']
            fileData = file.stream.read()
            fileName = file.filename
            content = file.content_type
            email = user['email']
            assignment_score.insert_one({
                'aid': id,
                'name': user['fname'] + " " + user['lname'],
                'email': email,
                'attachment': {'filename': fileName, 'filedata': fileData, 'content': content},
                'score': 'not released',
                'submission': datetime.now()
            })
        else:
            stdaid = ObjectId(request.form['id'])
            score = int(request.form['score'])
            assignment_score.update_one(
                {'_id': stdaid}, {'$set': {'score': score}})
        update_assngmt = assignment_score.find_one({'aid': id})
        data = assignment.find_one({'_id': id})
        session['assgnmtdata'] = data
        session['assgnmtscore'] = update_assngmt
        submission = list(assignment_score.find({'aid': id}))
        session['submission'] = submission
        return redirect(url_for('viewassignment'))
    return render_template('viewassignment.html')


@app.route('/viewfile', methods=['GET', 'POST'])
def viewfile():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    user = users.find_one({'email': email})
    classdata = session['classDetails']
    code = classdata['code']
    classDetails = classes.find_one({'code': code})
    if request.method == 'POST':
        if request.form['view'] == 'teacher':
            id = ObjectId(request.form['id'])
            data = assignment.find_one({'_id': id})
            content = data['content']
            file = b64encode(data['file']).decode('utf-8')
            if data:
                return render_template('viewfile.html', content=content, file=file, user=user, classDetails=classDetails)
        else:
            id = ObjectId(request.form['id'])
            data = assignment_score.find_one({'_id': id})
            attachment = data['attachment']
            content = attachment['content']
            file = b64encode(attachment['filedata']).decode('utf-8')
            if data:
                return render_template('viewfile.html', content=content, file=file, user=user, classDetails=classDetails)
    return render_template('viewfile.html', user=user, classDetails=classDetails)


########## Mark Notify #######
@app.route('/marknotify')
def mark():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')

    # Notifications
    notifications.update_many({'email': email}, {'$set': {'status': 'read'}})
    notifycount = notifications.count_documents(
        {'email': email, 'status': 'unread'})
    notifydata = list(notifications.find(
        {'email': email, 'status': 'unread'}))
    session['notifydata'] = notifydata
    session['notifycount'] = notifycount
    return redirect(request.referrer)


@app.route('/markdelete')
def markdelete():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')

    # Notifications
    notifications.delete_many({'email': email})
    notifycount = notifications.count_documents(
        {'email': email, 'status': 'unread'})
    notifydata = list(notifications.find(
        {'email': email, 'status': 'unread'}))
    session['notifydata'] = notifydata
    session['notifycount'] = notifycount
    return redirect(request.referrer)


@app.route('/notifications')
def showAllNotifications():
    if not session.get('user'):
        return redirect(url_for('login'))
    msg = ""
    email = session.get('user')
    return render_template('notifications.html')


############## Announcement ##############

@app.route('/announcement', methods=['POST'])
def postAnnouncement():
    if not session.get('user'):
        return redirect(url_for('login'))
    email = session.get('user')
    classDetails = session['classDetails']
    if request.method == 'POST' and request.form['lock'] == 'true':
        text = request.form['text']
        query = users.find_one({'email': email})
        result = announcement.find_one({'code': classDetails['code']})
        if result and len(result['comments']) == 0 and request.form['comment'] == 'true':
            name = query['fname'] + " " + query['lname']
            announcement.update_one({'code': classDetails['code']}, {
                                    '$push': {'comments': {'name': name, 'text': text}}})
            anndata = list(announcement.find({'code': classDetails['code']}))
            session['announcement'] = anndata
        else:
            if 'uploadOption' in request.form and request.form['uploadOption'] == 'link':
                link = request.form['link']
                announcement.insert_one({
                    'code': classDetails['code'],
                    'title': text,
                    'attachment': {'link': link},
                    'created': datetime.now(),
                    'comments': []
                })
                anndata = list(announcement.find(
                    {'code': classDetails['code']}))
                session['announcement'] = anndata
                return redirect(url_for('classDetails'))
            elif 'uploadOption' in request.form and request.form['uploadOption'] == 'file':
                file = request.files['fileUpload']
                fileData = file.stream.read()
                fileName = file.filename
                content = file.content_type
                announcement.insert_one({
                    'code': classDetails['code'],
                    'title': text,
                    'attachment': {'filename': fileName, 'filedata': fileData, 'content': content},
                    'created': datetime.now(),
                    'comments': []
                })
                anndata = list(announcement.find(
                    {'code': classDetails['code']}))
                session['announcement'] = anndata
                return redirect(url_for('classDetails'))
            elif 'uploadOption' in request.form and request.form['uploadOption'] == 'image':
                image = request.files['imageUpload']
                image_data = image.stream.read()
                image_name = image.filename
                content = image.content_type
                announcement.insert_one({
                    'code': classDetails['code'],
                    'title': text,
                    'attachment': {'filename': image_name, 'filedata': Binary(image_data), 'content': content},
                    'created': datetime.now(),
                    'comments': []
                })
                anndata = list(announcement.find(
                    {'code': classDetails['code']}))
                session['announcement'] = anndata
                return redirect(url_for('classDetails'))
            else:
                announcement.insert_one({
                    'code': classDetails['code'],
                    'title': text,
                    'created': datetime.now(),
                    'comments': []
                })
                anndata = list(announcement.find(
                    {'code': classDetails['code']}))
                session['announcement'] = anndata
                return redirect(url_for('classDetails'))
        anndata = list(announcement.find({'code': classDetails['code']}))
        session['announcement'] = anndata
        return redirect(url_for('classDetails'))
    return render_template('announcement.html')


########### Delete #############

@app.route('/delete', methods=['POST'])
def delete():
    if not session.get('user'):
        return redirect(url_for('login'))
    email = session.get('user')
    if request.method == 'POST':
        if request.form['delete'] == 'topic':
            topic_code = request.form['topic_code']
            topic.delete_one({'topic_code': topic_code})
            classdetails = session['classDetails']
            topics = list(topic.find({'code': classdetails['code']}))
            session['topics'] = topics
            return redirect(url_for('classDetails'))

########## View Announcement #############


@app.route('/viewannouncement', methods=['GET', 'POST'])
def viewAnnouncement():
    if not session.get('user'):
        return redirect(url_for('login'))
    email = session.get('user')
    if request.method == 'POST' and request.form['type'] == 'view':
        id = ObjectId(request.form['id'])
        anndata = announcement.find_one({'_id': id})
        session['anndata'] = anndata
        return render_template('viewannouncement.html')
    elif request.method == 'POST' and request.form['type'] == 'comment':
        id = ObjectId(request.form['id'])
        text = request.form['comment']
        query = users.find_one({'email': email})
        name = query['fname'] + " " + query['lname']
        announcement.update_one({'_id': id}, {
            '$push': {'comments': {'name': name, 'text': text, 'profile': query['profile'], 'posted': datetime.now()}}})
        anndata = announcement.find_one({'_id': id})
        session['anndata'] = anndata
        return redirect(url_for('viewAnnouncement'))
    elif request.method == 'POST' and request.form['type'] == 'remove':
        id = ObjectId(request.form['id'])
        announcement.delete_one({'_id': id})
        classdata = session['classDetails']
        anndata = list(announcement.find({'code': classdata['code']}))
        session['announcement'] = anndata
        return redirect(url_for('classDetails'))
    return render_template('viewannouncement.html')


@app.route('/viewannouncementfile', methods=['GET', 'POST'])
def viewAnnouncementFile():
    if not session.get('user'):
        return redirect(url_for('login'))
    email = session.get('user')
    if request.method == 'POST':
        id = ObjectId(request.form['file'])
        filedata = announcement.find_one({'_id': id})
        attachment = filedata['attachment']
        file = b64encode(attachment['filedata']).decode('utf-8')
        content = attachment['content']
        return render_template('viewfile.html', content=content, file=file)


@app.route('/classroomupdation', methods=['GET', 'POST'])
def crud():
    if not session.get('user'):
        return redirect(url_for('login'))
    email = session.get('user')
    user = users.find_one({'email': email})
    classdata = session['classDetails']
    if request.method == 'POST' and request.form['type'] == 'attachmentdlt':
        id = ObjectId(request.form['id'])
        announcement.update_one({'_id': id}, {'$unset': {'attachment': ''}})
        anndata = announcement.find_one({'_id': id})
        session['anndata'] = anndata
        return redirect(url_for('viewAnnouncement'))


########## LogOut ##########


@ app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('notifycount', None)
    session.pop('notifydata', None)
    return redirect(url_for('index'))


########## App Run ##########


if __name__ == '__main__':
    app.run(debug=True, port=9001)
