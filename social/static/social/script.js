document.addEventListener("DOMContentLoaded", () => {
    const postForm = document.getElementById("post-form");
    const postInput = document.getElementById("post-content");
    const characterCount = document.getElementById("character-count");
    const postsContainer = document.getElementById("posts-container");
    const emptyMessage = document.getElementById("empty-message");
    const postCount = document.getElementById("profile-post-count");
    const initialPostCount = postCount
        ? Number.parseInt(postCount.textContent, 10) || 0
        : 0;
    let createdPosts = 0;

    function showError(message) {
        let error = document.getElementById("action-error");
        if (!error) {
            error = document.createElement("p");
            error.id = "action-error";
            error.className = "form-errors";
            error.setAttribute("role", "alert");
            postsContainer.before(error);
        }
        error.textContent = message;
    }

    async function sendRequest(url, values) {
        const csrfInput = document.querySelector('[name="csrfmiddlewaretoken"]');
        if (!csrfInput) {
            throw new Error("Unable to verify your session. Please reload the page.");
        }
        const csrfToken = csrfInput.value;
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify(values),
        });
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            throw new Error("Please log in again to continue.");
        }
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || "The action could not be completed.");
        }
        return result;
    }

    function updatePostCount() {
        if (postCount) {
            postCount.textContent = initialPostCount + createdPosts;
        }
    }

    function updateEmptyMessage() {
        if (!emptyMessage) {
            return;
        }
        emptyMessage.classList.toggle(
            "hidden",
            postsContainer.querySelectorAll(".post").length > 0
        );
    }

    function createPostElement(data) {
        const article = document.createElement("article");
        article.className = "card post";
        article.dataset.postId = data.id;
        article.dataset.likeUrl = data.like_url;
        article.dataset.commentUrl = data.comment_url;

        const header = document.createElement("div");
        header.className = "post-header";
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.textContent = data.initial;
        const author = document.createElement("div");
        author.className = "post-author";
        const profileLink = document.createElement("a");
        profileLink.href = data.profile_url;
        const name = document.createElement("strong");
        name.textContent = data.author;
        profileLink.append(name);
        const handle = document.createElement("span");
        handle.className = "muted";
        handle.textContent = `@${data.username} · Just now`;
        author.append(profileLink, handle);
        header.append(avatar, author);

        const content = document.createElement("p");
        content.className = "post-text";
        content.textContent = data.content;

        const stats = document.createElement("div");
        stats.className = "post-stats";
        const likeCount = document.createElement("span");
        likeCount.className = "like-count";
        likeCount.textContent = "0 likes";
        const commentCount = document.createElement("span");
        commentCount.className = "comment-count";
        commentCount.textContent = "0 comments";
        stats.append(likeCount, commentCount);

        const actions = document.createElement("div");
        actions.className = "post-actions";
        const likeButton = document.createElement("button");
        likeButton.type = "button";
        likeButton.className = "action-button like-button";
        likeButton.setAttribute("aria-pressed", "false");
        likeButton.textContent = "♡ Like";
        const commentButton = document.createElement("button");
        commentButton.type = "button";
        commentButton.className = "action-button comment-toggle";
        commentButton.textContent = "💬 Comment";
        actions.append(likeButton, commentButton);

        const commentForm = document.createElement("form");
        commentForm.className = "comment-form hidden";
        const commentInput = document.createElement("input");
        commentInput.name = "comment";
        commentInput.maxLength = 300;
        commentInput.placeholder = "Write a comment...";
        commentInput.required = true;
        commentInput.setAttribute("aria-label", "Write a comment");
        const sendButton = document.createElement("button");
        sendButton.type = "submit";
        sendButton.className = "primary-button";
        sendButton.textContent = "Send";
        commentForm.append(commentInput, sendButton);

        const comments = document.createElement("div");
        comments.className = "comments-list";
        article.append(header, content, stats, actions, commentForm, comments);
        return article;
    }

    if (postInput) {
        postInput.addEventListener("input", () => {
            characterCount.textContent = `${postInput.value.length}/500`;
        });

        postForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const content = postInput.value.trim();
            if (!content) {
                return;
            }

            const submitButton = postForm.querySelector(
                'button[type="submit"]'
            );
            submitButton.disabled = true;
            try {
                const post = await sendRequest(postForm.action, { content });
                const searchInput = document.getElementById("community-search");
                const query = searchInput ? searchInput.value.trim().toLocaleLowerCase() : "";
                const matchesSearch = !query || [
                    post.content,
                    post.author,
                    post.username,
                ].some((value) => value.toLocaleLowerCase().includes(query));
                if (matchesSearch) {
                    postsContainer.prepend(createPostElement(post));
                }
                postForm.reset();
                characterCount.textContent = "0/500";
                createdPosts += 1;
                updatePostCount();
                updateEmptyMessage();
            } catch (error) {
                showError(error.message);
            } finally {
                submitButton.disabled = false;
            }
        });
    }

    postsContainer.addEventListener("click", async (event) => {
        const button = event.target.closest("button");
        if (!button) {
            return;
        }

        const post = button.closest(".post");
        if (button.classList.contains("comment-toggle") && post) {
            const form = post.querySelector(".comment-form");
            form.classList.toggle("hidden");
            if (!form.classList.contains("hidden")) {
                form.querySelector("input").focus();
            }
            return;
        }

        if (button.classList.contains("like-button") && post) {
            button.disabled = true;
            try {
                const result = await sendRequest(post.dataset.likeUrl, {});
                const countElement = post.querySelector(".like-count");
                countElement.textContent =
                    `${result.like_count} ${result.like_count === 1 ? "like" : "likes"}`;
                button.setAttribute("aria-pressed", String(result.liked));
                button.classList.toggle("liked", result.liked);
                button.textContent = result.liked ? "♥ Liked" : "♡ Like";
            } catch (error) {
                showError(error.message);
            } finally {
                button.disabled = false;
            }
        }
    });

    postsContainer.addEventListener("submit", async (event) => {
        const form = event.target;
        if (!form.matches(".comment-form")) {
            return;
        }
        event.preventDefault();

        const input = form.querySelector('input[name="comment"]');
        const content = input.value.trim();
        if (!content) {
            return;
        }

        const post = form.closest(".post");
        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        try {
            const comment = await sendRequest(post.dataset.commentUrl, { content });
            const item = document.createElement("p");
            item.className = "comment-item";
            const author = document.createElement("strong");
            author.textContent = `${comment.author}: `;
            item.append(author, document.createTextNode(comment.content));
            post.querySelector(".comments-list").append(item);

            const commentCount = post.querySelector(".comment-count");
            const total = post.querySelectorAll(".comment-item").length;
            commentCount.textContent =
                `${total} ${total === 1 ? "comment" : "comments"}`;
            form.reset();
        } catch (error) {
            showError(error.message);
        } finally {
            submitButton.disabled = false;
        }
    });

    document.querySelectorAll(".suggestion button.follow-button").forEach((button) => {
        button.addEventListener("click", async (event) => {
            event.preventDefault();
            const suggestion = button.closest(".suggestion");
            button.disabled = true;
            try {
                const result = await sendRequest(suggestion.dataset.followUrl, {});
                button.setAttribute("aria-pressed", String(result.following));
                button.classList.toggle("following", result.following);
                button.textContent = result.following ? "Following" : "Follow";
                const followerCount =
                    suggestion.querySelector(".follower-count") ||
                    document.querySelector(".profile-stats .follower-count");
                if (followerCount) {
                    followerCount.textContent = result.follower_count;
                }
                const followingCount = document.getElementById(
                    "profile-following-count"
                );
                if (followingCount) {
                    followingCount.textContent = result.following_count;
                }
            } catch (error) {
                showError(error.message);
            } finally {
                button.disabled = false;
            }
        });
    });

    updatePostCount();
    updateEmptyMessage();
});
