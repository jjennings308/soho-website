from django import template
register = template.Library()

@register.inclusion_tag('core/components/button.html')
def render_button(label, href='#', bg_color='bg-yellow-500', text_color='text-black'):
    return {
        'label': label,
        'href': href,
        'bg_color': bg_color,
        'text_color': text_color,
    }