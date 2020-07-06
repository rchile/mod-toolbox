from django.urls import path

from toolbox import views, views_api, views_session

urlpatterns = [
    path('', views_session.index, name='index'),
    path('home', views.home, name='home'),
    path('entries', views.entries, name='entries'),
    path('entries/page/<int:page>', views.entries, name='entries_paged'),
    path('entry/<str:entry_id>', views.entry_details, name='entry'),
    path('user/', views.user_search, name='user_form'),
    path('user/<str:username>', views.user_details, name='user_detail'),
    path('modmail', views.modmail, name='modmail'),
    path('modmail/<slug:convo_id>', views.modmail, name='modmail_details'),
    path('session/login', views_session.login, name='login'),
    path('session/logout', views_session.logout, name='logout'),
    path('session/return', views_session.login_return, name='login_return'),

    path('api/modlog/', views_api.modlog)
]
