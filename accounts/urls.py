# from django.urls import path
# from . import views
# urlpatterns = [
#     path("",views.teacher_login, name='login'),
#     path("logout/",views.teacher_logout, name='logout'),
#     path("dashboard/",views.dashboard, name="dashboard"),
# ]

# from django.urls import path
# from . import views
# urlpatterns = [
#     path('',views.home,name='home'),
#     path('about/' ,views.about,name="about"),
#     path('contact/', views.contact,name="contact" ),
#     path("login/", views.teacher_login, name="login"),
#     path("accounts/logout/", views.teacher_logout, name="teacher-logout"),
#     path("dashboard/", views.dashboard, name="dashboard"),
   
# ]
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),

    path("login/", views.teacher_login, name="login"),

    path(
        "admin-login/",
        views.admin_login,
        name="admin-login"
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard"
    ),

    path(
        "admin-dashboard/",
        views.admin_dashboard,
        name="admin-dashboard"
    ),

    path(
        "logout/",
        views.teacher_logout,
        name="teacher-logout"
    ),
]