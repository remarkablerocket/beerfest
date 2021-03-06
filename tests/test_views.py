from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.test import TestCase, RequestFactory
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from beerfest import views
from beerfest.models import Bar, Brewery, StarBeer, BeerRating
from tests import factories


class BaseViewTest(TestCase):
    def setUp(self):
        self.login_url = "/accounts/login/"
        self.factory = RequestFactory()
        self.user = factories.create_user()

    def setup_view(self, request, *args, **kwargs):
        view = self.view_class()
        view.request = request
        view.args = args
        view.kwargs = kwargs
        return view


class TestIndexView(BaseViewTest):
    def test_redirects_to_beer_list(self):
        request = self.factory.get("")
        response = views.IndexView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("beer-list"))


class TestUserProfileView(BaseViewTest):
    view_class = views.UserProfileView

    def create_test_data(self):
        bar = factories.create_bar()
        brewery = factories.create_brewery()
        self.beer1 = factories.create_beer(
            bar=bar, brewery=brewery, name="Mild")
        self.beer2 = factories.create_beer(
            bar=bar, brewery=brewery, name="IPA")
        self.beer3 = factories.create_beer(
            bar=bar, brewery=brewery, name="Bitter")
        self.beer4 = factories.create_beer(
            bar=bar, brewery=brewery, name="Stout")

        factories.star_beer(user=self.user, beer=self.beer1)
        factories.star_beer(user=self.user, beer=self.beer2)
        factories.rate_beer(user=self.user,  beer=self.beer2, rating=2)
        factories.rate_beer(user=self.user,  beer=self.beer3, rating=4)

    def test_get_context_data_adds_expected_beer_objects(self):
        self.create_test_data()
        starred_beers = (self.beer1, self.beer2)
        request = self.factory.get("")
        request.user = self.user
        view = self.setup_view(request)
        view.object = None

        context_data = view.get_context_data()
        rated_beers = context_data["rated_beers"]

        self.assertIn("starred_beers", context_data)
        self.assertCountEqual(context_data["starred_beers"], starred_beers)

        rated_list = list(rated_beers.values_list("name", "rating"))
        self.assertCountEqual(rated_list, [("IPA", 2), ("Bitter", 4)])

    def test_response_context_data_contains_expected_beers_after(self):
        self.create_test_data()
        starred_beers = (self.beer1, self.beer2)
        request = self.factory.get("")
        request.user = self.user
        view = self.setup_view(request)

        response = view.get(request)

        self.assertIn("starred_beers", response.context_data)
        self.assertCountEqual(
            response.context_data["starred_beers"], starred_beers)

        rated_beers = response.context_data["rated_beers"]
        rated_list = list(rated_beers.values_list("name", "rating"))
        self.assertCountEqual(rated_list, [("IPA", 2), ("Bitter", 4)])

    def test_user_object_variable_is_logged_in_user(self):
        request = self.factory.get("")
        request.user = self.user
        view = self.setup_view(request)

        response = view.get(request)

        self.assertIn("user", response.context_data)
        self.assertEqual(response.context_data["user"], self.user)

    def test_get_object_returns_logged_in_user(self):
        request = self.factory.get("")
        request.user = self.user
        view = self.setup_view(request)

        context_object = view.get_object()

        self.assertEqual(context_object, self.user)

    def test_get_template_names(self):
        request = self.factory.get("")
        request.user = self.user
        view = self.setup_view(request)

        template_names = view.get_template_names()

        self.assertEqual(template_names[0], "beerfest/user_profile.html")

    def test_unauthenticated_user_gets_redirected_to_login(self):
        request = self.factory.get("")
        request.user = AnonymousUser()
        view = self.setup_view(request)

        # Use view.dispatch as this is where logged in status is checked
        response = view.dispatch(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.login_url + "?next=/")

    def test_renders_using_test_client(self):
        # Just a sanity check; almost an integration test
        self.create_test_data()
        starred_beers = (self.beer1, self.beer2)
        self.client.force_login(self.user)

        response = self.client.get("/accounts/profile/")
        user = response.context["user"]
        beer_list = response.context["starred_beers"]
        rated_beers = response.context_data["rated_beers"]

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "beerfest/user_profile.html")
        self.assertEqual(user, self.user)
        self.assertCountEqual(beer_list, starred_beers)

        rated_list = list(rated_beers.values_list("name", "rating"))
        self.assertCountEqual(rated_list, [("IPA", 2), ("Bitter", 4)])


