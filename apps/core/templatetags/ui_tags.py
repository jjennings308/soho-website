from django import template
register = template.Library()

@register.inclusion_tag('core/components/button.html')
def render_button(button):
    if isinstance(button, dict):
        return {
            'label': button.get('label', ''),
            'href': button.get('href', '#'),
            'bg_color': button.get('bg_color', 'bg-yellow-500'),
            'text_color': button.get('text_color', 'text-black'),
        }
    return {
        'label': getattr(button, 'label', ''),
        'href': getattr(button, 'href', '#'),
        'bg_color': getattr(button, 'bg_color', 'bg-yellow-500'),
        'text_color': getattr(button, 'text_color', 'text-black'),
    }

#@register.inclusion_tag('core/components/button.html')
#def render_button(label, href='#', bg_color='bg-yellow-500', text_color='text-black'):
#    return {
#        'label': label,
#        'href': href,
#        'bg_color': bg_color,
#        'text_color': text_color,
#    }

