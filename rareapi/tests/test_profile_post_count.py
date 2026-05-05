import pytest
from datetime import date
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rareapi.models import RareUser, Post, Category


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def author(db):
    return RareUser.objects.create_user(
        username="author", password="x", is_active=True,
    )


@pytest.fixture
def viewer(db):
    return RareUser.objects.create_user(
        username="viewer", password="x", is_active=True,
    )


@pytest.fixture
def category(db):
    return Category.objects.create(label="General")


def auth(api_client, user):
    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


def make_post(user, category, approved):
    return Post.objects.create(
        user=user,
        category=category,
        title="A post",
        publication_date=date.today(),
        content="Body text.",
        approved=approved,
    )


class TestProfilePostCount:
    def test_zero_posts_returns_zero(self, api_client, author, viewer, db):
        auth(api_client, viewer)
        response = api_client.get(f"/profiles/{author.id}")
        assert response.status_code == 200
        assert response.json()["post_count"] == 0

    def test_approved_posts_are_counted(self, api_client, author, viewer, category, db):
        make_post(author, category, approved=True)
        make_post(author, category, approved=True)
        auth(api_client, viewer)
        response = api_client.get(f"/profiles/{author.id}")
        assert response.status_code == 200
        assert response.json()["post_count"] == 2

    def test_unapproved_posts_are_not_counted(self, api_client, author, viewer, category, db):
        make_post(author, category, approved=False)
        make_post(author, category, approved=False)
        auth(api_client, viewer)
        response = api_client.get(f"/profiles/{author.id}")
        assert response.status_code == 200
        assert response.json()["post_count"] == 0

    def test_only_approved_posts_count_when_mixed(self, api_client, author, viewer, category, db):
        make_post(author, category, approved=True)
        make_post(author, category, approved=False)
        make_post(author, category, approved=False)
        auth(api_client, viewer)
        response = api_client.get(f"/profiles/{author.id}")
        assert response.status_code == 200
        assert response.json()["post_count"] == 1

    def test_posts_from_other_users_are_not_counted(self, api_client, author, viewer, category, db):
        make_post(viewer, category, approved=True)
        make_post(viewer, category, approved=True)
        auth(api_client, viewer)
        response = api_client.get(f"/profiles/{author.id}")
        assert response.status_code == 200
        assert response.json()["post_count"] == 0
