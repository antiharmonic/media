#!/usr/bin/env python

from flask import Flask, Response, Blueprint, g, redirect, url_for, request, abort, render_template
import records
import json
import re
from datetime import date, timedelta, datetime, time
from configparser import ConfigParser, ExtendedInterpolation
import requests
import os
from imdb import Cinemagoer
from jinja2 import Environment
from jinja2_pluralize import pluralize
from sqlalchemy.exc import ResourceClosedError

cfg = ConfigParser(interpolation=ExtendedInterpolation())
configfile=os.environ.get('APP_CONFIG_FILE', default='config.ini')
cfg.read(configfile)
settings = dict(cfg.items('database'))
db = None

def app_start():
  global db
  try:
    db = records.Database("postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}".format(**settings), pool_size=50)
    print(db)
  except Exception as e:
    raise e

  return Flask(__name__)
app = app_start()
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.filters['pluralize'] = pluralize

api = Blueprint('action_only_endpoints', __name__, url_prefix='/api')
header_translation = {
  'title': 'Title',
  'begin_date': 'Begin Date',
  'end_date': 'Finish Date',
  'subsection': 'Subsection',
  'rating': 'Rating',
  'media_type_name': 'Type',
  'length': 'Length',
  'comments': 'Comments'
}

min_year = 1986
max_year = 2100

type_unit = {
  '1': 1,
  '2': 2,
  '4': 1,
  '6': 2,
  '3': 2,
  '7': 2,
  '8': 2,
  '9': 2,
  '10': 1,
  '11': 2,
  '12': 2,
  '13': 2,
  '14': 2
}

@app.before_request
def get_db():
  if hasattr(g, 'db') == False or g.db is None or g.db.open == False:
    g.db = db.get_connection()
  g.today_str = str(date.today())
  g.year_ago_str = str(date.today()-timedelta(days=365))
  g.current_year = str(date.today().year)

@app.after_request
def close_handle(response):
  g.db.close()
  return response

## View endpoints
@app.route("/")
def view_root():
  default_list=list_media(limit=20)
  return render_template('root.html', media=default_list, cols=['title', 'begin_date', 'end_date', 'rating', 'media_type_name'], headers=header_translation)

@app.route("/media/<id>")
def media_details(id):
  pass

@app.route("/view/<id>", endpoint='view_route')
@app.route("/update/<id>")
@app.route("/edit/<id>")
@app.route("/create")
def view_create_page(id=None):
  if id:
    try:
      media = g.db.query("select * from media left join media_integration_data on media_id = media.id where id = :id", id=id).first().as_dict()
      if media['length'] and media['length'].is_integer():
        media['length'] = int(media['length'])
    except:
      media = None
  else:
    media = None

  types = g.db.query("select * from media_type order by id").as_dict()
  units = g.db.query("select * from media_length").as_dict()
  units = {u['length_unit_id']: u['name'] for u in units}

  rule = request.url_rule
  if 'view' in rule.rule:
    return render_template("view.html", media=media, types=types, units=units)

  return render_template("create_update.html", media=media, types=types, units=units)


@app.route("/search")
@app.route("/list")
def view_list_page():
  begin_date = request.args.get('begin_date', None)
  begin_date_cmp = request.args.get('begin_date_cmp', None)
  end_date = request.args.get('end_date', None)
  end_date_cmp= request.args.get('end_date_cmp', None)
  if not valid_cmp(end_date_cmp):
    end_date_cmp = '<='
  if not valid_cmp(begin_date_cmp):
    begin_date_cmp = '>='
  completed = request.args.get('completed', None)
  if completed == 'True':
    completed = True
  elif completed is not None:
    completed = False
  rating = request.args.get('rating', None)
  rating_cmp = request.args.get('rating_cmp', None)
  if not valid_cmp(rating_cmp):
    rating_cmp = '>='
  title = request.args.get('title', None)
  onhold = boolean_resolve(request.args.get('onhold', None))
  rule = request.url_rule
  started = request.args.get('started', True)
  if started == 'True':
    started = True
  elif started != True:
    started = False
  if 'search' in rule.rule:
    g.current_search = title
  media_type = request.args.get('type', None)
  try:
    media_type = int(media_type)
  except ValueError as e:
    media_type = None
  except TypeError as e:
    media_type = None
  media = list_media(type=media_type, begin_date=begin_date, end_date=end_date, rating=rating, completed=completed, title=title,
                     begin_date_cmp=begin_date_cmp, end_date_cmp=end_date_cmp, rating_cmp=rating_cmp, onhold=onhold, started=started)
  return render_template("list.html", media=media, cols=['title', 'begin_date', 'end_date', 'rating', 'media_type_name'],  headers=header_translation)


