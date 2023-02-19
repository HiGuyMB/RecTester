import json
import re

import os
import platform
import subprocess
import traceback
import random
from time import sleep

import requests
from requests.exceptions import ConnectionError


def exec_run_wine(file):
    cmd = [
        'wine',
        os.environ['RUNNER_RECVERIFY_PATH'],
        '--auto',
        os.path.abspath(file)
    ]
    cwd = os.environ['RUNNER_MBG_PATH']

    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode, result.stdout


def exec_run_mac(file):
    if [int(v) for v in platform.mac_ver()[0].split('.')] >= [10, 15, 0]:
        raise RuntimeError("Cannot run Marble Blast natively on macOS >= Catalina")

    cmd = [
        os.environ['RUNNER_RECVERIFY_PATH'],
        '--auto',
        os.path.abspath(file)
    ]
    cwd = os.environ['RUNNER_MBG_PATH']

    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode, result.stdout


def exec_run_windows(file):
    cmd = [
        os.environ['RUNNER_RECVERIFY_PATH'],
        '--auto',
        os.path.abspath(file)
    ]
    cwd = os.environ['RUNNER_MBG_PATH']

    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode, result.stdout


def collapse_escape(text):
    replacements = [
        ("\\n", "\n"),
        ("\\r", "\r"),
        ("\\t", "\t"),
        ("\\'", "'"),
        ("\\\"", "\""),
        ("\\\\", "\\"),
        # Also \c0 etc but we don't care
    ]
    for (f, t) in replacements:
        text = text.replace(f, t)
    return text


def start_run(file):
    if os.environ['RUNNER_OS'] == 'wine':
        code, stdout = exec_run_wine(file)
    elif os.environ['RUNNER_OS'] == 'mac':
        code, stdout = exec_run_mac(file)
    elif os.environ['RUNNER_OS'] == 'windows':
        code, stdout = exec_run_windows(file)
    else:
        raise NotImplementedError("Unknown OS")

    if code != 0:
        return None, stdout.decode()

    stdout_lines = stdout.split(b'\n')
    status = None
    for line in stdout_lines:
        if line.startswith(b'STATUS: '):
            status = line.endswith(b'SUCCESS')
            break

    if status is None:
        return None, stdout.decode()

    # Parse successful run
    '''
    STATUS: SUCCESS
    DEMO: /Users/username/Documents/PycharmProjects/RecTester/uploads/07_Elevator_3.559.rec
    MISSION: marble/data/missions/beginner/elevator.mis
    LEVEL NAME: Elevator
    SCORE TIME: 3559 (00:03.559)
    ELAPSED TIME: 3559 (00:03.559)
    BONUS TIME: 0 (00:00.000)
    GEM COUNT: 0 / 0
    APPROXIMATE FPS: 897.4516
    TOTAL RECORDING TIME: 20742 (00:20.742)
    TOTAL RECORDING FRAMES: 18624
    TOTAL RECORDING FPS: 897.88837
    '''
    info = {}
    for line in stdout_lines[1:]:
        info[line.split(b': ')[0]] = b': '.join(line.split(b': ')[1:])

    if info[b'STATUS'] == b'SUCCESS':
        db_info = {
            'success':      info[b'STATUS'] == b'SUCCESS',
            'mission':      collapse_escape(info[b'MISSION'].decode()),
            'level_name':   collapse_escape(info[b'LEVEL NAME'].decode()),
            'score_time':   int(info[b'SCORE TIME'].split(b' ')[0]),
            'elapsed_time': int(info[b'ELAPSED TIME'].split(b' ')[0]),
            'bonus_time':   int(info[b'BONUS TIME'].split(b' ')[0]),
            'gem_count':    int(info[b'GEM COUNT'].split(b' / ')[0]),
            'gem_total':    int(info[b'GEM COUNT'].split(b' / ')[1]),
            'fps':          float(info[b'APPROXIMATE FPS']),
            'frames_count': int(info[b'TOTAL RECORDING FRAMES']),
            'frames_time':  int(info[b'TOTAL RECORDING TIME'].split(b' ')[0]),
        }

        return db_info, None
    else:
        db_info = {
            'success':      info[b'STATUS'] == b'SUCCESS',
            'mission':      collapse_escape(info[b'MISSION'].decode()),
            'level_name':   collapse_escape(info[b'LEVEL NAME'].decode()),
            'score_time':   0,
            'elapsed_time': 0,
            'bonus_time':   0,
            'gem_count':    0,
            'gem_total':    0,
            'fps':          float(info[b'APPROXIMATE FPS']),
            'frames_count': int(info[b'TOTAL RECORDING FRAMES']),
            'frames_time':  int(info[b'TOTAL RECORDING TIME'].split(b' ')[0]),
        }

        return db_info, None


def respond_to_submission(token, submission):
    download_url = submission['download_url']
    download_path = f'downloads/{submission["file_name"]}'

    if not os.path.exists('downloads'):
        os.mkdir('downloads')
    if os.path.exists(download_path):
        os.unlink(download_path)

    with requests.get(download_url, headers={'Authorization': f'Token {token}'}, stream=True) as req:
        req.raise_for_status()
        with open(download_path, 'wb') as f:
            for chunk in req.iter_content(chunk_size=8192):
                f.write(chunk)

    score, error = start_run(download_path)
    db_os = os.environ['RUNNER_OS']

    db_run = {
        'os': db_os,
        'score': score,
        'error': error
    }

    run_response = requests.post(submission['runs_url'], headers={'Authorization': f'Token {token}'}, json=db_run)
    print(run_response.text)


def main():
    if 'RUNNER_RECVERIFY_PATH' not in os.environ:
        print("Need to set env: $RUNNER_RECVERIFY_PATH")
        return

    if 'RUNNER_MBG_PATH' not in os.environ:
        print("Need to set env: $RUNNER_MBG_PATH")
        return

    if 'RUNNER_OS' not in os.environ:
        print("Need to set env: RUNNER_OS")
        return

    if 'RUNNER_SERVER' not in os.environ:
        print("Need to set env: RUNNER_SERVER")
        return

    if 'RUNNER_USERNAME' not in os.environ:
        print("Need to set env: RUNNER_USERNAME")
        return

    if 'RUNNER_PASSWORD' not in os.environ:
        print("Need to set env: RUNNER_PASSWORD")
        return

    root = f'{os.environ["RUNNER_SERVER"]}/api'
    token_root = f'{os.environ["RUNNER_SERVER"]}/api-auth-token/'

    response = requests.post(token_root, data={
        'username': os.environ['RUNNER_USERNAME'],
        'password': os.environ['RUNNER_PASSWORD']
    })
    print(response.content)
    token_response = json.loads(response.text)
    if 'token' in token_response:
        token = token_response['token']
    else:
        raise Exception('Cannot auth!')

    failed_submissions = []
    while True:
        try:
            submissions_response = requests.get(f'{root}/pending_submissions/{os.environ["RUNNER_OS"]}/',
                                                headers={'Authorization': f'Token {token}'})
            print(submissions_response.content)
            submissions_response = json.loads(submissions_response.text)
        except ConnectionError:
            sleep(random.randint(5, 25))
            continue
        for submission in submissions_response['results']:
            if submission['id'] in failed_submissions:
                continue

            try:
                respond_to_submission(token, submission)
            except:
                traceback.print_exc()
                print(f'Error loading submission {submission["id"]}!')
                failed_submissions.append(submission['id'])
        sleep(random.randint(5, 25))


if __name__ == '__main__':
    main()
