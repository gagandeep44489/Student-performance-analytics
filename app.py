import os
from functools import wraps
from flask import Flask, jsonify, redirect, render_template, request, send_file, flash, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from models import db, User, Student, StudentMark
from utils.analytics import (
    get_class_comparison,
    get_grade_distribution,
    get_insights,
    get_student_averages,
    get_subject_performance,
)
from utils.io_helpers import generate_student_report, import_students_from_csv


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///student_analytics.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))
            if current_user.role not in roles:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@app.route("/")
@login_required
def dashboard():
    kpi = {
        "total_students": Student.query.count(),
        "total_marks_records": StudentMark.query.count(),
        "overall_average": round(sum(m.marks for m in StudentMark.query.all()) / max(StudentMark.query.count(), 1), 2),
        "highest_mark": round(max([m.marks for m in StudentMark.query.all()] or [0]), 2),
    }
    return render_template("dashboard.html", kpi=kpi)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"].lower().strip()
        password = request.form["password"]
        role = request.form.get("role", "Student")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("register"))

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower().strip()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


@app.route("/students", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Teacher")
def students():
    if request.method == "POST":
        student = Student(
            name=request.form["name"],
            roll_number=request.form["roll_number"],
            student_class=request.form["student_class"],
            section=request.form["section"],
        )
        db.session.add(student)
        db.session.commit()
        flash("Student added successfully.", "success")
        return redirect(url_for("students"))

    query = Student.query
    search = request.args.get("search", "").strip()
    class_filter = request.args.get("class", "").strip()
    if search:
        query = query.filter((Student.name.ilike(f"%{search}%")) | (Student.roll_number.ilike(f"%{search}%")))
    if class_filter:
        query = query.filter_by(student_class=class_filter)
    all_students = query.order_by(Student.id.desc()).all()
    return render_template("students.html", students=all_students)


@app.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
@role_required("Admin", "Teacher")
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash("Student deleted.", "success")
    return redirect(url_for("students"))


@app.route("/students/<int:student_id>/marks", methods=["POST"])
@login_required
@role_required("Admin", "Teacher")
def add_mark(student_id):
    student = Student.query.get_or_404(student_id)
    mark = StudentMark(student_id=student.id, subject=request.form["subject"], marks=float(request.form["marks"]))
    db.session.add(mark)
    db.session.commit()
    flash("Marks added.", "success")
    return redirect(url_for("students"))


@app.route("/analytics")
@login_required
def analytics():
    if request.headers.get("Accept") == "application/json":
        return jsonify(
            {
                "student_averages": get_student_averages(),
                "subject_performance": get_subject_performance(),
                "class_comparison": get_class_comparison(),
                "grade_distribution": get_grade_distribution(),
                "insights": get_insights(),
            }
        )
    return render_template("analytics.html")


@app.route("/upload", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Teacher")
def upload():
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or not file.filename.endswith(".csv"):
            flash("Please upload a valid CSV file.", "danger")
            return redirect(url_for("upload"))
        try:
            imported = import_students_from_csv(file)
            flash(f"CSV imported successfully. {imported} records added.", "success")
        except Exception as exc:
            flash(f"Import failed: {exc}", "danger")
        return redirect(url_for("upload"))
    return render_template("upload.html")


@app.route("/report/<int:student_id>")
@login_required
def report(student_id):
    student = Student.query.get_or_404(student_id)
    pdf_buffer = generate_student_report(student)
    return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=f"report_{student.roll_number}.pdf")


@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    print("Initialized the database.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
