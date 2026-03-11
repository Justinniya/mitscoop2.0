from flask import Flask, render_template, redirect, url_for, session,send_file,flash,request,Response
from flask_mysqldb import MySQL
import base64,io,csv
import pandas as pd
from datetime import datetime,timedelta




app = Flask(__name__)

def encode_b64(data):
    return base64.b64encode(data).decode() if data else None
app.jinja_env.filters['b64encode'] = encode_b64

app.secret_key = 'your_secret_key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'mitscoop2'
app.config['MYSQL_UNIX_SOCKET'] = '/opt/lampp/var/mysql/mysql.sock'


mysql = MySQL(app)



@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        address = request.form['address']
        contact = request.form['contact']
        position = request.form['position']
        status = request.form['status']
        username = request.form['username']
        email = request.form['email']
        pwd = request.form['password']
        con_password = request.form['con_password']

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM user WHERE email = %s', (email,))
        email_count = cursor.fetchone()[0]
        cursor.close()

        if email_count > 0:
            flash('⚠️ Email is already in use.')
            return redirect(url_for('register'))
        elif pwd != con_password:
            flash('⚠️ Passwords do not match.')
            return redirect(url_for('register'))

    
        cursor = mysql.connection.cursor()
        cursor.execute(
            'INSERT INTO user (name, age, address, gender, contact, status, position, email, password,username) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (name, age, address, gender, contact, status, position, email, pwd,username)
        )
        mysql.connection.commit()

        user_id = cursor.lastrowid
        session['user_id'] = user_id

        cursor.close()

        return redirect(url_for('landing')) 
    else:
        return render_template('register.html')

@app.route('/', methods=["GET", "POST"])
def landing():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM user WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()

        if username == "admin" and password == "admin":
            session['user_id'] = "admin"
            return redirect(url_for('admin_dashboard'))


        if user:
            session['user_id'] = user[0] 
            session['name'] = user[1]
            return redirect(url_for('home'))
        else:
            flash('Wrong username or password')
            return redirect(url_for('landing'))

    return render_template('landing.html')

@app.route('/home')
def home():
    cur = mysql.connection.cursor()
    current_time = datetime.now()
    user_id = session.get('user_id')
    cur.execute("""
        UPDATE tasks 
        SET status = 'missed' 
        WHERE due_datetime < %s AND status != 'Completed' AND status != 'missed'
    """, (current_time,))
    mysql.connection.commit()
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s AND status = 'pending'", (user_id,))
        task_count = cursor.fetchone()[0]
        cursor.close()
    else:
        task_count = 0
    
    return render_template('home.html', task_count=task_count)
    

@app.route('/report', methods=["GET", "POST"])
def report():
    if 'user_id' not in session:
        return redirect(url_for('landing'))
    
    user_id = session['user_id']  

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY due_datetime DESC", (user_id,))
    tasks = cursor.fetchall()
    print(tasks)
    cursor.close()

    current_time = datetime.now()
    print(current_time)

    return render_template('report.html', tasks=tasks, current_time=current_time)
    
@app.route('/view_report/<int:id>',methods=["POST","GET"])
def view_report(id):
    if 'user_id' not in session:
        return redirect(url_for('landing'))
    
    user_id = session['user_id']  

    if request.method == "POST":
        message = request.form.get('message')  
        image = request.files.get('image')   
        task_des = request.form.get('task_des')

        if image:  
            image_data = image.read()

            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO report (message, image,user_id,status,task_des) VALUES (%s, %s,%s, %s,%s)", (message, image_data,user_id,'review',task_des))
            mysql.connection.commit()
            cursor.close()

            if user_id:
                cursor = mysql.connection.cursor()
                cursor.execute(f"DELETE FROM tasks WHERE user_id = %s AND id = %s", (user_id,id))
                mysql.connection.commit()

                if cursor.rowcount == 0:
                    print(f"No task updated for task_id {id} and user_id {user_id}")
                else:
                    print(f"Task {id} status updated successfully.")
        return redirect(url_for("home"))

        

    else:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM tasks WHERE user_id = %s AND id = %s", (user_id,id))
        tasks = cursor.fetchone()
        cursor.close()
        if tasks:

            return render_template('view_report.html', tasks=tasks)
        else:
            return redirect('/report')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
         return redirect(url_for('landing'))


    user_id = session['user_id']  
    cursor = mysql.connection.cursor()
    cursor.execute("""
    SELECT name, age, address, gender, status, contact, position,email
    FROM user
    WHERE user_id = %s
    """, (user_id,))


    user_data = cursor.fetchone()
    cursor.close()
   

    if user_data:
        return render_template('profile.html', 
                               name=user_data[0], 
                               age=user_data[1], 
                               address=user_data[2], 
                               gender=user_data[3],
                               status=user_data[4],
                               contact=user_data[5],
                               position=user_data[6],
                                email=user_data[7])
    
    else:
        return redirect(url_for('landing')) 
    
