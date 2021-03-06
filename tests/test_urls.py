from django.test import TestCase
from django.urls import resolve, reverse

from tests import factories


class URLTestBase(TestCase):
    def setUp(self):
        factories.star_beer()


class TestIndexURL(URLTestBase):
    def test_index_route_uses_index_view(self):
        self.assertEqual(resolve("/").func.__name__, "IndexView")

    def test_index_route_reverse(self):
        self.assertEqual(reverse("index"), "/")


class TestBarURLs(URLTestBase):
    def test_bar_list_route_uses_correct_view(self):
        self.assertEqual(resolve("/bars/").func.__name__, "BarViewSet")

    def test_bar_list_route_reverse(self):
        self.assertEqual(reverse("bar-list"), "/bars/")

    def test_bar_detail_route_uses_correct_view(self):
        match = resolve("/bars/1/")
        self.assertEqual(match.func.__name__, "BarViewSet")
        self.assertEqual(match.kwargs, {"pk": "1"})

    def test_bar_detail_route_reverse(self):
        self.assertEqual(reverse("bar-detail", args=(1,)), "/bars/1/")


class TestBreweryURLs(URLTestBase):
    def test_brewery_list_route_uses_correct_view(self):
        self.assertEqual(
            resolve("/breweries/").func.__name__, "BreweryViewSet"
        )

    def test_brewery_list_route_reverse(self):
        self.assertEqual(reverse("brewery-list"), "/breweries/")

    def test_brewery_detail_route_uses_correct_view(self):
        match = resolve("/breweries/1/")
        self.assertEqual(match.func.__name__, "BreweryViewSet")
        self.assertEqual(match.kwargs, {"pk": "1"})

    def test_brewery_detail_route_reverse(self):
        self.assertEqual(reverse("brewery-detail", args=(1,)), "/breweries/1/")


class TestBeerListURL(URLTestBase):
    def test_beer_list_route_uses_beer_list_view(self):
        self.assertEqual(resolve("/beers/").func.__name__, "BeerListView")

    def test_beer_list_route_reverse(self):
        self.assertEqual(reverse("beer-list"), "/beers/")


class TestBeerDetailURL(URLTestBase):
    def test_beer_detail_route_uses_beer_detail_view(self):
        match = resolve("/beers/1/")
        self.assertEqual(match.func.__name__, "BeerDetailView")
        self.assertEqual(match.kwargs, {"pk": 1})

    def test_beer_detail_route_reverse(self):
        self.assertEqual(reverse("beer-detail", args=(1,)), "/beers/1/")


class TestStarBeerURL(URLTestBase):
    def test_star_beer_route_uses_star_beer_view(self):
        match = resolve("/beers/1/star/")
        self.assertEqual(match.func.__name__, "StarBeerView")
        self.assertEqual(match.kwargs, {"pk": 1})

    def test_star_beer_route_reverse(self):
        self.assertEqual(reverse("beer-star", args=(1,)), "/beers/1/star/")


class TestBeerRatingURL(URLTestBase):
    def test_star_beer_route_uses_star_beer_view(self):
        match = resolve("/beers/1/rating/")
        self.assertEqual(match.func.__name__, "BeerRatingView")
        self.assertEqual(match.kwargs, {"pk": 1})

    def test_star_beer_route_reverse(self):
        self.assertEqual(reverse("beer-rating", args=(1,)), "/beers/1/rating/")
