from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.index, name='index'),
    path(
        'posts/<int:pk>/', views.post_detail, 
        name='post_detail'
    ),
    path(
        'posts/create/', views.PostCreate.as_view(), 
        name='create_post'
    ),
    path(
        'posts/<int:pk>/edit/', views.PostUpdate.as_view(), 
        name='edit_post'
    ),
    path(
        'posts/<int:pk>/delete/', views.PostDelete.as_view(), 
        name='delete_post'
    ),
    path('posts/<int:pk>/comment/', views.PostComment.as_view(),
         name='add_comment'),
    path(
        'posts/<int:pk>/edit_comment/<int:comment_id>/',
        views.CommentUpdate.as_view(), name='edit_comment'
    ),
    path(
        'posts/<int:pk>/delete_comment/<int:comment_id>/',
        views.CommentDelete.as_view(), name='delete_comment'
    ),
    path(
        'category/<slug:category_slug>/',
        views.category_posts, name='category_posts'
    ),
    path(
        'profile/edit/', views.ProfileUpdateView.as_view(), 
        name='edit_profile'
    ),
    path(
        'profile/<str:username>/', views.profile, 
        name='profile'
    ),
]
