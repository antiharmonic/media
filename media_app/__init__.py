#!/usr/bin/env python

from flask import Flask, Response, Blueprint, g, redirect, url_for, request, abort, render_template
import records
import json
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


@app.before_request
def get_db():
  g.db = db.get_connection()


## View endpoints
@app.route("/")
def view_root():
  default_list=list_media(limit=10)
  return render_template('base.html', list=default_list)

@app.route("/media/<id>")
def media_details(id):
  pass

@app.route("/create", methods=["GET"])
def view_create_page():
  pass

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


# utility/common functions
# i'm guessing this will be the largest function in terms of usage/utility
def list_media(type=None, started=True, begin_date=None, begin_date_cmp=None, end_date=None, end_date_cmp=None, completed=None, years=None, limit=None):
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
  sql = "select * from media"
  if len(predicates) >= 1:
    sql += ' where ' + ' and '.join(predicates)

  sql += ' order by begin_date desc'

  if limit:
    sql += f" limit {limit}"


  media = db.query(sql, type=type, begin_date=begin_date, end_date=end_date, completed=completed).as_dict()
  return media

##HELPERS
def json_serial(obj):
  # """JSON serializer for objects not serializable by default json code"""
  if isinstance(obj, (datetime, date, time)):
    return obj.isoformat()
  if isinstance(obj, decimal.Decimal):
    return float(obj)
  raise TypeError ("Type %s not serializable" % type(obj))

app.register_blueprint(api)

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5001, debug=True)
