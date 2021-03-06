from flask import (Blueprint, 
                request, 
                render_template,
                jsonify,
                flash,
                redirect,
                current_app
                )
from flask_login import (login_required,
                    current_user
                    )
from utils import *
from base64 import b64decode
from models import *
import xlrd
from time import time
from os import remove, getenv
from flask_mail import Message
from decorators import only_for_student, only_for_teacher
# from mail import mail

routes = Blueprint('routes', __name__)


@routes.get('/dashboard')
@login_required
def dashboard_get():
    if current_user.is_teacher:
        return render_template("teacher/dashboard.html")
    else:
        return render_template("student/dashboard.html", create_roll=create_roll)

@routes.get('/course')
@only_for_student
@login_required
def course_get():
    student = current_user.student
    # course_stream = Course.stream
    av_course = Course.query.filter_by(semester=student.semester).all()
    o_course = None
    for course in av_course:
        if course.stream.lower() == student.department.lower():
            o_course = course
    return render_template("student/course.html", course=o_course)

@routes.get("/student-notes")
@login_required
@only_for_student
def student_notes_get():
    notes:list = Notes.query.filter(Notes.semester==current_user.student.semester, Notes.department==current_user.student.department).all()
    return render_template("student/notes.html", notes=notes)

@routes.get("/teacher-notes")
@login_required
@only_for_teacher
def teacher_notes_get():
    notes:list = list()
    for note in Notes.query.all():
        if note.subject.teacher == current_user.teacher:
            notes.append(note)
    return render_template("teacher/notes.html", notes=notes)

@routes.post("/student-profile-pic-upload")
@login_required
def image_upload_post():
    image_enc_data = request.get_json().get("image_enc_data").split(",")[1]
    with open(f"static/uploads/{current_user.email}.jpg", "wb") as f:
        f.write(b64decode(image_enc_data))
    student = Student.query.get(current_user.student.id)
    student.profile_image = f"static/uploads/{current_user.email}.jpg"
    db.session.commit()
    return jsonify(message="image added successfully", status=True), 200

@routes.post("/teacher-profile-pic-upload")
@login_required
def teacher_image_upload_post():
    image_enc_data = request.get_json().get("image_enc_data").split(",")[1]
    with open(f"static/uploads/{current_user.email}.jpg", "wb") as f:
        f.write(b64decode(image_enc_data))
    teacher = Teacher.query.get(current_user.teacher.id)
    teacher.profile_image = f"static/uploads/{current_user.email}.jpg"
    db.session.commit()
    return jsonify(message="image added successfully", status=True), 200


@routes.get("/student-ca-marks/")
@login_required
@only_for_student
def student_ca_marks_get():
    return render_template('student/ca-marks.html')

@routes.get("/teacher-ca-marks/")
@login_required
@only_for_teacher
def teacher_ca_marks_get():
    ca_marks:list = CAMarks.query.all()
    ca_ans:list = list()
    for cam in ca_marks:
        if cam.subject.teacher == current_user.teacher:
            ca_ans.append(cam)
    return render_template('teacher/ca-marks.html', ca_marks=ca_ans)

@routes.post("/teacher-ca-marks/")
@login_required
@only_for_teacher
def teacher_ca_marks_post():
    stream = request.form.get("stream")
    semester = request.form.get("semester")
    subject_id = request.form.get("subject")
    subject = Subject.query.get(int(subject_id))
    ca_marks:list = CAMarks.query.filter(CAMarks.subject == subject).all()
    ca_ans:list = list()
    for cam in ca_marks:
        if int(cam.student.semester) == int(semester) and cam.student.department.lower() == stream.lower():
            ca_ans.append(cam)

    return render_template('teacher/ca-marks.html', ca_marks=ca_ans)

@routes.get("/contact-us")
def contact_us_get():
    return render_template('contact-us.html')

@routes.post("/contact-us")
@login_required
def contact_us_post():
    name = request.form.get('name')
    email = request.form.get("email")
    message = request.form.get('message')
    message = f"{message}\n\nSender Name : {name}\nSender Email : {email}"
    msg = Message("A new contact us form received.", 
                sender=getenv("MAIL_USERNAME"), 
                recipients=[getenv("MAIL_RECEIVER")],
                reply_to=email,
                )
    msg.body = message
    current_app.extensions['mail'].send(msg)
    return jsonify(message="email sended!")

@routes.get("/student-routine")
@login_required
def student_routine_get():
    # semester = request.args.get("semester")
    # department = request.args.get("department")
    # routine = Routines.query.filter(Routines.department == department, Routines.semester == semester).first()
    return render_template("student/routine.html")   

