
"""
Execução dos robôs
"""
import argparse
import sys, os
import time
import datetime
from app.config import BaseConfig as config
from app.utils import logger


def __clean_files(dont_clean=['tmp-files.md']):
    now = datetime.datetime.now()

    real_path = os.path.realpath(__file__).split('/')[:-1]
    real_path = "/".join(real_path)
    real_path = "{}/{}".format(real_path, config.UPLOAD_TMP_FOLDER)

    # Varrendo o diretório de arquivos que foram feitos o upload:
    for file in os.listdir(real_path):
        if file in dont_clean: continue

        file_path = '{}/{}'.format(real_path, file)

        stat = os.stat(file_path)

        created_date = None
        
        try:
            created_date = stat.st_birthtime
        except AttributeError:
            created_date = stat.st_mtime

        created_date = datetime.datetime.fromtimestamp(created_date)
        
        if now.date() > created_date.date():
            logger.info("Apagando: {} - {}".format(file_path, created_date))
            os.remove(file_path)
            

def __clean_log_file(file_path:str):
    with open(file_path, 'w') as file:
        file.truncate(0)
        file.close()


if __name__ == "__main__":
    real_path = os.path.realpath(__file__).split('/')[:-1]
    real_path = "/".join(real_path)

    # Limpando o arquivo de log
    __clean_log_file('{}/clean_files.log'.format(real_path))

    # Executando a limpeza dos arquivos expirados
    __clean_files()

