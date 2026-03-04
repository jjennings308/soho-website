"""
Django management command to load Soho Pittsburgh drinks menu data.
Place this file in: <your_app>/management/commands/load_soho_drinks.py

Usage: python manage.py load_soho_drinks

Note: This command only adds/updates drinks data. It does NOT clear existing
food data. Run load_soho_menu first (or alongside) for the full menu.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from decimal import Decimal
from apps.menu.models import MenuType, MenuCategory, MenuSubCategory, MenuItem, MenuItemVariation


class Command(BaseCommand):
    help = 'Loads Soho Pittsburgh drinks menu data into the database'

    def handle(self, *args, **kwargs):
        self.stdout.write('Loading Soho Pittsburgh drinks menu...')

        # Get or create the Drinks menu type
        self.drinks = self.create_type(
            'Drinks',
            'Cocktails, beer, wine, and non-alcoholic beverages',
            order=3
        )

        self.load_signature_cocktails()
        self.load_featured_drinks()
        self.load_mocktails()
        self.load_beer()
        self.load_wine()
        self.load_non_alcoholic_beverages()

        self.stdout.write(self.style.SUCCESS('Successfully loaded drinks menu!'))

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def create_type(self, name, description, order):
        menu_type, created = MenuType.objects.get_or_create(
            slug=slugify(name),
            defaults={
                'name': name,
                'description': description,
                'order': order,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f'Created menu type: {name}')
        else:
            self.stdout.write(f'Using existing menu type: {name}')
        return menu_type

    def create_category(self, name, description, order):
        category, created = MenuCategory.objects.get_or_create(
            slug=slugify(name),
            defaults={
                'menu_type': self.drinks,
                'name': name,
                'description': description,
                'order': order,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f'  Created category: {name}')
        return category

    def create_subcategory(self, category, name, description, order):
        subcategory, created = MenuSubCategory.objects.get_or_create(
            slug=slugify(f'{category.slug}-{name}'),
            defaults={
                'category': category,
                'name': name,
                'description': description,
                'order': order,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f'    Created subcategory: {name}')
        return subcategory

    def create_item(self, category, name, price, description='', subcategory=None, **kwargs):
        slug = slugify(name)
        # Ensure slug uniqueness within drinks (append category slug if needed)
        if not MenuItem.objects.filter(slug=slug).exists():
            final_slug = slug
        else:
            final_slug = f"{slug}-{slugify(category.name)}"

        has_price = price and price > 0
        item, created = MenuItem.objects.get_or_create(
            slug=final_slug,
            defaults={
                'category': category,
                'subcategory': subcategory,
                'name': name,
                'price': Decimal(str(price)) if has_price else Decimal('10.00'),
                'price_display': 'price' if has_price else 'hidden',
                'description': description,
                'short_description': description[:300] if len(description) > 300 else description,
                'is_available': True,
                **kwargs
            }
        )
        if created:
            self.stdout.write(f'      Added: {name}')
        return item

    # -------------------------------------------------------------------------
    # Categories
    # -------------------------------------------------------------------------

    def load_signature_cocktails(self):
        cat = self.create_category(
            'Signature Cocktails',
            'House-crafted cocktails made with premium spirits',
            order=1
        )

        self.create_item(cat, 'Blue Hawaiian', 0,
            'Bacardi, Svedka, Blue Curacao, pineapple juice, lime juice, and simple syrup')
        self.create_item(cat, 'Blueberry Lemon Drop Martini', 0,
            'Citron vodka, lemon juice, simple syrup, and blueberry puree')
        self.create_item(cat, 'Blue Raspberry Jolly Rancher', 0,
            'Blue Curacao, raspberry vodka, sours, and Sprite')
        self.create_item(cat, 'Espresso Martini', 0,
            'Absolut, Kahlua, simple syrup, and Stok espresso coffee')
        self.create_item(cat, 'Go Bananas', 0,
            'Bacardi, banana liquor, pineapple juice, and cherry juice')
        self.create_item(cat, 'Mango Cool Breeze', 0,
            'Svedka Mango Pineapple Vodka, Triple Sec, sours, and cranberry juice')
        self.create_item(cat, 'Million Dollar Margarita', 0,
            'Patron, Grand Marnier, simple syrup, and lime juice',
            is_featured=True)
        self.create_item(cat, 'Paloma', 0,
            'Espolon, grapefruit juice, club soda, and lime juice')
        self.create_item(cat, 'Peach Sunrise', 0,
            'Svedka Peach Vodka, peach schnapps, Triple Sec, orange juice, and grenadine')
        self.create_item(cat, 'Skinny Margarita', 0,
            'Jose Cuervo Silver, agave nectar, lime juice, and lemon juice')
        self.create_item(cat, 'Strawberry Lemonade', 0,
            'Svedka Strawberry Lemonade Vodka, Triple Sec, lemon juice, and strawberry puree')
        self.create_item(cat, 'Triple Black Manhattan', 0,
            'Crown Royal Black, blackberry brandy, sweet vermouth, and a dash of walnut bitters')

    def load_featured_drinks(self):
        cat = self.create_category(
            'Featured Drinks',
            'Seasonal and specialty cocktails',
            order=2
        )

        self.create_item(cat, 'Christmas Cocoa Martini', 0,
            'Bacardi, Kahlua, Creme de Cacao, chocolate bitters, and espresso',
            is_featured=True, is_seasonal=True)
        self.create_item(cat, 'Pomegranate French 75', 0,
            'Gin, Cointreau, PAMA, lime juice, and Prosecco',
            is_featured=True, is_seasonal=True)
        self.create_item(cat, 'Peppermint Mudslide', 0,
            'Svedka, peppermint schnapps, Baileys, Kahlua, cream, and chocolate syrup',
            is_seasonal=True)
        self.create_item(cat, 'Cranberry Moscow Mule', 0,
            'Svedka, lime juice, ginger beer, and cranberry juice',
            is_seasonal=True)
        self.create_item(cat, 'Brown Sugar Bourbon Smash', 0,
            'Makers Mark, ginger beer, brown sugar simple syrup, and a cinnamon stick',
            is_seasonal=True)

    def load_mocktails(self):
        cat = self.create_category(
            'Mocktails',
            'Non-alcoholic craft cocktails — all the flavor, none of the alcohol',
            order=3
        )

        self.create_item(cat, 'SoHo Sunrise', 0,
            'Orange juice, lime juice, grenadine, and Sprite')
        self.create_item(cat, 'Cranberry Fizz', 0,
            'Lemon juice, simple syrup, cranberry juice, and ginger beer')
        self.create_item(cat, 'Orange Dreamsicle', 0,
            'Orange juice, strawberry puree, Sprite, and cream')
        self.create_item(cat, 'NA Pineapple Margarita', 0,
            'Ritual Tequila Alternative, pineapple juice, lime juice, and agave nectar')
        self.create_item(cat, 'Citrus Smash', 0,
            'Ritual Tequila Alternative, lemon juice, lime juice, simple syrup, and club soda')
        self.create_item(cat, 'NA Apple Mule', 0,
            'Ritual Rum Alternative, apple juice, lime juice, ginger beer, and cinnamon')
        self.create_item(cat, 'NA Whiskey Palmer', 0,
            'Ritual Whiskey Alternative, lemonade, and iced tea')
        self.create_item(cat, 'Tropical Dream', 0,
            'Ritual Rum Alternative, orange juice, and pineapple juice topped with a splash of cream and nutmeg')
        self.create_item(cat, 'Red Winter Punch', 0,
            'Ritual Rum Alternative, cranberry juice, grenadine, lime juice, and Sprite',
            is_seasonal=True)

    def load_beer(self):
        cat = self.create_category(
            'Beer',
            'Draft, bottled, and canned beer selections',
            order=4
        )

        # --- On Tap ---
        sub_tap = self.create_subcategory(
            cat,
            'On Tap',
            'Draft beers served fresh from the tap',
            order=1
        )
        tap_beers = [
            'Allagash White',
            "Bell's Two Hearted",
            'Blockhouse Chocolate',
            'Brew Dog Hazy Jane',
            'Blue Moon',
            'Brew Gentlemen',
            'Bud Light',
            'Coors Light',
            'Dogfish Grateful Dead IPA',
            'Fatheads Head Hunter',
            'Guinness Stout',
            'I.C. Light',
            'Miller Lite',
            'Modelo Especial',
            'Penn Pilsner',
            'Sam Adams Seasonal',
            'Stella Artois',
            'Yuengling',
        ]
        for i, beer in enumerate(tap_beers):
            self.create_item(cat, beer, 0, subcategory=sub_tap, order=i)

        # --- IPA & Craft ---
        sub_ipa = self.create_subcategory(
            cat,
            'IPA & Craft',
            'India pale ales and craft selections',
            order=2
        )
        ipas = [
            'Dewey Swishy Pants',
            'Dogfish Head 60 Minute',
            'Lagunitas',
            'Sam Adams Just the Haze NA',
            'Sierra Nevada Hazy Peach',
            'Southern Tier 2XIPA',
        ]
        for i, beer in enumerate(ipas):
            self.create_item(cat, beer, 0, subcategory=sub_ipa, order=i)

        # --- Bottles & Cans ---
        sub_bottles = self.create_subcategory(
            cat,
            'Bottles & Cans',
            'Domestic, import, light beer, and more',
            order=3
        )
        bottles = [
            'Rolling Rock',
            'Budweiser',
            'Corona Extra',
            'Dos Equis',
            'Heineken',
            'Labatt Blue',
            'Iron City',
            'Coors Light',
            'Corona Light',
            'Heineken Light',
            'Heineken 00',
            'I.C. Light',
            'IC Light Mango',
            'Labatt Blue Light',
            'Michelob Ultra',
            'Miller Lite',
            'Yuengling Light',
            'Angry Orchard',
            'Great Lakes Christmas Ale',
            'Great Lakes Cookie Exchange',
            'High Noon',
            'Smirnoff Orange Cream Pop',
            'Southern Tier Old Man Winter',
            'Southern Tier 2XMAS',
            'White Claw',
        ]
        for i, beer in enumerate(bottles):
            self.create_item(cat, beer, 0, subcategory=sub_bottles, order=i)

    def load_wine(self):
        cat = self.create_category(
            'Wine',
            'White, red, and sparkling wines by the glass or bottle',
            order=5
        )

        # --- White ---
        sub_white = self.create_subcategory(cat, 'White', 'White wine selections', order=1)
        white_wines = [
            'Woodbridge Chardonnay',
            'Mondavi Chardonnay',
            'Chateau Ste. Michelle Riesling',
            'Elmo Pio Moscato',
            'Ruffino Pinot Grigio',
            'Nobilo Sauvignon Blanc',
        ]
        for i, name in enumerate(white_wines):
            self.create_item(cat, name, 0, subcategory=sub_white, order=i)

        # --- Red ---
        sub_red = self.create_subcategory(cat, 'Red', 'Red wine selections', order=2)
        red_wines = [
            'Woodbridge Cabernet',
            'Clos du Bois Cabernet',
            'Woodbridge Merlot',
            'Alamas Malbec',
            'Mark West Pinot Noir',
        ]
        for i, name in enumerate(red_wines):
            self.create_item(cat, name, 0, subcategory=sub_red, order=i)

        # --- Sparkling ---
        sub_sparkling = self.create_subcategory(cat, 'Sparkling', 'Sparkling wine and rosé', order=3)
        sparkling_wines = [
            'Ruffino Prosecco',
            'Ruffino Rosé',
        ]
        for i, name in enumerate(sparkling_wines):
            self.create_item(cat, name, 0, subcategory=sub_sparkling, order=i)

    def load_non_alcoholic_beverages(self):
        cat = self.create_category(
            'Non-Alcoholic Beverages',
            'Soft drinks and other non-alcoholic options',
            order=6
        )

        self.create_item(
            cat,
            'Unlimited Refill Drinks',
            4,
            'Coca-Cola, Diet Coke, Coke Zero, Cherry Coke, Sprite, Dr. Pepper, '
            'lemonade, ginger ale, unsweetened iced tea, Arnold Palmer. Unlimited refills.'
        )
        self.create_item(
            cat,
            'Single Serve Drinks',
            0,
            'Root beer, coffee, hot tea, milk, apple juice, orange juice, '
            'pineapple juice, bottled water, Perrier. Prices vary.'
        )
