from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Attendance
from students.models import ClassRoom, Student


# =========================================================
# HELPER
# =========================================================

def is_admin(user):
    """
    Admin or Django superuser can manage all attendance.
    """
    return (
        user.is_authenticated
        and (
            user.role == "ADMIN"
            or user.is_superuser
        )
    )


def get_accessible_classrooms(user):
    """
    Admin:
        All classrooms.

    Teacher:
        Only classrooms assigned to the teacher.
    """

    if is_admin(user):
        return ClassRoom.objects.all()

    return ClassRoom.objects.filter(
        teacher=user
    )


# =========================================================
# TODAY'S ATTENDANCE
# =========================================================

@login_required
def today_attendance(request):

    today = date.today()

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------
    if is_admin(request.user):

        attendance_records = (
            Attendance.objects
            .filter(date=today)
            .select_related(
                "student",
                "student__classroom"
            )
            .order_by(
                "student__classroom__name",
                "student__classroom__section",
                "student__name"
            )
        )

    # -----------------------------------------------------
    # TEACHER
    # -----------------------------------------------------
    else:

        attendance_records = (
            Attendance.objects
            .filter(
                date=today,
                student__classroom__teacher=request.user
            )
            .select_related(
                "student",
                "student__classroom"
            )
            .order_by(
                "student__name"
            )
        )

    present = attendance_records.filter(
        status="PRESENT"
    ).count()

    absent = attendance_records.filter(
        status="ABSENT"
    ).count()

    context = {
        "attendance_records": attendance_records,
        "today": today,
        "present": present,
        "absent": absent,
        "is_admin": is_admin(request.user),
    }

    return render(
        request,
        "attendance/today_attendance.html",
        context
    )


# =========================================================
# MARK ATTENDANCE
# =========================================================

@login_required
def mark_attendance(request):

    classrooms = get_accessible_classrooms(
        request.user
    )

    if not classrooms.exists():

        messages.error(
            request,
            "No classroom is available."
        )

        return redirect("dashboard")


    # -----------------------------------------------------
    # Select classroom
    # -----------------------------------------------------

    classroom_id = (
        request.POST.get("classroom")
        or request.GET.get("classroom")
    )

    classroom = None


    # Admin
    if is_admin(request.user):

        if classroom_id:

            classroom = get_object_or_404(
                ClassRoom,
                id=classroom_id
            )

        elif classrooms.count() == 1:

            classroom = classrooms.first()


    # Teacher
    else:

        classroom = get_object_or_404(
            ClassRoom,
            teacher=request.user
        )


    # -----------------------------------------------------
    # No classroom selected
    # -----------------------------------------------------

    if not classroom:

        context = {
            "classrooms": classrooms,
            "classroom": None,
            "students": Student.objects.none(),
            "today": date.today(),
            "is_admin": is_admin(request.user),
        }

        return render(
            request,
            "attendance/attendance_form.html",
            context
        )


    # -----------------------------------------------------
    # Students
    # -----------------------------------------------------

    students = (
        classroom.students
        .all()
        .order_by("name")
    )


    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        attendance_date = request.POST.get(
            "date"
        )

        if not attendance_date:

            messages.error(
                request,
                "Please select an attendance date."
            )

            return redirect(
                f"?classroom={classroom.id}"
            )


        saved_count = 0


        for student in students:

            status = request.POST.get(
                f"student_{student.id}"
            )

            if not status:
                continue


            if status not in [
                "PRESENT",
                "ABSENT"
            ]:

                continue


            Attendance.objects.update_or_create(

                student=student,

                date=attendance_date,

                defaults={
                    "status": status
                }
            )

            saved_count += 1


        if saved_count:

            messages.success(
                request,
                "Attendance saved successfully."
            )

        else:

            messages.warning(
                request,
                "No attendance records were selected."
            )


        return redirect("attendance")


    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    context = {
        "classrooms": classrooms,
        "classroom": classroom,
        "students": students,
        "today": date.today(),
        "is_admin": is_admin(request.user),
    }

    return render(
        request,
        "attendance/attendance_form.html",
        context
    )


# =========================================================
# ATTENDANCE HISTORY
# =========================================================

