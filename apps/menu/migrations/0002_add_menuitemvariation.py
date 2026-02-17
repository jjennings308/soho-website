# Generated migration file for adding MenuItemVariation model
# Place this in: <your_app>/migrations/0002_add_menuitemvariation.py

from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0001_initial'),  # Adjust to your last migration
    ]

    operations = [
        migrations.AddField(
            model_name='menuitem',
            name='has_variations',
            field=models.BooleanField(default=False, help_text='Check if this item has multiple size/quantity options'),
        ),
        migrations.AlterField(
            model_name='menuitem',
            name='price',
            field=models.DecimalField(decimal_places=2, help_text='Base price or price for standard size', max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.CreateModel(
            name='MenuItemVariation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Variation name (e.g., 'Small', 'Large', '6 Wings', '12 Wings')", max_length=100)),
                ('description', models.CharField(blank=True, help_text='Optional description of this variation', max_length=200)),
                ('price', models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('quantity', models.PositiveIntegerField(blank=True, help_text='Quantity/count for this variation (e.g., 6, 12, 30)', null=True)),
                ('size', models.CharField(blank=True, help_text="Size descriptor (e.g., 'Small', 'Medium', 'Large', 'Cup', 'Bowl')", max_length=50)),
                ('order', models.PositiveIntegerField(default=0, help_text='Display order (lower numbers first)')),
                ('is_default', models.BooleanField(default=False, help_text='Is this the default/recommended option?')),
                ('is_available', models.BooleanField(default=True, help_text='Is this variation currently available?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('menu_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variations', to='menu.menuitem')),
            ],
            options={
                'verbose_name': 'Menu Item Variation',
                'verbose_name_plural': 'Menu Item Variations',
                'ordering': ['order', 'price'],
                'unique_together': {('menu_item', 'name')},
            },
        ),
    ]
