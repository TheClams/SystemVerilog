import util
import logger

# shell window of log server will be closed with sublime text
logger.server_stop()
util.deployment(action='uninstall')