# @routes.post("student-routine")
# @login_required
# def student_routine_post():
#     image_enc_data = request.get_json().get("image_enc_data").split(",")[1]
#     with open(f"static/uploads/{current_user.email}.jpg", "wb") as f:
#         f.write(b64decode(image_enc_data))
#         student = Student.query.get(current_user.student.id)
#         student.profile_image = f"static/uploads/{current_user.email}.jpg"
#         db.session.commit()
#         return jsonify(message="image added successfully", status=True), 200

@routes.get("/teacher-routine")
@login_required
@only_for_teacher
def teacher_routine_get():
    # semester = request.args.get("semester")
    # department = request.args.get("department")
    # routine = Routines.query.filter(Routines.department == department, Routines.semester == semester).first()
    return render_template("teacher/routine.html") 

@routes.post("/add-ca-marks-from-teacher")
# @login_required
def add_ca_marks_from_teacher_post():
    flag:bool = False
    excel_enc_data = request.get_json().get("excel_enc_data").split(",")[1]

    filename = f"{str(time())}.xlsx"

    with open(f"static/temp/{filename}", "wb") as f:
        f.write(b64decode(excel_enc_data))

    book = xlrd.open_workbook(f"static/temp/{filename}")

    sheet = book.sheet_by_index(0)

    db_header = ["Student_University_Roll", "Subject", "ca1", "ca2", "ca3", "ca4"]
    excel_header:list = sheet.row_values(0)

    if not excel_header == db_header:
        remove("static/temp/"+filename)
        return jsonify(message="Invalid excel sheet", status=False)

    for i in range(1, sheet.nrows):
        excel_student:list = sheet.row_values(i)
        excel_student_u_roll = int(excel_student[0])
        excel_student_subject_code = excel_student[1]
        excel_student_ca1 = int(excel_student[2])
        excel_student_ca2 = int(excel_student[3])
        excel_student_ca3 = int(excel_student[4])
        excel_student_ca4 = int(excel_student[5])

        student = Student.query.filter_by(university_roll=excel_student_u_roll).first()
        
        if student is not None:
            if student.ca_marks is []:
                subject = Subject.query.filter_by(code=excel_student_subject_code)
                if subject is None:
                    return jsonify(message="subject code dosen't exists", status=False)
                new_mark = CAMarks(ca1=int(excel_student[2]),
                                ca2 = int(excel_student[3]),
                                ca3 = int(excel_student[4]),
                                ca4 = int(excel_student[5]),
                                subject = subject,
                                student=student)
                db.session.add(new_mark)

            elif student.ca_marks is not None:
                for ca_mark in student.ca_marks:
                    if ca_mark.subject.code == excel_student_subject_code:
                        ca_mark.ca1 = excel_student_ca1
                        ca_mark.ca2 = excel_student_ca2
                        ca_mark.ca3 = excel_student_ca3
                        ca_mark.ca4 = excel_student_ca4
                        flag = True
                if not flag:
                    subject = Subject.query.filter_by(code=excel_student_subject_code)
                    if subject is None:
                        return jsonify(message="subject code dosen't exists", status=False)
                    new_mark = CAMarks(ca1=excel_student_ca1,
                            ca2 = excel_student_ca2,
                            ca3 = excel_student_ca3,
                            ca4 = excel_student_ca4,
                            subject = subject,
                            student=student)
                    db.session.add(new_mark)

        else:
            remove("static/temp/"+filename)
            return jsonify(message="invalid student university roll number present", status=False)
        
    db.session.commit()
    remove("static/temp/"+filename)
    return jsonify(message="successfully added CAMarks from excel sheet.", status=True)

@routes.get("/aniket")
def aniket():
    return render_template("teacher/student-profile.html")

@routes.post("/student-details")
@login_required
@only_for_teacher
def student_details_for_teacher():
    university_roll = request.form.get("university_roll")
    student = Student.query.filter_by(university_roll=university_roll).first()
    if student is None:
        flash("invalid student university roll number", "danger")
        return redirect("/dashboard")
    return render_template("teacher/student-profile.html", student=student)

@routes.post("/teacher-details")
@login_required
@only_for_student
def teacher_details_for_student():
    emp_id = request.form.get("emp_id")
    teacher = Teacher.query.filter_by(emp_id=emp_id).first()
    if teacher is None:
        flash("invalid teacher employee Id", "danger")
        return redirect("/dashboard")
    return render_template("student/teacher-profile.html", teacher=teacher)