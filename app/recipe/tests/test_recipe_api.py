"""
Test the recipe API.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPE_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """ Create and return recipe detail URL. """
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """ Create and return a recipe. """
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'https://www.sample.com/recipe',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """ Create and return a sample user. """
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """ Test unauthenticated recipe API access. """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ Test that authentication is required. """
        res = self.client.get(RECIPE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """ Test authenticated recipe API access. """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@exampl.com',
                                password='testpass123')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """ Test retrieving a list of recipes. """
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """ Test retrieving recipes for user. """
        other_user = create_user(email='other@example.com',
                                 password='test123')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """ Test get recipe detail. """
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Testing creating a recipe."""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': Decimal('5.00'),
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))

    def test_partial_update(self):
        """Test partial update of a recipe"""
        original_link = 'https://www.original.com/recipe.pdf'
        recipe = create_recipe(user=self.user,
                               title="Sample Recipe Title",
                               link=original_link)
        payload = {
            'title': 'New title',
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update for recipe"""
        recipe = create_recipe(user=self.user,
                               title="Sample Recipe Title",
                               link='https://www.original.com/recipe.pdf',
                               description='Sample description',)

        payload = {
            'title': 'New title',
            'link': 'https://www.newlink.com/recipe.pdf',
            'description': 'New description',
            'time_minutes': 25,
            'price': Decimal('10.00'),
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))
        self.assertEqual(recipe.user, self.user)

    def test_update_user_return_error(self):
        """Test that user cannot update other user's recipe"""
        new_user = create_user(email='test@example.com', password='test123')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}

        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """test delete a recipe"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_user_recipe(self):
        """Test that user cannot delete other user's recipe"""
        new_user = create_user(email='user2@example.com',
                               password='test123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())
