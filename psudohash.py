#!/bin/python3
#
# Author: Panagiotis Chartas (t3l3machus)
# https://github.com/t3l3machus

import sys
import itertools
import argparse
from argparse import Namespace

try:
	from psudohash_config import *
	has_config = 1
except: has_config = 0

# ----------------( Base Settings )---------------- #
if has_config:
	if opts not in globals(): exit_with_msg("Config file found, but no 'opts' options object defined.")
else: opts = Namespace()

# NOTE: has to be here and like this, because arguments are not parsed if there is a config found
default_opts = Namespace(
	quiet                  = False,
	output                 = 'outfile.txt',
	keywords               = [],
	years                  = [],
	custom_paddings_only   = False,
	append_numbering       = True,
	common_padding         = [],
	common_paddings_before = [],
	common_paddings_after  = [],
	numbering_limit        = 50,
	transformations = {
		'a' : ['@', '4'],
		'b' : ['8'],
		'e' : ['3'],
		'g' : ['9', '6'],
		'i' : ['1', '!'],
		'o' : ['0'],
		's' : ['$', '5'],
		't' : ['7'],
	},
	# The following list is used to create variations of password values and appended years.
	# For example, a passwd value {passwd} will be mutated to "{passwd}{separator}{year}"
	# for each of the symbols included in the list below.
	year_separators = [
		'', '_', '-', '@'
	],
)

# Merge defaults with opts, opts overwritting if it had contents from a config file
opts = Namespace(**{**vars(default_opts), **vars(opts)})
del default_opts

# ---------------- Other globals ---------------- #
COMMON_PADDING_VALUES_FILE = 'common_padding_values.txt'
mutations_cage = []
basic_mutations = []

# Colors
MAIN   = '\033[38;5;50m'
LOGO   = '\033[38;5;41m'
LOGO2  = '\033[38;5;42m'
GREEN  = '\033[38;5;82m'
ORANGE = '\033[0;38;5;214m'
PRPL   = '\033[0;38;5;26m'
PRPL2  = '\033[0;38;5;25m'
RED    = '\033[1;31m'
END    = '\033[0m'
BOLD   = '\033[1m'

# -------------- Arguments & Usage -------------- #

# global because we want to print the help on error
parser = argparse.ArgumentParser(
	formatter_class=argparse.RawTextHelpFormatter,
	epilog='''
Output syntax:
     <permutation> [numbering] ([separator] [year]) [common_paddings]

Usage examples:

  Basic:
     python3 psudohash.py -w example -cpa

  Thorough:
     python3 psudohash.py -w test,example -cpa -an 3 -y 1990-2022
'''
	)

parser.add_argument("-q",   "--quiet",                  action="store_true", default=None, help = "Do not print the banner on startup")
parser.add_argument("-o",   "--output",                 action="store",      default=None, help = "Output filename (default: " + opts.output + ")", metavar='FILENAME')
parser.add_argument("-w",   "--words",                  action="store",      default=None, help = "Comma seperated keywords to mutate", required = True)
parser.add_argument("-y",   "--years",                  action="store",      default=None, help = "Singe OR comma seperated OR range of years to be appended to each word mutation (Example: 2022 OR 1990,2017,2022 OR 1990-2000)")
parser.add_argument("-an",  "--append-numbering",       action="store",      default=None, help = "Append numbering range at the end of each mutation (before appending year or common paddings).\nLEVEL (>=1) represents the minimum number of digits to pad to.\nLEVEL 1 results in: 1,2,3..100\nLEVEL 2 results in: 01,02,03..100 + previous\nLEVEL 3 results in: 001,002,003..100 + previous.\n\n", type = int, metavar='LEVEL')
parser.add_argument("-nl",  "--numbering-limit",        action="store",      default=None, help = "Change max numbering limit value of option -an. Default is 50. Must be used with -an.", type = int, metavar='LIMIT')
parser.add_argument("-ap",  "--append-padding",         action="store",      default=None, help = "Add comma seperated values to common paddings (must be used with -cpb OR -cpa)", metavar='VALUES')
parser.add_argument("-cpb", "--common-paddings-before", action="store_true", default=None, help = "Append common paddings before each mutated word") 
parser.add_argument("-cpa", "--common-paddings-after",  action="store_true", default=None, help = "Append common paddings after each mutated word") 
parser.add_argument("-cpo", "--custom-paddings-only",   action="store_true", default=None, help = "Use only user provided paddings for word mutations (must be used with -ap AND (-cpb OR -cpa))") 
parser.add_argument("-nt",  "--no-transformations",     action="store_true", default=None, help = "Do not generate common character transformations (such as 'a'->'4')") 

