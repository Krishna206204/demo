from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.urls import reverse

from .models import Assignment, Marks, Subject
from students.models import ClassRoom, Student



def is_admin(user):
    """
    Returns True if the logged-in user is an Admin or Superuser.
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
        Can access every classroom.

    Teacher:
        Can access only classrooms assigned to them.
    """

    if is_admin(user):
        return ClassRoom.objects.all()

    return ClassRoom.objects.filter(
        teacher=user
    )


# =========================================================
# ADD ASSIGNMENT
# =========================================================

def add_assignment(request):

    classrooms = get_accessible_classrooms(request.user)

    if not classrooms.exists():

        messages.error(
            request,
            "No classroom is available."
        )

        return redirect("dashboard")


    # -----------------------------------------------------
    # Get classroom
    # -----------------------------------------------------

    classroom_id = (
        request.POST.get("classroom")
        or request.GET.get("classroom")
    )

    classroom = None

    if classroom_id:

        if is_admin(request.user):

            classroom = get_object_or_404(
                ClassRoom,
                id=classroom_id
            )

        else:

            classroom = get_object_or_404(
                ClassRoom,
                id=classroom_id,
                teacher=request.user
            )

    elif not is_admin(request.user):

        # Teacher normally has one classroom
        classroom = classrooms.first()

    elif classrooms.count() == 1:

        # Admin has only one classroom
        classroom = classrooms.first()


    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        if not classroom:

            messages.error(
                request,
                "Please select a classroom."
            )

            return redirect("assignment-add")


        title = request.POST.get(
            "title",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        subject_id = request.POST.get(
            "subject"
        )


        # Validate title
        if not title:

            messages.error(
                request,
                "Assignment title is required."
            )

            return redirect(
                f"{reverse('assignment-add')}?classroom={classroom.id}"
            )


        # Validate subject
        if not subject_id:

            messages.error(
                request,
                "Please select a subject."
            )

            return redirect(
                f"{reverse('assignment-add')}?classroom={classroom.id}"
            )


        subject = get_object_or_404(
            Subject,
            id=subject_id,
            classroom=classroom
        )


        Assignment.objects.create(
            title=title,
            description=description,
            subject=subject,
            classroom=classroom
        )


        messages.success(
            request,
            "Assignment created successfully."
        )

        return redirect("assignment-list")


    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    subjects = Subject.objects.filter(
        classroom=classroom
    ) if classroom else Subject.objects.none()


    context = {
        "classroom": classroom,
        "classrooms": classrooms,
        "subjects": subjects,
    }

    return render(
        request,
        "academics/assignment_form.html",
        context
    )


# =========================================================
# ASSIGNMENT LIST
# =========================================================

def assignment_list(request):

    if is_admin(request.user):

        assignments = (
            Assignment.objects
            .select_related(
                "subject",
                "classroom"
            )
            .order_by("-created_at")
        )

    else:

        assignments = (
            Assignment.objects
            .filter(
                classroom__teacher=request.user
            )
            .select_related(
                "subject",
                "classroom"
            )
            .order_by("-created_at")
        )


    return render(
        request,
        "academics/assignment_list.html",
        {
            "assignments": assignments
        }
    )


# =========================================================
# ADD MARKS
# =========================================================

def add_marks(request):

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


    if classroom_id:

        if is_admin(request.user):

            classroom = get_object_or_404(
                ClassRoom,
                id=classroom_id
            )

        else:

            classroom = get_object_or_404(
                ClassRoom,
                id=classroom_id,
                teacher=request.user
            )

    elif not is_admin(request.user):

        classroom = classrooms.first()

    elif classrooms.count() == 1:

        classroom = classrooms.first()


    if not classroom:

        return render(
            request,
            "academics/marks_form.html",
            {
                "classrooms": classrooms,
                "classroom": None,
                "students": Student.objects.none(),
                "subjects": Subject.objects.none(),
            }
        )


    students = classroom.students.all()

    subjects = Subject.objects.filter(
        classroom=classroom
    )


    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        subject_id = request.POST.get(
            "subject"
        )

        exam_name = request.POST.get(
            "exam_name",
            ""
        ).strip().title()


        if not subject_id or not exam_name:

            messages.error(
                request,
                "Subject and exam name are required."
            )

            return redirect(
                f"{reverse('add-marks')}?classroom={classroom.id}"
            )


        subject = get_object_or_404(
            Subject,
            id=subject_id,
            classroom=classroom
        )


        saved_count = 0


        for student in students:

            marks = request.POST.get(
                f"student_{student.id}"
            )


            if marks in [None, ""]:
                continue


            try:
                marks = float(marks)

            except (ValueError, TypeError):

                messages.error(
                    request,
                    f"Invalid marks for {student.name}."
                )

                return redirect(
                    f"{reverse('add-marks')}?classroom={classroom.id}"
                )


            Marks.objects.update_or_create(

                student=student,

                subject=subject,

                exam_name=exam_name,

                defaults={
                    "marks_obtained": marks
                }
            )


            saved_count += 1


        if saved_count:

            messages.success(
                request,
                "Marks saved successfully."
            )

        else:

            messages.warning(
                request,
                "No marks were entered."
            )


        return redirect(
            f"{reverse('add-marks')}?classroom={classroom.id}"
        )


    context = {

        "classrooms": classrooms,

        "classroom": classroom,

        "students": students,

        "subjects": subjects,
    }


    return render(
        request,
        "academics/marks_form.html",
        context
    )


# =========================================================
# VIEW MARKS
# =========================================================

def view_marks(request):

    classrooms = get_accessible_classrooms(
        request.user
    )


    # -----------------------------------------------------
    # Base Query
    # -----------------------------------------------------

    if is_admin(request.user):

        marks = Marks.objects.all()

        subjects = Subject.objects.all()

        exam_names = (
            Marks.objects
            .values_list(
                "exam_name",
                flat=True
            )
            .distinct()
        )

    else:

        marks = Marks.objects.filter(
            student__classroom__teacher=request.user
        )

        subjects = Subject.objects.filter(
            classroom__teacher=request.user
        )

        exam_names = (
            Marks.objects
            .filter(
                student__classroom__teacher=request.user
            )
            .values_list(
                "exam_name",
                flat=True
            )
            .distinct()
        )


    marks = (
        marks
        .select_related(
            "student",
            "subject",
            "student__classroom"
        )
        .order_by(
            "student__name"
        )
    )


    # -----------------------------------------------------
    # Filters
    # -----------------------------------------------------

    classroom_id = request.GET.get(
        "classroom"
    )

    subject_id = request.GET.get(
        "subject"
    )

    exam_name = request.GET.get(
        "exam"
    )


    if classroom_id:

        marks = marks.filter(
            student__classroom_id=classroom_id
        )


    if subject_id:

        marks = marks.filter(
            subject_id=subject_id
        )


    if exam_name:

        marks = marks.filter(
            exam_name=exam_name
        )


    context = {

        "marks": marks,

        "subjects": subjects,

        "exam_names": exam_names,

        "classrooms": classrooms,

        "selected_classroom": classroom_id or "",

        "selected_subject": subject_id or "",

        "selected_exam": exam_name or "",
    }


    return render(
        request,
        "academics/marks_list.html",
        context
    )


# =========================================================
# REPORT CARD
# =========================================================

def report_card(
    request,
    student_id,
    exam_name
):

    student = get_object_or_404(
        Student.objects.select_related(
            "classroom__teacher"
        ),
        pk=student_id
    )


    # -----------------------------------------------------
    # Permission check
    # -----------------------------------------------------

    if not is_admin(request.user):

        if student.classroom.teacher != request.user:

            messages.error(
                request,
                "You are not authorized to view this report card."
            )

            return redirect("dashboard")


    # -----------------------------------------------------
    # Marks
    # -----------------------------------------------------

    marks = (
        Marks.objects
        .filter(
            student=student,
            exam_name=exam_name
        )
        .select_related(
            "subject",
            "student__classroom"
        )
        .order_by(
            "subject__name"
        )
    )


    subject_rows = []

    total_full_marks = 0

    total_obtained_marks = 0


    for mark in marks:

        full_marks = mark.full_marks or 0

        obtained_marks = (
            mark.marks_obtained or 0
        )


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


    # -----------------------------------------------------
    # Overall percentage
    # -----------------------------------------------------

    overall_percentage = (

        round(
            (
                total_obtained_marks
                / total_full_marks
            ) * 100,
            2
        )

        if total_full_marks

        else 0

    )


    # -----------------------------------------------------
    # Grade
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # Result
    # -----------------------------------------------------

    if overall_percentage >= 40:

        result = "PASS"

    else:

        result = "FAIL"


    # -----------------------------------------------------
    # Remarks
    # -----------------------------------------------------

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


    teacher = student.classroom.teacher


    if teacher:

        class_teacher = (
            teacher.get_full_name()
            or teacher.username
        )

    else:

        class_teacher = "Class Teacher"


    context = {

        "school_name":
            "Jhime Malika Secondary School",

        "school_address":
            "K.i singh 04, Doti",

        "report_title":
            "Report Card",

        "academic_session":
            "2026",

        "student":
            student,

        "exam_name":
            exam_name,

        "subject_rows":
            subject_rows,

        "total_full_marks":
            total_full_marks,

        "total_obtained_marks":
            total_obtained_marks,

        "overall_percentage":
            overall_percentage,

        "grade":
            grade,

        "result":
            result,

        "remarks":
            remarks,

        "class_teacher":
            class_teacher,

        "principal_name":
            "Nar Bahadur Karki",
    }


    return render(
        request,
        "academics/report_card.html",
        context
    )


# =========================================================
# STUDENT RESULTS
# =========================================================

def student_results(request):

    classrooms = get_accessible_classrooms(
        request.user
    )


    # -----------------------------------------------------
    # Students
    # -----------------------------------------------------

    if is_admin(request.user):

        students = Student.objects.all()

        exam_queryset = Marks.objects.all()

    else:

        students = Student.objects.filter(
            classroom__teacher=request.user
        )

        exam_queryset = Marks.objects.filter(
            student__classroom__teacher=request.user
        )


    students = students.select_related(
        "classroom"
    )


    # -----------------------------------------------------
    # Filters
    # -----------------------------------------------------

    search_query = request.GET.get(
        "search",
        ""
    ).strip()


    selected_exam = request.GET.get(
        "exam",
        ""
    ).strip()


    selected_classroom = request.GET.get(
        "classroom",
        ""
    ).strip()


    if search_query:

        students = students.filter(
            name__icontains=search_query
        )


    if selected_classroom:

        students = students.filter(
            classroom_id=selected_classroom
        )


    # -----------------------------------------------------
    # Available exams
    # -----------------------------------------------------

    available_exams = list(

        exam_queryset
        .values_list(
            "exam_name",
            flat=True
        )
        .distinct()
        .order_by("exam_name")

    )


    # -----------------------------------------------------
    # Student results
    # -----------------------------------------------------

    student_results = []

    percentages = []


    for student in students:

        marks_qs = Marks.objects.filter(
            student=student
        )


        if selected_exam:

            marks_qs = marks_qs.filter(
                exam_name=selected_exam
            )


        marks_qs = marks_qs.select_related(
            "subject"
        )


        total_full_marks = 0

        total_obtained_marks = 0


        for mark in marks_qs:

            total_full_marks += (
                mark.full_marks or 0
            )

            total_obtained_marks += (
                mark.marks_obtained or 0
            )


        if total_full_marks:

            percentage = round(
                (
                    total_obtained_marks
                    / total_full_marks
                ) * 100,
                2
            )

        else:

            percentage = 0


        # -------------------------------------------------
        # Grade
        # -------------------------------------------------

        if percentage >= 90:

            grade = "A+"

        elif percentage >= 80:

            grade = "A"

        elif percentage >= 70:

            grade = "B+"

        elif percentage >= 60:

            grade = "B"

        elif percentage >= 50:

            grade = "C"

        else:

            grade = "F"


        percentages.append(
            percentage
        )


        # -------------------------------------------------
        # Report URL
        # -------------------------------------------------

        if selected_exam:

            report_url = reverse(
                "report-card",
                kwargs={
                    "student_id": student.id,
                    "exam_name": selected_exam,
                }
            )

        else:

            report_url = reverse(
                "report-card",
                kwargs={
                    "student_id": student.id,
                    "exam_name": "Mid-Term",
                }
            )


        student_results.append({

            "student":
                student,

            "total_marks":
                total_full_marks,

            "obtained_marks":
                total_obtained_marks,

            "percentage":
                percentage,

            "grade":
                grade,

            "report_url":
                report_url,

        })


    # -----------------------------------------------------
    # Class statistics
    # -----------------------------------------------------

    total_students = len(
        student_results
    )


    class_average = (

        round(
            sum(percentages)
            / total_students,
            2
        )

        if total_students

        else 0

    )


    highest_percentage = (
        max(percentages)
        if percentages
        else 0
    )


    lowest_percentage = (
        min(percentages)
        if percentages
        else 0
    )


    context = {

        "students_results":
            student_results,

        "total_students":
            total_students,

        "class_average":
            class_average,

        "highest_percentage":
            highest_percentage,

        "lowest_percentage":
            lowest_percentage,

        "available_exams":
            available_exams,

        "selected_exam":
            selected_exam,

        "selected_classroom":
            selected_classroom,

        "search_query":
            search_query,

        "classrooms":
            classrooms,
    }


    return render(
        request,
        "academics/student_results.html",
        context
    )


# =========================================================
# DELETE ASSIGNMENT
# =========================================================

def delete_assignment(
    request,
    id
):

    assignment = get_object_or_404(
        Assignment,
        id=id
    )


    # -----------------------------------------------------
    # Admin can delete anything
    # -----------------------------------------------------

    if is_admin(request.user):

        assignment.delete()

        messages.success(
            request,
            "Assignment deleted successfully."
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER",
                reverse("assignment-list")
            )
        )


    # -----------------------------------------------------
    # Teacher can delete only their own classroom
    # -----------------------------------------------------

    if assignment.classroom.teacher != request.user:

        messages.error(
            request,
            "You are not authorized to delete this assignment."
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER",
                reverse("assignment-list")
            )
        )


    assignment.delete()

    messages.success(
        request,
        "Assignment deleted successfully."
    )


    return redirect(
        request.META.get(
            "HTTP_REFERER",
            reverse("assignment-list")
        )
    )





