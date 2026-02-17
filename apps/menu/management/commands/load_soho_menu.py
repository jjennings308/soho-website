"""
Django management command to load Soho Pittsburgh menu data with size/quantity variations
Place this file in: <your_app>/management/commands/load_soho_menu.py

Usage: python manage.py load_soho_menu
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from decimal import Decimal
from apps.menu.models import MenuCategory, MenuItem, MenuItemVariation  # Adjust 'menu' to your actual app name


class Command(BaseCommand):
    help = 'Loads Soho Pittsburgh menu data with variations into the database'

    def handle(self, *args, **kwargs):
        self.stdout.write('Loading Soho Pittsburgh menu data...')
        
        # Clear existing data (optional - comment out if you want to keep existing data)
        MenuItemVariation.objects.all().delete()
        MenuItem.objects.all().delete()
        MenuCategory.objects.all().delete()
        
        # Create categories and items
        self.load_starters()
        self.load_soups_and_salads()
        self.load_tacos_and_wraps()
        self.load_sandwiches()
        self.load_burgers()
        self.load_pizzas()
        self.load_entrees()
        self.load_sides()
        self.load_beverages()
        self.load_kids_menu()
        self.load_desserts()
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded menu data!'))

    def create_category(self, name, description, order):
        """Helper method to create a menu category"""
        category, created = MenuCategory.objects.get_or_create(
            slug=slugify(name),
            defaults={
                'name': name,
                'description': description,
                'order': order,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(f'  Created category: {name}')
        return category

    def create_item(self, category, name, price, description='', variations=None, **kwargs):
        """
        Helper method to create a menu item with optional variations
        
        Args:
            variations: List of dicts with 'name' and 'price' keys, e.g.:
                [{'name': '6 Wings', 'price': 4, 'quantity': 6},
                 {'name': '12 Wings', 'price': 7.50, 'quantity': 12}]
        """
        has_variations = variations is not None and len(variations) > 0
        
        item, created = MenuItem.objects.get_or_create(
            slug=slugify(name),
            defaults={
                'category': category,
                'name': name,
                'price': Decimal(str(price)),
                'description': description,
                'short_description': description[:300] if len(description) > 300 else description,
                'is_available': True,
                'has_variations': has_variations,
                **kwargs
            }
        )
        
        if created:
            self.stdout.write(f'    Added: {name} - ${price}')
            
            # Add variations if provided
            if has_variations:
                for idx, var in enumerate(variations):
                    MenuItemVariation.objects.create(
                        menu_item=item,
                        name=var.get('name', ''),
                        price=Decimal(str(var.get('price', 0))),
                        quantity=var.get('quantity'),
                        size=var.get('size', ''),
                        order=idx,
                        is_default=var.get('is_default', idx == 0)
                    )
                    self.stdout.write(f'      - Variation: {var["name"]} (${var["price"]})')
        
        return item

    def load_starters(self):
        category = self.create_category(
            'Starters',
            'Appetizers and shareable plates to start your meal',
            order=1
        )
        
        self.create_item(category, 'Mozzarella Sticks', 16,
            'Eight battered mozzarella sticks served with a side of our homemade marinara')
        
        self.create_item(category, 'Hand-Breaded Fried Zucchini', 12,
            'Five planks of our parmesan and panko hand-breaded fried zucchini, served with our homemade marinara')
        
        self.create_item(category, 'Pulled Pork Sliders', 17,
            'Three pulled pork sliders topped with BBQ sauce, our homemade cilantro lime coleslaw, and garlic aioli')
        
        self.create_item(category, 'SoHo Sliders', 19,
            'Four 100% Angus beef sliders with American cheese and pickles')
        
        self.create_item(category, 'SoHo Sampler', 20,
            'Hand-breaded fried zucchini, mozzarella sticks, SoHo sliders, and french fries. Upgrade to SoHo fries +3 | Gravy fries +2',
            is_featured=True)
        
        self.create_item(category, 'Cheese Quesadilla', 15,
            'Grilled peppers & onions with cheddar jack cheese in a flour tortilla served with a side of sour cream, homemade pico de gallo, and jalapeños. Grilled chicken +5 | Pulled pork +6 | Steak +7')
        
        self.create_item(category, 'SoHo Nachos', 18,
            'House-fried tortilla chips topped with queso, jalapeños, black bean salsa, pico de gallo, cheddar jack cheese, lime crema, and a spicy ranch drizzle. Guacamole +2 | Grilled chicken +6 | BBQ pulled pork +6 | Chili +4')
        
        self.create_item(category, 'Sautéed Pierogies', 19,
            'Four locally sourced pierogies sautéed and topped with caramelized onions, crispy bacon, and a balsamic drizzle')
        
        self.create_item(category, 'Bavarian Pretzel', 18,
            'Sixteen salted, warm, soft pretzel bites served with queso and honey mustard')
        
        self.create_item(category, 'Potstickers', 15,
            'Savory pork and veggie dumplings fried golden brown. Served with a tangy sesame sauce for dipping')
        
        # Wings with variations
        self.create_item(
            category, 
            'SoHo Wings', 
            20,  # Base price for display
            'Traditional wings tossed with your choice of sauce or dry rub. Served with buttermilk ranch or blue cheese dressing on the side. Sauces: Buffalo, Mango Habanero, Sweet BBQ, Sweet Chili, Garlic Parmesan, Honey Garlic, Cajun Dry Rub, or Old Bay',
            is_featured=True,
            variations=[
                {'name': '6 Wings', 'price': 10, 'quantity': 6, 'is_default': False},
                {'name': '12 Wings', 'price': 18, 'quantity': 12, 'is_default': True},
                {'name': '20 Wings', 'price': 28, 'quantity': 20, 'is_default': False},
            ]
        )
        
        self.create_item(category, 'Chicken Tenders', 17,
            'Chicken tenders tossed in your choice of sauce or dry rub with buttermilk ranch or blue cheese dressing')
        
        self.create_item(category, 'Spinach Artichoke Dip', 17,
            'Our homemade mix of spinach, artichoke hearts, garlic, parmesan, and cream cheese. Served warm with tortilla chips')
        
        self.create_item(category, 'Buffalo Chicken Dip', 17,
            'Pulled buffalo chicken blended with cream cheese, cheddar jack cheese, and ranch. Served warm with tortilla chips')
        
        self.create_item(category, 'Chili Queso Dip', 17,
            'Our signature SoHo chili blended with homemade smoked cheddar cheese queso, and topped with green onion. Served with tortilla chips')
        
        self.create_item(category, 'SoHo Style Fries', 16,
            'Crispy french fries smothered with smoked cheddar cheese queso and SoHo chili. Topped with crumbled bacon, jalapeños, and a spicy ranch drizzle')

    def load_soups_and_salads(self):
        category = self.create_category(
            'Soups and Salads',
            'Fresh salads and homemade soups',
            order=2
        )
        
        # Soup of the Day with Cup/Bowl variations
        self.create_item(
            category, 
            'Soup of the Day', 
            7,
            "Chef's homemade selection",
            variations=[
                {'name': 'Cup', 'price': 7, 'size': 'Cup', 'is_default': True},
                {'name': 'Bowl', 'price': 9, 'size': 'Bowl', 'is_default': False},
            ]
        )
        
        self.create_item(category, 'French Onion Soup', 9,
            'Homemade with caramelized onions, burgundy wine, and beef broth, topped with house made croutons and Swiss cheese')
        
        # Chili with Cup/Bowl variations
        self.create_item(
            category,
            'SoHo Chili',
            7,
            'Homemade chili topped with cheddar jack cheese, sour cream and scallions. Served with tortilla chips',
            variations=[
                {'name': 'Cup', 'price': 7, 'size': 'Cup', 'is_default': True},
                {'name': 'Bowl', 'price': 9, 'size': 'Bowl', 'is_default': False},
            ]
        )
        
        self.create_item(category, 'Side Salad', 7,
            'Mixed greens, tomatoes, carrots, red onions, cheddar jack cheese, and croutons')
        
        self.create_item(category, 'Garden Salad', 14,
            'Mixed greens, tomatoes, onions, cucumbers, fire-roasted corn, shredded carrots, cheddar jack cheese, homemade croutons, and your choice of dressing')
        
        self.create_item(category, 'Caesar Salad', 14,
            'Romaine lettuce, parmesan cheese and homemade croutons. Served with a side of Caesar dressing')
        
        self.create_item(category, 'Chopped Cobb Salad', 14,
            'Mixed greens, onions, diced roma tomatoes, bacon, egg, roasted red peppers, and blue cheese crumbles. Served with your choice of dressing')
        
        self.create_item(category, 'Pittsburgh Chicken Salad', 19,
            'Marinated chicken served over mixed greens, bell peppers, red onions, cheddar jack cheese, eggs, and cucumbers. Topped with french fries and served your choice of dressing. Substitute steak +4')
        
        self.create_item(category, 'Southern Fried Chicken Salad', 18,
            'Fried chicken tenders over mixed greens, fire-roasted corn, crispy bacon bits, red onions, black bean salsa, diced tomatoes, and cheddar jack cheese. Served with your choice of dressing')

    def load_tacos_and_wraps(self):
        category = self.create_category(
            'Tacos and Wraps',
            'Fresh wraps and tacos with your choice of side',
            order=3
        )
        
        self.create_item(category, 'Buffalo Chicken Wrap', 19,
            'Crispy or grilled buffalo chicken, shredded romaine lettuce, tomatoes, cheddar jack cheese, and ranch dressing')
        
        self.create_item(category, 'SoHo Tacos', 15,
            'Fire-roasted corn, grilled peppers, and cilantro lime slaw. Topped with a chimichurri crema, cotija cheese, and pico de gallo. Served in a warm flour tortilla. Grilled chicken +4 | Pulled pork +4 | Strip steak +8 | Shrimp +8')
        
        self.create_item(category, 'Santa Fe Chicken Wrap', 19,
            'Grilled chicken, shredded romaine lettuce, pico de gallo, roasted red peppers, fire roasted corn, pepperjack cheese, and smokey ranch dressing')
        
        self.create_item(category, 'SoHo Veggie Wrap', 17,
            'Arugula, tomato, shredded carrots, roasted red peppers, cucumbers, red onions, pepper chutney, and pepperjack cheese',
            dietary_type='vegetarian', is_dairy_free=False)
        
        self.create_item(category, 'Club Wrap', 19,
            'Smoked ham, turkey, bacon, shredded romaine lettuce, tomatoes, garlic aioli, and Swiss cheese')

    def load_sandwiches(self):
        category = self.create_category(
            'Sandwiches',
            'Signature sandwiches served with your choice of side',
            order=4
        )
        
        self.create_item(category, 'Green Goddess Ciabatta', 18,
            'Grilled marinated zucchini, arugula, tomato, red onion, cucumber, caramelized onions, balsamic drizzle, and pepperjack cheese. Served on a toasted ciabatta bun with a queen olive',
            dietary_type='vegetarian')
        
        self.create_item(category, 'Pulled Pork Sandwich', 19,
            'House-smoked BBQ pulled pork topped with smoked cheddar cheese, onion rings, and jalapeños. Served on a toasted brioche bun',
            is_featured=True)
        
        self.create_item(category, 'Pub Fish Sandwich', 20,
            'Beer-battered haddock served on a brioche bun with homemade tartar sauce. Cheese +2')
        
        self.create_item(category, 'Steak & Cheese', 20,
            'Philly steak with sautéed peppers & onions, topped with white American cheese and served on a steamed hoagie roll. Mushrooms +2 | Lettuce, tomato, and onion +2')
        
        self.create_item(category, 'Grilled Chicken Sandwich', 19,
            'Marinated grilled chicken breast with your choice of cheese. Served on a toasted brioche bun and topped with lettuce, tomato, onion, and pickle. Bacon +2')
        
        self.create_item(category, 'Reuben', 19,
            'Corned beef, Swiss cheese, sauerkraut, and homemade thousand island dressing. Served on toasted rye bread')
        
        self.create_item(category, 'Rachel', 19,
            'Smoked turkey breast, Swiss cheese, coleslaw, and homemade thousand island dressing. Served on grilled rye bread')
        
        self.create_item(category, 'Hot Sausage Sandwich', 19,
            'Hot Italian sausage cooked with peppers & onions in a classic tomato sauce. Topped with provolone cheese and served on a hoagie roll')
        
        self.create_item(category, 'Pittsburgh Lasagna', 20,
            "SoHo's original handheld lasagna with meat sauce and vine-ripened tomatoes, topped with mozzarella cheese, sandwiched between grilled garlic toast",
            is_chef_special=True)
        
        self.create_item(category, 'SoHo Super Dogs', 16,
            "Two Nathan's famous all-beef hot dogs topped with American cheese and sliced bacon. Chili +2")

    def load_burgers(self):
        category = self.create_category(
            'Burgers',
            'Half-pound burgers served with your choice of side',
            order=5
        )
        
        self.create_item(category, 'Cheeseburger', 19,
            'Half-pound burger served with your choice of cheese. Topped with lettuce, tomato, onion, and pickle. Bacon +2')
        
        self.create_item(category, 'Black & Blue Burger', 20,
            'Half-pound blackened burger, blue cheese crumbles, and bacon. Topped with lettuce, tomato, and onion')
        
        self.create_item(category, 'Western BBQ Burger', 20,
            'Half-pound burger covered with BBQ sauce, smoked cheddar cheese, bacon, and onion rings. Topped with lettuce and tomato. Top with BBQ pulled pork +2')
        
        self.create_item(category, 'Mushroom Swiss Burger', 20,
            'Half-pound burger, mushrooms, caramelized onions, and Swiss cheese. Topped with lettuce and tomato')
        
        self.create_item(category, 'Smash Burger', 19,
            'Two smashed beef patties, topped with white American cheese, dill pickles, caramelized onions, and drizzled with housemade thousand island dressing')
        
        self.create_item(category, 'Impossible Burger', 19,
            'Impossible burger with caramelized onions. Topped with lettuce, tomato, and pickle. Cheese +2',
            dietary_type='vegan')

    def load_pizzas(self):
        category = self.create_category(
            'Pizza',
            'All pizzas are baked on our homemade pizza dough',
            order=6
        )
        
        self.create_item(category, 'Cheese Pizza', 18,
            'Homemade red sauce, mozzarella, provolone, and parmesan cheese',
            dietary_type='vegetarian')
        
        self.create_item(category, 'Buffalo Chicken Pizza', 20,
            'Buffalo grilled chicken, buffalo ranch sauce, with mozzarella and cheddar cheese. Drizzled with ranch')
        
        self.create_item(category, 'BBQ Chicken Pizza', 20,
            'Grilled chicken, sweet BBQ sauce, and mozzarella. Topped with bacon and green onions')
        
        self.create_item(category, 'Meat Lovers Pizza', 24,
            'Homemade red sauce, four cheese blend, pepperoni, hot sausage, bacon, and ham')

    def load_entrees(self):
        category = self.create_category(
            'Entrées',
            'Signature dinner entrées',
            order=7
        )
        
        self.create_item(category, 'Pasta Primavera', 18,
            'Lightly sautéed peppers, onions, mushrooms, and roasted tomatoes. Tossed in a garlic white wine sauce, and served over farfalle pasta. **Lunch portions available until 2PM',
            dietary_type='vegetarian')
        
        self.create_item(category, 'Chicken Parmesan', 20,
            'Hand-breaded chicken tenderloins over linguini. Topped with homemade marinara and melted provolone cheese',
            is_featured=True)
        
        self.create_item(category, 'Creamy Mushroom Marsala', 20,
            'Pan-seared chicken tenderloins served over farfalle pasta and tossed in our creamy mushroom marsala sauce')
        
        self.create_item(category, 'Bourbon Glazed Salmon', 24,
            'Pan-seared salmon topped with our signature brown sugar bourbon glaze. Served over rice pilaf with steamed broccoli and garlic butter',
            is_featured=True)
        
        self.create_item(category, 'Shrimp Scampi', 23,
            'Lightly floured shrimp sautéed in a rich garlic-butter sauce with a touch of white wine and fresh lemon. Tossed with linguini and finished with parmesan and parsley',
            contains_shellfish=True)
        
        self.create_item(category, 'Smokey Pork Chop', 25,
            'One-inch thick 10 oz bone-in grilled pork chop topped with our sweet and smokey BBQ glaze. Served with mashed potatoes and sautéed green beans')
        
        self.create_item(category, 'Guiltless Chicken', 19,
            'Grilled marinated chicken, roasted tomatoes, rice pilaf, and green beans')
        
        self.create_item(category, 'Pittsburgh Pierogies', 25,
            'Locally sourced pierogies topped with caramelized onions, kielbasa, and broccoli. Served with sour cream and scallions')
        
        self.create_item(category, 'Fish & Chips', 23,
            'Beer-battered haddock on a bed of french fries. Served with coleslaw and homemade tartar sauce')
        
        self.create_item(category, 'Grilled New York Strip', 35,
            '12 oz New York strip grilled to perfection. Served with creamy mashed potatoes and broccoli. Sautéed mushrooms & onions +4 | Shrimp +8',
            is_chef_special=True)

    def load_sides(self):
        category = self.create_category(
            'Sides',
            'Side dishes and add-ons',
            order=8
        )
        
        self.create_item(category, 'French Fries', 7, 'Crispy french fries')
        self.create_item(category, 'Cajun Fries', 7, 'Seasoned cajun fries')
        self.create_item(category, 'Tater Tots', 7, 'Crispy tater tots')
        self.create_item(category, 'Cajun Tots', 7, 'Seasoned cajun tots')
        self.create_item(category, 'Onion Rings', 7, 'Beer-battered onion rings')
        self.create_item(category, 'Coleslaw', 7, 'Homemade coleslaw')
        self.create_item(category, 'Black Bean Salsa', 7, 'Fresh black bean salsa')
        self.create_item(category, 'Caesar Side Salad', 7, 'Small Caesar salad')
        self.create_item(category, "Chef's Vegetables", 7, 'Seasonal vegetables')
        self.create_item(category, 'Tortilla Chips', 7, 'House-fried tortilla chips')
        self.create_item(category, 'Rice Pilaf', 7, 'Seasoned rice pilaf')
        self.create_item(category, 'Mashed Potatoes with Gravy', 8, 'Creamy mashed potatoes with gravy')
        self.create_item(category, 'Gravy Fries', 8, 'French fries with gravy')

    def load_beverages(self):
        category = self.create_category(
            'Beverages',
            'Soft drinks and beverages',
            order=9
        )
        
        self.create_item(category, 'Fountain Drinks', 4,
            'Coca-Cola, Diet Coke, Coke Zero, Cherry Coke, Sprite, Dr. Pepper, Lemonade, Ginger Ale, Unsweetened Iced Tea, Arnold Palmer - Unlimited refills')

    def load_kids_menu(self):
        category = self.create_category(
            'Kids Menu',
            'For children 12 & under. Served with your choice of broccoli, fries, or tots',
            order=10
        )
        
        self.create_item(category, "I Don't Know (Mac & Cheese)", 10,
            'Macaroni and cheese')
        
        self.create_item(category, "I'm Not Hungry (Chicken Tenders)", 10,
            'Two chicken tenders')
        
        self.create_item(category, "I Want to Go to McDonald's (Kids Burger)", 10,
            'Kids burger')
        
        self.create_item(category, "I Don't Care (Pasta)", 10,
            'Penne pasta mixed with butter or red sauce')
        
        self.create_item(category, "I Want to Go Home (Grilled Cheese)", 10,
            'Grilled American cheese on sourdough bread',
            dietary_type='vegetarian')
        
        self.create_item(category, 'Nothing (Hot Dog)', 10,
            'Angus beef hotdog')

    def load_desserts(self):
        category = self.create_category(
            'Desserts',
            'Sweet endings to your meal',
            order=11
        )
        
        self.create_item(category, 'Seasonal Cheesecake', 10,
            "A creamy vanilla cheesecake with SoHo's seasonal topping. Ask your server about our current selections")
        
        self.create_item(category, 'Carrot Cake', 10,
            'Two layers of soft carrot cake iced with cream cheese icing and rimmed with walnuts',
            dietary_type='vegetarian')
        
        self.create_item(category, 'Brownie Sundae', 10,
            'Our house-made brownie served warm and topped with vanilla ice cream, drizzled with chocolate sauce - perfect to share',
            is_featured=True)
        
        self.create_item(category, 'Chocolate Torte', 9,
            'This flourless chocolate torte is made with a blend of four chocolates and finished with a ganache topping, raspberry sauce, and whipped cream',
            is_gluten_free=True)
        
        self.create_item(category, 'Oreo Cream Pie', 8,
            'A fluffy whipped cream filling infused with Oreo pieces in a chocolate cookie crust',
            dietary_type='vegetarian')
