from django.shortcuts import get_object_or_404, render, redirect
from django.utils.timezone import now
from .models import Post, Category, Comment
from django.views.generic import UpdateView
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator
from django.views import generic
from .forms import PostForm, CommentForm
from django.db.models import Count, Q


# Фильтрация постов с условием публикации и даты
def filter_posts(queryset):
    queryset = queryset.filter(is_published=True)
    queryset = queryset.filter(category__is_published=True)
    queryset = queryset.filter(pub_date__lte=now())
    return queryset.order_by('-created_at')


# Пагинация
def pagin(request, post_list):
    page_number = request.GET.get('page')
    paginator = Paginator(post_list, 10)
    return paginator.get_page(page_number)


# Представление для домашней страницы
def index(request):
    template = 'blog/index.html'
    post_list = Post.objects.select_related('category').annotate(
        comment_count=Count('comment'))
    filtered_posts = filter_posts(post_list)
    page_obj = pagin(request, filtered_posts)
    context = {'page_obj': page_obj}
    return render(request, template, context)


# Представление для отображения поста
def post_detail(request, pk):
    template = 'blog/detail.html'
    post = get_object_or_404(
        Post.objects.select_related('category').filter(
            Q(is_published=True,
              category__is_published=True,
              pub_date__lte=now()) | Q(
                author=request.user if request.user.is_authenticated else None
            )
        ),
        pk=pk
    )
    comments = Comment.objects.filter(post=post).select_related('author')
    form = CommentForm()
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


# Представление для отображения постов по категории
def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(Category, slug=category_slug,
                                 is_published=True)
    post_list = Post.objects.filter(category=category).annotate(
        comment_count=Count('comment'))
    filtered_posts = filter_posts(post_list)
    page_obj = pagin(request, filtered_posts)
    context = {'category': category, 'page_obj': page_obj}
    return render(request, template, context)


# Представление для отображения профиля пользователя
def profile(request, username):
    user = get_object_or_404(User, username=username)
    post_list = Post.objects.filter(author=user).annotate(
        comment_count=Count('comment'))
    page_obj = pagin(request, post_list)
    context = {'profile': user, 'page_obj': page_obj}
    return render(request, 'blog/profile.html', context)


class ProfileUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Обновление профиля пользователя."""

    model = User
    template_name = 'blog/user.html'
    fields = ['first_name', 'last_name', 'email']

    def get_object(self):
        return self.request.user

    def test_func(self):
        username = self.kwargs.get('username')
        if username:
            return self.request.user.username == username
        return True

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('blog:index')
        return super().handle_no_permission()

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user.username})


class PostBase(LoginRequiredMixin):
    """Базовый класс для работы с постами."""

    model = Post

    def get_queryset(self):
        return self.model.objects.filter(is_published=True)


class PostCreate(PostBase, generic.CreateView):
    """Создание поста."""

    template_name = 'blog/create.html'
    form_class = PostForm

    def form_valid(self, form):
        new_post = form.save(commit=False)
        new_post.author = self.request.user
        new_post.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user.username})


class PostUpdate(PostBase, generic.UpdateView):
    """Редактирование поста."""

    template_name = 'blog/create.html'
    form_class = PostForm

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            post_id = self.kwargs.get('pk')
            return redirect('blog:post_detail', pk=post_id)
        return super().handle_no_permission()

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect('blog:post_detail', pk=post.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'pk': self.object.pk})


class PostDelete(PostBase, generic.DeleteView):
    """Удаление поста."""

    template_name = 'blog/create.html'

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            post_id = self.kwargs.get('pk')
            return redirect('blog:post_detail', pk=post_id)
        return super().handle_no_permission()

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect('blog:post_detail', pk=post.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('blog:profile',
                            kwargs={'username': self.request.user.username})


class PostComment(
        LoginRequiredMixin,
        generic.detail.SingleObjectMixin,
        generic.FormView
):
    """Добавление комментария к посту."""

    model = Post
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.post = self.object
        comment.author = self.request.user
        comment.save()
        return super().form_valid(form)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            post_id = self.kwargs.get('pk')
            return redirect('blog:post_detail', pk=post_id)
        return super().handle_no_permission()

    def get_success_url(self):
        post = self.get_object()
        return reverse('blog:post_detail',
                       kwargs={'pk': post.pk}) + '#comments'


class CommentBase(LoginRequiredMixin):
    """Базовый класс для работы с комментариями."""

    model = Comment
    pk_url_kwarg = 'comment_id'

    def get_success_url(self):
        comment = self.get_object()
        return reverse('blog:post_detail',
                       kwargs={'pk': comment.post.pk}) + '#comments'

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            post_id = self.kwargs.get('pk')
            return redirect('blog:post_detail', pk=post_id)
        return super().handle_no_permission()

    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user:
            return redirect('blog:post_detail', pk=comment.post.pk)
        return super().dispatch(request, *args, **kwargs)


class CommentUpdate(CommentBase, generic.UpdateView):
    """Редактирование комментария."""

    template_name = 'blog/comment.html'
    form_class = CommentForm


class CommentDelete(CommentBase, generic.DeleteView):
    """Удаление комментария."""

    template_name = 'blog/comment.html'