# from django.shortcuts import get_object_or_404, redirect, render
# from django.contrib import messages
# from django.urls import reverse
# from .models import Assignment, Marks, Subject
# from students.models import ClassRoom, Student


# def add_assignment(request):
#     classroom = ClassRoom.objects.filter(teacher=request.user).first()

#     if not classroom:
#         messages.error(request, "No Classroom assigned to you")
#         return redirect("dashboard")

#     subjects = Subject.objects.filter(classroom=classroom)
#     if request.method == "POST":
#         title = request.POST.get("title")
#         description = request.POST.get("description")
#         subject_id = request.POST.get("subject")

#         subject = Subject.objects.get(id=subject_id)
#         Assignment.objects.create(
#             title=title, description=description, subject=subject, classroom=classroom
#         )
#         messages.success(request, "Assignment Created Successfully")
#         return redirect("assignment-list")
#     context = {"classroom": classroom, "subjects": subjects}
#     return render(request, "academics/assignment_form.html", context)


# def assignment_list(request):
#     assignments = (
#         Assignment.objects.filter(classroom__teacher=request.user)
#         .select_related("subject", "classroom")
#         .order_by("-created_at")
#     )
#     return render(
#         request, "academics/assignment_list.html", {"assignments": assignments}
#     )


# def add_marks(request):
#     classroom = ClassRoom.objects.filter(teacher=request.user).first()
#     if not classroom:
#         messages.error(request, "No Classroom assigned to you")
#         return redirect("dashboard")
#     students = classroom.students.all()
#     subjects = Subject.objects.filter(classroom=classroom)
#     if request.method == "POST":
#         subject_id = request.POST.get("subject")
#         exam_name = request.POST.get("exam_name", "").strip().title()

