import requests
import time
from tornado import ioloop, httpclient, gen, queues
from urllib import parse
TTS_servers = [
  '10.0.0.247:5002',
  '10.0.0.247:5003',
  '10.0.0.247:5004',
  '10.0.0.247:5005'
]
# This list will contain any of the ips from above whenever the program is waiting on them to complete the request
utilized_server = []

sentences = [
  'baa baa black sheep',
  'Have you any wool',
  'yes sir yes sir',
  'three bags full']

finished_sentences = []


def getServerIP(sentence):
    for ips in TTS_servers:
        if ips not in utilized_server:
            utilized_server.append(ips)
            finished_sentences.append(sentence)
            return ips
    return False


def finishServerIP(selectedIP):
    utilized_server.remove(selectedIP)


def getText():
    for i in range(len(sentences)):
        if sentences[i] not in finished_sentences:
            return i, sentences[i]
    return False


def ioLockedAttempt():
    # Default time is 82.4 seconds
    while True:
        text = getText()
        if text is False:
            break
        ip = getServerIP(text[1])
        if ip is not False:
            url = f'http://{ip}/api/tts?text={text[1]}'
            r = requests.get(url)
            with open('{}.wav'.format(text[0]), 'wb') as f:
                f.write(r.content)
            finishServerIP(ip)
            print('saved wav for {}'.format(url))


async def handle_response(fileNum, ip, url):
    print(url)
    response = await httpclient.AsyncHTTPClient(defaults=dict(request_timeout=180)).fetch(url)
    with open('{}.wav'.format(fileNum), 'wb') as f:
        f.write(response.body)
    print('saved wav for {}'.format(sentences[fileNum]))
    finishServerIP(ip)


def non_ioLockedAttempt():
    # Default time is
    while True:
        text = getText()
        if text is False:
            break
        ip = getServerIP(text[1])
        if ip is not False:
            url = f'http://{ip}/api/tts?text={parse.quote(text[1])}'
            handle_response(text[0], ip, url)
        else:
            time.sleep(1)
            print('no free ips.. sleeping')
    # ioloop.IOLoop.current().start()


start_time = time.time()

io_loop = ioloop.IOLoop.current()
io_loop.run_sync(non_ioLockedAttempt)
io_loop.start()

end_time = time.time()
print('Finished program in {} seconds'.format(end_time-start_time))

