from logging.handlers import DEFAULT_TCP_LOGGING_PORT
import os

COMMAND_STOP_SERVER = 'Sending command to stop logging server'

CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s:%(filename)s:%(lineno)d:%(levelname)s:%(message)s'
        },
        'simple': {
            'format': '%(levelname)s: %(message)s'
        },
    },
    'handlers': {
        'console_debug': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'console_info': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'socket': {
            'level': 'DEBUG',
            'class': 'logging.handlers.SocketHandler',
            'host': 'localhost',
            'port': DEFAULT_TCP_LOGGING_PORT,
        },
        'file': {
            'backupCount': 1,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.expanduser(os.path.join('~', 'sublime_system_verilog.log')),
            'formatter': 'verbose',
            'level': 'DEBUG',
            'maxBytes': 1000000,
        },
    },
    'loggers': {
        'sv_socket': {
            'handlers': ['socket'],
            'level': 'DEBUG',
        },
        'sv_console_debug': {
            'handlers': ['console_debug', 'socket'],
            'level': 'DEBUG',
        },
        'log_server': {
            'handlers': ['file', 'console_debug'],
            'level': 'DEBUG'
        }
    }
}