@app.route('/admin_dashboard')
def admin_dashboard():
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM report")
    total_reports = cursor.fetchone()[0]

    
    cursor.execute("SELECT COUNT(*) FROM report WHERE status = 'review'")
    to_be_evaluated_reports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM report WHERE status = 'approved'")
    approved_reports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM report WHERE status = 'rejected'")
    rejected_reports = cursor.fetchone()[0]

    
    to_be_evaluated_percentage = (to_be_evaluated_reports / total_reports) * 100 if total_reports > 0 else 0
    approved_percentage = (approved_reports / total_reports) * 100 if total_reports > 0 else 0
    pending_percentage = (rejected_reports / total_reports) * 100 if total_reports > 0 else 0

   
    cursor.execute("""
        SELECT u.user_id, u.name, COUNT(r.report_id) AS reports_submitted
        FROM user u
        LEFT JOIN report r ON u.user_id = r.user_id
        GROUP BY u.user_id
    """)
    users_reports = cursor.fetchall()  

    cursor.execute("SELECT COUNT(report_id) FROM report")
    total_reports = cursor.fetchone()
    
    cursor.close()
    print(total_reports)
    return render_template(
        'admin_dashboard.html',
        to_be_evaluated_percentage=to_be_evaluated_percentage,
        approved_percentage=approved_percentage,
        pending_percentage=pending_percentage,
        users_reports=users_reports,total_reports=total_reports
    )

@app.route('/check/<int:report_id>', methods=['GET', 'POST'])
def check(report_id):
    if 'user_id' not in session:
        return redirect(url_for('landing'))

    if request.method == 'POST':
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE report SET status = 'approved' WHERE report_id = %s", (report_id,))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('admin_list_report')) 
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT report_id, message, image, status FROM report")
    reports = cursor.fetchall()
    cursor.close()

    return render_template('admin_list_report.html', reports=reports)




@app.route('/view/<int:report_id>')
def view(report_id):
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT image FROM report WHERE report_id = %s", (report_id,))
    report = cursor.fetchone()


    if report and report[0]:
        image_data = report[0] 
        
        
        return send_file(io.BytesIO(image_data), mimetype='image/jpeg')

    else:
        return "Image not found", 404
    
@app.route('/view_photo/<int:report_id>')
def view_photo(report_id):
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT image FROM tasks WHERE id = %s", (report_id,))
    report = cursor.fetchone()


    if report and report[0]:
        image_data = report[0] 
        
        
        return send_file(io.BytesIO(image_data), mimetype='image/jpeg')

    else:
        return "Image not found", 404
    

@app.route('/delete/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    
        cursor = mysql.connection.cursor()

        cursor.execute("DELETE FROM report WHERE report_id = %s", (report_id,))
       
        mysql.connection.commit()

        return redirect(url_for('check'))

@app.route('/delete_task/<int:task_id>', methods=["POST","GET"])
def delete_task(task_id):
    user_id = session['user_id']  
    cursor = mysql.connection.cursor()
    cursor.execute(f"DELETE FROM tasks WHERE user_id = %s AND id = %s", (user_id,task_id))
    
    mysql.connection.commit()

    return redirect(url_for('report'))


@app.route('/reject_task/<int:task_id>', methods=["POST","GET"])
def reject_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('landing'))

    if request.method == 'POST':
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE report SET status = 'rejected' WHERE report_id = %s", (task_id,))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('admin_list_report')) 
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT report_id, message, image, status FROM report")
    reports = cursor.fetchall()
    cursor.close()

    return render_template('admin_list_report.html', reports=reports)



