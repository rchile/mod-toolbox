from django.urls import path

import toolbox.views_session
from toolbox import views

urlpatterns = [
    path('', views.index, name='index'),
    path('home', views.home, name='home'),
    path('entries', views.entries, name='entries'),
    path('entries/page/<int:page>', views.entries, name='entries_paged'),
    path('user', views.user, name='user_form'),
    path('user/<str:username>', views.user, name='user_detail'),
    path('session/login', toolbox.views_session.login, name='login'),
    path('session/logout', toolbox.views_session.logout, name='logout'),
    path('session/return', toolbox.views_session.login_return, name='login_return'),
]