def parse_arguments():
	global opts

	args = parser.parse_args()

	# Keywords
	args.keywords = []
	for w in args.words.split(','):
		w = w.strip()
		if w.isdecimal(): exit_with_msg('Unable to mutate digit-only keywords.')
		if w in [None, '']: continue
		args.keywords.append(w)

	# Append numbering
	if args.numbering_limit and not args.append_numbering:
		exit_with_msg('Option -nl must be used with -an.')

	if args.append_numbering:
		if args.append_numbering <= 0:
			exit_with_msg('Numbering level must be > 0.')

	# Create years list		
	years = []
	if args.years:
		def illegal_years_input():
			exit_with_msg('Illegal year(s) input. Acceptable years range: 1000 - 3200.')
		
		if args.years.count(',') == 0 and args.years.count('-') == 0 and args.years.isdecimal() and int(args.years) >= 1000 and int(args.years) <= 3200:
			years.append(str(args.years))
		elif args.years.count(',') > 0:
			for year in args.years.split(','):
				if year.strip() != '' and year.isdecimal() and int(year) >= 1000 and int(year) <= 3200: 
					years.append(year)
				else:
					illegal_years_input()
		elif args.years.count('-') == 1:
			start_year, end_year = args.years.split('-')
			if (start_year.isdecimal() and int(start_year) < int(end_year) and int(start_year) >= 1000) and (end_year.isdecimal() and int(end_year) <= 3200):
				for year in range(int(start_year), int(end_year)+1):
					years.append(str(year))
			else:
				illegal_years_input()
		else:
			illegal_years_input()

	args.years = years

	# Common Padding Values
	if (args.custom_paddings_only or args.append_padding) and not (args.common_paddings_before or args.common_paddings_after):
		exit_with_msg('Options -ap and -cpo must be used with -cpa or -cpb.')
	elif (args.common_paddings_before or args.common_paddings_after) and not args.custom_paddings_only:
		try:
			f = open(COMMON_PADDING_VALUES_FILE, 'r')
			content = f.readlines()
			args.common_paddings = [val.strip() for val in content]
			f.close()
		except:
			exit_with_msg('File "common_padding_values.txt" not found.')
	elif (args.common_paddings_before or args.common_paddings_after) and (args.custom_paddings_only and args.append_padding):
		args.common_paddings = []
	elif not (args.common_paddings_before or args.common_paddings_after):
		args.common_paddings = []
	else:
		exit_with_msg('\nIllegal padding settings.\n')		

	if args.append_padding:
		for val in args.append_padding.split(','):
			if val.strip() != '' and val not in args.common_paddings: 
				args.common_paddings.append(val)

	if (args.common_paddings_before or args.common_paddings_after):
		args.common_paddings = list(set(args.common_paddings))

	# Transformations
	if args.no_transformations: args.transformations = {}

	# Merge args into opts
	args = Namespace(**{k: v for k, v in vars(args).items() if v is not None})
	opts = Namespace(**{**vars(opts), **vars(args)})

def exit_with_msg(msg):
	parser.print_help()
	print(f'\n[{RED}Debug{END}] {msg}\n')
	sys.exit(1)	


# ----------------( Functions )---------------- #
def calculate_transformations(keyword):
	trans_chars = []
	basic_total = 1

	for i, char in enumerate(keyword):
		if char in opts.transformations.keys():
			trans_chars.append(i)
			basic_total *= (len(opts.transformations[char.lower()]) + 2)
		else:
			basic_total = basic_total * 2 if char.isalpha() else basic_total

	return basic_total, trans_chars


def mutate(tc, word):
	global mutations_cage, basic_mutations
	
	trans = opts.transformations[word[tc].lower()]
	limit = len(trans) * len(mutations_cage)
	c = 0
	
	for m in mutations_cage:
		w = list(m)			

		if isinstance(trans, list):
			for tt in trans:
				w[tc] = tt
				transformed = ''.join(w)
				mutations_cage.append(transformed)
				c += 1
		else:
			w[tc] = trans
			transformed = ''.join(w)
			mutations_cage.append(transformed)
			c += 1
		
		if limit == c: break
		
	return mutations_cage
	


def mutations_handler(kword, trans_chars, total, wordlist_handle):
	global mutations_cage, basic_mutations
	
	container = []
	
	for word in basic_mutations:
		mutations_cage = [word.strip()]	
		for tc in trans_chars:
			results = mutate(tc, kword)
		container.append(results)
	
	for m_set in container:
		for m in m_set:
			basic_mutations.append(m)
	
	basic_mutations = list(set(basic_mutations))

	for m in basic_mutations:
		wordlist_handle.write(m + '\n')



def case_mutations_handler(word, mutability, wordlist_handle):
	def mutate_case(word):
		return list(map(''.join, itertools.product(*zip(word.upper(), word.lower()))))
	global basic_mutations

	basic_mutations += mutate_case(word)

	if mutability: return

	basic_mutations = list(set(basic_mutations))
	
	for m in basic_mutations:
		wordlist_handle.write(m + '\n')



