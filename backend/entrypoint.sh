#!/bin/sh
set -e

python manage.py migrate --noinput

if [ "${AUTO_SEED_EXAMS:-1}" = "1" ]; then
  EXAM_COUNT=$(python manage.py shell --verbosity 0 -c "from exams.models import Exam; print(Exam.objects.count())" 2>/dev/null || echo "0")
  if [ "${AUTO_SEED_EXAMS_FORCE:-0}" = "1" ] || [ "$EXAM_COUNT" = "0" ]; then
    if ! python manage.py seed_exams; then
      echo "WARNING: seed_exams failed, continuing startup." >&2
    fi
  else
    echo "AUTO_SEED_EXAMS=1, but exams already exist ($EXAM_COUNT). Skipping seed_exams."
  fi
fi

if [ "${DJANGO_COLLECTSTATIC:-1}" = "1" ]; then
  if ! python manage.py collectstatic --noinput; then
    if [ "${COLLECTSTATIC_STRICT:-0}" = "1" ]; then
      echo "collectstatic failed and COLLECTSTATIC_STRICT=1, exiting." >&2
      exit 1
    fi
    echo "WARNING: collectstatic failed, continuing startup." >&2
  fi
fi

exec gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-60}