#         if not subject_id or not exam_name:
#             messages.error(request, "Subject and exam name are required..")
#             return redirect("add-marks")

#         subject = Subject.objects.get(id=subject_id, classroom=classroom)

#         for student in students:
#             marks = request.POST.get(f"student_{student.id}")
#             if not marks:
#                 continue
#             Marks.objects.update_or_create(
#                 student=student,
#                 subject=subject,
#                 exam_name=exam_name,
#                 defaults={"marks_obtained": marks},
#             )
#         messages.success(request, "Marks saved successfully..")
#         return redirect("add-marks")

#     context = {"classroom": classroom, "students": students, "subjects": subjects}
#     return render(request, "academics/marks_form.html", context)


# def view_marks(request):
#     classroom = ClassRoom.objects.filter(teacher=request.user).first()
#     marks = Marks.objects.none()
#     subjects = Subject.objects.none()
#     exam_name = []
#     if classroom:
#         subjects = Subject.objects.filter(classroom=classroom)
#         marks = (
#             Marks.objects.filter(student__classroom=classroom)
#             .select_related(
#                 "student",
#                 "subject",
#             )
#             .order_by("student__name")
#         )
#         subject_id = request.GET.get("subject")
#         exam_name = request.GET.get("exam")

#         if subject_id:
#             marks = marks.filter(subject_id=subject_id)

