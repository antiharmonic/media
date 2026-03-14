var query_url = '/api/integration/yt/title/';
var no_music_theme_types = [6, 8, 9, 12]; // Album, Podcast, Live Show, Audiobook

function update_music_theme_visibility() {
  var current_type = parseInt($('#media_type_select option:selected').val());
  if (no_music_theme_types.includes(current_type)) {
    $('#music_theme_section').hide();
  } else {
    $('#music_theme_section').show();
  }
}

$('#media_type_select').change(update_music_theme_visibility);
update_music_theme_visibility();

$('#music_theme').blur(function() {
  yt_url = $('#music_theme').val()
  if (yt_url === "") {
    $("#music_theme_title").html("");
  } else {
    $.getJSON(query_url + encodeURIComponent(yt_url), function(data) {
      console.log(data)
      if (data) {
        $('#music_theme_title').html(`<a href="${yt_url}">${data}</a>`);
      }
    });
  }
});