class TestBarViewSet(APITestCase):
    def setUp(self):
        self.user = factories.create_user()
        self.admin = factories.create_user("Test")
        perms = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Bar)
        )
        self.admin.user_permissions.set(list(perms))
        self.bar1 = factories.create_bar()
        self.bar2 = factories.create_bar("Test Bar 2")

    def test_GET_bar(self):
        response = self.client.get("/bars/1/")
        self.assertEqual(response.data, {"id": 1, "name": "Test Bar"})

    def test_GET_bar_list(self):
        response = self.client.get("/bars/")
        self.assertEqual(
            response.data,
            [{"id": 1, "name": "Test Bar"}, {"id": 2, "name": "Test Bar 2"}],
        )

    def test_PATCH_bar(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            "/bars/1/", data={"name": "Testing Bar"}
        )
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.bar1.refresh_from_db()
        self.assertEqual(self.bar1.name, "Testing Bar")

    def test_PATCH_bar_unauthorised(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            "/bars/1/", data={"name": "Testing Bar"}
        )
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.bar1.refresh_from_db()
        self.assertEqual(self.bar1.name, "Test Bar")

    def test_PATCH_bar_anonymous(self):
        response = self.client.patch(
            "/bars/1/", data={"name": "Testing Bar"}
        )
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.bar1.refresh_from_db()
        self.assertEqual(self.bar1.name, "Test Bar")

    def test_POST_bar(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/bars/", data={"name": "The Test Bar"}
        )
        new_bar = Bar.objects.get(id=3)

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(new_bar.name, "The Test Bar")

    def test_POST_bar_unauthorised(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/bars/", data={"name": "The Test Bar"}
        )
        with self.assertRaises(Bar.DoesNotExist):
            Bar.objects.get(id=3)

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_POST_bar_anonymous(self):
        response = self.client.post(
            "/bars/", data={"name": "The Test Bar"}
        )
        with self.assertRaises(Bar.DoesNotExist):
            Bar.objects.get(id=3)

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_DELETE_bar(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(
            "/bars/1/"
        )
        with self.assertRaises(Bar.DoesNotExist):
            Bar.objects.get(id=1)

        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

    def test_DELETE_bar_unauthorised(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            "/bars/1/"
        )
        bar = Bar.objects.get(id=1)
        self.assertEqual(bar.name, "Test Bar")

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_DELETE_bar_anonymous(self):
        response = self.client.delete(
            "/bars/1/"
        )
        bar = Bar.objects.get(id=1)
        self.assertEqual(bar.name, "Test Bar")

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class TestBreweryViewSet(APITestCase):
    def setUp(self):
        self.user = factories.create_user()
        self.admin = factories.create_user("Test")
        perms = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Brewery)
        )
        self.admin.user_permissions.set(list(perms))
        self.brewery1 = factories.create_brewery()
        self.brewery2 = factories.create_brewery("Test Brew Ltd")

    def test_GET_brewery(self):
        response = self.client.get("/breweries/1/")

        self.assertEqual(
            response.data,
            {"id": 1, "name": "Test Brew Co", "location": "Testville"}
        )

    def test_GET_brewery_list(self):
        response = self.client.get("/breweries/")

        self.assertEqual(
            response.data, [
                {"id": 1, "name": "Test Brew Co", "location": "Testville"},
                {"id": 2, "name": "Test Brew Ltd", "location": "Testville"}
            ],
        )

    def test_PATCH_brewery(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            "/breweries/1/", data={"name": "Test Brew Corp"}
        )
        self.brewery1.refresh_from_db()

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(self.brewery1.name, "Test Brew Corp")
        self.assertEqual(self.brewery1.location, "Testville")

    def test_PATCH_brewery_unauthorised(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            "/breweries/1/", data={"name": "Test Brew Corp"}
        )
        self.brewery1.refresh_from_db()

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(self.brewery1.name, "Test Brew Co")

    def test_PATCH_brewery_anonymous(self):
        response = self.client.patch(
            "/breweries/1/", data={"name": "Test Brew Corp"}
        )
        self.brewery1.refresh_from_db()

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual(self.brewery1.name, "Test Brew Co")

    def test_POST_brewery(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            "name": "The Test Brewery",
            "location": "Test Town",
        }
        response = self.client.post("/breweries/", data=data)
        new_brewery = Brewery.objects.get(id=3)

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual(new_brewery.name, "The Test Brewery")

    def test_POST_brewery_unauthorised(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "name": "The Test Brewery",
            "location": "Test Town",
        }
        response = self.client.post("/breweries/", data=data)

        with self.assertRaises(Brewery.DoesNotExist):
            Brewery.objects.get(id=3)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_POST_brewery_anonymous(self):
        data = {
            "name": "The Test Brewery",
            "location": "Test Town",
        }
        response = self.client.post("/breweries/", data=data)

        with self.assertRaises(Brewery.DoesNotExist):
            Brewery.objects.get(id=3)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_DELETE_brewery(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(
            "/breweries/1/"
        )

        with self.assertRaises(Brewery.DoesNotExist):
            Brewery.objects.get(id=1)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)

    def test_DELETE_brewery_unauthorised(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            "/breweries/1/"
        )
        brewery = Brewery.objects.get(id=1)

        self.assertEqual(brewery.name, "Test Brew Co")
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_DELETE_brewery_anonymous(self):
        response = self.client.delete(
            "/breweries/1/"
        )
        brewery = Brewery.objects.get(id=1)

        self.assertEqual(brewery.name, "Test Brew Co")
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