@app.route('/admin_record')
def admin_record():
    cur = mysql.connection.cursor()
    current_date = datetime.now()
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    start_of_week_str = start_of_week.strftime('%Y-%m-%d')
    end_of_week_str = end_of_week.strftime('%Y-%m-%d')

    cur.execute("""
        SELECT u.user_id, u.name, a.date, a.time, a.status
        FROM user u
        RIGHT JOIN attendance a 
            ON u.user_id = a.user_id 
            
                 """,
                #  AND a.date BETWEEN %s AND %s
    #  (start_of_week_str, end_of_week_str)
    )
    attendance_records = cur.fetchall()  # returns tuples
    cur.close()
    print(attendance_records)

    return render_template('admin_record.html', attendance=attendance_records)




@app.route('/logs')
def logs():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    
    

    # --- TASKS ---
    cur.execute("""
        SELECT due_datetime AS datetime, task_description AS description, status, 'Task' AS type
        FROM tasks
        WHERE user_id = %s
    """, (user_id,))
    task_logs = list(cur.fetchall())

    # --- ATTENDANCE ---
    cur.execute("""
        SELECT 
            STR_TO_DATE(CONCAT(date, ' ', time), '%%Y-%%m-%%d %%H:%%i:%%s') AS datetime,
            status AS description,
            status,
            'Attendance' AS type
        FROM attendance
        WHERE user_id = %s
    """, (user_id,))
    attendance_logs = list(cur.fetchall())


    # --- REPORTS ---
    cur.execute("""
        SELECT report_date AS datetime, message AS description, status, 'Report' AS type
        FROM report
        WHERE user_id = %s
    """, (user_id,))
    report_logs = list(cur.fetchall())

    cur.close()

    # --- Combine all logs ---
    all_logs = task_logs + attendance_logs + report_logs

    # --- Convert string timestamps to datetime objects ---
    def to_datetime(value):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except:
            try:
                return datetime.strptime(value, "%Y-%m-%d")
            except:
                return datetime.now()

    all_logs = [(to_datetime(log[0]), log[1], log[2], log[3]) for log in all_logs]

    all_logs.sort(key=lambda x: x[0], reverse=True)

    return render_template('logs.html', logs=all_logs)



@app.route('/help')
def help():
    
    return render_template("help.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))


@app.route('/attendance')
def attendance():
    user_id = session.get('user_id')
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM attendance WHERE user_id = %s", (user_id,))
        attendance = cursor.fetchall()
        return render_template('attendance.html',attendance=attendance)
    else:
        return redirect('/')

@app.route('/list_report')
def list_report():
    cursor = mysql.connection.cursor()
    user_id = session['user_id']
    cursor.execute("""
        SELECT report.report_id, report.message, user.name, report.task_des
        FROM report
        JOIN user ON report.user_id = user.user_id
        WHERE user.user_id = %s
    """, (user_id,))
    
    report = cursor.fetchall()
    cursor.close()
    return render_template('list_report.html',report=report)

@app.route('/admin_list_report')
def admin_list_report():
    status = request.args.get('status')  # e.g. 'approved', 'rejected', 'review'
    cursor = mysql.connection.cursor()

    if status:
        cursor.execute("""
            SELECT report.report_id, report.message, user.name, report.task_des, report.status
            FROM report
            JOIN user ON report.user_id = user.user_id
            WHERE report.status = %s
            ORDER BY report.report_id DESC
        """, (status,))
    else:
        cursor.execute("""
            SELECT report.report_id, report.message, user.name, report.task_des, report.status
            FROM report
            JOIN user ON report.user_id = user.user_id
            ORDER BY report.report_id DESC
        """)

    report = cursor.fetchall()
    cursor.close()

    return render_template('admin_list_report.html', report=report, selected_status=status)


@app.route('/admin_add_task', methods=['GET', 'POST'])
def admin_add_task():
    cursor = mysql.connection.cursor()
    
    if request.method == 'POST':
        # user_id = request.form.get('user_id')
        task_description = request.form.get('task_description')
        due_date = request.form.get('due_date')
        due_time = request.form.get('due_time')
        task_attachment = request.files.get('task_attachment')

        if task_attachment:
            task_attachment_file = task_attachment.read()
            cursor.execute("SELECT user_id FROM user")
            users = cursor.fetchall()
            print(users)
            if task_description and due_date and due_time:
                try:
                    for user_id in users:
                        due_datetime = f"{due_date} {due_time}"

                        cursor.execute("""
                            INSERT INTO tasks (user_id, task_description, due_datetime,image)
                            VALUES (%s, %s, %s,%s)
                        """, (user_id, task_description, due_datetime,task_attachment_file))
                        mysql.connection.commit()
                        flash("Task assigned successfully.", "success")
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f"Error: {str(e)}", "danger")
            else:
                flash("Please fill in all fields.", "warning")

            cursor.close()
            return redirect(url_for('admin_add_task'))
    
    cursor.execute("SELECT user_id, name FROM user")
    users = cursor.fetchall()
    cursor.close()

    return render_template('admin_add_task.html', users=users)
    

