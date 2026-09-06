from functools import wraps
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from academics.models import Assignment, Marks, Subject
from attendance.models import Attendance
from students.models import ClassRoom, Student
from accounts.models import User


# recommend by chatgpt
def student_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        logged_student_id = request.session.get("student_id")
        requested_student_id = kwargs.get("student_id")

        # Student is not logged in
        if not logged_student_id:
            return redirect("student-lookup")

        # Prevent one student from accessing another student's data
        if requested_student_id is not None:
            if int(logged_student_id) != int(requested_student_id):
                return redirect(
                    "student-dashboard",
                    student_id=logged_student_id
                )

        return view_func(request, *args, **kwargs)
    return wrapper


# @login_required
# def student(request):

#     # ADMIN / SUPERUSER
#     if request.user.role == "ADMIN" or request.user.is_superuser:

#         # All students with classroom information
#         students = (
#             Student.objects
#             .select_related("classroom", "classroom__teacher")
#             .all()
#             .order_by("classroom__name", "classroom__section", "name")
#         )

#         context = {
#             "classroom": None,
#             "student_count": students.count(),
#             "subject_count": Subject.objects.count(),
#             "students": students,
#             "is_admin": True,
#         }

#         return render(
#             request,
#             "students/student_list.html",
#             context
#         )


#     # TEACHER
#     classroom = ClassRoom.objects.filter(
#         teacher=request.user
#     ).first()

#     if not classroom:

#         messages.error(
#             request,
#             "No classroom assigned to you."
#         )

#         return redirect("dashboard")


#     students = (
#         Student.objects
#         .filter(classroom=classroom)
#         .select_related("classroom")
#         .order_by("name")
#     )


#     student_count = students.count()

#     subject_count = Subject.objects.filter(
#         classroom=classroom
#     ).count()


#     context = {
#         "classroom": classroom,
#         "student_count": student_count,
#         "subject_count": subject_count,
#         "students": students,
#         "is_admin": False,
#     }


#     return render(
#         request,
#         "students/student_list.html",
#         context
#     )

@login_required
def admin_students(request):
    # Get all students in the school
    students = Student.objects.select_related("classroom").all()

    # Total number of students
    student_count = students.count()

    # Total number of classrooms
    classroom_count = ClassRoom.objects.count()

    # Total number of subjects
    subject_count = Subject.objects.count()

    # Total number of teachers
    teacher_count = User.objects.filter(role="TEACHER").count()

    context = {
        "students": students,
        "student_count": student_count,
        "classroom_count": classroom_count,
        "subject_count": subject_count,
        "teacher_count": teacher_count,
    }

    return render(request, "students/admin_student.html", context)




def student(request):
    classroom = ClassRoom.objects.filter(teacher=request.user).first()
    student_count = 0
    subject_count = 0

    students = Student.objects.filter(classroom=classroom)

    if classroom:
        student_count = classroom.students.count()
        subject_count = Subject.objects.filter(classroom=classroom).count()

    context = {
        "classroom": classroom,
        "student_count": student_count,
        "subject_count": subject_count,
        "students": students,
    }
    return render(request, "students/student_list.html", context)


# def student_lookup(request):
#     if request.method == "POST":
#         student_id = request.POST.get("student_id", "").strip()
#         if student_id.isdigit():
#             student = Student.objects.filter(pk=int(student_id)).first()
#             if student:
#                 return redirect("student-dashboard", student_id=student.pk)

#         return render(
#             request,
#             "students/student_lookup.html",
#             {
#                 "error_message": "No student found with that Student ID. Please try again."
#             },
#         )

#     return render(request, "students/student_lookup.html")



def student_lookup(request):
    if request.method == "POST":

        student_id = request.POST.get("student_id")
        # phone = request.POST.get("phone")
        date_of_birth=request.POST.get("date_of_birth")

        try:
            student = Student.objects.get(
                id=student_id,
                date_of_birth=date_of_birth,
            )
            request.session["student_id"] = student.id
            return redirect(
                "student-dashboard",
                student_id=student.id
            )

        except Student.DoesNotExist:

            return render(
                request,
                "students/student_lookup.html",
                {
                    "error_message": "Invalid Student ID or Date of birth."
                }
            )

    return render(request, "students/student_lookup.html")


