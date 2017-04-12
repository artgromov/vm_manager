#!/usr/bin/env python3

import configparser
import logging

import re
import os
import sys
from subprocess import run, PIPE
from datetime import datetime, timedelta
from time import sleep


class LockFile:
    def __init__(self, filename):
        self.filename = os.path.abspath(filename)
        self.pid = os.getpid()

    def __repr__(self):
        return '<LockFile({}), process id {}>'.format(self.filename, self.pid)

    def _get(self):
        try:
            with open(self.filename) as file:
                return int(file.read())
        except FileNotFoundError:
            return None

    def _set(self, pid):
        if isinstance(pid, int):
            with open(self.filename, 'w') as file:
                file.write(str(pid))
        elif pid is None:
            os.remove(self.filename)
        else:
            raise ValueError

    @property
    def free(self):
        return self._get() is None

    @property
    def ours(self):
        return self._get() == self.pid

    def clear(self):
        self._set(None)

    def seize(self):
        self._set(self.pid)

    def acquire(self):
        pid = self._get()
        if pid == self.pid or pid is None:
            self._set(self.pid)
        else:
            raise Locked('owner process id %s' % pid)

    def release(self):
        pid = self._get()
        if pid == self.pid:
            self.clear()
        elif pid is None:
            pass
        else:
            raise Locked('owner process id %s' % pid)


class Locked(Exception):
    pass


def vbox_get_state(vmname):
    result = run('/usr/bin/VBoxManage showvminfo {}'.format(vmname), shell=True, stdout=PIPE, stderr=PIPE)
    stdout = result.stdout.decode('utf-8')
    regex = re.search('State:\s+([\w\s]*) (\(.*?\))?\n', stdout)
    state = regex.group(1)
    logging.debug('vm "{}" in state "{}"'.format(vmname, state))
    return state


def vbox_start(vmname):
    state = vbox_get_state(vmname)
    if state == 'saved' or state == 'powered off':
        logging.info('starting vm')
        run('/usr/bin/VBoxManage startvm {} --type headless'.format(vmname), shell=True, stdout=PIPE, stderr=PIPE)

        if vbox_get_state(vmname) != 'running':
            logging.error('failed to start vm')
            sys.exit(1)

        logging.debug('vm started successfully')

    elif state == 'running':
        logging.debug('vm is already started'.format(vmname))

    else:
        logging.error('incorrect vm state for startvm call "{}"'.format(state))
        sys.exit(1)


def vbox_save(vmname):
    state = vbox_get_state(vmname)
    if state == 'running':
        logging.info('saving vm')
        run('/usr/bin/VBoxManage controlvm {} savestate'.format(vmname), shell=True, stdout=PIPE, stderr=PIPE)
        logging.debug('saving done')

    else:
        logging.error('incorrect vm state for savestate call "{}"'.format(state))
        sys.exit(1)


def wait(timeout, days, hours_start, hours_end, control_lock):
    logging.debug('starting wait sequence')
    timeout = timedelta(minutes=timeout)
    days = {int(i.strip()) for i in days.split(',')}
    hours_start = datetime.strptime(hours_start, '%H:%M').time()
    hours_end = datetime.strptime(hours_end, '%H:%M').time()

    now = datetime.now()
    if now.weekday()+1 in days and hours_start <= now.time() <= hours_end:
        end_of_workday = datetime.combine(now.date(), hours_end)
        end_of_timeout = now + timeout
        logging.debug('end_of_workday: {}, end_of_timeout: {}'.format(end_of_workday, end_of_timeout))

        time_to_save = min(end_of_timeout, end_of_workday)
        logging.info('waiting till {}'.format(time_to_save.time()))

    else:
        time_to_save = now

    while now < time_to_save:
        # need to check control process id
        if not control_lock.ours:
            logging.info('waiting cancelled')
            sys.exit(0)

        sleep(60)

        now = datetime.now()
        minutes_left = (time_to_save - now).seconds // 60
        if minutes_left % 5 == 0:
            logging.debug('waiting {} minutes left'.format(minutes_left))


def rdp_connect(host, port, username, password, options):
    logging.info('connecting to vm')
    run('/usr/bin/xfreerdp  /v:{}:{} /u:{} /p:{} {}'.format(host, port, username, password, options), shell=True, stdout=PIPE, stderr=PIPE)
    logging.debug('rdp session closed')


if __name__ == '__main__':
    SCRIPTDIR = os.path.abspath(os.path.dirname(__file__))
    SCRIPTFILE = __file__
    CONFIGFILE = os.path.join(SCRIPTDIR, 'vm_manager.conf')

    RDP_LOCK = LockFile('/tmp/vm_manager.rdp.lock')
    CONTROL_LOCK = LockFile('/tmp/vm_manager.con.lock')

    config = configparser.ConfigParser()
    config.read(CONFIGFILE)

    logging.basicConfig(level=getattr(logging, config['logging']['level']),
                        format='%(asctime)s %(levelname)s: %(message)s',
                        stream=sys.stdout)

    logging.debug('init done')

    vbox_start(config['virtualbox']['vmname'])

    try:
        logging.debug('locking rdp session')
        RDP_LOCK.acquire()
    except Locked:
        logging.error('rdp session is opened')
        sys.exit(1)
    else:
        logging.debug('seizing control to this process')
        CONTROL_LOCK.seize()
        rdp_connect(config['rdp']['host'],
                    config['rdp']['port'],
                    config['rdp']['username'],
                    config['rdp']['password'],
                    config['rdp']['options'])
        logging.debug('releasing rdp lock')
        RDP_LOCK.release()

    wait(config['save_timeout'].getint('timeout'),
         config['save_timeout']['days'],
         config['save_timeout']['hours_start'],
         config['save_timeout']['hours_end'],
         CONTROL_LOCK)

    vbox_save(config['virtualbox']['vmname'])

    logging.info('exiting')
    sys.exit(0)