@app.route('/monitor')
def monitor():
    return render_template('monitor.html')

@app.route('/admin_check_attendance', methods=['GET', 'POST'])
def admin_check_attendance():
    print("check attendance")
    if request.method == 'POST':
        print("posting")
        cursor = mysql.connection.cursor()
        user_id = request.form.get('user_id')
        time = request.form.get('time')  
        status = request.form.get('status')

        cursor.execute("SELECT * FROM user WHERE user_id = %s", (user_id,))
        employee = cursor.fetchone()

        if not employee:
            return render_template('admin_check_attendance.html', message="Employee not found.")

        cursor.execute("""
            SELECT * FROM attendance WHERE user_id = %s AND time = %s
        """, (user_id, time))
        existing_attendance = cursor.fetchone()

        # if existing_attendance:
        #     cursor.execute("""
        #         UPDATE attendance
        #         SET time = %s, status = %s
        #         WHERE user_id = %s AND time = %s
        #     """, (status, user_id, time))
        #     mysql.connection.commit()
        #     message = "Attendance updated successfully."
        # else:
        cursor.execute("""
            INSERT INTO attendance (user_id,time,status)
            VALUES (%s, %s, %s)
        """, (user_id, time, status))
        mysql.connection.commit()
        message = "Attendance recorded successfully."
        
        cursor.close()
        return render_template('admin_check_attendance.html', message=message)

    else:
        print("getting")
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM user")
        users = cursor.fetchall()
        print(users)

        if not users:
            return render_template('check_attendance.html', message="No employees found in the database.")
        
        cursor.close()
        
        return render_template('admin_check_attendance.html', users=users)

