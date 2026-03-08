from django.db import migrations, models
import django.db.models.deletion
import django_ckeditor_5.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContentSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(
                    max_length=100,
                    unique=True,
                    help_text="Machine name used in templates: {% get_active_block 'about_header' %}"
                )),
                ('label', models.CharField(
                    max_length=200,
                    help_text='Human-readable name shown in admin'
                )),
                ('description', models.TextField(
                    blank=True,
                    help_text='Optional hint for editors about where/how this content is used'
                )),
            ],
            options={
                'verbose_name': 'Content Slot',
                'verbose_name_plural': 'Content Slots',
                'ordering': ['slug'],
            },
        ),
        migrations.CreateModel(
            name='ContentBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slot', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='blocks',
                    to='content.contentslot'
                )),
                ('label', models.CharField(
                    blank=True,
                    max_length=200,
                    help_text="Internal label to distinguish versions, e.g. 'Summer 2025' or 'Original'"
                )),
                ('body', django_ckeditor_5.fields.CKEditor5Field(
                    blank=True,
                    help_text='Rich text content. Leave blank if this block is image-only.'
                )),
                ('image', models.ImageField(
                    blank=True,
                    null=True,
                    upload_to='content/blocks/',
                    help_text='Optional image. Leave blank if this block is text-only.'
                )),
                ('is_active', models.BooleanField(
                    default=False,
                    help_text='Only one block per slot can be active. Activating this will deactivate others.'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Content Block',
                'verbose_name_plural': 'Content Blocks',
                'ordering': ['-updated_at'],
            },
        ),
    ]