# login required

@student_login_required
def student_dashboard(request, student_id):
    student = get_object_or_404(
        Student.objects.select_related("classroom"),
        pk=student_id,
    )

    marks_qs = Marks.objects.filter(student=student).select_related("subject")
    attendance_qs = Attendance.objects.filter(student=student)

    total_full_marks = sum(mark.full_marks or 0 for mark in marks_qs)
    total_obtained_marks = sum(mark.marks_obtained or 0 for mark in marks_qs)
    overall_percentage = (
        round((total_obtained_marks / total_full_marks) * 100, 2)
        if total_full_marks
        else 0
    )

    present_days = attendance_qs.filter(status="PRESENT").count()
    total_days = attendance_qs.count()
    attendance_percentage = (
        round((present_days / total_days) * 100, 2) if total_days else 0
    )

    subject_count = Subject.objects.filter(classroom=student.classroom).count()
    assignment_count = Assignment.objects.filter(classroom=student.classroom).count()
    report_exam = (
        marks_qs.values_list("exam_name", flat=True)
        .distinct()
        .order_by("exam_name")
        .first()
        or "Mid-Term"
    )

    context = {
        "student": student,
        "student_id": student.id,
        "classroom": student.classroom,
        "overall_percentage": overall_percentage,
        "attendance_percentage": attendance_percentage,
        "subject_count": subject_count,
        "assignment_count": assignment_count,
        "report_exam": report_exam,
    }
    return render(request, "students/student_dashboard.html", context)



# login required
@student_login_required
def student_marks(request, student_id):
    student = get_object_or_404(Student.objects.select_related("classroom"), pk=student_id)
    marks = (
        Marks.objects.filter(student=student)
        .select_related("subject")
        .order_by("subject__name", "exam_name")
    )

    mark_rows = []
    for mark in marks:
        full_marks = mark.full_marks or 0
        obtained_marks = mark.marks_obtained or 0
        percentage = (
            round((obtained_marks / full_marks) * 100, 2) if full_marks else 0
        )
        mark_rows.append(
            {
                "subject": mark.subject.name,
                "exam_name": mark.exam_name,
                "marks_obtained": obtained_marks,
                "full_marks": full_marks,
                "percentage": percentage,
            }
        )

    context = {"student": student, "mark_rows": mark_rows}
    return render(request, "students/student_marks.html", context)


# login requird

@student_login_required
def student_attendance(request, student_id):
    student = get_object_or_404(Student.objects.select_related("classroom"), pk=student_id)
    attendance_records = (
        Attendance.objects.filter(student=student)
        .order_by("-date")
    )

    present_days = attendance_records.filter(status="PRESENT").count()
    absent_days = attendance_records.filter(status="ABSENT").count()
    total_days = attendance_records.count()
    attendance_percentage = (
        round((present_days / total_days) * 100, 2) if total_days else 0
    )

    context = {
        "student": student,
        "attendance_records": attendance_records,
        "present_days": present_days,
        "absent_days": absent_days,
        "total_days": total_days,
        "attendance_percentage": attendance_percentage,
    }
    return render(request, "students/student_attendance.html", context)


# login required