@app.route('/all_reports')
def all_reports():
    cur = mysql.connection.cursor()

    # --- Load base user info (from user table) ---
    cur.execute("SELECT user_id, name FROM user")
    user_df = pd.DataFrame(cur.fetchall(), columns=["user_id", "name"])

    # --- Attendance ---
    cur.execute("SELECT user_id, status FROM attendance")
    attendance_df = pd.DataFrame(cur.fetchall(), columns=["user_id", "status"])
    attendance_df = attendance_df.merge(user_df, on="user_id", how="left")
    att_summary = attendance_df.groupby(["user_id", "status"]).size().unstack(fill_value=0)

    # --- Tasks ---
    cur.execute("SELECT user_id, status FROM tasks")
    task_df = pd.DataFrame(cur.fetchall(), columns=["user_id", "status"])
    task_df = task_df.merge(user_df, on="user_id", how="left")
    task_summary = task_df.groupby(["user_id", "status"]).size().unstack(fill_value=0)

    # --- Reports ---
    cur.execute("SELECT user_id, status FROM report")
    report_df = pd.DataFrame(cur.fetchall(), columns=["user_id", "status"])
    report_df = report_df.merge(user_df, on="user_id", how="left")
    report_summary = report_df.groupby(["user_id", "status"]).size().unstack(fill_value=0)

    # --- Calculate percentages per user ---
    final_users = []
    for _, user in user_df.iterrows():
        uid = user["user_id"]
        name = user["name"]

        # Attendance %
        if uid in att_summary.index:
            p = att_summary.loc[uid].get("present", 0)
            a = att_summary.loc[uid].get("absent", 0)
            total = p + a
            att_pct = round((p / total) * 100, 2) if total > 0 else 0
        else:
            att_pct = 0

        # Task %
        if uid in task_summary.index:
            c = task_summary.loc[uid].get("completed", 0)
            p = task_summary.loc[uid].get("pending", 0)
            total = c + p
            task_pct = round((c / total) * 100, 2) if total > 0 else 0
        else:
            task_pct = 0

        # Report %
        if uid in report_summary.index:
            appr = report_summary.loc[uid].get("approved", 0)
            rej = report_summary.loc[uid].get("rejected", 0)
            rev = report_summary.loc[uid].get("review", 0)
            total = appr + rej + rev
            report_pct = round((appr / total) * 100, 2) if total > 0 else 0
        else:
            report_pct = 0

        # Average %
        avg_pct = round((att_pct + task_pct + report_pct) / 3, 2)

        # --- Insert or Update users table ---
        cur.execute("""
            INSERT INTO users (id, name, attendance, tasks, reports)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                attendance = VALUES(attendance),
                tasks = VALUES(tasks),
                reports = VALUES(reports)
        """, (uid, name, att_pct, task_pct, report_pct,))

        final_users.append({
            "id": uid,
            "name": name,
            "attendance": att_pct,
            "tasks": task_pct,
            "reports": report_pct,
            "status": 'Active'
        })

    mysql.connection.commit()

    # --- Fetch updated users for frontend ---
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    # cur.close()

    final_users = []
    for each_user in users:
        cur.execute("SELECT * FROM user WHERE user_id = %s", (each_user[0],))
        user = cur.fetchone()
        print(user)
        final_users.append({
            'id': each_user[0],
            'name': each_user[1],
            'attendance': each_user[2],
            'tasks': each_user[3],
            'reports': each_user[4],
            'status': each_user[5],
            'account_status': user[5]
        })
        

    # Attendance data
    cur.execute("SELECT user_id, status FROM attendance")
    attendance_df = pd.DataFrame(cur.fetchall(), columns=["user_id", "status"])

    # Tasks data
    cur.execute("SELECT user_id, status FROM tasks")
    task_df = pd.DataFrame(cur.fetchall(), columns=["user_id", "status"])

    # Reports data
    cur.execute("SELECT user_id, status FROM report")
    report_df = pd.DataFrame(cur.fetchall(), columns=["user_id", "status"])

    # User data
    cur.execute("SELECT user_id, name FROM user")
    user_df = pd.DataFrame(cur.fetchall(), columns=["user_id", "name"])
    cur.close()

    # Merge and summarize attendance
    attendance_df = attendance_df.merge(user_df, on="user_id", how="left")
    att_summary = attendance_df.groupby(["name", "status"]).size().unstack(fill_value=0)
    att_labels = att_summary.index.tolist()
    att_present = att_summary.get("present", pd.Series([0]*len(att_labels))).tolist()
    att_absent = att_summary.get("absent", pd.Series([0]*len(att_labels))).tolist()

    # Merge and summarize tasks
    task_df = task_df.merge(user_df, on="user_id", how="left")
    task_summary = task_df.groupby(["name", "status"]).size().unstack(fill_value=0)
    task_labels = task_summary.index.tolist()
    task_pending = task_summary.get("pending", pd.Series([0]*len(task_labels))).tolist()
    task_completed = task_summary.get("completed", pd.Series([0]*len(task_labels))).tolist()

    # Merge and summarize reports
    report_df = report_df.merge(user_df, on="user_id", how="left")
    report_summary = report_df.groupby(["name", "status"]).size().unstack(fill_value=0)
    report_labels = report_summary.index.tolist()
    report_approved = report_summary.get("approved", pd.Series([0]*len(report_labels))).tolist()
    report_rejected = report_summary.get("rejected", pd.Series([0]*len(report_labels))).tolist()
    report_review = report_summary.get("review", pd.Series([0]*len(report_labels))).tolist()

    return render_template(
        "all_reports.html",
        att_labels=att_labels,
        att_present=att_present,
        att_absent=att_absent,
        task_labels=task_labels,
        task_pending=task_pending,
        task_completed=task_completed,
        report_labels=report_labels,
        report_approved=report_approved,
        report_rejected=report_rejected,
        report_review=report_review,
        final_users=final_users
    )


@app.route("/warn/<int:user_id>", methods=["POST"])
def warn_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET status=%s WHERE id=%s", ("Warning", user_id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for("all_reports"))

# Route to suspend a user
@app.route("/suspend/<int:user_id>", methods=["POST"])
def suspend_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET status=%s WHERE id=%s", ("Suspended", user_id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for("all_reports"))

