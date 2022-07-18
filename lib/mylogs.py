import logging
import os
from logging import handlers
import os
import time
import datetime
from lib.helper import main_dir
from dateutil import parser
import shutil


# 实现logger单例，避免多次make_logger, 导致日志重复打印
logger_dict = {}
log_dir = os.path.join(main_dir, 'logs')


def make_logger(name):
    if name in logger_dict:
        return logger_dict[name]

    today = datetime.datetime.now().strftime(r'%Y-%m-%d')
    file_name = os.path.join(log_dir, name + '_' + today + '.log')

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # fh = handlers.RotatingFileHandler(filename, mode='a', maxBytes=5*1024*1024, backupCount=3)
    fh = handlers.TimedRotatingFileHandler(
        file_name, when='D', interval=1, backupCount=7)
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s   %(levelname)s   %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger_dict[name] = logger
    return logger


def clean_old_logs(keep_day=3):
    today = datetime.date.today()
    yesterday = str(today - datetime.timedelta(days=1))
    expired_date = str(today - datetime.timedelta(days=keep_day))

    for name in os.listdir(log_dir):
        fpath = os.path.join(log_dir, name)
        create_date = _get_create_date(fpath)
        if create_date < expired_date:
            _rm_dir_and_file(fpath)
        else:
            if (create_date == yesterday) and (not name.startswith('20')):
                _move_to_yesdir(name, log_dir, dirname=yesterday)


def _get_create_date(fpath):
    time_str = time.ctime(os.path.getctime(fpath))
    time_struct = parser.parse(time_str)
    create_date = time_struct.strftime("%Y-%m-%d")
    return create_date


def _rm_dir_and_file(fpath):
    if os.path.isdir(fpath):
        shutil.rmtree(fpath)
    else:
        os.remove(fpath)


def _move_to_yesdir(name, log_dir, dirname):
    yesdir = os.path.join(log_dir, dirname)
    if not os.path.isdir(yesdir):
        os.mkdir(yesdir)

    old_file = os.path.join(log_dir, name)
    new_file = os.path.join(yesdir, name)
    shutil.move(old_file, new_file)
