release: python manage.py migrate --noinput
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --access-logfile - --error-logfile -
emailworker: python manage.py email_worker