class TestBeerListView(BaseViewTest):
    view_class = views.BeerListView

    def create_beers(self):
        bar = factories.create_bar()
        brewery = factories.create_brewery()
        self.beer1 = factories.create_beer(
            bar=bar, brewery=brewery, name="IPA")
        self.beer2 = factories.create_beer(
            bar=bar, brewery=brewery, name="Mild")
        self.beer3 = factories.create_beer(
            bar=bar, brewery=brewery, name="Stout")

        return (self.beer1, self.beer2, self.beer3)

    def test_GETs_beer_list_context_variable(self):
        beers = self.create_beers()
        request = self.factory.get("")
        view = self.setup_view(request)

        response = view.get(request)

        self.assertIn("beer_list", response.context_data)
        self.assertCountEqual(response.context_data["beer_list"], beers)

    def test_get_queryset_returns_beer_list(self):
        beers = self.create_beers()
        request = self.factory.get("")

        view = self.setup_view(request)
        qs = view.get_queryset()

        self.assertCountEqual(qs, beers)

    def test_get_template_names(self):
        request = self.factory.get("")
        view = self.setup_view(request)
        # The following line is needed for get_template_names() to work as it
        # should (view.get assigns view.object_list before get_templates names
        # is called by view.render_to_response)
        view.object_list = view.get_queryset()

        template_names = view.get_template_names()

        self.assertEqual(template_names[0], "beerfest/beer_list.html")

    def test_renders_using_test_client(self):
        # Just a sanity check; almost an integration test
        beers = self.create_beers()

        response = self.client.get("/beers/")
        beer_list = response.context["beer_list"]

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "beerfest/beer_list.html")
        self.assertCountEqual(beer_list, beers)

    def test_get_queryset_annotates_starred_status_if_user_logged_in(self):
        self.create_beers()
        factories.star_beer(user=self.user, beer=self.beer1)

        request = self.factory.get("")
        request.user = self.user
        view = self.setup_view(request)
        qs = view.get_queryset()

        self.assertEqual(qs[0].starred, True)
        self.assertEqual(qs[1].starred, False)
        self.assertEqual(qs[2].starred, False)

    def test_GETs_annotated_beer_list_context_variable(self):
        self.create_beers()
        factories.star_beer(
            user=self.user, beer=self.beer1)
        user2 = factories.create_user("Ms Test")
        factories.star_beer(user=user2, beer=self.beer2)

        request = self.factory.get("")
        request.user = self.user
        view = self.setup_view(request)
        response = view.get(request)
        beer_list = response.context_data["beer_list"]

        self.assertEqual(beer_list[0].starred, True)
        self.assertEqual(beer_list[1].starred, False)
        self.assertEqual(beer_list[2].starred, False)

    def test_beer_annotations_do_not_cause_duplicates(self):
        # Some types of DB queries result in duplicates - eg repeating a beer
        # for each value of starred. Test that we haven't formed such a query.
        self.create_beers()
        factories.star_beer(user=self.user, beer=self.beer1)
        factories.star_beer(user=self.user, beer=self.beer2)

        user2 = factories.create_user("A Test")
        factories.star_beer(user=user2, beer=self.beer1)
        factories.star_beer(user=user2, beer=self.beer3)

        request = self.factory.get("")
        request.user = self.user
        view = self.setup_view(request)
        qs = view.get_queryset()

        self.assertEqual(len(qs), 3)

        request.user = user2
        view = self.setup_view(request)
        qs = view.get_queryset()

        self.assertEqual(len(qs), 3)


