"""
Management command to load the full SoHo Pittsburgh menu into the new
unified model structure.

Usage:
    python manage.py load_soho_menu

What this does:
    1. Creates all MenuCategory and MenuSubCategory records
    2. Creates all MenuItem records (item library)
    3. Creates MenuItemCategoryAssignment records (places items into categories)
    4. Creates the default Menu records (combined, food, drinks)
    5. Creates MenuCategoryAssignment records (declares which categories each menu uses)

Safe to re-run — uses get_or_create throughout. Running again will not
duplicate items or categories. To do a full reset, wipe the tables first
via the Django shell or a separate management command.

Place at: apps/menu/management/commands/load_soho_menu.py
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from decimal import Decimal

from apps.menu.models import (
    MenuCategory,
    MenuSubCategory,
    MenuItem,
    MenuItemVariation,
    MenuItemCategoryAssignment,
    Menu,
    MenuCategoryAssignment,
)


class Command(BaseCommand):
    help = 'Loads the full SoHo Pittsburgh menu into the new unified model structure.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Loading SoHo Pittsburgh menu...\n')

        # ── Step 1: Categories ────────────────────────────────────────────────
        self.stdout.write('── Creating categories...')
        self._create_categories()

        # ── Step 2: Items + assignments ───────────────────────────────────────
        self.stdout.write('\n── Loading food items...')
        self.load_starters()
        self.load_soups_and_salads()
        self.load_tacos_and_wraps()
        self.load_sandwiches()
        self.load_burgers()
        self.load_pizzas()
        self.load_entrees()
        self.load_sides()
        self.load_kids_menu()
        self.load_desserts()
        self.load_sweet_street()

        self.stdout.write('\n── Loading drink items...')
        self.load_signature_cocktails()
        self.load_featured_drinks()
        self.load_mocktails()
        self.load_beer()
        self.load_wine()
        self.load_non_alcoholic_beverages()

        # ── Step 3: Default menus ─────────────────────────────────────────────
        self.stdout.write('\n── Creating default menus...')
        self._create_default_menus()

        self.stdout.write(self.style.SUCCESS('\nDone. SoHo menu loaded successfully.'))

    # =========================================================================
    # CATEGORY CREATION
    # =========================================================================

    def _create_categories(self):
        """
        Creates all categories and subcategories up front.
        Stored as instance attributes so item loaders can reference them directly.
        """

        def cat(name, category_type, order, description=''):
            obj, created = MenuCategory.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    'name':          name,
                    'category_type': category_type,
                    'description':   description,
                    'order':         order,
                    'is_active':     True,
                }
            )
            if created:
                self.stdout.write(f'  + Category: {name}')
            return obj

        def subcat(category, name, order, description=''):
            obj, created = MenuSubCategory.objects.get_or_create(
                slug=slugify(f'{category.slug}-{slugify(name)}'),
                defaults={
                    'category':    category,
                    'name':        name,
                    'description': description,
                    'order':       order,
                    'is_active':   True,
                }
            )
            if created:
                self.stdout.write(f'    + SubCategory: {category.name} › {name}')
            return obj

        # ── Food categories ───────────────────────────────────────────────────
        self.cat_starters       = cat('Starters',         'food',   1, 'Appetizers and shareable plates')
        self.cat_soups_salads   = cat('Soups and Salads',  'food',   2, 'Fresh salads and homemade soups')
        self.cat_tacos_wraps    = cat('Tacos and Wraps',   'food',   3, 'Fresh wraps and tacos with your choice of side')
        self.cat_sandwiches     = cat('Sandwiches',        'food',   4, 'Signature sandwiches served with your choice of side')
        self.cat_burgers        = cat('Burgers',           'food',   5, 'Half-pound burgers served with your choice of side')
        self.cat_pizza          = cat('Pizza',             'food',   6, 'All pizzas are baked on our homemade pizza dough')
        self.cat_entrees        = cat('Entrées',           'food',   7, 'Signature dinner entrées')
        self.cat_sides          = cat('Sides',             'food',   8, 'Side dishes and add-ons')
        self.cat_kids           = cat('Kids Menu',         'food',   9, 'For children 12 & under. Served with broccoli, fries, or tots')
        self.cat_desserts       = cat('Desserts',          'food',  10, 'Sweet endings to your meal')
        self.cat_sweet_street   = cat('Sweet Street',      'food',  11, 'Featured desserts')

        # ── Drink categories ──────────────────────────────────────────────────
        self.cat_cocktails      = cat('Signature Cocktails',     'drinks', 1, 'House-crafted cocktails')
        self.cat_featured_drinks= cat('Featured Drinks',         'drinks', 2, 'Seasonal and specialty cocktails')
        self.cat_mocktails      = cat('Mocktails',               'drinks', 3, 'Non-alcoholic craft cocktails')
        self.cat_beer           = cat('Beer',                    'drinks', 4, 'Draft, bottled, and canned selections')
        self.cat_wine           = cat('Wine',                    'drinks', 5, 'White, red, and sparkling wines')
        self.cat_na_beverages   = cat('Non-Alcoholic Beverages', 'drinks', 6, 'Soft drinks and other non-alcoholic options')

        # ── Beer subcategories ────────────────────────────────────────────────
        self.sub_tap      = subcat(self.cat_beer, 'On Tap',         1, 'Draft beers served fresh from the tap')
        self.sub_ipa      = subcat(self.cat_beer, 'IPA & Craft',    2, 'India pale ales and craft selections')
        self.sub_bottles  = subcat(self.cat_beer, 'Bottles & Cans', 3, 'Domestic, import, light, and more')

        # ── Wine subcategories ────────────────────────────────────────────────
        self.sub_white     = subcat(self.cat_wine, 'White',    1, 'White wine selections')
        self.sub_red       = subcat(self.cat_wine, 'Red',      2, 'Red wine selections')
        self.sub_sparkling = subcat(self.cat_wine, 'Sparkling', 3, 'Sparkling wine and rosé')

    # =========================================================================
    # ITEM CREATION HELPERS
    # =========================================================================

    def _make_slug(self, name, category):
        """
        Generates a unique slug. Appends category slug if base slug is taken
        by an item in a different category context.
        """
        base = slugify(name)
        if not MenuItem.objects.filter(slug=base).exists():
            return base
        candidate = f'{base}-{category.slug}'
        if not MenuItem.objects.filter(slug=candidate).exists():
            return candidate
        # Last resort — append pk-safe suffix
        return f'{base}-{category.slug}-{MenuItem.objects.count()}'

    def create_item(
        self, category, name, price, description='',
        subcategory=None, order=0, variations=None,
        available_game_day=False, note='',
        **item_kwargs
    ):
        """
        Creates or retrieves a MenuItem and creates its MenuItemCategoryAssignment.

        Args:
            category:          MenuCategory instance
            name:              Item name
            price:             Base price (0 = hidden price for drinks)
            description:       Full description
            subcategory:       Optional MenuSubCategory instance
            order:             Display order within the category
            variations:        List of variation dicts (name, price, size, quantity)
            available_game_day: Include on game day limited menu
            note:              Per-placement callout note
            **item_kwargs:     Any additional MenuItem field values
        """
        has_variations = bool(variations)
        has_price = price and price > 0

        slug = self._make_slug(name, category)

        item, item_created = MenuItem.objects.get_or_create(
            slug=slug,
            defaults={
                'name':              name,
                'price':             Decimal(str(price)) if has_price else None,
                'price_display':     'price' if has_price else 'hidden',
                'description':       description,
                'short_description': description[:300],
                'is_available':      True,
                'has_variations':    has_variations,
                **item_kwargs,
            }
        )

        if item_created:
            self.stdout.write(f'    + {name}')
            if has_variations:
                for idx, var in enumerate(variations):
                    MenuItemVariation.objects.create(
                        menu_item=item,
                        name=var.get('name', ''),
                        price=Decimal(str(var['price'])),
                        quantity=var.get('quantity'),
                        size=var.get('size', ''),
                        order=idx,
                        is_default=var.get('is_default', idx == 0),
                    )
                    self.stdout.write(f'      - {var["name"]} (${var["price"]})')

        # Always ensure the category assignment exists
        assignment, assign_created = MenuItemCategoryAssignment.objects.get_or_create(
            menu_item=item,
            category=category,
            defaults={
                'subcategory':       subcategory,
                'order':             order,
                'available_game_day': available_game_day,
                'note':              note,
                'is_active':         True,
            }
        )

        return item

    # =========================================================================
    # DEFAULT MENU SETUP
    # =========================================================================

    def _create_default_menus(self):
        """
        Creates the three default Menu records and declares their categories.

        - Default Combined menu: all food + drink categories (main menu pages)
        - Default Food menu: food categories only
        - Default Drinks menu: drink categories only

        MenuCategoryAssignment records are created for each, using the
        category's natural order as display_order.
        """

        def make_menu(title, slug, menu_type, description=''):
            menu, created = Menu.objects.get_or_create(
                slug=slug,
                defaults={
                    'title':       title,
                    'menu_type':   menu_type,
                    'description': description,
                    'is_default':  True,
                    'is_active':   True,
                    'show_on_homepage': False,
                }
            )
            if created:
                self.stdout.write(f'  + Menu: {title}')
            return menu

        def assign_categories(menu, categories):
            for display_order, category in enumerate(categories, start=1):
                obj, created = MenuCategoryAssignment.objects.get_or_create(
                    menu=menu,
                    category=category,
                    defaults={'display_order': display_order}
                )
                if created:
                    self.stdout.write(f'    → {category.name}')

        # ── All food categories in order ──────────────────────────────────────
        food_cats = [
            self.cat_starters,
            self.cat_soups_salads,
            self.cat_tacos_wraps,
            self.cat_sandwiches,
            self.cat_burgers,
            self.cat_pizza,
            self.cat_entrees,
            self.cat_sides,
            self.cat_kids,
            self.cat_desserts,
        ]

        # ── All drink categories in order ─────────────────────────────────────
        drink_cats = [
            self.cat_cocktails,
            self.cat_featured_drinks,
            self.cat_mocktails,
            self.cat_beer,
            self.cat_wine,
            self.cat_na_beverages,
        ]

        # ── Default combined menu (main site menu) ────────────────────────────
        combined = make_menu(
            'SoHo Menu',
            'soho-menu',
            'combined',
            'The full SoHo Pittsburgh menu — food and drinks.'
        )
        assign_categories(combined, food_cats + drink_cats)

        # ── Default food-only menu ────────────────────────────────────────────
        food = make_menu(
            'Food Menu',
            'food-menu',
            'food',
            'SoHo Pittsburgh food menu.'
        )
        assign_categories(food, food_cats)

        # ── Default drinks-only menu ──────────────────────────────────────────
        drinks = make_menu(
            'Drinks Menu',
            'drinks-menu',
            'drinks',
            'SoHo Pittsburgh drinks menu.'
        )
        assign_categories(drinks, drink_cats)

        # ── Sweet Street promo menu ───────────────────────────────────────────
        sweet_street, created = Menu.objects.get_or_create(
            slug='sweet-street',
            defaults={
                'title':            'Sweet Street',
                'menu_type':        'promo',
                'description':      'Featured desserts.',
                'is_default':       False,
                'is_active':        True,
                'show_on_homepage': True,
            }
        )
        if created:
            self.stdout.write('  + Menu: Sweet Street (promo)')
        MenuCategoryAssignment.objects.get_or_create(
            menu=sweet_street,
            category=self.cat_sweet_street,
            defaults={'display_order': 1}
        )

    # =========================================================================
    # FOOD ITEMS
    # =========================================================================

    def load_starters(self):
        self.stdout.write('  Starters...')
        c = self.cat_starters

        self.create_item(c, 'Mozzarella Sticks', 16, order=1,
            description='Eight battered mozzarella sticks served with a side of our homemade marinara',
            available_game_day=True)

        self.create_item(c, 'Hand-Breaded Fried Zucchini', 12, order=2,
            description='Five planks of our parmesan and panko hand-breaded fried zucchini, served with our homemade marinara')

        self.create_item(c, 'Pulled Pork Sliders', 17, order=3,
            description='Three pulled pork sliders topped with BBQ sauce, our homemade cilantro lime coleslaw, and garlic aioli',
            available_game_day=True)

        self.create_item(c, 'SoHo Sliders', 19, order=4,
            description='Four 100% Angus beef sliders with American cheese and pickles',
            available_game_day=True)

        self.create_item(c, 'SoHo Sampler', 20, order=5,
            description='Hand-breaded fried zucchini, mozzarella sticks, SoHo sliders, and french fries. Upgrade to SoHo fries +3 | Gravy fries +2',
            is_featured=True, available_game_day=True)

        self.create_item(c, 'Cheese Quesadilla', 15, order=6,
            description='Grilled peppers & onions with cheddar jack cheese in a flour tortilla served with a side of sour cream, homemade pico de gallo, and jalapeños. Grilled chicken +5 | Pulled pork +6 | Steak +7')

        self.create_item(c, 'SoHo Nachos', 18, order=7,
            description='House-fried tortilla chips topped with queso, jalapeños, black bean salsa, pico de gallo, cheddar jack cheese, lime crema, and a spicy ranch drizzle. Guacamole +2 | Grilled chicken +6 | BBQ pulled pork +6 | Chili +4',
            available_game_day=True)

        self.create_item(c, 'Sautéed Pierogies', 19, order=8,
            description='Four locally sourced pierogies sautéed and topped with caramelized onions, crispy bacon, and a balsamic drizzle',
            is_chef_special=True)

        self.create_item(c, 'Bavarian Pretzel', 18, order=9,
            description='Sixteen salted, warm, soft pretzel bites served with queso and honey mustard',
            available_game_day=True)

        self.create_item(c, 'Potstickers', 15, order=10,
            description='Savory pork and veggie dumplings fried golden brown. Served with a tangy sesame sauce for dipping',
            available_game_day=True)

        self.create_item(c, 'SoHo Wings', 20, order=11,
            description='Traditional wings tossed with your choice of sauce or dry rub. Served with buttermilk ranch or blue cheese dressing. Sauces: Buffalo, Mango Habanero, Sweet BBQ, Sweet Chili, Garlic Parmesan, Honey Garlic, Cajun Dry Rub, or Old Bay',
            is_featured=True, available_game_day=True,
            variations=[
                {'name': '6 Wings',  'price': 10, 'quantity': 6,  'is_default': False},
                {'name': '12 Wings', 'price': 18, 'quantity': 12, 'is_default': True},
                {'name': '20 Wings', 'price': 28, 'quantity': 20, 'is_default': False},
            ])

        self.create_item(c, 'Chicken Tenders', 17, order=12,
            description='Chicken tenders tossed in your choice of sauce or dry rub with buttermilk ranch or blue cheese dressing',
            available_game_day=True)

        self.create_item(c, 'Spinach Artichoke Dip', 17, order=13,
            description='Our homemade mix of spinach, artichoke hearts, garlic, parmesan, and cream cheese. Served warm with tortilla chips',
            dietary_type='vegetarian')

        self.create_item(c, 'Buffalo Chicken Dip', 17, order=14,
            description='Pulled buffalo chicken blended with cream cheese, cheddar jack cheese, and ranch. Served warm with tortilla chips')

        self.create_item(c, 'Chili Queso Dip', 17, order=15,
            description='Our signature SoHo chili blended with homemade smoked cheddar cheese queso, and topped with green onion. Served with tortilla chips')

        self.create_item(c, 'SoHo Style Fries', 16, order=16,
            description='Crispy french fries smothered with smoked cheddar cheese queso and SoHo chili. Topped with crumbled bacon, jalapeños, and a spicy ranch drizzle',
            available_game_day=True)

    def load_soups_and_salads(self):
        self.stdout.write('  Soups and Salads...')
        c = self.cat_soups_salads

        self.create_item(c, 'Soup of the Day', 7, order=1,
            description="Chef's homemade selection",
            variations=[
                {'name': 'Cup',  'price': 7, 'size': 'Cup',  'is_default': True},
                {'name': 'Bowl', 'price': 9, 'size': 'Bowl', 'is_default': False},
            ])

        self.create_item(c, 'French Onion Soup', 9, order=2,
            description='Homemade with caramelized onions, burgundy wine, and beef broth, topped with house made croutons and Swiss cheese')

        self.create_item(c, 'SoHo Chili', 7, order=3,
            description='Homemade chili topped with cheddar jack cheese, sour cream and scallions. Served with tortilla chips',
            variations=[
                {'name': 'Cup',  'price': 7, 'size': 'Cup',  'is_default': True},
                {'name': 'Bowl', 'price': 9, 'size': 'Bowl', 'is_default': False},
            ])

        self.create_item(c, 'Side Salad', 7, order=4,
            description='Mixed greens, tomatoes, carrots, red onions, cheddar jack cheese, and croutons')

        self.create_item(c, 'Garden Salad', 14, order=5,
            description='Mixed greens, tomatoes, onions, cucumbers, fire-roasted corn, shredded carrots, cheddar jack cheese, homemade croutons, and your choice of dressing',
            dietary_type='vegetarian')

        self.create_item(c, 'Caesar Salad', 14, order=6,
            description='Romaine lettuce, parmesan cheese and homemade croutons. Served with a side of Caesar dressing')

        self.create_item(c, 'Chopped Cobb Salad', 14, order=7,
            description='Mixed greens, onions, diced roma tomatoes, bacon, egg, roasted red peppers, and blue cheese crumbles. Served with your choice of dressing')

        self.create_item(c, 'Pittsburgh Chicken Salad', 19, order=8,
            description='Marinated chicken served over mixed greens, bell peppers, red onions, cheddar jack cheese, eggs, and cucumbers. Topped with french fries and served your choice of dressing. Substitute steak +4',
            is_featured=True)

        self.create_item(c, 'Southern Fried Chicken Salad', 18, order=9,
            description='Fried chicken tenders over mixed greens, fire-roasted corn, crispy bacon bits, red onions, black bean salsa, diced tomatoes, and cheddar jack cheese. Served with your choice of dressing')

    def load_tacos_and_wraps(self):
        self.stdout.write('  Tacos and Wraps...')
        c = self.cat_tacos_wraps

        self.create_item(c, 'Buffalo Chicken Wrap', 19, order=1,
            description='Crispy or grilled buffalo chicken, shredded romaine lettuce, tomatoes, cheddar jack cheese, and ranch dressing')

        self.create_item(c, 'SoHo Tacos', 15, order=2,
            description='Fire-roasted corn, grilled peppers, and cilantro lime slaw. Topped with a chimichurri crema, cotija cheese, and pico de gallo. Served in a warm flour tortilla. Grilled chicken +4 | Pulled pork +4 | Strip steak +8 | Shrimp +8')

        self.create_item(c, 'Santa Fe Chicken Wrap', 19, order=3,
            description='Grilled chicken, shredded romaine lettuce, pico de gallo, roasted red peppers, fire roasted corn, pepperjack cheese, and smokey ranch dressing')

        self.create_item(c, 'SoHo Veggie Wrap', 17, order=4,
            description='Arugula, tomato, shredded carrots, roasted red peppers, cucumbers, red onions, pepper chutney, and pepperjack cheese',
            dietary_type='vegetarian')

        self.create_item(c, 'Club Wrap', 19, order=5,
            description='Smoked ham, turkey, bacon, shredded romaine lettuce, tomatoes, garlic aioli, and Swiss cheese')

    def load_sandwiches(self):
        self.stdout.write('  Sandwiches...')
        c = self.cat_sandwiches

        self.create_item(c, 'Green Goddess Ciabatta', 18, order=1,
            description='Grilled marinated zucchini, arugula, tomato, red onion, cucumber, caramelized onions, balsamic drizzle, and pepperjack cheese. Served on a toasted ciabatta bun with a queen olive',
            dietary_type='vegetarian')

        self.create_item(c, 'Pulled Pork Sandwich', 19, order=2,
            description='House-smoked BBQ pulled pork topped with smoked cheddar cheese, onion rings, and jalapeños. Served on a toasted brioche bun',
            is_featured=True)

        self.create_item(c, 'Pub Fish Sandwich', 20, order=3,
            description='Beer-battered haddock served on a brioche bun with homemade tartar sauce. Cheese +2')

        self.create_item(c, 'Steak & Cheese', 20, order=4,
            description='Philly steak with sautéed peppers & onions, topped with white American cheese and served on a steamed hoagie roll. Mushrooms +2 | Lettuce, tomato, and onion +2')

        self.create_item(c, 'Grilled Chicken Sandwich', 19, order=5,
            description='Marinated grilled chicken breast with your choice of cheese. Served on a toasted brioche bun and topped with lettuce, tomato, onion, and pickle. Bacon +2')

        self.create_item(c, 'Reuben', 19, order=6,
            description='Corned beef, Swiss cheese, sauerkraut, and homemade thousand island dressing. Served on toasted rye bread')

        self.create_item(c, 'Rachel', 19, order=7,
            description='Smoked turkey breast, Swiss cheese, coleslaw, and homemade thousand island dressing. Served on grilled rye bread')

        self.create_item(c, 'Hot Sausage Sandwich', 19, order=8,
            description='Hot Italian sausage cooked with peppers & onions in a classic tomato sauce. Topped with provolone cheese and served on a hoagie roll')

        self.create_item(c, 'Pittsburgh Lasagna', 20, order=9,
            description="SoHo's original handheld lasagna with meat sauce and vine-ripened tomatoes, topped with mozzarella cheese, sandwiched between grilled garlic toast",
            is_chef_special=True)

        self.create_item(c, 'SoHo Super Dogs', 16, order=10,
            description="Two Nathan's famous all-beef hot dogs topped with American cheese and sliced bacon. Chili +2",
            available_game_day=True)

    def load_burgers(self):
        self.stdout.write('  Burgers...')
        c = self.cat_burgers

        self.create_item(c, 'Cheeseburger', 19, order=1,
            description='Half-pound burger served with your choice of cheese. Topped with lettuce, tomato, onion, and pickle. Bacon +2',
            available_game_day=True)

        self.create_item(c, 'Black & Blue Burger', 20, order=2,
            description='Half-pound blackened burger, blue cheese crumbles, and bacon. Topped with lettuce, tomato, and onion')

        self.create_item(c, 'Western BBQ Burger', 20, order=3,
            description='Half-pound burger covered with BBQ sauce, smoked cheddar cheese, bacon, and onion rings. Topped with lettuce and tomato. Top with BBQ pulled pork +2')

        self.create_item(c, 'Mushroom Swiss Burger', 20, order=4,
            description='Half-pound burger, mushrooms, caramelized onions, and Swiss cheese. Topped with lettuce and tomato',
            is_featured=True)

        self.create_item(c, 'Smash Burger', 19, order=5,
            description='Two smashed beef patties, topped with white American cheese, dill pickles, caramelized onions, and drizzled with housemade thousand island dressing',
            available_game_day=True)

        self.create_item(c, 'Impossible Burger', 19, order=6,
            description='Impossible burger with caramelized onions. Topped with lettuce, tomato, and pickle. Cheese +2',
            dietary_type='vegan')

    def load_pizzas(self):
        self.stdout.write('  Pizza...')
        c = self.cat_pizza

        self.create_item(c, 'Cheese Pizza', 18, order=1,
            description='Homemade red sauce, mozzarella, provolone, and parmesan cheese',
            dietary_type='vegetarian')

        self.create_item(c, 'Buffalo Chicken Pizza', 20, order=2,
            description='Buffalo grilled chicken, buffalo ranch sauce, with mozzarella and cheddar cheese. Drizzled with ranch')

        self.create_item(c, 'BBQ Chicken Pizza', 20, order=3,
            description='Grilled chicken, sweet BBQ sauce, and mozzarella. Topped with bacon and green onions')

        self.create_item(c, 'Meat Lovers Pizza', 24, order=4,
            description='Homemade red sauce, four cheese blend, pepperoni, hot sausage, bacon, and ham')

    def load_entrees(self):
        self.stdout.write('  Entrées...')
        c = self.cat_entrees

        self.create_item(c, 'Pasta Primavera', 18, order=1,
            description='Lightly sautéed peppers, onions, mushrooms, and roasted tomatoes. Tossed in a garlic white wine sauce, and served over farfalle pasta. Lunch portions available until 2PM',
            dietary_type='vegetarian')

        self.create_item(c, 'Chicken Parmesan', 20, order=2,
            description='Hand-breaded chicken tenderloins over linguini. Topped with homemade marinara and melted provolone cheese',
            is_featured=True)

        self.create_item(c, 'Creamy Mushroom Marsala', 20, order=3,
            description='Pan-seared chicken tenderloins served over farfalle pasta and tossed in our creamy mushroom marsala sauce')

        self.create_item(c, 'Bourbon Glazed Salmon', 24, order=4,
            description='Pan-seared salmon topped with our signature brown sugar bourbon glaze. Served over rice pilaf with steamed broccoli and garlic butter',
            is_featured=True)

        self.create_item(c, 'Shrimp Scampi', 23, order=5,
            description='Lightly floured shrimp sautéed in a rich garlic-butter sauce with a touch of white wine and fresh lemon. Tossed with linguini and finished with parmesan and parsley',
            contains_shellfish=True)

        self.create_item(c, 'Smokey Pork Chop', 25, order=6,
            description='One-inch thick 10 oz bone-in grilled pork chop topped with our sweet and smokey BBQ glaze. Served with mashed potatoes and sautéed green beans')

        self.create_item(c, 'Guiltless Chicken', 19, order=7,
            description='Grilled marinated chicken, roasted tomatoes, rice pilaf, and green beans')

        self.create_item(c, 'Pittsburgh Pierogies', 25, order=8,
            description='Locally sourced pierogies topped with caramelized onions, kielbasa, and broccoli. Served with sour cream and scallions',
            is_featured=True)

        self.create_item(c, 'Fish & Chips', 23, order=9,
            description='Beer-battered haddock on a bed of french fries. Served with coleslaw and homemade tartar sauce')

        self.create_item(c, 'Grilled New York Strip', 35, order=10,
            description='12 oz New York strip grilled to perfection. Served with creamy mashed potatoes and broccoli. Sautéed mushrooms & onions +4 | Shrimp +8',
            is_chef_special=True)

    def load_sides(self):
        self.stdout.write('  Sides...')
        c = self.cat_sides

        sides = [
            ('French Fries',              7,  True),
            ('Cajun Fries',               7,  True),
            ('Tater Tots',                7,  True),
            ('Cajun Tots',                7,  True),
            ('Onion Rings',               7,  False),
            ('Coleslaw',                  7,  False),
            ('Black Bean Salsa',          7,  False),
            ('Caesar Side Salad',         7,  False),
            ("Chef's Vegetables",         7,  False),
            ('Tortilla Chips',            7,  False),
            ('Rice Pilaf',                7,  False),
            ('Mashed Potatoes with Gravy', 8, True),
            ('Gravy Fries',               8,  True),
        ]
        for order, (name, price, game_day) in enumerate(sides, start=1):
            self.create_item(c, name, price, order=order, available_game_day=game_day)

    def load_kids_menu(self):
        self.stdout.write('  Kids Menu...')
        c = self.cat_kids

        kids = [
            ("I Don't Know",         10, 'Macaroni and cheese',                                         'none'),
            ("I'm Not Hungry",        10, 'Two chicken tenders',                                          'none'),
            ("I Want to Go to McDonald's", 10, 'Kids burger',                                             'none'),
            ("I Don't Care",          10, 'Penne pasta mixed with butter or red sauce',                  'vegetarian'),
            ("I Want to Go Home",     10, 'Grilled American cheese on sourdough bread',                  'vegetarian'),
            ('Nothing',               10, 'Angus beef hotdog',                                            'none'),
        ]
        for order, (name, price, desc, dietary) in enumerate(kids, start=1):
            self.create_item(c, name, price, description=desc, order=order,
                dietary_type=dietary, available_game_day=True)

    def load_desserts(self):
        self.stdout.write('  Desserts...')
        c = self.cat_desserts

        self.create_item(c, 'Seasonal Cheesecake', 10, order=1,
            description="A creamy vanilla cheesecake with SoHo's seasonal topping. Ask your server about our current selections")

        self.create_item(c, 'Carrot Cake', 10, order=2,
            description='Two layers of soft carrot cake iced with cream cheese icing and rimmed with walnuts',
            dietary_type='vegetarian')

        self.create_item(c, 'Brownie Sundae', 10, order=3,
            description='Our house-made brownie served warm and topped with vanilla ice cream, drizzled with chocolate sauce — perfect to share',
            is_featured=True)

        self.create_item(c, 'Chocolate Torte', 9, order=4,
            description='This flourless chocolate torte is made with a blend of four chocolates and finished with a ganache topping, raspberry sauce, and whipped cream',
            is_gluten_free=True)

        self.create_item(c, 'Oreo Cream Pie', 8, order=5,
            description='A fluffy whipped cream filling infused with Oreo pieces in a chocolate cookie crust',
            dietary_type='vegetarian')

    def load_sweet_street(self):
        """
        Sweet Street is a separate promotional category with its own name.
        The same dessert items are assigned here as a second placement —
        this is the core benefit of the new model: one item, multiple categories.
        """
        self.stdout.write('  Sweet Street (promo desserts)...')
        c = self.cat_sweet_street

        # These items already exist from load_desserts() — get_or_create on the
        # item is a no-op, but the category assignment is new.
        dessert_items = [
            ('Seasonal Cheesecake', 10, 1),
            ('Carrot Cake',         10, 2),
            ('Brownie Sundae',      10, 3),
            ('Chocolate Torte',     9,  4),
            ('Oreo Cream Pie',      8,  5),
        ]
        for name, price, order in dessert_items:
            item = MenuItem.objects.filter(slug=slugify(name)).first()
            if item:
                MenuItemCategoryAssignment.objects.get_or_create(
                    menu_item=item,
                    category=c,
                    defaults={'order': order, 'is_active': True}
                )
                self.stdout.write(f'    → {name} assigned to Sweet Street')
            else:
                self.stdout.write(
                    self.style.WARNING(f'    ! {name} not found — run load_desserts first')
                )

    # =========================================================================
    # DRINK ITEMS
    # =========================================================================

    def load_signature_cocktails(self):
        self.stdout.write('  Signature Cocktails...')
        c = self.cat_cocktails

        cocktails = [
            ('Blue Hawaiian',                 'Bacardi, Svedka, Blue Curacao, pineapple juice, lime juice, and simple syrup'),
            ('Blueberry Lemon Drop Martini',  'Citron vodka, lemon juice, simple syrup, and blueberry puree'),
            ('Blue Raspberry Jolly Rancher',  'Blue Curacao, raspberry vodka, sours, and Sprite'),
            ('Espresso Martini',              'Absolut, Kahlua, simple syrup, and Stok espresso coffee'),
            ('Go Bananas',                    'Bacardi, banana liquor, pineapple juice, and cherry juice'),
            ('Mango Cool Breeze',             'Svedka Mango Pineapple Vodka, Triple Sec, sours, and cranberry juice'),
            ('Million Dollar Margarita',      'Patron, Grand Marnier, simple syrup, and lime juice'),
            ('Paloma',                        'Espolon, grapefruit juice, club soda, and lime juice'),
            ('Peach Sunrise',                 'Svedka Peach Vodka, peach schnapps, Triple Sec, orange juice, and grenadine'),
            ('Skinny Margarita',              'Jose Cuervo Silver, agave nectar, lime juice, and lemon juice'),
            ('Strawberry Lemonade',           'Svedka Strawberry Lemonade Vodka, Triple Sec, lemon juice, and strawberry puree'),
            ('Triple Black Manhattan',        'Crown Royal Black, blackberry brandy, sweet vermouth, and a dash of walnut bitters'),
        ]
        for order, (name, desc) in enumerate(cocktails, start=1):
            self.create_item(c, name, 0, description=desc, order=order)

    def load_featured_drinks(self):
        self.stdout.write('  Featured Drinks...')
        c = self.cat_featured_drinks

        drinks = [
            ('Christmas Cocoa Martini',  'Bacardi, Kahlua, Creme de Cacao, chocolate bitters, and espresso',        True),
            ('Pomegranate French 75',    'Gin, Cointreau, PAMA, lime juice, and Prosecco',                           True),
            ('Peppermint Mudslide',      'Svedka, peppermint schnapps, Baileys, Kahlua, cream, and chocolate syrup', True),
            ('Cranberry Moscow Mule',    'Svedka, lime juice, ginger beer, and cranberry juice',                     True),
            ('Brown Sugar Bourbon Smash','Makers Mark, ginger beer, brown sugar simple syrup, and a cinnamon stick', True),
        ]
        for order, (name, desc, seasonal) in enumerate(drinks, start=1):
            self.create_item(c, name, 0, description=desc, order=order,
                is_featured=True, is_seasonal=seasonal)

    def load_mocktails(self):
        self.stdout.write('  Mocktails...')
        c = self.cat_mocktails

        mocktails = [
            ('SoHo Sunrise',           'Orange juice, lime juice, grenadine, and Sprite'),
            ('Cranberry Fizz',         'Lemon juice, simple syrup, cranberry juice, and ginger beer'),
            ('Orange Dreamsicle',      'Orange juice, strawberry puree, Sprite, and cream'),
            ('NA Pineapple Margarita', 'Ritual Tequila Alternative, pineapple juice, lime juice, and agave nectar'),
            ('Citrus Smash',           'Ritual Tequila Alternative, lemon juice, lime juice, simple syrup, and club soda'),
            ('NA Apple Mule',          'Ritual Rum Alternative, apple juice, lime juice, ginger beer, and cinnamon'),
            ('NA Whiskey Palmer',      'Ritual Whiskey Alternative, lemonade, and iced tea'),
            ('Tropical Dream',         'Ritual Rum Alternative, orange juice, and pineapple juice topped with a splash of cream and nutmeg'),
            ('Red Winter Punch',       'Ritual Rum Alternative, cranberry juice, grenadine, lime juice, and Sprite'),
        ]
        for order, (name, desc) in enumerate(mocktails, start=1):
            self.create_item(c, name, 0, description=desc, order=order)

    def load_beer(self):
        self.stdout.write('  Beer...')
        c = self.cat_beer

        tap_beers = [
            'Allagash White', "Bell's Two Hearted", 'Blockhouse Chocolate',
            'Brew Dog Hazy Jane', 'Blue Moon', 'Brew Gentlemen', 'Bud Light',
            'Coors Light', 'Dogfish Grateful Dead IPA', 'Fatheads Head Hunter',
            'Guinness Stout', 'I.C. Light', 'Miller Lite', 'Modelo Especial',
            'Penn Pilsner', 'Sam Adams Seasonal', 'Stella Artois', 'Yuengling',
        ]
        for order, name in enumerate(tap_beers, start=1):
            self.create_item(c, name, 0, order=order,
                subcategory=self.sub_tap, available_game_day=True)

        ipas = [
            'Dewey Swishy Pants', 'Dogfish Head 60 Minute', 'Lagunitas',
            'Sam Adams Just the Haze NA', 'Sierra Nevada Hazy Peach', 'Southern Tier 2XIPA',
        ]
        for order, name in enumerate(ipas, start=1):
            self.create_item(c, name, 0, order=order, subcategory=self.sub_ipa)

        bottles = [
            'Rolling Rock', 'Budweiser', 'Corona Extra', 'Dos Equis', 'Heineken',
            'Labatt Blue', 'Iron City', 'Corona Light', 'Heineken Light',
            'Heineken 00', 'IC Light Mango', 'Labatt Blue Light', 'Michelob Ultra',
            'Yuengling Light', 'Angry Orchard', 'Great Lakes Christmas Ale',
            'Great Lakes Cookie Exchange', 'High Noon', 'Smirnoff Orange Cream Pop',
            'Southern Tier Old Man Winter', 'Southern Tier 2XMAS', 'White Claw',
        ]
        for order, name in enumerate(bottles, start=1):
            self.create_item(c, name, 0, order=order, subcategory=self.sub_bottles)

    def load_wine(self):
        self.stdout.write('  Wine...')
        c = self.cat_wine

        whites = [
            'Woodbridge Chardonnay', 'Mondavi Chardonnay',
            'Chateau Ste. Michelle Riesling', 'Elmo Pio Moscato',
            'Ruffino Pinot Grigio', 'Nobilo Sauvignon Blanc',
        ]
        for order, name in enumerate(whites, start=1):
            self.create_item(c, name, 0, order=order, subcategory=self.sub_white)

        reds = [
            'Woodbridge Cabernet', 'Clos du Bois Cabernet',
            'Woodbridge Merlot', 'Alamas Malbec', 'Mark West Pinot Noir',
        ]
        for order, name in enumerate(reds, start=1):
            self.create_item(c, name, 0, order=order, subcategory=self.sub_red)

        sparkling = ['Ruffino Prosecco', 'Ruffino Rosé']
        for order, name in enumerate(sparkling, start=1):
            self.create_item(c, name, 0, order=order, subcategory=self.sub_sparkling)

    def load_non_alcoholic_beverages(self):
        self.stdout.write('  Non-Alcoholic Beverages...')
        c = self.cat_na_beverages

        self.create_item(c, 'Unlimited Refill Drinks', 4, order=1,
            description='Coca-Cola, Diet Coke, Coke Zero, Cherry Coke, Sprite, Dr. Pepper, lemonade, ginger ale, unsweetened iced tea, Arnold Palmer. Unlimited refills.',
            available_game_day=True)

        self.create_item(c, 'Single Serve Drinks', 0, order=2,
            description='Root beer, coffee, hot tea, milk, apple juice, orange juice, pineapple juice, bottled water, Perrier. Prices vary.')
