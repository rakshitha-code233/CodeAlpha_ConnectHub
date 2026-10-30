import json

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import ProfileForm, RegistrationForm
from .models import Comment, Follow, Like, Post, User


def _json_error(message, status):
    return JsonResponse({"error": message}, status=status)


def _post_data(request):
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return data if isinstance(data, dict) else None
    return request.POST


def home(request):
    user = request.user
    query = request.GET.get("q", "").strip()[:100]
    posts = Post.objects.select_related("author").prefetch_related(
        "comments__author",
        "likes",
    )
    if query:
        posts = posts.filter(
            Q(content__icontains=query)
            | Q(author__username__icontains=query)
            | Q(author__first_name__icontains=query)
            | Q(author__last_name__icontains=query)
        )
    suggestions = (
        User.objects.exclude(pk=user.pk)
        if user.is_authenticated
        else User.objects.none()
    )
    if query:
        suggestions = suggestions.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(bio__icontains=query)
        )
    followed_ids = (
        set(user.following.values_list("following_id", flat=True))
        if user.is_authenticated
        else set()
    )
    context = {}

    if user.is_authenticated:
        context.update(
            display_name=user.get_full_name() or user.username,
            avatar_initial=(user.get_full_name() or user.username)[0].upper(),
            post_count=user.posts.count(),
            follower_count=user.followers.count(),
            following_count=user.following.count(),
        )

    context.update(
        query=query,
        posts=posts,
        suggestions=[
            {"user": suggested_user, "is_following": suggested_user.pk in followed_ids}
            for suggested_user in suggestions.order_by("username")[:5]
        ],
    )
    return render(request, "social/home.html", context)


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profile", username=request.user.username)
    return render(request, "social/profile_form.html", {"form": form})


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = (
        Post.objects.filter(author=profile_user)
        .select_related("author")
        .prefetch_related("comments__author", "likes")
    )
    is_following = (
        request.user.is_authenticated
        and request.user.following.filter(following=profile_user).exists()
    )
    return render(
        request,
        "social/profile.html",
        {
            "profile_user": profile_user,
            "posts": posts,
            "post_count": posts.count(),
            "follower_count": profile_user.followers.count(),
            "following_count": profile_user.following.count(),
            "is_following": is_following,
        },
    )


@require_http_methods(["POST"])
@login_required
def create_post(request):
    data = _post_data(request)
    if data is None:
        return _json_error("Invalid request body.", 400)
    content = data.get("content")
    if not isinstance(content, str):
        return _json_error("Post content must be text.", 400)
    content = content.strip()
    if not content or len(content) > 500:
        return _json_error("Post content must be between 1 and 500 characters.", 400)

    post = Post.objects.create(author=request.user, content=content)
    return JsonResponse(
        {
            "id": post.pk,
            "content": post.content,
            "author": request.user.get_full_name() or request.user.username,
            "username": request.user.username,
            "initial": (request.user.get_full_name() or request.user.username)[0].upper(),
            "created_at": post.created_at.isoformat(),
            "like_count": 0,
            "comment_count": 0,
            "liked": False,
            "like_url": reverse("toggle_like", args=[post.pk]),
            "comment_url": reverse("create_comment", args=[post.pk]),
            "profile_url": reverse("profile", args=[request.user.username]),
        },
        status=201,
    )


@require_http_methods(["POST"])
@login_required
def create_comment(request, post_id):
    data = _post_data(request)
    if data is None:
        return _json_error("Invalid request body.", 400)
    content = data.get("content")
    if not isinstance(content, str):
        return _json_error("Comment must be text.", 400)
    content = content.strip()
    if not content or len(content) > 300:
        return _json_error("Comment must be between 1 and 300 characters.", 400)

    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        return _json_error("Post not found.", 404)

    comment = Comment.objects.create(post=post, author=request.user, content=content)
    return JsonResponse(
        {
            "id": comment.pk,
            "content": comment.content,
            "author": request.user.get_full_name() or request.user.username,
        },
        status=201,
    )


@require_http_methods(["POST"])
@login_required
def toggle_like(request, post_id):
    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        return _json_error("Post not found.", 404)

    like, created = Like.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    return JsonResponse(
        {
            "liked": created,
            "like_count": post.likes.count(),
        }
    )


@require_http_methods(["POST"])
@login_required
def toggle_follow(request, user_id):
    if user_id == request.user.pk:
        return _json_error("You cannot follow yourself.", 400)

    try:
        followed_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return _json_error("User not found.", 404)

    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=followed_user,
    )
    if not created:
        follow.delete()
    return JsonResponse(
        {
            "following": created,
            "follower_count": followed_user.followers.count(),
            "following_count": request.user.following.count(),
        }
    )


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")

    return render(request, "social/auth_form.html", {
        "form": form,
        "title": "Create your account",
        "eyebrow": "Find your people",
        "intro": "Join the conversation, share what matters, and make your corner of ConnectHub your own.",
        "submit_label": "Register",
        "alternate_prompt": "Already have an account?",
        "alternate_url": reverse("login"),
        "alternate_label": "Log in",
    })
