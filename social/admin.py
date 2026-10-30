from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Comment, Follow, Like, Post, User


@admin.register(User)
class SocialUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("bio",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profile", {"fields": ("bio",)}),
    )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "created_at", "updated_at")
    search_fields = ("author__username", "content")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "created_at")
    search_fields = ("author__username", "content")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    search_fields = ("user__username",)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__username", "following__username")
