this_script = $(document.currentScript);
this_integration = 1;
title = this_script.attr('data-title');
imdb_types = [2, 7, 3, 11, 13, 14]; //ew hardcoding, but i'm too lazy to make an endpoint and convert this to a when()
ol_types = [1, 4];
var local_data;
orig_title = $('#media_title').val();
var current_type = parseInt($('#media_type_select option:selected').val());
var orig_integration = $('#current_integration_id').val();
var orig_integration_id = $('#media_integration_id').val();

$('#media_type_select').change(function() {
  current_type = parseInt($('#media_type_select option:selected').val());
});

$('#media_title').blur(function() {
  changed_title = $('#media_title').val();
  if (orig_title != changed_title && (imdb_types.includes(current_type) || ol_types.includes(current_type))) {
    display_dropdown(changed_title);
  }
});

if (title && title != '' && (imdb_types.includes(current_type) || ol_types.includes(current_type))) {
  display_dropdown(title);
}

function display_dropdown(title) {
search_url = '/api/integration/imdb/search/';
if (ol_types.includes(current_type)) {
  search_url = '/api/integration/ol/search/';
}

$.getJSON(search_url + title, function(data) {
  var html = "<div><select id=\"integration_select\">\n<option></option>";
  local_data = {};
  $.each( data, function(idx, ele) {
    title_str = ele.title;
    if (ele.year) {
      title_str += " (" + ele.year + ")";
    }
    html += `<option value="${ele.id}">${title_str}</option>\n`;
    local_data[ele.id] = {'title': ele.title, 'image': ele.cover, 'year': ele.year};
   });
   html += '</select></div><div id="integration_details"><div id="integration_image"></div><div id="integration_plot"></div></div>';
  $('#integration').html(html);
  $('#integration_select').change(function() {
    selected_id = $('#integration_select option:selected').val();
    if (selected_id) {
      $('#integration_plot').html('Loading...');
      update_details(selected_id);
    } else {
      $('#integration_details #integration_image').html('');
      $('#integration_details #integration_plot').html('');
    }
  });
  if (title == orig_title && orig_integration_id != '') {
    $('#integration_select').val(orig_integration_id).change();
  }
});
}

function update_details(id, div_id) {
  div_id = div_id ? div_id : '#integration_details';
  console.log(orig_integration_id);
  console.log(id);
  if (orig_integration_id == id) {
    $('#new_media_integration_id').val(null);
    $(`${div_id} #integration_image`).html('<img src="/static/images/covers/' + $('#media_integration_image_url').val() + '" height="400">');
    $(`${div_id} #integration_plot`).html($('#media_integration_plot').val());
  } else {
    $('#new_media_integration_id').val(id);
    detail_url = '/api/integration/imdb/get/';
    if (ol_types.includes(current_type)) {
      detail_url = '/api/integration/ol/get/';
    }
    $.getJSON(detail_url + id, function(data) {
      $(`${div_id} #integration_image`).html(`<img src="${data.image}" height="400">`);
      $(`${div_id} #integration_plot`).html(data.plot);
    });
  }
}