@student_login_required
def student_report_card(request, student_id, exam_name=None):
    student = get_object_or_404(Student.objects.select_related("classroom"), pk=student_id)
    if not exam_name:
        exam_name = (
            Marks.objects.filter(student=student)
            .values_list("exam_name", flat=True)
            .distinct()
            .order_by("exam_name")
            .first()
            or "Mid-Term"
        )

    marks = (
        Marks.objects.filter(student=student, exam_name=exam_name)
        .select_related("subject", "student__classroom")
        .order_by("subject__name")
    )

    subject_rows = []
    total_full_marks = 0
    total_obtained_marks = 0

    for mark in marks:
        full_marks = mark.full_marks or 0
        obtained_marks = mark.marks_obtained or 0
        percentage = round((obtained_marks / full_marks) * 100, 2) if full_marks else 0
        total_full_marks += full_marks
        total_obtained_marks += obtained_marks

        subject_rows.append(
            {
                "subject": mark.subject.name,
                "full_marks": full_marks,
                "obtained_marks": obtained_marks,
                "percentage": percentage,
            }
        )

    overall_percentage = (
        round((total_obtained_marks / total_full_marks) * 100, 2)
        if total_full_marks
        else 0
    )

    if overall_percentage >= 90:
        grade = "A+"
    elif overall_percentage >= 80:
        grade = "A"
    elif overall_percentage >= 70:
        grade = "B+"
    elif overall_percentage >= 60:
        grade = "B"
    elif overall_percentage >= 50:
        grade = "C"
    else:
        grade = "F"

    result = "PASS" if overall_percentage >= 40 else "FAIL"

    if overall_percentage >= 90:
        remarks = "Outstanding Performance"
    elif overall_percentage >= 80:
        remarks = "Excellent Work"
    elif overall_percentage >= 70:
        remarks = "Very Good Performance"
    elif overall_percentage >= 60:
        remarks = "Good Effort"
    elif overall_percentage >= 50:
        remarks = "Satisfactory"
    else:
        remarks = "Needs Improvement"

    context = {
        "student": student,
        "exam_name": exam_name,
        "subject_rows": subject_rows,
        "total_full_marks": total_full_marks,
        "total_obtained_marks": total_obtained_marks,
        "overall_percentage": overall_percentage,
        "grade": grade,
        "result": result,
        "remarks": remarks,
        "school_name": "Jhime Malika Secondary School ",
        "school_address": "K.i singh 04, doti",
        "report_title": "Report Card",
        "academic_session": "2026",
    }
    return render(request, "students/student_report_card.html", context)





@login_required
def admin_report_cards(request):

    search = request.GET.get("search", "").strip()
    classroom_id = request.GET.get("classroom", "").strip()
    exam_name = request.GET.get("exam_name", "").strip()

    students = Student.objects.select_related(
        "classroom"
    ).all()

    # Search
    if search:

        if search.isdigit():

            students = students.filter(
                id=int(search)
            )

        else:

            students = students.filter(
                name__icontains=search
            )

    # Class filter
    if classroom_id:

        students = students.filter(
            classroom_id=classroom_id
        )

    # Exam filter
    if exam_name:

        students = students.filter(
            marks__exam_name__iexact=exam_name
        ).distinct()

    classrooms = ClassRoom.objects.all().order_by("name")

    exam_names = (
        Marks.objects
        .values_list("exam_name", flat=True)
        .distinct()
        .order_by("exam_name")
    )

    context = {
        "students": students,
        "classrooms": classrooms,
        "exam_names": exam_names,
        "search": search,
        "selected_classroom": classroom_id,
        "selected_exam": exam_name,
    }

    return render(
        request,
        "students/admin_report_card.html",
        context
    )