class TestBeerDetailView(BaseViewTest):
    view_class = views.BeerDetailView

    def create_beers(self):
        bar = factories.create_bar()
        brewery = factories.create_brewery()
        beer1 = factories.create_beer(bar=bar, brewery=brewery, name="IPA")
        beer2 = factories.create_beer(bar=bar, brewery=brewery, name="Mild")

        return (beer1, beer2)

    def test_GETs_correct_beer_context_variable(self):
        beer1, beer2 = self.create_beers()
        request = self.factory.get("")
        view = self.setup_view(request, pk=2)

        response = view.get(request)

        self.assertIn("beer", response.context_data)
        self.assertEqual(response.context_data["beer"], beer2)

    def test_get_object_returns_beer_for_given_pk(self):
        beer1, beer2 = self.create_beers()
        request = self.factory.get("")

        view = self.setup_view(request, pk=1)
        context_object1 = view.get_object()

        view = self.setup_view(request, pk=2)
        context_object2 = view.get_object()

        self.assertEqual(context_object1, beer1)
        self.assertEqual(context_object2, beer2)

    def test_get_context_data_returns_context_with_starred_status(self):
        beer1, beer2 = self.create_beers()
        factories.star_beer(user=self.user, beer=beer2)
        request = self.factory.get("")
        request.user = self.user

        view = self.setup_view(request, pk=1)
        view.object = beer1
        context_data = view.get_context_data()

        self.assertIn("starred", context_data)
        self.assertFalse(context_data["starred"])

        view = self.setup_view(request, pk=2)
        view.object = beer2
        context_data = view.get_context_data()

        self.assertIn("starred", context_data)
        self.assertTrue(context_data["starred"])

    def test_get_context_data_returns_context_with_num_stars(self):
        beer1, beer2 = self.create_beers()
        user2 = factories.create_user("Test User 2")
        factories.star_beer(user=self.user, beer=beer2)
        factories.star_beer(user=user2, beer=beer2)
        request = self.factory.get("")
        request.user = self.user

        view = self.setup_view(request, pk=1)
        view.object = beer1
        context_data = view.get_context_data()

        self.assertIn("num_stars", context_data)
        self.assertEqual(context_data["num_stars"], 0)

        view = self.setup_view(request, pk=2)
        view.object = beer2
        context_data = view.get_context_data()

        self.assertIn("num_stars", context_data)
        self.assertEqual(context_data["num_stars"], 2)

    def test_get_context_data_returns_context_with_user_rating(self):
        beer1, beer2 = self.create_beers()
        factories.rate_beer(user=self.user, beer=beer2, rating=5)
        request = self.factory.get("")
        request.user = self.user

        view = self.setup_view(request, pk=1)
        view.object = beer1
        context_data = view.get_context_data()

        self.assertIn("rating", context_data)
        self.assertIsNone(context_data["rating"])

        view = self.setup_view(request, pk=2)
        view.object = beer2
        context_data = view.get_context_data()

        self.assertIn("rating", context_data)
        self.assertEqual(context_data["rating"], 5)

    def test_get_context_data_returns_context_with_avg_rating(self):
        beer1, beer2 = self.create_beers()
        user2 = factories.create_user("Test User 2")
        factories.rate_beer(user=self.user, beer=beer2, rating=4)
        factories.rate_beer(user=user2, beer=beer2, rating=1)
        request = self.factory.get("")
        request.user = self.user

        view = self.setup_view(request, pk=1)
        view.object = beer1
        context_data = view.get_context_data()

        self.assertIn("avg_rating", context_data)
        self.assertIsNone(context_data["avg_rating"])

        view = self.setup_view(request, pk=2)
        view.object = beer2
        context_data = view.get_context_data()

        self.assertIn("avg_rating", context_data)
        self.assertEqual(context_data["avg_rating"], 2.5)

    def test_get_object_and_get_with_invalid_id_raises_404(self):
        request = self.factory.get("")
        view = self.setup_view(request, pk=1)

        with self.assertRaises(Http404):
            view.get_object()

        with self.assertRaises(Http404):
            view.get(request)

    def test_get_template_names(self):
        request = self.factory.get("")
        view = self.setup_view(request)
        view.object = None

        template_names = view.get_template_names()

        self.assertEqual(template_names[0], "beerfest/beer_detail.html")

    def test_renders_using_test_client(self):
        # Just a sanity check; almost an integration test
        beer1, beer2 = self.create_beers()

        response = self.client.get("/beers/1/")
        context_beer1 = response.context["beer"]
        context_beer2 = self.client.get("/beers/2/").context["beer"]

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "beerfest/beer_detail.html")
        self.assertEqual(context_beer1, beer1)
        self.assertEqual(context_beer2, beer2)


