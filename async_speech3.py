import re
from urllib.parse import quote as urlparse
import time
import os
import grequests
from pydub import AudioSegment

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


completed_urls = []

text = '''
It was so beautiful out on the country! it was summer- the wheat fields were golden, the oats were green, and down
among the green meadows the hay was stacked. There the stork minced about on his red legs, clacking away in Egyptian,
which was the language his mother had taught him. Round about the field and meadow lands rose vast forests,
in which deep lakes lay hidden.
'''


def _to_url_format(sentences):
	for i in range(len(sentences)):
		sentences[i] = urlparse(sentences[i])
	return sentences


def _filter_sentences(sentences):
	sanitized_sentences = []
	for i in range(len(sentences)):
		if '\n' in sentences[i]:
			sentences[i] = sentences[i].replace('\n', '')
		sanitized_sentences.append(sentences[i])
	return sanitized_sentences


def get_sentences(original_text):
	# make sure to add ? to the regular expression
	temp = re.split(r'(?<=\.|!) ', original_text)
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

	sounds.export('./output/' + finished_file_name+'.wav', format='wav')


def _fix_broken_urls_helper(broken_urls):
	if len(urls) == 0:
		# No working urls please check server
		raise Exception()
	if len(broken_urls) == 0:
		return
	temp = []
	for i in range(len(broken_urls)):
		if broken_urls[i].status_code != 200:
			for url in urls:
				if url['url'][:-2] in broken_urls[i].url:
					urls.remove(url)
					break
			temp.append(broken_urls[i].url.split('=')[1])
	redo_urls = []
	if len(temp) != 0:
		for i in range(len(temp)):
			redo_urls.append(urls[i % len(urls)]['url'].format(temp[i]))

	rs = [grequests.get(u, timeout=300) for u in redo_urls]
	t = grequests.map(rs, size=len(urls))
	fix_broken_urls(t)


def fix_broken_urls(t):
	broken_urls = []
	for i in range(len(t)):
		if t[i].status_code != 200:
			for url in urls:
				if url['url'][:-2] in t[i].url:
					urls.remove(url)
					break
			broken_urls.append(t[i].url.split('=')[1])
	if len(broken_urls) != 0:
		_fix_broken_urls_helper(broken_urls)


def main(finished_file_name):
	# current best 401 sec
	# 139.4 sec best
	# currently 201.28 sec
	# text = get_text_from_file('./BeeMovieScript')

	setup_urls(text)
	rs = [grequests.get(u, timeout=300) for u in completed_urls]
	t = grequests.map(rs, size=len(urls))
	requests = []
	for i in range(len(t)):
		requests.append({'request': t[i], 'position': i, 'url': completed_urls[i]})
	print(completed_urls)
	print(requests)

	# fix_broken_urls(t)

	# broken_urls = []
	# for i in range(len(t)):
	# 	if t[i].status_code != 200:
	# 		for url in urls:
	# 			if url[:-2] in t[i].url:
	# 				urls.remove(url)
	# 				break
	# 		broken_urls.append(t[i].url.split('=')[1])
	# redo_urls = []
	# if len(broken_urls) != 0:
	# 	for i in range(len(broken_urls)):
	# 		redo_urls.append(urls[i % len(urls)].format(broken_urls[i]))

	completed_files = []
	for i in range(len(requests)):
		if requests[i]['request'] is not None:
			data = requests[i]['request'].content
			file_location = '{}'.format(i)
			save_file(data, file_location)
			completed_files.append(file_location)
		else:
			print('skipping {}.wav; found None object'.format(i))

	combine_audio_files(completed_files, finished_file_name)


start_time = time.time()
audio_file_name = 'temp'
main(audio_file_name)

print('total time = {}'.format(str(time.time() - start_time)))
