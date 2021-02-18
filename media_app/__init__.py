#!/usr/bin/env python

from flask import Flask, Response, Blueprint, g, redirect, url_for, request, abort, render_template
import records
import json
import re
from datetime import date, timedelta, datetime, time
from configparser import ConfigParser, ExtendedInterpolation

cfg = ConfigParser(interpolation=ExtendedInterpolation())
cfg.read('config.ini')
settings = dict(cfg.items('database'))
db = None

def app_start():
  global db
  try:
    db = records.Database("postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}".format(**settings), pool_size=10)
    print(db)
  except Exception as e:
    raise e

  return Flask(__name__)

app = app_start()
app.config['TEMPLATES_AUTO_RELOAD'] = True
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

@app.before_request
def get_db():
  g.db = db.get_connection()
  g.today_str = str(date.today()-timedelta(days=365))

## View endpoints
@app.route("/")
def view_root():
  default_list=list_media(limit=20)
  return render_template('root.html', media=default_list, cols=['title', 'begin_date', 'end_date', 'rating', 'media_type_name'], headers=header_translation)

@app.route("/media/<id>")
def media_details(id):
  pass

@app.route("/update/<id>")
@app.route("/edit/<id>")
@app.route("/create")
def view_create_page(id=None):
  if id:
    try:
      media = g.db.query("select * from media where id = :id", id=id).first().as_dict()
      if media['length'] and media['length'].is_integer():
        media['length'] = int(media['length'])
    except:
      media = None
  else:
    media = None

  types = g.db.query("select * from media_type order by id").as_dict()
  units = g.db.query("select * from media_length").as_dict()
  units = {u['length_unit_id']: u['name'] for u in units}

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
  completed = request.args.get('completed', True)
  if completed == 'False':
    completed = False
  else:
    completed = True
  rating = request.args.get('rating', None)
  rating_cmp = request.args.get('rating_cmp', None)
  if not valid_cmp(rating_cmp):
    rating_cmp = '>='
  title = request.args.get('title', None)
  rule = request.url_rule
  if 'search' in rule.rule:
    g.current_search = title
  media = list_media(begin_date=begin_date, end_date=end_date, rating=rating, completed=completed, title=title,
                     begin_date_cmp=begin_date_cmp, end_date_cmp=end_date_cmp, rating_cmp=rating_cmp)
  return render_template("list.html", media=media, cols=['title', 'begin_date', 'end_date', 'rating', 'media_type_name'],  headers=header_translation)

# API endpoints
@api.route("/create")
def action_create_media():
  pass

@api.route("/update")
def action_update_media():
  pass

@api.route("/rewatch")
def action_rewatch():
  pass

@api.route("/list")
@api.route("/list/<type>")
def action_list_media(type=None):
  media = list_media(type=type)
  return Response(json.dumps(media, default=json_serial), mimetype="application/json")


# real time validation for e.g. media creation so you don't enter a title that already exists
@api.route("/validate")
def action_validate():
  pass


# utility/common functions
# i'm guessing this will be the largest function in terms of usage/utility
def list_media(type=None, started=True, begin_date=None, begin_date_cmp=None, end_date=None, end_date_cmp=None, completed=None, years=None, limit=None, rating=None, rating_cmp=None, title=None):
  predicates = list()
  if type is not None:
    type = type.lower()
    valid_types = g.db.query('select * from media_type').as_dict()
    valid_types = {t['name'].lower(): t['id'] for t in valid_types}
    if type in valid_types.keys():
      type = valid_types[type]
      predicates.append('media_type = :type')
    # no else, if the type is in the list it will silenty fail and just include all types
  if started:
    predicates.append('begin_date is not null')
  if begin_date:
    predicates.append(f"begin_date {begin_date_cmp} :begin_date")
  if end_date:
    predicates.append(f"end_date {end_date_cmp} :end_date")
  if completed:
    predicates.append("end_date is not null")
  if rating:
    predicates.append(f"rating {rating_cmp} :rating")
  if title:
    predicates.append("lower(title) like '%' || lower(:title) || '%'")
  sql = "select media.*, mt.name as media_type_name from media join media_type mt on mt.id = media.media_type"
  if len(predicates) >= 1:
    sql += ' where ' + ' and '.join(predicates)

  sql += ' order by begin_date desc'

  if limit:
    sql += f" limit {limit}"


  media = db.query(sql, type=type, begin_date=begin_date, end_date=end_date, completed=completed, rating=rating, title=title).as_dict()
  return media

def type_select_list():
  types = g.db.query("select * from media_type")
  str = "<select name=\"media_type\" class=\"form-control\">\n"
  for type in types:
    str += f"\t<option value=\"{type.id}\">{type.name}</option>\n"
  str += "</select>"
  return str

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


app.register_blueprint(api)

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5001, debug=True)
