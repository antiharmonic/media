#!/bin/bash
PORT=5001
HOST=0.0.0.0
WORKERS=1
LOGFILE=media-app-access.log
ERRORFILE=media-app-error.log
FLASK_APP=media_app

gunicorn $FLASK_APP:app --workers $WORKERS --bind=$HOST:$PORT -access-logfile "$LOGFILE" --error-logfile "$ERRORFILE" #--daemon <- removed since this is for testing now
