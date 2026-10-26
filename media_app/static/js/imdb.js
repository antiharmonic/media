this_script = $(document.currentScript);
title = this_script.attr('data-title');
imdb_types = [2, 7, 3, 11, 13, 14];
ol_types = [1, 4];
var local_data;
orig_title = $('#media_title').val();
var current_type = parseInt($('#media_type_select option:selected').val());
var orig_integration_id = $('#media_integration_id').val();
var integration_loaded = false;

function update_toggle_visibility() {
  if (imdb_types.includes(current_type) || ol_types.includes(current_type)) {
    $('#integration_toggle').show();
  } else {
    $('#integration_toggle').hide();
    $('#integration').hide();
    integration_loaded = false;
  }
}

$('#media_type_select').change(function() {
  current_type = parseInt($('#media_type_select option:selected').val());
  integration_loaded = false;
  update_toggle_visibility();
});

$('#integration_toggle').click(function() {
  var $panel = $('#integration');
  if ($panel.is(':visible')) {
    $panel.hide();
  } else {
    $panel.show();
    if (!integration_loaded) {
      display_dropdown($('#media_title').val());
      integration_loaded = true;
    }
  }
});

update_toggle_visibility();

function display_dropdown(search_title) {
  search_url = '/api/integration/imdb/search/';
  if (ol_types.includes(current_type)) {
    search_url = '/api/integration/ol/search/';
  }

  $('#integration').html('<p class="text-muted small mt-2">Searching...</p>');

  $.getJSON(search_url + encodeURIComponent(search_title), function(data) {
    var escaped_title = $('<div>').text(search_title).html();
    var html = `<div class="d-flex gap-1 mb-2 mt-1">
      <input type="text" id="integration_search_input" class="form-control form-control-sm" value="${escaped_title}">
      <button type="button" class="btn btn-outline-secondary btn-sm" id="integration_search_btn">Search</button>
    </div>`;
    html += '<select id="integration_select" class="form-select form-select-sm mb-2"><option></option>';
    local_data = {};
    $.each(data, function(idx, ele) {
      var title_str = ele.title;
      if (ele.year) { title_str += ' (' + ele.year + ')'; }
      html += `<option value="${ele.id}">${title_str}</option>`;
      local_data[ele.id] = {title: ele.title, image: ele.cover, year: ele.year};
    });
    html += '</select><div id="integration_details"><div id="integration_image"></div><div id="integration_plot"></div></div>';
    $('#integration').html(html);

    $('#integration_search_btn').click(function() {
      integration_loaded = true;
      display_dropdown($('#integration_search_input').val());
    });

    $('#integration_search_input').keydown(function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        integration_loaded = true;
        display_dropdown($(this).val());
      }
    });

    $('#integration_select').change(function() {
      var selected_id = $('#integration_select option:selected').val();
      if (selected_id) {
        $('#integration_plot').html('Loading...');
        update_details(selected_id);
      } else {
        $('#integration_details #integration_image').html('');
        $('#integration_details #integration_plot').html('');
      }
    });

    if (search_title == orig_title && orig_integration_id != '') {
      $('#integration_select').val(orig_integration_id).change();
    }
  });
}

function update_details(id, div_id) {
  div_id = div_id ? div_id : '#integration_details';
  var existing_image = $('#media_integration_image_url').val();
  if (orig_integration_id == id && existing_image) {
    // Same integration, image already downloaded — use cache
    $('#new_media_integration_id').val(null);
    $(`${div_id} #integration_image`).html('<img src="/static/images/covers/' + existing_image + '" height="400">');
    $(`${div_id} #integration_plot`).html($('#media_integration_plot').val());
  } else {
    // New selection, or same selection but no cached image — fetch fresh
    $('#new_media_integration_id').val(id);
    var detail_url = ol_types.includes(current_type) ? '/api/integration/ol/get/' : '/api/integration/imdb/get/';
    $.getJSON(detail_url + id, function(data) {
      if (data['image']) {
        $(`${div_id} #integration_image`).html(`<img src="${data.image}" height="400">`);
      }
      $(`${div_id} #integration_plot`).html(data.plot);
      if (!orig_integration_id && data.length) {
        $('#media_length').val(data.length);
      }
    });
  }
}
