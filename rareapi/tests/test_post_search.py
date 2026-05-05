import pytest
from datetime import date
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rareapi.models import RareUser, Post, Category


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def category(db):
    return Category.objects.create(label="General")


@pytest.fixture
def diana(db):
    return RareUser.objects.create_user(username="diana", password="x", is_active=True)


@pytest.fixture
def alice(db):
    return RareUser.objects.create_user(username="alice", password="x", is_active=True)


@pytest.fixture
def searcher(db):
    return RareUser.objects.create_user(username="searcher", password="x", is_active=True)


def auth(api_client, user):
    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


def make_post(user, category, title, approved=True):
    return Post.objects.create(
        user=user,
        category=category,
        title=title,
        publication_date=date.today(),
        content="Body text.",
        approved=approved,
    )


class TestPostSearch:
    def test_title_search_returns_matching_posts(self, api_client, searcher, diana, category, db):
        make_post(diana, category, "Python Tips")
        make_post(diana, category, "Django Guide")
        auth(api_client, searcher)
        response = api_client.get("/posts/search?q=python")
        assert response.status_code == 200
        titles = [p["title"] for p in response.json()]
        assert "Python Tips" in titles
        assert "Django Guide" not in titles

    def test_author_search_returns_posts_by_that_user(self, api_client, searcher, diana, alice, category, db):
        make_post(diana, category, "Diana Post One")
        make_post(alice, category, "Alice Post One")
        auth(api_client, searcher)
        response = api_client.get("/posts/search?author=diana")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Diana Post One"

    def test_author_search_is_case_insensitive(self, api_client, searcher, diana, category, db):
        make_post(diana, category, "Some Post")
        auth(api_client, searcher)
        response = api_client.get("/posts/search?author=DIANA")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_combined_q_and_author_filters(self, api_client, searcher, diana, alice, category, db):
        make_post(diana, category, "Python Tips")
        make_post(diana, category, "Django Guide")
        make_post(alice, category, "Python Basics")
        auth(api_client, searcher)
        response = api_client.get("/posts/search?q=python&author=diana")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Python Tips"

    def test_empty_params_returns_empty_list(self, api_client, searcher, diana, category, db):
        make_post(diana, category, "Some Post")
        auth(api_client, searcher)
        response = api_client.get("/posts/search")
        assert response.status_code == 200
        assert response.json() == []

    def test_author_only_excludes_unapproved(self, api_client, searcher, diana, category, db):
        make_post(diana, category, "Approved Post", approved=True)
        make_post(diana, category, "Draft Post", approved=False)
        auth(api_client, searcher)
        response = api_client.get("/posts/search?author=diana")
        assert response.status_code == 200
        titles = [p["title"] for p in response.json()]
        assert "Approved Post" in titles
        assert "Draft Post" not in titles