#         if exam_name:
#             marks = marks.filter(exam_name=exam_name)

#         exam_name = (
#             Marks.objects.filter(student__classroom=classroom)
#             .values_list("exam_name", flat=True)
#             .distinct()
#         )
#     context = {
#         "marks": marks,
#         "subjects": subjects,
#         "exam_names": exam_name,
#         "selected_subject": request.GET.get("subject", ""),
#         "selected_exam": request.GET.get("exam", ""),
#     }
#     return render(request, "academics/marks_list.html", context)


# # added
# def report_card(request, student_id, exam_name):

#     student = get_object_or_404(
#         Student.objects.select_related("classroom__teacher"),
#         pk=student_id,
#     )

#     marks = (
#         Marks.objects.filter(student=student, exam_name=exam_name)
#         .select_related("subject", "student__classroom")
#         .order_by("subject__name")
#     )

#     subject_rows = []
#     total_full_marks = 0
#     total_obtained_marks = 0

#     for mark in marks:
#         full_marks = mark.full_marks or 0
#         obtained_marks = mark.marks_obtained or 0
#         percentage = round((obtained_marks / full_marks) * 100, 2) if full_marks else 0

#         total_full_marks += full_marks
#         total_obtained_marks += obtained_marks

#         subject_rows.append(
#             {
#                 "subject": mark.subject.name,
#                 "full_marks": full_marks,
#                 "obtained_marks": obtained_marks,
#                 "percentage": percentage,
#             }
#         )

#     overall_percentage = (
#         round((total_obtained_marks / total_full_marks) * 100, 2)
#         if total_full_marks
#         else 0
#     )

#     if overall_percentage >= 90:
#         grade = "A+"
#     elif overall_percentage >= 80:
#         grade = "A"
#     elif overall_percentage >= 70:
#         grade = "B+"
#     elif overall_percentage >= 60:
#         grade = "B"
#     elif overall_percentage >= 50:
#         grade = "C"
#     else:
#         grade = "F"

#     if overall_percentage >= 40:
#         result = "PASS"
#     else:
#         result = "FAIL"

#     if overall_percentage >= 90:
#         remarks = "Outstanding Performance"
#     elif overall_percentage >= 80:
#         remarks = "Excellent Work"
#     elif overall_percentage >= 70:
#         remarks = "Very Good Performance"
#     elif overall_percentage >= 60:
#         remarks = "Good Effort"
#     elif overall_percentage >= 50:
#         remarks = "Satisfactory"
#     else:
#         remarks = "Needs Improvement"

