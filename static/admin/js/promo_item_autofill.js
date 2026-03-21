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

      $select.on('change', function () {
        var itemId = $(this).val();
        if (!itemId) return;

        var row = $(this).closest('.inline-related');

        fetch('/menu/api/menu-item-data/' + itemId + '/')
          .then(function (r) { return r.json(); })
          .then(function (data) {
            var nameField = row.find('input[name$="-name"]')[0];
            var priceField = row.find('input[name$="-promo_price"]')[0];

            if (nameField && !nameField.value) {
              nameField.value = data.name || '';
            }
            if (priceField && !priceField.value) {
              priceField.value = data.price || '';
            }
          })
          .catch(function (err) { console.error('promo_item_autofill error:', err); });
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
          setTimeout(function () {
            attachToRow($row[0]);
          }, 0);
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (typeof django !== 'undefined' && django.jQuery) {
      init(django.jQuery);
    } else {
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