import sys, os
from crontab import CronTab
from app.config import BaseConfig as config

if __name__ == "__main__":
    command = '59 23 * * 1-5'
    
    cron = CronTab(user=True)
    
    
    real_path = os.path.realpath(__file__).split('/')[:-1]
    real_path = "/".join(real_path)

    job = cron.new(
        command='{}/env/bin/python {}/clean_files.py >> {}/clean_files.log 2>> {}/clean_files.log'\
            .format(real_path, real_path, real_path, real_path)
        )
    
    job.setall(command)

    cron.write()