#     context = {
#         "school_name": "Jhime Malika Secondary School",
#         "school_address": "K.i singh 04, Doti",
#         "report_title": "Report Card",
#         "academic_session": "2026",
#         "student": student,
#         "exam_name": exam_name,
#         "subject_rows": subject_rows,
#         "total_full_marks": total_full_marks,
#         "total_obtained_marks": total_obtained_marks,
#         "overall_percentage": overall_percentage,
#         "grade": grade,
#         "result": result,
#         "remarks": remarks,
#         "class_teacher": (
#             student.classroom.teacher.get_full_name()
#             or student.classroom.teacher.username
#             if student.classroom.teacher
#             else "Class Teacher"
#         ),
#         "principal_name": "Nar Bahadur Karki",
#     }

#     return render(request, "academics/report_card.html", context)

# def student_results(request):
#     classroom = ClassRoom.objects.filter(teacher=request.user).first()
#     if not classroom:
#         messages.error(request, "No classroom assigned to you.")
#         return redirect("dashboard")

#     search_query = request.GET.get("search", "").strip()
#     selected_exam = request.GET.get("exam", "").strip()

#     students = Student.objects.filter(classroom=classroom).select_related("classroom")

#     if search_query:
#         students = students.filter(name__icontains=search_query)

#     available_exams = list(
#         Marks.objects.filter(student__classroom=classroom)
#         .values_list("exam_name", flat=True)
#         .distinct()
#         .order_by("exam_name")
#     )

#     student_results = []
#     percentages = []

#     for student in students:
#         marks_qs = Marks.objects.filter(student=student)

#         if selected_exam:
#             marks_qs = marks_qs.filter(exam_name=selected_exam)

#         marks_qs = marks_qs.select_related("subject")

#         total_full_marks = 0
#         total_obtained_marks = 0

#         for mark in marks_qs:
#             total_full_marks += mark.full_marks or 0
#             total_obtained_marks += mark.marks_obtained or 0

#         if total_full_marks:
#             percentage = round((total_obtained_marks / total_full_marks) * 100, 2)
#         else:
#             percentage = 0

#         if percentage >= 90:
#             grade = "A+"
#         elif percentage >= 80:
#             grade = "A"
#         elif percentage >= 70:
#             grade = "B+"
#         elif percentage >= 60:
#             grade = "B"
#         elif percentage >= 50:
#             grade = "C"
#         else:
#             grade = "F"

#         percentages.append(percentage)
#         student_results.append(
#             {
#                 "student": student,
#                 "total_marks": total_full_marks,
#                 "obtained_marks": total_obtained_marks,
#                 "percentage": percentage,
#                 "grade": grade,
#                 "report_url": (
#                     reverse(
#                         "report-card",
#                         kwargs={
#                             "student_id": student.id,
#                             "exam_name": selected_exam or "",
#                         },
#                     )
#                     if selected_exam
#                     else reverse(
#                         "report-card",
#                         kwargs={"student_id": student.id, "exam_name": "Mid-Term"},
#                     )
#                 ),
#             }
#         )

#     total_students = len(student_results)
#     class_average = round(sum(percentages) / total_students, 2) if total_students else 0
#     highest_percentage = max(percentages) if percentages else 0
#     lowest_percentage = min(percentages) if percentages else 0

#     context = {
#         "students_results": student_results,
#         "total_students": total_students,
#         "class_average": class_average,
#         "highest_percentage": highest_percentage,
#         "lowest_percentage": lowest_percentage,
#         "available_exams": available_exams,
#         "selected_exam": selected_exam,
#         "search_query": search_query,
#     }
#     return render(request, "academics/student_results.html", context)



# def delete_assignment(request,id):
#     assignment = get_object_or_404(Assignment, id=id)
#     assignment.delete()
#     messages.success(request, "Assignment Deleted Successfully")
#     return redirect(request.META.get("HTTP_REFERER"))


# # def report_card(request, student_id, exam_name):
# #     student = get_object_or_404(
# #         Student.objects.select_related("classroom__teacher"),
# #         pk=student_id,
# #     )

# #     marks = (
# #         Marks.objects.filter(student=student, exam_name=exam_name)
# #         .select_related("subject", "student__classroom")
# #         .order_by("subject__name")
# #     )

# #     subject_rows = []
# #     total_full_marks = 0
# #     total_obtained_marks = 0

# #     for mark in marks:
# #         full_marks = mark.full_marks or 0
# #         obtained_marks = mark.marks_obtained or 0
# #         percentage = round((obtained_marks / full_marks) * 100, 2) if full_marks else 0

# #         total_full_marks += full_marks
# #         total_obtained_marks += obtained_marks

# #         subject_rows.append(
# #             {
# #                 "subject": mark.subject.name,
# #                 "full_marks": full_marks,
# #                 "obtained_marks": obtained_marks,
# #                 "percentage": percentage,
# #             }
# #         )

# #     overall_percentage = (
# #         round((total_obtained_marks / total_full_marks) * 100, 2)
# #         if total_full_marks
# #         else 0
# #     )

# #     if overall_percentage >= 90:
# #         grade = "A+"
# #     elif overall_percentage >= 80:
# #         grade = "A"
# #     elif overall_percentage >= 70:
# #         grade = "B+"
# #     elif overall_percentage >= 60:
# #         grade = "B"
# #     elif overall_percentage >= 50:
# #         grade = "C"
# #     else:
# #         grade = "F"

# #     if overall_percentage >= 40:
# #         result = "PASS"
# #     else:
# #         result = "FAIL"

