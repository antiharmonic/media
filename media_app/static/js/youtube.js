var query_url = '/api/integration/yt/title/';

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