@app.route("/stats")
@app.route("/stats/<year>")
def view_stats_page(year=None):
  stats = action_stats(year)
  return render_template("stats.html", stats=stats)


# API endpoints
@api.route("/create", methods=['GET', 'POST'])
@api.route("/update", methods=['GET', 'POST'])
def action_update_media():
  fields = ['title', 'subsection', 'begin_date', 'end_date', 'new_media_integration_id', 'rating', 'length', 'comments', 'media_type', 'id']
  optional_numeric_fields = ['begin_date', 'end_date', 'rating', 'length']
  media = dict()
  for k in fields:
    media[k] = request.form.get(k, None)
    if k in optional_numeric_fields and media[k] == '':
      media[k] = None
  rule = request.url_rule
  external = 'imdb'
  print(media)
  print(integrations['ol']['media_types'])
  print(media['media_type'] in integrations['ol']['media_types'])
  if int(media['media_type']) in integrations['ol']['media_types']:
    external = 'ol'
  print(external)
  if 'create' in rule.rule:
    try:
      res = g.db.query("""insert into media (title, begin_date, end_Date, media_type, rating, subsection, length, comments, length_unit)
                                    values (:title,:begin_date,:end_date,:media_type,:rating,:subsection,:length,:comments,:length_unit) 
                                    returning id""",
                                    title=media['title'], begin_date=media['begin_date'], end_date=media['end_date'], media_type=media['media_type'],
                                    rating=media['rating'], subsection=media['subsection'], length=media['length'], comments=media['comments'],
                                    length_unit=type_unit[media['media_type']]).first().as_dict()
    except Exception as e:
      raise e
    media['id'] = res['id']
    if media['new_media_integration_id']:
      action_update_integration_data(media['id'], media['new_media_integration_id'], integrations[external])
  elif 'update' in rule.rule:
    try:
      g.db.query("""update media set title = :title, begin_date = :begin_date, end_date = :end_date, rating = :rating, subsection = :subsection,
                          length = :length, comments = :comments where id = :id""",
                                    title=media['title'], begin_date=media['begin_date'], end_date=media['end_date'], id=media['id'],
                                    rating=media['rating'], subsection=media['subsection'], length=media['length'], comments=media['comments'])
    except Exception as e:
      print(e)
      raise e
    if media['new_media_integration_id'] and media['new_media_integration_id'] != request.form.get('media_integration_id'):
      action_update_integration_data(media['id'], media['new_media_integration_id'], integrations[external])

  print(f"attempting to redirect to {url_for('view_route', id=media['id'])} with id={media['id']}")
  return redirect(url_for('view_root'))

@api.route("/rewatch")
def action_rewatch():
  pass


@api.route("/stats")
@api.route("/stats/<year>")
def action_stats(year=None):
  if year == None:
    year = g.current_year
  else:
    year = int(year)
    if year < min_year or year > max_year:
      year = g.current_year
  sql = """select mt.name, media.length_unit::integer, extract(year from end_date)::integer as "year",
            count(media.id), sum(length) from media join media_type mt on mt.id = media.media_type
            where end_date is not null and extract(year from end_date) = :year
            group by 1, 2, 3 order by 2,3 desc"""
  stats = g.db.query(sql, year=year)
  rule = request.url_rule
  if 'api' in rule.rule:
    return Response(stats.export('json'), mimetype="application/json")
  else:
    return stats.as_dict()


@api.route("/list")
@api.route("/list/<type>")
def action_list_media(type=None):
  media = list_media(type=type)
  return Response(json.dumps(media, default=json_serial), mimetype="application/json")