# #     if overall_percentage >= 90:
# #         remarks = "Outstanding performance."
# #     elif overall_percentage >= 80:
# #         remarks = "Excellent work."
# #     elif overall_percentage >= 70:
# #         remarks = "Very good performance."
# #     elif overall_percentage >= 60:
# #         remarks = "Good effort."
# #     elif overall_percentage >= 50:
# #         remarks = "Satisfactory performance."
# #     else:
# #         remarks = "Needs improvement."

# #     context = {
# #         "school_name": "Jhime Malika",
# #         "school_address": "K.i singh 04 Doti, Sudur.",
# #         "report_title": "Report Card",
# #         "academic_session": "2026",
# #         "student": student,
# #         "exam_name": exam_name,
# #         "subject_rows": subject_rows,
# #         "total_full_marks": total_full_marks,
# #         "total_obtained_marks": total_obtained_marks,
# #         "overall_percentage": overall_percentage,
# #         "grade": grade,
# #         "result": result,
# #         "remarks": remarks,
# #         "class_teacher": student.classroom.teacher.get_full_name() or student.classroom.teacher.username if student.classroom.teacher else "Class Teacher",
# #         "principal_name": "Nar bahadur Karki",
# #     }

# #     return render(request, "academics/report_card.html", context)






# # from django.shortcuts import get_object_or_404, redirect, render
# # from django.contrib import messages
# # from django.urls import reverse
# # from .models import Assignment, Marks, Subject
# # from students.models import ClassRoom, Student


# # def add_assignment(request):
# #     classroom = ClassRoom.objects.filter(teacher=request.user).first()

# #     if not classroom:
# #         messages.error(request, "No Classroom assigned to you")
# #         return redirect("dashboard")

# #     subjects = Subject.objects.filter(classroom=classroom)
# #     if request.method == "POST":
# #         title = request.POST.get("title")
# #         description = request.POST.get("description")
# #         subject_id = request.POST.get("subject")

# #         subject = Subject.objects.get(id=subject_id)
# #         Assignment.objects.create(
# #             title=title, description=description, subject=subject, classroom=classroom
# #         )
# #         messages.success(request, "Assignment Created Successfully")
# #         return redirect("assignment-list")
# #     context = {"classroom": classroom, "subjects": subjects}
# #     return render(request, "academics/assignment_form.html", context)


# # def assignment_list(request):
# #     assignments = (
# #         Assignment.objects.filter(classroom__teacher=request.user)
# #         .select_related("subject", "classroom")
# #         .order_by("-created_at")
# #     )
# #     return render(
# #         request, "academics/assignment_list.html", {"assignments": assignments}
# #     )


# # def add_marks(request):
# #     classroom = ClassRoom.objects.filter(teacher=request.user).first()
# #     if not classroom:
# #         messages.error(request, "No Classroom assigned to you")
# #         return redirect("dashboard")
# #     students = classroom.students.all()
# #     subjects = Subject.objects.filter(classroom=classroom)
# #     if request.method == "POST":
# #         subject_id = request.POST.get("subject")
# #         exam_name = request.POST.get("exam_name")

# #         if not subject_id or not exam_name:
# #             messages.error(request, "Subject and exam name are required..")
# #             return redirect("add-marks")

# #         subject = Subject.objects.get(id=subject_id, classroom=classroom)

# #         for student in students:
# #             marks = request.POST.get(f"student_{student.id}")
# #             if not marks:
# #                 continue
# #             Marks.objects.update_or_create(
# #                 student=student,
# #                 subject=subject,
# #                 exam_name=exam_name,
# #                 defaults={"marks_obtained": marks},
# #             )
# #         messages.success(request, "Marks saved successfully..")
# #         return redirect("add-marks")

# #     context = {"classroom": classroom, "students": students, "subjects": subjects}
# #     return render(request, "academics/marks_form.html", context)


# # def view_marks(request):
# #     classroom = ClassRoom.objects.filter(teacher=request.user).first()
# #     marks = Marks.objects.none()
# #     subjects = Subject.objects.none()
# #     exam_name = []
# #     if classroom:
# #         subjects = Subject.objects.filter(classroom=classroom)
# #         marks = (
# #             Marks.objects.filter(student__classroom=classroom)
# #             .select_related(
# #                 "student",
# #                 "subject",
# #             )
# #             .order_by("student__name")
# #         )
# #         subject_id = request.GET.get("subject")
# #         exam_name = request.GET.get("exam")

# #         if subject_id:
# #             marks = marks.filter(subject_id=subject_id)

# #         if exam_name:
# #             marks = marks.filter(exam_name=exam_name)

# #         exam_name = (
# #             Marks.objects.filter(student__classroom=classroom)
# #             .values_list("exam_name", flat=True)
# #             .distinct()
# #         )
# #     context = {
# #         "marks": marks,
# #         "subjects": subjects,
# #         "exam_names": exam_name,
# #         "selected_subject": request.GET.get("subject", ""),
# #         "selected_exam": request.GET.get("exam", ""),
# #     }
# #     return render(request, "academics/marks_list.html", context)