class TestStarBeerView(BaseViewTest):
    view_class = views.StarBeerView

    def setUp(self):
        super().setUp()
        bar = factories.create_bar()
        brewery = factories.create_brewery()

        self.beer1 = factories.create_beer(
            bar=bar, brewery=brewery, name="IPA")
        self.beer2 = factories.create_beer(
            bar=bar, brewery=brewery, name="Mild")

        factories.star_beer(user=self.user, beer=self.beer1)

    def test_star_beer(self):
        request = self.factory.put("")
        request.user = self.user
        view = self.setup_view(request, pk=2)

        view.put(request)
        qs = StarBeer.objects.filter(user=self.user, beer=self.beer2)

        self.assertTrue(qs.exists())

    def test_star_beer_anonymous_forbidden(self):
        request = self.factory.put("")
        request.user = AnonymousUser()
        view = self.setup_view(request, pk=2)

        with self.assertRaises(PermissionDenied):
            # Use view.dispatch as this is where logged in status is checked
            view.dispatch(request)

        qs = StarBeer.objects.filter(user=self.user, beer=self.beer2)

        self.assertFalse(qs.exists())

    def test_star_beer_returns_204(self):
        request = self.factory.put("")
        request.user = self.user
        view = self.setup_view(request, pk=2)

        response = view.put(request)

        self.assertEqual(response.status_code, 204)

    def test_star_beer_already_starred_has_no_effect(self):
        request = self.factory.put("")
        request.user = self.user
        view = self.setup_view(request, pk=1)

        response = view.put(request)
        qs = StarBeer.objects.filter(user=self.user, beer=self.beer1)

        self.assertTrue(qs.exists())
        self.assertEqual(response.status_code, 204)

    def test_star_beer_using_test_client(self):
        # Just a sanity check; almost an integration test
        self.client.force_login(self.user)

        response = self.client.put("/beers/2/star/")
        qs = StarBeer.objects.filter(user=self.user, beer=self.beer2)

        self.assertTrue(qs.exists())
        self.assertEqual(response.status_code, 204)

    def test_unstar_beer(self):
        request = self.factory.delete("")
        request.user = self.user
        view = self.setup_view(request, pk=1)

        view.delete(request)
        qs = StarBeer.objects.filter(user=self.user, beer=self.beer1)

        self.assertFalse(qs.exists())

    def test_unstar_beer_anonymous_forbidden(self):
        request = self.factory.delete("")
        request.user = AnonymousUser()
        view = self.setup_view(request, pk=1)

        with self.assertRaises(PermissionDenied):
            # Use view.dispatch as this is where logged in status is checked
            view.dispatch(request)

        qs = StarBeer.objects.filter(user=self.user, beer=self.beer1)

        self.assertTrue(qs.exists())

    def test_unstar_beer_returns_204(self):
        request = self.factory.delete("")
        request.user = self.user
        view = self.setup_view(request, pk=1)

        response = view.delete(request)

        self.assertEqual(response.status_code, 204)

    def test_unstar_beer_already_unstarred_has_no_effect(self):
        request = self.factory.delete("")
        request.user = self.user
        view = self.setup_view(request, pk=2)

        response = view.delete(request)
        qs = StarBeer.objects.filter(user=self.user, beer=self.beer2)

        self.assertFalse(qs.exists())
        self.assertEqual(response.status_code, 204)

    def test_unstar_beer_using_test_client(self):
        # Just a sanity check; almost an integration test
        self.client.force_login(self.user)

        response = self.client.delete("/beers/1/star/")
        qs = StarBeer.objects.filter(user=self.user, beer=self.beer1)

        self.assertFalse(qs.exists())
        self.assertEqual(response.status_code, 204)