@api.route("/integration/imdb/search/<search_text>")
def action_search_imdb(search_text):
  return Response(json.dumps(imdb_search(search_text), default=json_serial), mimetype="application/json")
  
@api.route("/integration/imdb/get/<id>")
def action_get_imdb_media(id):
  return Response(json.dumps(imdb_info(id), default=json_serial), mimetype="application/json")

@api.route("/integration/update/<media_id>/<external_id>")
def action_update_integration_data(media_id, external_id, integration):
  media_getter = integration['get']
  external_info = media_getter(external_id)
  if 'rating' not in  external_info:
    external_info['rating'] = None
  filename=None
  if external_info['image']:
    filename = integration_image_download(external_info['image'], media_id)
    print(f"file downloaded to {filename}")
  try:
    db.query("insert into media_integration_data values (:media_id, :imdb_id, :integration_id, :rating, :cover_image, :synopsis) on conflict (media_id, media_integration_id) do update set meta_rating = :rating, cover_image = :cover_image, synopsis=:synopsis",
           media_id=media_id, imdb_id=external_id, integration_id=integration['id'], rating=external_info['rating'], cover_image=filename, synopsis=external_info['plot'])
  except Exception as e:
    print(e)
    abort(f"db error: {e}")
  return filename

@api.route("/integration/ol/get/<id>")
def action_get_ol_media(id):
  return Response(json.dumps(ol_info(id), default=json_serial), mimetype="application/json")

@api.route("/integration/ol/search/<title>")
def action_search_ol(title):
  return Response(json.dumps(ol_search(title), default=json_serial), mimetype="application/json")

@api.route("/admin/redownload_cover_images")
def action_admin_get_covers():
  "to be run upon redeployment to another location from source or during dev"
  media = db.query("select * from media_integration_data where cover_image is not null and media_integration_id = 1")
  for m in media:
    info = imdb_info(m.integration_id)
    integration_image_download(info['image'], m.media_id)
  return f"updated len(m)"

# real time validation for e.g. media creation so you don't enter a title that already exists
@api.route("/validate")
def action_validate():
  pass


# utility/common functions
# i'm guessing this will be the largest function in terms of usage/utility
def list_media(type=None, started=True, begin_date=None, begin_date_cmp=None, end_date=None, end_date_cmp=None, completed=None, years=None, limit=None, rating=None, rating_cmp=None, title=None, onhold=None):
  predicates = list()
  if type is not None and isinstance(type, str):
    type = type.lower()
    valid_types = g.db.query('select * from media_type').as_dict()
    valid_types = {t['name'].lower(): t['id'] for t in valid_types}
    if type in valid_types.keys():
      type = valid_types[type]
  if type is not None and isinstance(type, int):
      predicates.append('media_type = :type')
    # no else, if the type is in the list it will silenty fail and just include all types
  if started == True:
    predicates.append('begin_date is not null')
  elif started == False:
    predicates.append('begin_date is null')
  if begin_date:
    predicates.append(f"begin_date {begin_date_cmp} :begin_date")
  if end_date:
    predicates.append(f"end_date {end_date_cmp} :end_date")
  if completed == True:
    predicates.append("end_date is not null")
  elif completed == False:
    predicates.append("end_date is null")
  if rating:
    predicates.append(f"rating {rating_cmp} :rating")
  if title:
    predicates.append("lower(title) like '%' || lower(:title) || '%'")
  if onhold == True:
    predicates.append("onhold = true")
  elif onhold == False:
    predicates.append("onhold = false")
  sql = "select media.*, mt.name as media_type_name from media join media_type mt on mt.id = media.media_type"
  if len(predicates) >= 1:
    sql += ' where ' + ' and '.join(predicates)

  sql += ' order by begin_date desc'

  if limit:
    sql += f" limit {limit}"

  print(f"Currently running query {sql}")
  media = db.query(sql, type=type, begin_date=begin_date, end_date=end_date, completed=completed, rating=rating, title=title).as_dict()
  return media

def type_select_list():
  types = g.db.query("select * from media_type")
  str = "<select name=\"media_type\" class=\"form-control\">\n"
  for type in types:
    str += f"\t<option value=\"{type.id}\">{type.name}</option>\n"
  str += "</select>"
  return str

