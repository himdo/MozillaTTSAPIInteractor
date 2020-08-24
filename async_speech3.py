import re
from urllib.parse import quote as urlparse
import time
import os
import grequests
from pydub import AudioSegment
import pickle
import request_object

urls = [
	{
		'url': 'http://10.0.0.247:5002/api/tts?text={}',
		'reboot_url': 'http://10.0.0.247:5000'
	},
	{
		'url': 'http://10.0.0.247:5003/api/tts?text={}',
		'reboot_url': 'http://10.0.0.247:5000'
	},
	{
		'url': 'http://10.0.0.247:5004/api/tts?text={}',
		'reboot_url': 'http://10.0.0.247:5000'
	},
	{
		'url': 'http://10.0.0.247:5005/api/tts?text={}',
		'reboot_url': 'http://10.0.0.247:5000'
	}
]

# TODO increase this when timeouts repeatly occure incase if a sentence is to long
requests_timeout = 300
ping_rest_time = 45
completed_urls = []

# text = '''
# It was so beautiful out on the country! it was summer- the wheat fields were golden, the oats were green, and down
# among the green meadows the hay was stacked. There the stork minced about on his red legs, clacking away in Egyptian,
# which was the language his mother had taught him. Round about the field and meadow lands rose vast forests,
# in which deep lakes lay hidden.
# '''


def _to_url_format(sentences):
	for i in range(len(sentences)):
		sentences[i] = urlparse(sentences[i])
	return sentences


def _filter_sentences(sentences):
	sanitized_sentences = []
	for i in range(len(sentences)):
		if '\n' in sentences[i]:
			sentences[i] = sentences[i].replace('\n', '')
		if '...' in sentences[i]:
			sentences[i] = sentences[i].replace('...', '.')
		if ':' in sentences[i]:
			sentences[i] = sentences[i].replace(':', ' ')
		cutoff_point = 0
		for x in range(len(sentences[i])):
			if '.' == sentences[i][x]:
				cutoff_point += 1
			elif ' ' == sentences[i][x]:
				cutoff_point += 1
			elif '!' == sentences[i][x]:
				cutoff_point += 1
			elif '?' == sentences[i][x]:
				cutoff_point += 1
			elif '-' == sentences[i][x]:
				cutoff_point += 1
			elif ':' == sentences[i][x]:
				cutoff_point += 1
			else:
				break
		sentences[i] = sentences[i][cutoff_point:]
		if len(sentences[i]) > 0:
			sanitized_sentences.append(sentences[i])
	return sanitized_sentences


def get_sentences(original_text):
	# temp = re.split(r'(?<=\.|!) ', original_text)
	temp = re.split(r'(?<=[.!?]).', original_text)
	temp = _filter_sentences(temp)
	temp = _to_url_format(temp)
	temp1 = []
	for t in temp:
		if len(t) != 0:
			temp1.append(t)
	print('{} sentences found'.format(len(temp1)))
	return temp1


def setup_urls(original_text):
	sentences = get_sentences(original_text)
	completed_urls.clear()
	for i in range(len(sentences)):
		completed_urls.append(urls[i % len(urls)]['url'].format(sentences[i]))


def save_file(data, file_name):
	with open(file_name, 'wb') as f:
		f.write(data)


def get_text_from_file(file_location):
	with open(file_location, 'r') as file:
		file_text = file.read().replace('\n', '')
	return file_text


def combine_audio_files(file_locations, finished_file_name):
	sounds = None
	for file in file_locations:
		if sounds is None:
			sounds = AudioSegment.from_file(file)
		else:
			sounds = sounds + AudioSegment.from_file(file)
		os.remove(file)
	if sounds is not None:
		sounds.export('./output/' + finished_file_name+'.wav', format='wav')
	else:
		print('Could not export sounds, it is None')


