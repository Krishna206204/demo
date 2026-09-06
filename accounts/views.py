from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import User
from students.models import Student, ClassRoom
from academics.models import Subject


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------
def home(request):
    return render(request, "accounts/home.html")


# ---------------------------------------------------------
# CONTACT
# ---------------------------------------------------------
def contact(request):
    return render(request, "accounts/contact.html")


# ---------------------------------------------------------
# ABOUT
# ---------------------------------------------------------
def about(request):
    return render(request, "accounts/about.html")


# ---------------------------------------------------------
# TEACHER LOGIN
# ---------------------------------------------------------
def teacher_login(request):

    # If already logged in
    if request.user.is_authenticated:

        if request.user.role == "ADMIN" or request.user.is_superuser:
            return redirect("admin-dashboard")

        if request.user.role == "TEACHER":
            return redirect("dashboard")

        return redirect("home")

    # Handle login form
    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        # Invalid username/password
        if user is None:

            messages.error(
                request,
                "Invalid username or password."
            )

            return redirect("login")

        # Only Teacher can login from teacher login page
        if user.role != "TEACHER":

            messages.error(
                request,
                "This account is not a Teacher account."
            )

            return redirect("login")

        # Login teacher
        login(request, user)

        messages.success(
            request,
            "Teacher login successful."
        )

        return redirect("dashboard")

    return render(
        request,
        "accounts/login.html"
    )


# ---------------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------------
def admin_login(request):

    # If already logged in
    if request.user.is_authenticated:

        if request.user.role == "ADMIN" or request.user.is_superuser:
            return redirect("admin-dashboard")

        return redirect("dashboard")

    # Handle login form
    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        # Invalid credentials
        if user is None:

            messages.error(
                request,
                "Invalid username or password."
            )

            return redirect("admin-login")

        # Check Admin role
        if user.role != "ADMIN" and not user.is_superuser:

            messages.error(
                request,
                "You do not have Admin access."
            )

            return redirect("admin-login")

        # Login admin
        login(request, user)

        messages.success(
            request,
            "Admin login successful."
        )

        return redirect("admin-dashboard")

    return render(
        request,
        "accounts/admin_login.html"
    )


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------
def teacher_logout(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect("home")


# ---------------------------------------------------------
# TEACHER DASHBOARD
# ---------------------------------------------------------
@login_required
def dashboard(request):

    # Admin should use Admin Dashboard
    if request.user.role == "ADMIN" or request.user.is_superuser:
        return redirect("admin-dashboard")

    # Only Teacher should reach this section
    if request.user.role != "TEACHER":

        messages.error(
            request,
            "You are not authorized to access the Teacher Dashboard."
        )

        return redirect("home")

    # Get teacher's classroom
    classroom = ClassRoom.objects.filter(
        teacher=request.user
    ).first()

    student_count = 0
    subject_count = 0

    if classroom:

        student_count = classroom.students.count()

        subject_count = Subject.objects.filter(
            classroom=classroom
        ).count()

    context = {
        "classroom": classroom,
        "student_count": student_count,
        "subject_count": subject_count,
    }

    return render(
        request,
        "accounts/dashboard.html",
        context
    )


# ---------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------
@login_required
def admin_dashboard(request):

    # Only Admin / Superuser
    if request.user.role != "ADMIN" and not request.user.is_superuser:

        messages.error(
            request,
            "You are not authorized to access the Admin Dashboard."
        )

        return redirect("dashboard")

    # Count complete system data
    total_students = Student.objects.count()

    total_teachers = User.objects.filter(
        role="TEACHER"
    ).count()

    total_classrooms = ClassRoom.objects.count()

    total_subjects = Subject.objects.count()

    context = {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_classrooms": total_classrooms,
        "total_subjects": total_subjects,
    }

    return render(
        request,
        "accounts/admin_dashboard.html",
        context
    )