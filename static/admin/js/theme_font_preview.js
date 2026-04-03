document.addEventListener('DOMContentLoaded', function () {

    const GOOGLE_FONTS_MAP = {
        '"Playfair Display", serif':        'Playfair+Display:ital,wght@0,400;0,600',
        '"Cormorant Garamond", serif':      'Cormorant+Garamond:ital,wght@0,300;0,400;0,600',
        '"Libre Baskerville", serif':       'Libre+Baskerville:ital,wght@0,400;0,700',
        '"Inter", sans-serif':              'Inter:wght@300;400;500;600',
        '"Lato", sans-serif':               'Lato:wght@0,300;0,400;0,700',
        '"Montserrat", sans-serif':         'Montserrat:wght@300;400;500;600',
        '"Open Sans", sans-serif':          'Open+Sans:wght@0,300;0,400;0,600',
        '"Cinzel", serif':                  'Cinzel:wght@400;600',
        '"Oswald", sans-serif':             'Oswald:wght@300;400;500',
        '"Raleway", sans-serif':            'Raleway:wght@300;400;500;600',
        '"Playwrite IE", sans-serif':  'Playwrite+IE:wght@100;200;300;400',
    };

    const loadedFonts = new Set();

    function ensureFontLoaded(fontValue) {
        const param = GOOGLE_FONTS_MAP[fontValue];
        if (!param || loadedFonts.has(param)) return;
        loadedFonts.add(param);
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `https://fonts.googleapis.com/css2?family=${param}&display=swap`;
        document.head.appendChild(link);
    }

    function updatePreview(select, preview) {
        const val = select.value;
        if (!val) {
            preview.textContent = '';
            return;
        }
        ensureFontLoaded(val);
        preview.style.fontFamily = val;
        preview.style.fontWeight = '400';  // add this line
        preview.textContent = 'The quick brown fox jumps over the lazy dog';
    }

    // Target the three font selects by their field name
    ['primary_font', 'secondary_font', 'accent_font'].forEach(function (fieldName) {
        const select = document.getElementById('id_' + fieldName);
        if (!select) return;

        // Insert preview span after the select
        const preview = document.createElement('span');
        preview.style.cssText = [
            'display: inline-block',
            'margin-left: 12px',
            'margin-top: 6px',
            'font-size: 1.1rem',
            'color: #333',
            'min-height: 1.5em',
            'transition: font-family 0.2s',
        ].join(';');

        select.parentNode.insertBefore(preview, select.nextSibling);

        // Set initial state and listen for changes
        updatePreview(select, preview);
        select.addEventListener('change', function () {
            updatePreview(select, preview);
        });
    });
});