def fix_broken_urls(requests):
	broken_translated_urls = []
	broken_server_url = []
	repeated_requests_timeout = requests_timeout
	for i in range(len(requests)):
		if requests[i]['request'] is not None:
			if requests[i]['request'].status_code != 200:
				broken_translated_urls.append(requests[i]['request'].url.split('=')[1])
				broken_server_url.append(requests[i]['request'].url.split('=')[0]+'={}')
		else:
			broken_translated_urls.append(requests[i]['url'].split('=')[1])
			broken_server_url.append(requests[i]['url'].split('=')[0]+'={}')

	while len(broken_server_url) != 0:
		if len(broken_translated_urls) != 0:
			print('found broken urls:')
			print(broken_server_url)
			print(broken_translated_urls)

			reboot_server_ips = []
			for i in range(len(broken_server_url)):
				for x in range(len(urls)):
					if broken_server_url[i] == urls[x]['url']:
						if urls[x]['reboot_url'] not in reboot_server_ips:
							reboot_server_ips.append(urls[x]['reboot_url'])
						break
			# if there is broken servers then you will want to ping the restart script on all servers then wait 1 minute
			print('pinging: {}'.format(reboot_server_ips))
			rs = (grequests.get(u, timeout=requests_timeout) for u in reboot_server_ips)
			grequests.map(rs)
			time.sleep(ping_rest_time)

			redo_urls = []
			# after that re assign the urls to re-balance them
			for i in range(len(broken_translated_urls)):
				redo_urls.append(urls[i % len(urls)]['url'].format(broken_translated_urls[i]))
			print('Redoing URLS:')
			print(redo_urls)
			# then request all of them again
			rs = [grequests.get(u, timeout=repeated_requests_timeout) for u in redo_urls]
			r = grequests.map(rs, size=len(urls))

			for i in range(len(requests)):
				if requests[i]['request'] is not None:
					if requests[i]['request'].status_code == 200:
						# this was a valid submission
						continue
				else:
					# if there was a timeout increase the timeout time by 1 minute
					repeated_requests_timeout += 60

				for x in range(len(redo_urls)):
					# check which spot it goes into and replace it
					if requests[i]['url'].split('=')[1] == redo_urls[x].split('=')[1]:
						requests[i]['request'] = r[x]

			# repeat until there are no more broken requests
			broken_translated_urls = []
			broken_server_url = []
			for i in range(len(requests)):
				if requests[i]['request'] is not None:
					if requests[i]['request'].status_code != 200:
						broken_translated_urls.append(requests[i]['request'].url.split('=')[1])
						broken_server_url.append(requests[i]['request'].url.split('=')[0] + '={}')
				else:
					broken_translated_urls.append(requests[i]['url'].split('=')[1])
					broken_server_url.append(requests[i]['url'].split('=')[0] + '={}')
			print(requests)
	return requests


def save_tts_files(requests):
	completed_files = []
	print('saving: {}'.format(requests))
	for i in range(len(requests)):

		if requests[i]['request'] is not None:
			data = requests[i]['request'].content
			file_location = '{}'.format(requests[i]['position'])
			save_file(data, file_location)
			completed_files.append(file_location)
		else:
			print('skipping {} file; found None object'.format(i))
	return completed_files


def main(finished_file_name):
	# current best 401 sec
	# 139.4 sec best
	# currently 201.28 sec
	completed_requests = []
	text = get_text_from_file('./input/BeeMovieScript')

	setup_urls(text)
	rs = [grequests.get(u, timeout=requests_timeout) for u in completed_urls]
	chunk_number = 0

	path = './output/{}.dump'.format(finished_file_name)
	if os.path.exists(path) and os.path.isfile(path):
		pickled_data = None
		with open(path, 'rb') as pickle_file:
			pickled_data = pickle.load(pickle_file)
		if pickled_data is not None:
			if pickled_data['sentenceNum'] == len(completed_urls):
				completed_requests = pickled_data['requests']
				chunk_number = len(completed_requests)
				# TODO add some logic to check the processing url count and dynamically move the chunk number while minimizing
				# the amount of lost requests
				print('valid backup found skipping to chunk: {}'.format(chunk_number))

	while chunk_number*len(urls) < len(rs):
		max_number = min(len(urls), len(rs))
		chunk = rs[chunk_number*len(urls): max_number + max_number * chunk_number]
		t = grequests.map(chunk, size=len(urls))
		requests = []
		for i in range(len(t)):
			new_request = None
			if t[i] is not None:
				new_request = request_object.requestObject(t[i].url, t[i].status_code, t[i].content)
			requests.append(
				{
					'request': new_request,
					'position': i + chunk_number * len(urls),
					'url': completed_urls[i + chunk_number * len(urls)]
				})
		print(completed_urls)
		print(requests)

		requests = fix_broken_urls(requests)
		completed_requests.append(requests)
		pickle_object = {'sentenceNum': len(completed_urls), 'requests': completed_requests}
		with open('./output/{}.dump'.format(finished_file_name), 'wb') as file:
			print('Saving serializable data')
			pickle.dump(pickle_object, file)
		chunk_number += 1
	requests = []
	for i in range(len(completed_requests)):
		for x in range(len(completed_requests[i])):
			requests.append(completed_requests[i][x])
	print(requests)
	completed_files = (save_tts_files(requests))

	combine_audio_files(completed_files, finished_file_name)


start_time = time.time()
audio_file_name = 'BeeMovieScript'
main(audio_file_name)

print('total time = {}'.format(str(time.time() - start_time)))