## Integrations
def imdb_info(id):
  ia = Cinemagoer()
  id = str(id)
  imdb_info = ia.get_movie(id)
  desired_keys = ['year', 'rating', 'cover url', 'plot', 'runtimes']
  media_info = {'title': imdb_info.get('title')}
  for k in desired_keys:
    if k in imdb_info:
      print(f"{k} is in imdb_info")
      if k == 'cover url':
        media_info['image'] = imdb_info.get('full-size cover url')
      elif k == 'plot':
        media_info[k] = imdb_info['plot'][0].split("::")[0]
      elif k == 'runtimes':
        media_info['length'] = int(imdb_info['runtimes'][0])
      else:
        media_info[k] = imdb_info.get(k)
    else:
      if k == 'cover url':
        media_info['image'] = None
      elif k == 'runtimes':
        media_info['length'] = None
      else:
        media_info[k] = None
  #media_info['integration'] = imdb_info
  return media_info

def imdb_search(s):
  ia = Cinemagoer()
  media_list = ia.search_movie(s)
  parsed_media_list = list()
  for m in media_list:
    tmp = dict()
    tmp['title'] = m.get('title')
    tmp['year']  = m.get('year')
    tmp['id'] = m.getID()
    if 'cover url' in m:
      tmp['cover'] = m.get('cover url')
    else:
      tmp['cover'] = None
    parsed_media_list.append(tmp)
  return parsed_media_list

def ol_info(olid):
  url = "https://openlibrary.org/works/" + olid + ".json"
  res = requests.get(url)
  if res.status_code != 200:
    raise Exception(f"Unable to access the OpenLibrary API: {res.text}")
  res = res.json()
  print(res)
  if 'description' not in res:
    res['description'] = 'No Description Provided'
  if not isinstance(res['description'], str):
    if 'value' not in res['description']:
      res['description'] = 'No Description provided'
    else:
      res['description'] = res['description']['value']
  media_info = {
    'title': res['title'],
    'plot': res['description']
  }
  media_info['image'] = None
  if 'covers' in res:
    try:
      media_info['image'] = 'http://covers.openlibrary.org/b/id/' + str(res['covers'][0]) + '-L.jpg'
    except Exception as e:
      print(f"Couldn't assign cover url: {e}")
  return media_info

def ol_search(title):
  url = "https://openlibrary.org/search.json?title="
  title = title.replace('&', 'and')
  title = f"\"{title}\""
  res = requests.get(url+title)
  if res.status_code == 200:
    res = res.json()
    if 'docs' in res:
      books = list()
      for book in res['docs']:
        tmp = dict()
        tmp['title'] = book['title']
        tmp['id'] = book['key'].replace('/works/', '')
        if 'first_publish_year' in book:
          tmp['year'] = book['first_publish_year']
        else:
          tmp['year'] = None
        books.append(tmp)
      return books
  return None

def integration_image_download(url, media_id):
  download_dir = "./media_app/static/images/covers/"
  filename = None
  res = requests.get(url)
  _, ext = os.path.splitext(url)
  if res.status_code == 200:
    filename = str(media_id) + ext
    with open(os.path.join(download_dir, filename), 'wb') as f:
      f.write(res.content)
  return filename


##HELPERS
def json_serial(obj):
  # """JSON serializer for objects not serializable by default json code"""
  if isinstance(obj, (datetime, date, time)):
    return obj.isoformat()
  if isinstance(obj, decimal.Decimal):
    return float(obj)
  raise TypeError ("Type %s not serializable" % type(obj))

def valid_cmp(s):
  if s is None:
    return False
  m = re.match('>|>=|=|<=|<', s)
  if m:
    return True
  else:
    return False

def boolean_resolve(s):
  if s is None:
    return None
  elif s.lower() == 'true':
    return True
  else:
    return False

integrations = {
  'imdb': {
    'search': imdb_search,
    'get': imdb_info ,
    'media_types': [2, 7, 3, 11, 13, 14],
    'id': 1
  },
  'ol': {
    'search': ol_search,
    'get': ol_info,
    'media_types': [1, 4],
    'id': 2
  }
}

app.register_blueprint(api)

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5001, debug=True)