@login_required
def admin_student_report_card(request, student_id):

    student = get_object_or_404(
        Student.objects.select_related("classroom"),
        pk=student_id
    )

    # -----------------------------------------
    # Get all exams for this student
    # -----------------------------------------

    exam_names = (
        Marks.objects
        .filter(student=student)
        .values_list("exam_name", flat=True)
        .distinct()
        .order_by("exam_name")
    )

    # -----------------------------------------
    # Get selected exam from URL
    # -----------------------------------------

    selected_exam = request.GET.get("exam_name", "").strip()

    # -----------------------------------------
    # If no exam was selected
    # use the first available exam
    # -----------------------------------------

    if not selected_exam:

        selected_exam = exam_names.first()

    # -----------------------------------------
    # Get marks for selected exam
    # -----------------------------------------

    marks = (
        Marks.objects
        .filter(
            student=student,
            exam_name=selected_exam
        )
        .select_related(
            "subject",
            "student__classroom"
        )
        .order_by("subject__name")
    )

    # -----------------------------------------
    # Subject rows
    # -----------------------------------------

    subject_rows = []

    total_full_marks = 0
    total_obtained_marks = 0

    for mark in marks:

        full_marks = mark.full_marks or 0
        obtained_marks = mark.marks_obtained or 0

        percentage = (
            round(
                (obtained_marks / full_marks) * 100,
                2
            )
            if full_marks
            else 0
        )

        total_full_marks += full_marks
        total_obtained_marks += obtained_marks

        subject_rows.append({
            "subject": mark.subject.name,
            "full_marks": full_marks,
            "obtained_marks": obtained_marks,
            "percentage": percentage,
        })

    # -----------------------------------------
    # Overall percentage
    # -----------------------------------------

    overall_percentage = (
        round(
            (total_obtained_marks / total_full_marks) * 100,
            2
        )
        if total_full_marks
        else 0
    )

    # -----------------------------------------
    # Grade
    # -----------------------------------------

    if overall_percentage >= 90:
        grade = "A+"

    elif overall_percentage >= 80:
        grade = "A"

    elif overall_percentage >= 70:
        grade = "B+"

    elif overall_percentage >= 60:
        grade = "B"

    elif overall_percentage >= 50:
        grade = "C"

    else:
        grade = "F"

    # -----------------------------------------
    # Result
    # -----------------------------------------

    result = (
        "PASS"
        if overall_percentage >= 40
        else "FAIL"
    )

    # -----------------------------------------
    # Remarks
    # -----------------------------------------

    if overall_percentage >= 90:
        remarks = "Outstanding Performance"

    elif overall_percentage >= 80:
        remarks = "Excellent Work"

    elif overall_percentage >= 70:
        remarks = "Very Good Performance"

    elif overall_percentage >= 60:
        remarks = "Good Effort"

    elif overall_percentage >= 50:
        remarks = "Satisfactory"

    else:
        remarks = "Needs Improvement"

    # -----------------------------------------
    # Context
    # -----------------------------------------

    context = {

        "student": student,

        "exam_name": selected_exam,

        "exam_names": exam_names,

        "subject_rows": subject_rows,

        "total_full_marks": total_full_marks,

        "total_obtained_marks": total_obtained_marks,

        "overall_percentage": overall_percentage,

        "grade": grade,

        "result": result,

        "remarks": remarks,

        "school_name": "Jhime Malika Secondary School",

        "school_address": "K.i singh 04, doti",

        "report_title": "Report Card",

        "academic_session": "2026",
    }

    return render(
        request,
        "students/admin_student_report_card.html",
        context
    )
# added manually

def student_logout(request):
    request.session.flush()     # Optional
    # return redirect("student-lookup")
    # return redirect("student-lookup")
    return redirect("home")


def student_assignment(request, student_id):
    student = get_object_or_404(Student.objects.select_related("classroom"), pk=student_id)
    assignment_list = (
        Assignment.objects.filter(classroom=student.classroom)
        .order_by("-created_at")
    )
    
    
    context={
        "assignment_list":assignment_list,
        "student":student,
    }
    
    return render(request,"students/student_assignment.html",context)



# def student_attendance(request, student_id):
#     student = get_object_or_404(Student.objects.select_related("classroom"), pk=student_id)
#     attendance_records = (
#         Attendance.objects.filter(student=student)
#         .order_by("-date")
#     )

#     present_days = attendance_records.filter(status="PRESENT").count()
#     absent_days = attendance_records.filter(status="ABSENT").count()
#     total_days = attendance_records.count()
#     attendance_percentage = (
#         round((present_days / total_days) * 100, 2) if total_days else 0
#     )

#     context = {
#         "student": student,
#         "attendance_records": attendance_records,
#         "present_days": present_days,
#         "absent_days": absent_days,
#         "total_days": total_days,
#         "attendance_percentage": attendance_percentage,
#     }
#     return render(request, "students/student_attendance.html", context)





# from django.shortcuts import render
# from students.models import ClassRoom, Student
# from academics.models import Subject

# # Create your views here.

# def student(request):
#     classroom = ClassRoom.objects.filter(teacher=request.user).first()
#     student_count = 0
#     subject_count = 0

#     students = Student.objects.filter(classroom=classroom)

#     if classroom:
#         student_count = classroom.students.count()
#         subject_count = Subject.objects.filter(classroom=classroom).count()

#     context = {
#         "classroom": classroom,
#         "student_count": student_count,
#         "subject_count": subject_count,
#         "students": students,
#     }
#     return render(request, "students/student_list.html", context)

    