import html
import json
import os
import re
import sys
import requests
import lxml.html
import tqdm

from getargs import GetArgs

session = requests.Session()
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'
session.headers['Accept-Language'] = 'en-GB,en;q=0.5'

YOUTUBE = 'https://www.youtube.com'

NON_CHANNELID_VOCAB = ['https:', '', 'www.youtube.com', 'channel', 'user', 'videos', 'featured', 'playlists', 'community', 'channels', 'about']
NON_CHANNELID_PARTS = ['videos?view=0', 'search?query=', '?view_as=subscriber']


def extract_channel_id(channel_url):
	
	"""
		Extracts the channel id from any given channel url, whether
		it's the homepage or the search query url.
		
		If given a proper url, it's always the 4th part if prefixed 
		with "user" or "channel". This must be verified first, too. If
		this is not the case, then the whole URL will be scanned for
		the channel id.
	"""
	
	parts = re.split('/|\?', channel_url)
	
	#extract channel type, urls for "users" are valid when "user" is omitted
	if 'channel' in parts:
		channel_type = 'channel'
	else:
		channel_type = 'user'
	
	#extract channel id
	for part in parts:
		if part not in NON_CHANNELID_VOCAB:
			for cip in NON_CHANNELID_PARTS:
				if cip in part:
					break
			channel_id = part
			break
	else:
		raise ValueError('Invalid channel url!')
	
	return channel_type, channel_id


def extract_info_from_search(channel_id):

	search_url = 'https://www.youtube.com/results?search_query=' + channel_id
	response = session.get(search_url)
	tree = lxml.html.fromstring(response.text)
	
	#extract video count
	video_count_display = tree.cssselect('.yt-lockup-content .yt-lockup-meta-info')[0].text_content()
	video_count = int(re.sub(',','',video_count_display).split(' ')[0])
	
	#extract channel title
	username = tree.cssselect('.yt-lockup-content .yt-uix-tile-link')[0].get('title')

	return video_count, username


class ChannelUploads():
	
	"""
		Class to fetch a channel's uploads info: url, title, views and 
		publish date. These will be stored in lists and written to a
		text file. The filename can be specified, and by default, the
		stored info will be added to the lists, and newly uploaded
		videos appended to the file. If "overwrite_outfile = True", 
		the file will be wiped clean and all the new info written to
		it. If "track_progress = True" the video amount is first fetched
		via search for the channel and a progress bar is displayed. It's
		recommended to set this to True when fetching entire channels and
		when "overwrite_outfile = True", but set it to False when you're
		just updating for new uploads.
	"""
	
	video_url_lst = []
	video_title_lst = []
	video_pubdate_lst = []
	
	def __init__(self, channel_url, outfile = None, overwrite_outfile = False):
		
		channel_type, channel_id = extract_channel_id(channel_url)
		
		#specify file to write to, default one with channelid
		if not outfile:
			outfile = channel_id + '.txt'
		
		#whether to overwrite this file
		if os.path.isfile(outfile):
			if overwrite_outfile:
				if input(f'Warning! {outfile} already exists. Overwrite? (y/n): ') == 'y':
					open(outfile, 'w', encoding='utf-8').close()
					display_pbar = True
				else:
					display_pbar = False
			else:
				display_pbar = False
		else:
			display_pbar = True
			
		#read in the file
		if os.path.isfile(outfile): 
			with open(outfile, 'r', encoding='utf-8') as f:
				lines = f.readlines()
				if lines:
					urls, titles, pubdates = zip(*[line.strip().split('\t') for line in lines])
					self.video_url_lst += list(urls)
					self.video_title_lst += list(titles)
					self.video_pubdate_lst += list(pubdates)
				
		#fetch channel username and video count before scraping!
		if display_pbar:
			video_count, username = extract_info_from_search(channel_id)
			print(f'\nFetching approximately {video_count} videos for user {username}\n')
			pbar = tqdm.tqdm(total=video_count, desc='Fetching video info')
		else:
			pbar = None
		
		#start
		with open(outfile, 'a', encoding='utf-8') as f:
		
			#load newest -> oldest video urls, stops after 3000 loads
			channel_vids_url = f'https://www.youtube.com/{channel_type}/{channel_id}/videos'
			
			if not self.fetch_and_scroll(channel_vids_url, f, pbar):
				if pbar:
					pbar.close()
				return
				
			#load oldest -> newest video urls
			if pbar.n < video_count:
			
				channel_vids_url += '?view=0&sort=da&flow=grid'
				
				if not self.fetch_and_scroll(channel_vids_url, f, pbar):
					if pbar:
						pbar.close()
					return

	def fetch_and_scroll(self, channel_vids_url, f, pbar):
	
		#get first response
		response = session.get(channel_vids_url)
		tree = lxml.html.fromstring(response.text)
		#extract stuff from links
		n, stop_scraping = self.extract_and_append_links(f, tree)
		if pbar:
			pbar.update(n)
		if stop_scraping: 
			return 
		#extract link to load more videos
		buttons = tree.cssselect('button.yt-uix-button')
		load_more_link = YOUTUBE + list(filter(None,[button.get('data-uix-load-more-href') for button in buttons]))[0]
		
		#effectively scroll down the page by posting AJAX requests
		while True:
			#make request to further reponses
			response = session.post(load_more_link)
			response_dict = json.loads(response.text)
			#extract reponses
			tree = lxml.html.fromstring( response_dict['content_html'] )
			#
			n, stop_scraping = self.extract_and_append_links(f, tree)
			if pbar:
				pbar.update(n)
			if stop_scraping:
				return
			#extract continuation url
			load_more_html = response_dict['load_more_widget_html']
			if load_more_html == '':
				break
			tree = lxml.html.fromstring(load_more_html)
			load_more_link = YOUTUBE + tree.cssselect('button.yt-uix-button')[0].get('data-uix-load-more-href')
			
		return True

	def extract_and_append_links(self, f, tree):
		stop_scraping = False
		#
		n = 0
		links = tree.cssselect('.yt-lockup-content')
		for link in links:
			#extract data from tree
			video_url = YOUTUBE + link.cssselect('.yt-uix-sessionlink')[0].get('href')
			video_title = link.cssselect('.yt-uix-sessionlink')[0].get('title')
			video_views, video_pubdate = link.cssselect('.yt-lockup-meta-info')[0].xpath('li/text()')
			#check if data has already been stored, stop scraping if so
			if video_url in self.video_url_lst:
				stop_scraping = True
				break
			#append data to lists
			self.video_url_lst.append(video_url)
			self.video_title_lst.append(video_title)
			self.video_pubdate_lst.append(video_pubdate)
			n += 1
			#write to f
			f.write(f'{video_url}\t{video_title}\t{video_pubdate}\n')
		#
		return n, stop_scraping
		
if __name__ == '__main__':
	
	cmd_args = GetArgs()
	
	c = ChannelUploads(**cmd_args.kwargs)
	
	
		
		


"""
TO DO:

bypass "view all" !!!: https://www.youtube.com/channel/UC1wUo-29zS7m_Jp-U_xYcFQ/videos
add argparse to write filename, compare two different files

"""
