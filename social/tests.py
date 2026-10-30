import json
import re

from django.db import IntegrityError, transaction
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Comment, Follow, Like, Post, User


class SocialModelsTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username="author",
            password="test-password",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="test-password",
        )
        self.post = Post.objects.create(author=self.author, content="Hello!")

    def test_post_and_comment_relationships(self):
        comment = Comment.objects.create(
            post=self.post,
            author=self.other_user,
            content="Welcome!",
        )

        self.assertEqual(self.author.posts.get(), self.post)
        self.assertEqual(self.post.comments.get(), comment)
        self.assertEqual(self.other_user.comments.get(), comment)

    def test_user_can_like_a_post_once(self):
        Like.objects.create(post=self.post, user=self.other_user)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Like.objects.create(post=self.post, user=self.other_user)

    def test_follow_relationships_cannot_be_duplicated_or_self_referential(self):
        Follow.objects.create(follower=self.author, following=self.other_user)
        self.assertEqual(self.other_user.followers.get().follower, self.author)
        self.assertEqual(self.author.following.get().following, self.other_user)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Follow.objects.create(follower=self.author, following=self.other_user)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Follow.objects.create(follower=self.author, following=self.author)


class AuthenticationTests(TestCase):
    def test_auth_pages_are_available_and_empty_registration_shows_validation(self):
        response = self.client.get(reverse("login"), {"next": "/friends/"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")
        self.assertContains(response, reverse("register"))
        self.assertContains(response, reverse("password_reset"))
        self.assertContains(response, "Forgot password?")
        self.assertContains(response, '<input type="hidden" name="next" value="/friends/">')

        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")

        response = self.client.post(reverse("register"), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertFalse(User.objects.exists())

        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("login"))
        self.assertContains(response, reverse("register"))
        self.assertNotContains(response, "Log Out")

    def test_registration_creates_user_and_logs_them_in(self):
        response = self.client.post(
            "/register/",
            {
                "username": "newmember",
                "email": "newmember@example.com",
                "password1": "R@ndom-password-491!",
                "password2": "R@ndom-password-491!",
            },
        )

        self.assertRedirects(response, "/")
        self.assertEqual(self.client.session["_auth_user_id"], str(
            User.objects.get(username="newmember").pk
        ))

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            "/register/",
            {
                "username": "newmember",
                "email": "newmember@example.com",
                "password1": "R@ndom-password-491!",
                "password2": "different-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newmember").exists())
        self.assertContains(response, "password")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_email_link_resets_password(self):
        user = User.objects.create_user(
            username="resetmember",
            email="resetmember@example.com",
            password="R@ndom-password-491!",
        )

        response = self.client.post(
            reverse("password_reset"),
            {"email": user.email},
        )
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Reset your ConnectHub password", mail.outbox[0].subject)

        reset_path = re.search(
            r"http://testserver(/reset/[\w-]+/[\w-]+/)",
            mail.outbox[0].body,
        ).group(1)
        response = self.client.get(reset_path, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a new password")

        response = self.client.post(
            response.request["PATH_INFO"],
            {
                "new_password1": "N3w-and-safer-password!",
                "new_password2": "N3w-and-safer-password!",
            },
        )
        self.assertRedirects(response, reverse("password_reset_complete"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("N3w-and-safer-password!"))
        self.assertTrue(self.client.login(
            username="resetmember",
            password="N3w-and-safer-password!",
        ))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_response_does_not_disclose_unknown_email(self):
        response = self.client.post(
            reverse("password_reset"),
            {"email": "unknown@example.com"},
        )
        self.assertRedirects(response, reverse("password_reset_done"))
        response = self.client.get(reverse("password_reset_done"))
        self.assertContains(response, "If an account matches that email address")
        self.assertEqual(len(mail.outbox), 0)

    def test_login_redirects_to_next_and_logout_clears_the_session(self):
        User.objects.create_user(
            username="redirectmember",
            password="R@ndom-password-491!",
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "redirectmember",
                "password": "R@ndom-password-491!",
                "next": "/?from=login",
            },
        )
        self.assertRedirects(
            response,
            "/?from=login",
            fetch_redirect_response=False,
        )
        self.assertEqual(
            self.client.session["_auth_user_id"],
            str(User.objects.get(username="redirectmember").pk),
        )

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_logout_and_home_show_the_authenticated_profile(self):
        user = User.objects.create_user(
            username="profileuser",
            password="R@ndom-password-491!",
            first_name="Profile",
            last_name="Member",
            bio="My profile bio",
        )
        Post.objects.create(author=user, content="My post")
        follower = User.objects.create_user(username="follower")
        Follow.objects.create(follower=follower, following=user)
        Follow.objects.create(follower=user, following=follower)

        response = self.client.post(
            "/login/",
            {
                "username": "profileuser",
                "password": "R@ndom-password-491!",
            },
        )

        self.assertRedirects(response, "/")
        response = self.client.get("/")
        self.assertContains(response, "Profile Member")
        self.assertContains(response, "@profileuser")
        self.assertContains(response, "My profile bio")
        self.assertContains(response, '<strong id="profile-post-count">1</strong>')
        self.assertContains(response, '<strong id="profile-following-count">1</strong>')
        self.assertContains(response, 'aria-label="Profile avatar">P</div>')
        self.assertContains(response, "<strong>1</strong>")

        response = self.client.post("/logout/")
        self.assertRedirects(response, "/")
        self.assertContains(self.client.get("/"), "Log in")


class PersistentSocialActionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="member",
            password="R@ndom-password-491!",
        )
        self.other_user = User.objects.create_user(username="another")
        self.client.login(username="member", password="R@ndom-password-491!")

    def post_json(self, url, values=None):
        return self.client.post(
            url,
            data=json.dumps(values or {}),
            content_type="application/json",
        )

    def test_home_search_filters_posts_and_member_suggestions(self):
        matching_post = Post.objects.create(
            author=self.other_user,
            content="A quiet walk along the river",
        )
        Post.objects.create(author=self.user, content="A recipe for lunch")
        self.other_user.first_name = "River"
        self.other_user.save(update_fields=["first_name"])

        response = self.client.get(reverse("home"), {"q": "river"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["posts"].values_list("pk", flat=True)),
            [matching_post.pk],
        )
        self.assertEqual(
            [suggestion["user"] for suggestion in response.context["suggestions"]],
            [self.other_user],
        )
        self.assertContains(response, 'value="river"')
        self.assertContains(response, "Search results for “river”")

        response = self.client.get(reverse("home"), {"q": "no matches"})
        self.assertFalse(response.context["posts"].exists())
        self.assertEqual(response.context["suggestions"], [])
        self.assertContains(response, "No posts match")

    def test_posts_comments_likes_and_follows_persist_on_home(self):
        post_response = self.post_json(
            reverse("create_post"),
            {"content": "Persisted post"},
        )
        self.assertEqual(post_response.status_code, 201)
        post_id = post_response.json()["id"]

        comment_response = self.post_json(
            reverse("create_comment", args=[post_id]),
            {"content": "Persisted comment"},
        )
        self.assertEqual(comment_response.status_code, 201)

        like_url = reverse("toggle_like", args=[post_id])
        self.assertTrue(self.post_json(like_url).json()["liked"])

        follow_url = reverse("toggle_follow", args=[self.other_user.pk])
        self.assertTrue(self.post_json(follow_url).json()["following"])

        response = self.client.get(reverse("home"))
        self.assertContains(response, "Persisted post")
        self.assertContains(response, "Persisted comment")
        self.assertContains(response, "1 like")
        self.assertContains(response, "Following")
        self.assertContains(response, "another")

    def test_like_and_follow_endpoints_toggle_saved_relationships(self):
        post = Post.objects.create(author=self.other_user, content="Other post")
        like_url = reverse("toggle_like", args=[post.pk])
        follow_url = reverse("toggle_follow", args=[self.other_user.pk])

        self.assertTrue(self.post_json(like_url).json()["liked"])
        self.assertFalse(self.post_json(like_url).json()["liked"])
        followed = self.post_json(follow_url).json()
        self.assertTrue(followed["following"])
        self.assertEqual(followed["follower_count"], 1)
        self.assertEqual(followed["following_count"], 1)
        unfollowed = self.post_json(follow_url).json()
        self.assertFalse(unfollowed["following"])
        self.assertEqual(unfollowed["follower_count"], 0)
        self.assertEqual(unfollowed["following_count"], 0)

        self.assertFalse(Like.objects.filter(post=post, user=self.user).exists())
        self.assertFalse(
            Follow.objects.filter(follower=self.user, following=self.other_user).exists()
        )

    def test_social_actions_require_authentication(self):
        self.client.logout()

        response = self.post_json(reverse("create_post"), {"content": "Not saved"})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.filter(content="Not saved").exists())

    def test_public_profile_shows_member_details_posts_and_follow_state(self):
        Post.objects.create(author=self.other_user, content="A public profile post")
        Follow.objects.create(follower=self.user, following=self.other_user)

        response = self.client.get(
            reverse("profile", args=[self.other_user.username])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "@another")
        self.assertContains(response, "A public profile post")
        self.assertContains(response, "Following")
        self.assertContains(response, '<strong class="follower-count">1</strong>')

    def test_profile_can_be_edited_and_updates_public_view(self):
        response = self.client.get(reverse("edit_profile"))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("edit_profile"),
            {
                "first_name": "Community",
                "last_name": "Member",
                "bio": "Hello from my profile",
            },
        )

        self.assertRedirects(
            response,
            reverse("profile", args=[self.user.username]),
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Community Member")
        self.assertEqual(self.user.bio, "Hello from my profile")
        self.assertContains(
            self.client.get(reverse("profile", args=[self.user.username])),
            "Hello from my profile",
        )

    def test_profile_edit_requires_authentication_and_unknown_profiles_are_404(self):
        self.client.logout()

        response = self.client.get(reverse("edit_profile"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('edit_profile')}",
        )
        self.assertEqual(
            self.client.get(reverse("profile", args=["not-a-member"])).status_code,
            404,
        )