# # def student_results(request):
# #     classroom = ClassRoom.objects.filter(teacher=request.user).first()
# #     if not classroom:
# #         messages.error(request, "No classroom assigned to you.")
# #         return redirect("dashboard")

# #     search_query = request.GET.get("search", "").strip()
# #     selected_exam = request.GET.get("exam", "").strip()

# #     students = Student.objects.filter(classroom=classroom).select_related("classroom")

# #     if search_query:
# #         students = students.filter(name__icontains=search_query)

# #     available_exams = list(
# #         Marks.objects.filter(student__classroom=classroom)
# #         .values_list("exam_name", flat=True)
# #         .distinct()
# #         .order_by("exam_name")
# #     )

# #     student_results = []
# #     percentages = []

# #     for student in students:
# #         marks_qs = Marks.objects.filter(student=student)
# #         if selected_exam:
# #             marks_qs = marks_qs.filter(exam_name=selected_exam)

# #         marks_qs = marks_qs.select_related("subject")

# #         total_full_marks = 0
# #         total_obtained_marks = 0

# #         for mark in marks_qs:
# #             total_full_marks += mark.full_marks or 0
# #             total_obtained_marks += mark.marks_obtained or 0

# #         if total_full_marks:
# #             percentage = round((total_obtained_marks / total_full_marks) * 100, 2)
# #         else:
# #             percentage = 0

# #         if percentage >= 90:
# #             grade = "A+"
# #         elif percentage >= 80:
# #             grade = "A"
# #         elif percentage >= 70:
# #             grade = "B+"
# #         elif percentage >= 60:
# #             grade = "B"
# #         elif percentage >= 50:
# #             grade = "C"
# #         else:
# #             grade = "F"

# #         percentages.append(percentage)
# #         student_results.append(
# #             {
# #                 "student": student,
# #                 "total_marks": total_full_marks,
# #                 "obtained_marks": total_obtained_marks,
# #                 "percentage": percentage,
# #                 "grade": grade,
# #                 "report_url": reverse(
# #                     "report-card",
# #                     kwargs={"student_id": student.id, "exam_name": selected_exam or ""},
# #                 )
# #                 if selected_exam
# #                 else reverse("report-card", kwargs={"student_id": student.id, "exam_name": "Mid-Term"}),
# #             }
# #         )

# #     total_students = len(student_results)
# #     class_average = round(sum(percentages) / total_students, 2) if total_students else 0
# #     highest_percentage = max(percentages) if percentages else 0
# #     lowest_percentage = min(percentages) if percentages else 0

# #     context = {
# #         "students_results": student_results,
# #         "total_students": total_students,
# #         "class_average": class_average,
# #         "highest_percentage": highest_percentage,
# #         "lowest_percentage": lowest_percentage,
# #         "available_exams": available_exams,
# #         "selected_exam": selected_exam,
# #         "search_query": search_query,
# #     }
# #     return render(request, "academics/student_results.html", context)














# # from django.shortcuts import redirect, render,get_object_or_404
# # from django.contrib import messages
# # from .models import Assignment, Subject
# # from students.models import ClassRoom
# # from .models import Marks, Subject


# # def add_assignment(request):
# #     classroom = ClassRoom.objects.filter(teacher=request.user).first()

# #     if not classroom:
# #         messages.error(request, "No Classroom assigned to you")
# #         return redirect("dashboard")

# #     subjects = Subject.objects.filter(classroom=classroom)
# #     if request.method == "POST":
# #         title = request.POST.get("title")
# #         description = request.POST.get("description")
# #         subject_id = request.POST.get("subject")

# #         subject = Subject.objects.get(id=subject_id)
# #         Assignment.objects.create(
# #             title=title, description=description, subject=subject, classroom=classroom
# #         )
# #         messages.success(request, "Assignment Created Successfully")
# #         return redirect("assignment-list")
# #     context = {"classroom": classroom, "subjects": subjects}
# #     return render(request, "academics/assignment_form.html", context)


# # def assignment_list(request):
# #     assignments = (
# #         Assignment.objects.filter(classroom__teacher=request.user)
# #         .select_related("subject", "classroom")
# #         .order_by("-created_at")
# #     )
# #     return render(
# #         request, "academics/assignment_list.html", {"assignments": assignments}
# #     )


# # def add_marks(request):
# #     classroom = ClassRoom.objects.filter(teacher=request.user).first()
# #     if not classroom:
# #         messages.error(request, "No Classroom assigned to you")
# #         return redirect("dashboard")
# #     students = classroom.students.all()
# #     subjects = Subject.objects.filter(classroom=classroom)
# #     if request.method == "POST":
# #         subject_id = request.POST.get("subject")
# #         exam_name = request.POST.get("exam_name")

# #         if not subject_id or not exam_name:
# #             messages.error(request, "Subject and exam name are required..")
# #             return redirect("add-marks")

# #         subject = Subject.objects.get(id=subject_id, classroom=classroom)

# #         for student in students:
# #             marks = request.POST.get(f"student_{student.id}")
# #             if not marks:
# #                 continue
# #             Marks.objects.update_or_create(
# #                 student=student,
# #                 subject=subject,
# #                 exam_name=exam_name,
# #                 defaults={"marks_obtained": marks},
# #             )
# #         messages.success(request, "Marks saved successfully..")
# #         return redirect("add-marks")