def do_append_numbering(wordlist_handle):
	first_cycle = True
	previous_list = []
	lvl = opts.append_numbering
	
	for word in basic_mutations:
		for i in range(1, lvl+1):		
			for k in range(1, opts.numbering_limit + 1):
				if first_cycle:
					wordlist_handle.write(f'{word}{str(k).zfill(i)}\n')
					wordlist.write(f'{word}_{str(k).zfill(i)}\n')
					previous_list.append(f'{word}{str(k).zfill(i)}')
				else:
					if previous_list[k - 1] != f'{word}{str(k).zfill(i)}':
						wordlist_handle.write(f'{word}{str(k).zfill(i)}\n')
						wordlist.write(f'{word}_{str(k).zfill(i)}\n')
						previous_list[k - 1] = f'{word}{str(k).zfill(i)}'

			first_cycle = False
	del previous_list



def mutate_years(wordlist_handle):
	current_mutations = basic_mutations.copy()

	for word in current_mutations:
		for y in opts.years:
			for sep in opts.year_separators:		
				wordlist_handle.write(f'{word}{sep}{y}\n')				
				basic_mutations.append(f'{word}{sep}{y}')
				wordlist_handle.write(f'{word}{sep}{y[2:]}\n')
				basic_mutations.append(f'{word}{sep}{y[2:]}')		

	del current_mutations



def append_paddings_before(wordlist_handle):
	current_mutations = basic_mutations.copy()
	
	for word in current_mutations:
		for val in opts.common_paddings:
			wordlist_handle.write(f'{val}{word}\n')
			if not check_underscore(val, -1):
				wordlist_handle.write(f'{val}_{word}\n')

	del current_mutations



def append_paddings_after(wordlist_handle):
	current_mutations = basic_mutations.copy()

	for word in current_mutations:
		for val in opts.common_paddings:	
			wordlist_handle.write(f'{word}{val}\n')			
			if not check_underscore(val, 0):
				wordlist_handle.write(f'{word}_{val}\n')
						
	del current_mutations



def calculate_output(keyword):
	numbering_count = 0
	numbering_size = 0
	
	# Basic total
	basic_total, _ = calculate_transformations(keyword)
	total = basic_total
	basic_size = total * (len(keyword) + 1)
	size = basic_size
	
	# Words numbering mutations calc
	if opts.append_numbering:
		word_len = len(keyword) + 1
		first_cycle = True
		previous_list = []
		lvl = opts.append_numbering
			
		for w in range(0, total):
			for i in range(1, lvl+1):		
				for k in range(1, opts.numbering_limit + 1):
					n = str(k).zfill(i)
					if first_cycle:					
						numbering_count += 2						
						numbering_size += (word_len * 2) + (len(n) * 2) + 1
						previous_list.append(f'{w}{n}')
						
					else:
						if previous_list[k - 1] != f'{w}{n}':
							numbering_size += (word_len * 2) + (len(n) * 2) + 1
							numbering_count += 2
							previous_list[k - 1] = f'{w}{n}'

				first_cycle = False

		del previous_list
		
	# Adding years mutations calc
	if opts.years:
		patterns = len(opts.year_separators) * 2
		year_chars = 4
		year_short = 2
		years_len = len(opts.years)
		size += (basic_size * patterns * years_len)

		for sep in opts.year_separators:
			size += (basic_total * (year_chars + len(sep)) * years_len)
			size += (basic_total * (year_short  + len(sep)) * years_len)

		total += total * len(opts.years) * patterns
		basic_total = total
		basic_size = size
	
	# Common paddings mutations calc
	patterns = 2
	
	if opts.common_paddings_after or opts.common_paddings_before:
		paddings_len = len(opts.common_paddings)
		pads_wlen_sum = sum([basic_total*len(w) for w in opts.common_paddings])
		_pads_wlen_sum = sum([basic_total*(len(w)+1) for w in opts.common_paddings])
		
		if opts.common_paddings_after and opts.common_paddings_before:		
			size += ((basic_size * patterns * paddings_len) + pads_wlen_sum + _pads_wlen_sum) * 2
			total += (total * len(opts.common_paddings) * 2) * 2
		
		elif opts.common_paddings_after or opts.common_paddings_before:
			size += (basic_size * patterns * paddings_len) + pads_wlen_sum + _pads_wlen_sum
			total += total * len(opts.common_paddings) * 2
	
	return total + numbering_count, size + numbering_size



def check_mutability(word):
	return sum([word.count(k) for k in opts.transformations.keys()])


def check_underscore(word, pos):
	return word[pos] == '_'