# (Optional) Route to reset to appreciation
@app.route("/appreciate/<int:user_id>", methods=["POST"])
def appreciate_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET status=%s WHERE id=%s", ("Appreciation", user_id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for("all_reports"))

@app.route('/status_user/<int:user_id>/<action>', methods=['POST'])
def status_user(user_id, action):
    cur = mysql.connection.cursor()
    if action == 'warning':
        cur.execute("UPDATE user SET status=%s WHERE user_id=%s", ("Warning", user_id))
    elif action == 'suspend':
        cur.execute("UPDATE user SET status=%s WHERE user_id=%s", ("Suspended", user_id))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for("all_reports"))



















# @app.route('/test_att')
# def test_att():
#     cur = mysql.connection.cursor()
#     current_date = datetime.now()
#     start_of_week = current_date - timedelta(days=current_date.weekday())
#     end_of_week = start_of_week + timedelta(days=6)

#     start_of_week_str = start_of_week.strftime('%Y-%m-%d')
#     end_of_week_str = end_of_week.strftime('%Y-%m-%d')

#     cur.execute("""
#         SELECT u.user_id, u.name, a.date, a.time, a.status
#         FROM user u
#         RIGHT JOIN attendance a 
#             ON u.user_id = a.user_id 
#             AND a.date BETWEEN %s AND %s
#     """, (start_of_week_str, end_of_week_str))
#     attendance_records = cur.fetchall()  # returns tuples
#     cur.close()
#     print(attendance_records)
#     return render_template('test_attendance.html', attendance=attendance_records)


@app.route('/upload_attendance', methods=['POST'])
def upload_attendance():
    if 'file' not in request.files:
        flash("No file part", "danger")
        return redirect(url_for('index'))

    file = request.files['file']
    if not file or file.filename.strip() == '':
        flash("No selected file", "danger")
        return redirect(url_for('admin_record'))

    if not file.filename.endswith('.csv'):
        flash("Invalid file type. Please upload a CSV file.", "danger")
        return redirect(url_for('admin_record'))

    # Read CSV
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)

    # ✅ Skip header row
    next(csv_input, None)

    cur = mysql.connection.cursor()
    inserted, skipped = 0, 0

    for row in csv_input:
        # CSV format: user_id, name, date, time, status
        if len(row) < 5:
            skipped += 1
            continue

        user_id, name, date, time, status = row[0], row[1], row[2], row[3], row[4]

        try:
            # ✅ Check if user exists
            cur.execute("SELECT COUNT(*) FROM user WHERE user_id=%s", (user_id,))
            if cur.fetchone()[0] == 0:
                print(f"Skipping row: user_id {user_id} not found")
                skipped += 1
                continue

            # ✅ Prevent duplicate attendance
            cur.execute(
                "SELECT COUNT(*) FROM attendance WHERE user_id=%s AND date=%s AND time=%s AND status=%s",
                (user_id, date, time, status)
            )
            exists = cur.fetchone()[0]

            if not exists:
                cur.execute(
                    "INSERT INTO attendance (user_id, date, time, status) VALUES (%s, %s, %s, %s)",
                    (user_id, date, time, status)
                )
                inserted += 1
            else:
                skipped += 1

        except Exception as e:
            print("Skipping row due to error:", e)
            skipped += 1

    mysql.connection.commit()
    cur.close()
    flash(f"Attendance uploaded successfully! Inserted: {inserted}, Skipped: {skipped}", "success")
    return redirect(url_for('admin_record'))




# ---------------- Download Attendance ----------------
@app.route('/download_attendance')
def download_attendance():
    cur = mysql.connection.cursor()
    current_date = datetime.now()
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    start_of_week_str = start_of_week.strftime('%Y-%m-%d')
    end_of_week_str = end_of_week.strftime('%Y-%m-%d')

    cur.execute("""
        SELECT u.user_id, u.name, a.date, a.time, a.status
        FROM user u
        RIGHT JOIN attendance a 
            ON u.user_id = a.user_id 
            
    """
    )
    attendance_records = cur.fetchall() 
    cur.close()

    # Write CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['user_id','name', 'date', 'time', 'status'])
    writer.writerows(attendance_records)

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=attendance.csv"
    return response






if __name__ == "__main__":
    app.run(debug=True)



# fixing upload data for attendance adjusting the all_report with user compliance