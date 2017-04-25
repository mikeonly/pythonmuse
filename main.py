import time
import os
import logging
import logging.config
import yaml

from server import MuseServer, Saver


def setup_logging(
        default_path='logging.yaml', default_level=logging.INFO,
        env_key='LOG_CFG'):
    """Setup logging configuration
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def main():
    relay = MuseServer(port=5000)
    saver = Saver(name='Saver', savefile='data.csv')
    relay.start()
    saver.start()


# Starts all the processes.
if __name__ == '__main__':
    setup_logging()
    logging.info('Started')
    main()
    logging.info('Main initialized, waiting until done')
    time.sleep(200)
    logging.info('Main finished')
