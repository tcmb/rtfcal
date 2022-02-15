import multiprocessing

bind = ['127.0.0.1:8001']
workers = multiprocessing.cpu_count() + 1
wsgi_app = 'application:app'
accesslog = '/home/flo/rtfcal/gunicorn_access.log'
access_log_format = '%(h)s %({X-Real-IP}i)s %({X-Forwarded-For}i)s %({X-Forwarded-Host}i)s %(l)s %(t)s %(m)s "%(r)s" ' \
                    '%(U)s %(q)s %(s)s %(b)s "%(f)s" "%(a)s" %(M)s'
errorlog = '/home/flo/rtfcal/gunicorn_error.log'
loglevel = 'info'
chdir = '/home/flo/rtfcal'
