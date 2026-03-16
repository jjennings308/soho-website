(function () {
  'use strict';

  function init($) {

    function getItemData(itemId, formRow) {
      if (!itemId) return;

      fetch('/menu/api/menu-item-data/' + itemId + '/')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var nameField = formRow.querySelector('input[name$="-name"]');
          var priceField = formRow.querySelector('input[name$="-promo_price"]');

          if (nameField && !nameField.value) {
            nameField.value = data.name || '';
          }
          if (priceField && !priceField.value) {
            priceField.value = data.price || '';
          }
        })
        .catch(function (err) { console.error('promo_item_autofill error:', err); });
    }

    function attachToRow(formRow) {
      var $select = $(formRow).find('select[name$="-menu_item"]');
      if (!$select.length || $select.data('promoAutofillAttached')) return;

      $select.data('promoAutofillAttached', true);

      $select.on('select2:select', function (e) {
        var itemId = e.params.data.id;
        if (itemId) {
          getItemData(itemId, formRow);
        }
      });
    }

    function attachAll() {
      document.querySelectorAll('.inline-related').forEach(function (row) {
        attachToRow(row);
      });
    }

    $(document).ready(function () {
      attachAll();

      $(document).on('formset:added', function (event, $row) {
        if ($row && $row[0]) {
          attachToRow($row[0]);
        }
      });
    });
  }

  // Wait for django.jQuery to be available
  document.addEventListener('DOMContentLoaded', function () {
    if (typeof django !== 'undefined' && django.jQuery) {
      init(django.jQuery);
    } else {
      // Fallback: poll briefly in case django.jQuery loads slightly after DOMContentLoaded
      var attempts = 0;
      var interval = setInterval(function () {
        attempts++;
        if (typeof django !== 'undefined' && django.jQuery) {
          clearInterval(interval);
          init(django.jQuery);
        } else if (attempts > 20) {
          clearInterval(interval);
          console.warn('promo_item_autofill: django.jQuery not found.');
        }
      }, 50);
    }
  });

})();