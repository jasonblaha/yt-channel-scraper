import os
import sys


class GetArgs():
	
	def __init__(self, cmd_args=None):
		
		if cmd_args is None:
			cmd_args = sys.argv[1:]
			
		self.channel_url = ''
		self.outfile = None
		self.overwrite_outfile = False
		
		skip_iter = False
		for i in range(len(cmd_args)):
			
			if skip_iter:
				skip_iter = False
				continue
			
			arg = cmd_args[i]
			
			#specify out-file name
			if arg in ['-o', '--outfile']:
				try:
					self.outfile = cmd_args[i+1]
				except IndexError:
					raise IndexError('Insert argument for -o.')
				
				basename, ext = os.path.splitext(self.outfile)
				if ext != '.txt':
					raise ValueError('Please specify filepath for .txt file.')
					
				skip_iter = True
				
			#overwrite out-file
			elif arg in ['-w', '--overwrite-outfile']:
				self.overwrite_outfile = True
			
			#help for args
			elif arg in ['-h', '--help']:
			
				try:
					help = cmd_args[i+1]
				except IndexError:
					help = None
				
				if help in ['o', 'outfile']:
					print(HELP_OUTFILE)
				elif help in ['w', 'overwrite-outfile']:
					print(HELP_OVERWRITE_OUTFILE)
				elif help in ['tp', 'track-progress']:
					print(HELP_TRACK_PROGRESS)
				elif help is None:
					print(HELP_ALL)
				else:
					raise ValueError('Insert valid argument to get help on.')
				
				skip_iter = True
				
			#last argument should be the url
			elif i == len(cmd_args)-1:
				self.channel_url += arg
			
			else:
				raise ValueError('Invalid arguments.')
		
		self.kwargs = {
			'channel_url': self.channel_url,
			'outfile': self.outfile,
			'overwrite_outfile': self.overwrite_outfile,
		}
		

if __name__ == '__main__':
	cmd_args = GetArgs()
	print('Channel URL list: ', cmd_args.channel_url)
	print('Outfile: ', cmd_args.outfile)
	print('Overwrite outfile: ', cmd_args.overwrite_outfile)
	print('kwargs: ', cmd_args.kwargs)
	
	
	#add an args.kwargs object which returns a dict for use as kwargs!!!