def banner():
	padding = '  '

	P = [[' ', '┌', '─', '┐'], [' ', '├', '─', '┘'], [' ', '┴', ' ', ' ']]
	S = [[' ', '┌', '─', '┐'], [' ', '└', '─', '┐'], [' ', '└', '─', '┘']]
	U = [[' ', '┬', ' ', '┬'], [' ', '│', ' ', '│'], [' ', '└', '─', '┘']]
	D = [[' ', '┌', '┬', '┐'], [' ', ' ', '│', '│'], [' ', '─', '┴', '┘']]
	O =	[[' ', '┌', '─', '┐'], [' ', '│', ' ', '│'], [' ', '└', '─', '┘']]
	H = [[' ', '┐', ' ', '┌'], [' ', '├', '╫', '┤'], [' ', '┘', ' ', '└']]	
	A = [[' ', '┌', '─', '┐'], [' ', '├', '─', '┤'], [' ', '┴', ' ', '┴']]
	S = [[' ', '┌', '─', '┐'], [' ', '└', '─', '┐'], [' ', '└', '─', '┘']]
	H = [[' ', '┬', ' ', '┬'], [' ', '├', '─', '┤'], [' ', '┴', ' ', '┴']]

	banner = [P,S,U,D,O,H,A,S,H]
	final = []
	print('\r')
	init_color = 37
	txt_color = init_color
	cl = 0

	for charset in range(0, 3):
		for pos in range(0, len(banner)):
			for i in range(0, len(banner[pos][charset])):
				clr = f'\033[38;5;{txt_color}m'
				char = f'{clr}{banner[pos][charset][i]}'
				final.append(char)
				cl += 1
				txt_color = txt_color + 36 if cl <= 3 else txt_color

			cl = 0

			txt_color = init_color
		init_color += 31

		if charset < 2: final.append('\n   ')

	print(f"   {''.join(final)}")
	print(f'{END}{padding}                        by t3l3machus\n')


def main():
	def ask_for_consent(msg : str) -> bool:
		try: consent = input(msg)
		except KeyboardInterrupt: exit('\n')
		return consent.lower() in ['y', 'yes']

	global basic_mutations, mutations_cage

	if not opts.quiet: banner()

	if len(opts.keywords) == 0: exit_with_msg('No keywords provided, nothing to do.')
	
	# Calculate total words and size of output
	total_count, total_size = 0, 0
	
	for keyword in opts.keywords:
		count_size = calculate_output(keyword.lower())
		total_count += count_size[0]
		total_size  += count_size[1]
	
	size = round(((total_size/1000)/1000), 1) if total_size > 100000 else total_size
	prefix = 'bytes' if total_size <= 100000 else 'MB'
	fsize = f'{size} {prefix}'
	
	print(f'[{MAIN}Info{END}] Calculating output length and size...')

	# Inform user about the output size
	did_agree = ask_for_consent(f'[{ORANGE}Warning{END}] This operation will produce {BOLD}{total_count}{END} words, {BOLD}{fsize}{END}. Are you sure you want to proceed? [y/n]: ')
	if not did_agree: sys.exit(f'\n[{RED}X{END}] Aborting.')

	try: open(opts.output, "w").close()
	except: exit_with_msg(f"Failed to open output file '{opts.output}'.")
	
	with open(opts.output, 'a') as wordlist:		
		for word in opts.keywords:
			print(f'[{GREEN}*{END}] Mutating keyword: {GREEN}{word}{END} ')	
			mutability = check_mutability(word.lower())
					
			# Produce case mutations
			print(f' ├─ Producing character case-based transformations... ')
			case_mutations_handler(word.lower(), mutability, wordlist)
			
			if mutability:
				# Produce char substitution mutations
				print(f' ├─ Mutating word based on commonly used char-to-symbol and char-to-number substitutions... ')
				basic_total, trans_chars = calculate_transformations(word.lower())
				mutations_handler(word, trans_chars, basic_total, wordlist)
			else:
				print(f' ├─ {ORANGE}No character substitution instructions match this word.{END}')

			# Append numbering
			if opts.append_numbering:
				print(f' ├─ Appending numbering to each word mutation... ')
				do_append_numbering(wordlist)
			
			# Handle years
			if opts.years:
				print(f' ├─ Appending year patterns after each word mutation... ')
				mutate_years(wordlist)
			
			# Append common paddings		
			if opts.common_paddings_after or opts.custom_paddings_only:
				print(f' ├─ Appending common paddings after each word mutation... ')
				append_paddings_after(wordlist)
			if opts.common_paddings_before:
				print(f' ├─ Appending common paddings before each word mutation... ')
				append_paddings_before(wordlist)
			
			# Done
			basic_mutations = []
			mutations_cage = []
			print(f' └─ Done!')
	
	print(f'\n[{MAIN}Info{END}] Completed! List saved in {opts.output}\n')
		

if __name__ == '__main__':
	if not has_config: parse_arguments()
	main()
