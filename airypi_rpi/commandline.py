import sys, argparse
from client import run
from subprocess import call
import os

def cmd_run():
	if os.getuid() != 0:
		print "No superuser permissions"
		print "I/O capabilities are disabled"
		print "To run as superuser. Enter"
		print "$ sudo airypi"

	parser = argparse.ArgumentParser(prog='airypi')
	parser.add_argument('-n', action='store_true', help='Disable auto-update')
	parser.add_argument('-u', nargs=1, help='Connect to specified url')
	parser.add_argument('-s', action='store_true', help='Connect to self')
	parser.add_argument('-l', action='store_true', help='help for -w blah')

	args = parser.parse_args()

	if not args.n:
		result = call(['pip', 'install', '-U','airypi-rpi'])
		if result == 0:
			print 'Checked for upgrade, restarting...'
			args = sys.argv
			args.insert(1, '-n')
			os.execv(args[0], args)
		else:
			print 'Unable to check for upgrade, continuing...'

	if args.u is not None:
		run(url = args.u)
	elif args.s:
		run(url = "http://localhost:8080")
	elif args.l:
		import logging
		logging.basicConfig(level=logging.DEBUG)

	run()

if __name__ == "__main__":
	cmd_run()