@login_required
def attendance_history(request):

    from_date = request.GET.get(
        "from"
    )

    to_date = request.GET.get(
        "to"
    )

    classroom_id = request.GET.get(
        "classroom"
    )


    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    if is_admin(request.user):

        queryset = Attendance.objects.all()

    # -----------------------------------------------------
    # TEACHER
    # -----------------------------------------------------

    else:

        queryset = Attendance.objects.filter(
            student__classroom__teacher=request.user
        )


    # -----------------------------------------------------
    # Classroom filter
    # -----------------------------------------------------

    if classroom_id:

        queryset = queryset.filter(
            student__classroom_id=classroom_id
        )


    # -----------------------------------------------------
    # Date filters
    # -----------------------------------------------------

    if from_date:

        queryset = queryset.filter(
            date__gte=from_date
        )


    if to_date:

        queryset = queryset.filter(
            date__lte=to_date
        )


    # -----------------------------------------------------
    # Attendance summary
    # -----------------------------------------------------

    attendance_records = (

        queryset

        .values(
            "date",
            "student__classroom__name",
            "student__classroom__section",
        )

        .annotate(

            present_count=Count(
                "id",
                filter=Q(
                    status="PRESENT"
                )
            ),

            absent_count=Count(
                "id",
                filter=Q(
                    status="ABSENT"
                )
            ),

        )

        .order_by(
            "-date",
            "student__classroom__name",
            "student__classroom__section",
        )

    )


    # -----------------------------------------------------
    # Calculate percentage
    # -----------------------------------------------------

    for record in attendance_records:

        total = (
            record["present_count"]
            + record["absent_count"]
        )


        if total > 0:

            record["attendance_percentage"] = round(
                (
                    record["present_count"]
                    / total
                ) * 100,
                2
            )

        else:

            record["attendance_percentage"] = 0


    # -----------------------------------------------------
    # Context
    # -----------------------------------------------------

    context = {

        "attendance_records":
            attendance_records,

        "from_date":
            from_date,

        "to_date":
            to_date,

        "classrooms":
            get_accessible_classrooms(
                request.user
            ),

        "selected_classroom":
            classroom_id or "",

        "is_admin":
            is_admin(request.user),

    }


    return render(
        request,
        "attendance/attendance_history.html",
        context
    )

# from django.core.checks import messages
# from django.shortcuts import render, redirect
# from datetime import date
# from .models import Attendance
# from django.db.models import Count, Q

# from attendance.models import Attendance
# from students.models import ClassRoom
# from datetime import date
# # new added to check the login
# # from django.contrib.auth.decorators import login_required

# from django.contrib import messages


# def today_attendance(request):
#     today = date.today()

#     attendance_records = Attendance.objects.filter(
#         date=today, student__classroom__teacher=request.user
#     ).select_related("student")
#     present = attendance_records.filter(status="PRESENT").count()
#     absent = attendance_records.filter(status="ABSENT").count()

#     context = {
#         "attendance_records": attendance_records,
#         "today": today,
#         "present": present,
#         "absent": absent,
#     }
#     return render(request, "attendance/today_attendance.html", context)


# def mark_attendance(request):
#     classroom = ClassRoom.objects.filter(teacher=request.user).first()
#     if not classroom:
#         messages.error(request, "No classroom assigned to you.")
#         # return redirect("accounts:dashboard")
#         return redirect("dashboard")
#     students = classroom.students.all()
#     if request.method == "POST":
#         attendance_date = request.POST.get("date")
#         for student in students:
#             status = request.POST.get(f"student_{student.id}")
#             if not status:
#                 continue
#             Attendance.objects.update_or_create(
#                 student=student, date=attendance_date, defaults={"status": status}
#             )
#         messages.success(request, "Attendance saved successfully.")
#         return redirect("attendance")
#     context = {
#         "classroom": classroom,
#         "students": students,
#         "today": date.today(),
#     }
#     return render(
#         request,
#         "attendance/attendance_form.html",
#         context,
#     )


# def attendance_history(request):
#     from_date = request.GET.get("from")
#     to_date = request.GET.get("to")

#     queryset = Attendance.objects.filter(student__classroom__teacher=request.user)

#     if from_date:
#         queryset = queryset.filter(date__gte=from_date)

#     if to_date:
#         queryset = queryset.filter(date__lte=to_date)

#     attendance_records = (
#         queryset.values(
#             # added mannually
#             # "student__name",
#             "date", "student__classroom__name", "student__classroom__section"
#         )
#         .annotate(
#             present_count=Count("id", filter=Q(status="PRESENT")),
#             absent_count=Count("id", filter=Q(status="ABSENT")),
#         )
#         .order_by("-date")
#     )
    
#     # to check the percentage of student present in the specific date
#     for record in attendance_records:
#         total = record["present_count"] + record["absent_count"]

#         if total > 0:
#             record["attendance_percentage"] = round(
#                 (record["present_count"] / total) * 100,
#                 2,
#             )
#         else:
#             record["attendance_percentage"] = 0

#     context = {
#         "attendance_records": attendance_records,
#         "from_date": from_date,
#         "to_date": to_date,
#     }

#     return render(request, "attendance/attendance_history.html", context)




