class TestBeerRatingView(BaseViewTest):
    view_class = views.BeerRatingView

    def setUp(self):
        super().setUp()
        bar = factories.create_bar()
        brewery = factories.create_brewery()

        self.beer1 = factories.create_beer(
            bar=bar, brewery=brewery, name="IPA")
        self.beer2 = factories.create_beer(
            bar=bar, brewery=brewery, name="Mild")

        factories.rate_beer(user=self.user, beer=self.beer1, rating=3)

    def test_rate_beer(self):
        request = self.factory.put("", data={"rating": 1},
                                   content_type="application/json")
        request.user = self.user
        view = self.setup_view(request, pk=2)

        view.put(request)
        beer_rating = BeerRating.objects.get(user=self.user, beer=self.beer2)

        self.assertEqual(beer_rating.rating, 1)

    def test_rate_beer_anonymous_forbidden(self):
        request = self.factory.put("", data={"rating": 1},
                                   content_type="application/json")
        request.user = AnonymousUser()
        view = self.setup_view(request, pk=2)

        with self.assertRaises(PermissionDenied):
            # Use view.dispatch as this is where logged in status is checked
            view.dispatch(request)

        qs = BeerRating.objects.filter(user=self.user, beer=self.beer2)

        self.assertFalse(qs.exists())

    def test_rate_beer_returns_204(self):
        request = self.factory.put("", data={"rating": 1},
                                   content_type="application/json")
        request.user = self.user
        view = self.setup_view(request, pk=2)

        response = view.put(request)

        self.assertEqual(response.status_code, 204)

    def test_invalid_rating_returns_400(self):
        request = self.factory.put("", data={"rating": 0},
                                   content_type="application/json")
        request.user = self.user
        view = self.setup_view(request, pk=2)

        response = view.put(request)
        self.assertEqual(response.status_code, 400)

        qs = BeerRating.objects.filter(user=self.user, beer=self.beer2)
        self.assertFalse(qs.exists())

    def test_rate_beer_already_rated_updates_rating(self):
        request = self.factory.put("", data={"rating": 1},
                                   content_type="application/json")
        request.user = self.user
        view = self.setup_view(request, pk=1)

        response = view.put(request)
        beer_rating = BeerRating.objects.get(user=self.user, beer=self.beer1)

        self.assertEqual(beer_rating.rating, 1)
        self.assertEqual(response.status_code, 204)

    def test_rate_beer_using_test_client(self):
        # Just a sanity check; almost an integration test
        self.client.force_login(self.user)

        response = self.client.put("/beers/2/rating/", data={"rating": 1},
                                   content_type="application/json")
        self.assertEqual(response.status_code, 204)

        beer_rating = BeerRating.objects.get(user=self.user, beer=self.beer2)
        self.assertEqual(beer_rating.rating, 1)

    def test_unrate_beer(self):
        request = self.factory.delete("")
        request.user = self.user
        view = self.setup_view(request, pk=1)

        view.delete(request)
        qs = BeerRating.objects.filter(user=self.user, beer=self.beer1)

        self.assertFalse(qs.exists())

    def test_unrate_beer_anonymous_forbidden(self):
        request = self.factory.delete("")
        request.user = AnonymousUser()
        view = self.setup_view(request, pk=1)

        with self.assertRaises(PermissionDenied):
            # Use view.dispatch as this is where logged in status is checked
            view.dispatch(request)

        qs = BeerRating.objects.filter(user=self.user, beer=self.beer1)

        self.assertTrue(qs.exists())

    def test_unrate_beer_returns_204(self):
        request = self.factory.delete("")
        request.user = self.user
        view = self.setup_view(request, pk=1)

        response = view.delete(request)

        self.assertEqual(response.status_code, 204)

    def test_unrate_beer_not_already_rated_has_no_effect(self):
        request = self.factory.delete("")
        request.user = self.user
        view = self.setup_view(request, pk=2)

        response = view.delete(request)
        qs = BeerRating.objects.filter(user=self.user, beer=self.beer2)

        self.assertFalse(qs.exists())
        self.assertEqual(response.status_code, 204)

    def test_unrate_beer_using_test_client(self):
        # Just a sanity check; almost an integration test
        self.client.force_login(self.user)

        response = self.client.delete("/beers/1/rating/")
        qs = BeerRating.objects.filter(user=self.user, beer=self.beer1)

        self.assertFalse(qs.exists())
        self.assertEqual(response.status_code, 204)