# #     context = {"classroom": classroom, "students": students, "subjects": subjects}
# #     return render(request, "academics/marks_form.html", context)


# # def view_marks(request):
# #     classroom = ClassRoom.objects.filter(teacher=request.user).first()
# #     marks = Marks.objects.none()
# #     subjects = Subject.objects.none()
# #     exam_name = []
# #     if classroom:
# #         subjects = Subject.objects.filter(classroom=classroom)
# #         marks = (
# #             Marks.objects.filter(student__classroom=classroom)
# #             .select_related(
# #                 "student",
# #                 "subject",
# #             )
# #             .order_by("student__name")
# #         )
# #         subject_id = request.GET.get("subject")
# #         exam_name = request.GET.get("exam")

# #         if subject_id:
# #             marks = marks.filter(subject_id=subject_id)

# #         if exam_name:
# #             marks = marks.filter(exam_name=exam_name)

# #         exam_name = (
# #             Marks.objects.filter(student__classroom=classroom)
# #             .values_list("exam_name", flat=True)
# #             .distinct()
# #         )
# #     context = {
# #         "marks": marks,
# #         "subjects": subjects,
# #         "exam_names": exam_name,
# #         "selected_subject": request.GET.get("subject", ""),
# #         "selected_exam": request.GET.get("exam", ""),
# #     }
# #     return render(request, "academics/marks_list.html", context)



























# # # # from django.shortcuts import render,redirect

# # # # # Create your views here.
# # # # from django.contrib import messages
# # # # from .models import Assignment, Subject
# # # # from students.models import ClassRoom

# # # # def add_assignment(request):
# # # #     classroom =ClassRoom.objects.filter(teacher=request.user).first()
    
# # # #     if not classroom:
# # # #         messages.error(request,"No classroom assiged to you")
# # # #         return redirect("dashboard")
# # # #     subjects=Subject.objects.filter(classroom=classroom)
    
# # # #     if request.method=="POST":
# # # #         title=request.POST.get("title")
# # # #         description=request.POST.get("description")
# # # #         subject_id=request.POST.get("subject")
        
        
        
# # # from django.shortcuts import render
# # # from django.contrib import messages
# # # from django.shortcuts import redirect, render
# # # from academics.models import Assignment, Subject
# # # from students.models import ClassRoom


# # # def add_assignment(request):
# # #     classroom = ClassRoom.objects.filter(teacher=request.user).first()
# # #     if not classroom:
# # #         messages.error(request, "No classroom assigned to you.")
# # #         return redirect("accounts:dashboard")
# # #     subjects = Subject.objects.filter(classroom=classroom)
# # #     if request.method == "POST":
# # #         title = request.POST.get("title")
# # #         description = request.POST.get("description")
# # #         subject_id = request.POST.get("subject")
# # #         subject = Subject.objects.get(id=subject_id)
# # #         Assignment.objects.create(
# # #             title=title,
# # #             description=description,
# # #             subject=subject,
# # #             classroom=classroom,
# # #         )
# # #         messages.success(request, "Assignment created successfully.")
# # #         return redirect("assignment-list")
# # #     context = {
# # #         "classroom": classroom,
# # #         "subjects": subjects,
# # #     }
# # #     return render(
# # #         request,
# # #         "academics/assignment_form.html",
# # #         context,
# # #     )


# # # def assignments_list(request):
# # #     assignments = (
# # #         Assignment.objects.filter(classroom__teacher=request.user)
# # #         .select_related("subject", "classroom")
# # #         .order_by("-created_at")
# # #     )
# # #     return render(
# # #         request, "academics/assignment_list.html", {"assignments": assignments}
# # #     )
    
# # # def add_marks(request):
# # #     classroom=ClassRoom.objects,filter(teacher=request.user)
    
# # #     if not classroom:
# # #         messages.error(request,"No Classroom assigned to you")
# # #         return redirect("dashboard")
    
# # #     students=classroom.students.all()
# # #     subjects=Subject.objects.filter(classroom=classroom)
    
# # #     if request.method=="POST":
# # #         subject_id=request.POST.get("description")
# # #         exam_name=request.POST.get("exam_name")
        
# # #         if not subject_id or not exam_name:
# # #             messages.eror(request,"Subject and exam are require")
# # #             return redirect("add_marks")
        
# # #         subject=Subject.objects.get(id=subject_id,classroom=classroom)
# # #         for student in students:
# # #             marks=request.Post.get(f"student_{student.id}")
# # #             if not marks:
# # #                 continue
            
# # #             marks.objects.update_or_create(
# # #                 student=student, 
# # #                 subject=subject,
# # #                 exam_name=exam_name,
# # #                 defaults={"marks_obtained":marks},
# # #             )
# # #         messages.success(request,"Marks saved successfully.")
# # #         return redirect("add-marks")
# # #     context={
        
# # #         "classroom":classroom, 
# # #         "students":students,
# # #         "subjects":subjects
# # #     }
# # #     return render(request,"academics/marks_form.html",context)
        
        